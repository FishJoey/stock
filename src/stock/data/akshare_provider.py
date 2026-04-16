"""AKShare 数据适配器"""

import os
import socket
import time
from datetime import date
from functools import wraps

import akshare as ak
import pandas as pd
import urllib3.util.connection
from loguru import logger

from stock.constants import get_board, get_exchange
from stock.data.provider import DataProvider

# 强制 requests/urllib3 使用 IPv4
# 东方财富的 IPv6 在部分网络环境下不通，导致连接被重置
urllib3.util.connection.HAS_IPV6 = False
_orig_create_connection = urllib3.util.connection.create_connection


def _ipv4_only_create_connection(address, *args, **kwargs):
    """强制使用 IPv4 连接"""
    kwargs["socket_options"] = kwargs.get("socket_options", [])
    return _orig_create_connection(address, *args, **kwargs, source_address=None)


# Monkey-patch: 让所有连接只走 AF_INET (IPv4)
_orig_allowed = urllib3.util.connection.allowed_gai_family


def _allowed_gai_family():
    return socket.AF_INET


urllib3.util.connection.allowed_gai_family = _allowed_gai_family

# AKShare 访问的是国内网站（东方财富等），不应走代理
_PROXY_KEYS = [
    "http_proxy", "https_proxy", "all_proxy",
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
]


def _clear_proxy():
    """临时清除代理环境变量，避免 requests 走代理连不上国内站点"""
    saved = {}
    for key in _PROXY_KEYS:
        if key in os.environ:
            saved[key] = os.environ.pop(key)
    return saved


def _restore_proxy(saved: dict):
    """恢复代理环境变量"""
    for key, val in saved.items():
        os.environ[key] = val


def retry(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器，指数退避"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            saved = _clear_proxy()
            try:
                for attempt in range(1, max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_retries:
                            raise
                        wait = delay * (2 ** (attempt - 1))
                        logger.warning(f"{func.__name__} 第{attempt}次失败: {e}，{wait:.0f}s 后重试")
                        time.sleep(wait)
            finally:
                _restore_proxy(saved)
        return wrapper
    return decorator


class AKShareProvider(DataProvider):
    """基于 AKShare 的免费数据源"""

    @retry()
    def get_stock_list(self) -> pd.DataFrame:
        """获取全部A股股票列表（轻量接口，只拉代码+名称）"""
        logger.info("正在从 AKShare 获取股票列表...")
        df = ak.stock_info_a_code_name()
        result = pd.DataFrame({
            "code": df["code"].astype(str).str.zfill(6),
            "name": df["name"],
        })
        result["exchange"] = result["code"].apply(get_exchange)
        result["board"] = result["code"].apply(get_board)
        result["industry"] = ""
        result["list_date"] = ""
        logger.info(f"获取到 {len(result)} 只股票")
        return result

    @retry()
    def get_daily_kline(
        self,
        code: str,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        adjust: str = "",
    ) -> pd.DataFrame:
        """获取日K线数据"""
        start_str = self._to_date_str(start_date, "20200101")
        end_str = self._to_date_str(end_date, date.today().strftime("%Y%m%d"))

        df = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_str,
            end_date=end_str,
            adjust=adjust,
        )

        if df.empty:
            return pd.DataFrame()

        result = pd.DataFrame({
            "code": code,
            "date": pd.to_datetime(df["日期"]).dt.date,
            "open": df["开盘"].astype(float),
            "high": df["最高"].astype(float),
            "low": df["最低"].astype(float),
            "close": df["收盘"].astype(float),
            "volume": df["成交量"].astype(float),
            "amount": df["成交额"].astype(float),
            "turnover": df["换手率"].astype(float) if "换手率" in df.columns else 0.0,
            "amplitude": df["振幅"].astype(float) if "振幅" in df.columns else 0.0,
            "pct_change": df["涨跌幅"].astype(float) if "涨跌幅" in df.columns else 0.0,
            "change": df["涨跌额"].astype(float) if "涨跌额" in df.columns else 0.0,
        })
        return result

    @retry()
    def get_index_daily(
        self,
        code: str,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
    ) -> pd.DataFrame:
        """获取指数日K线"""
        start_str = self._to_date_str(start_date, "20200101")
        end_str = self._to_date_str(end_date, date.today().strftime("%Y%m%d"))

        df = ak.stock_zh_index_daily_em(symbol=code, start_date=start_str, end_date=end_str)

        if df.empty:
            return pd.DataFrame()

        result = pd.DataFrame({
            "code": code,
            "date": pd.to_datetime(df["date"]).dt.date,
            "open": df["open"].astype(float),
            "high": df["high"].astype(float),
            "low": df["low"].astype(float),
            "close": df["close"].astype(float),
            "volume": df["volume"].astype(float) if "volume" in df.columns else 0.0,
            "amount": df["amount"].astype(float) if "amount" in df.columns else 0.0,
        })
        return result

    @staticmethod
    def _to_date_str(d: str | date | None, default: str) -> str:
        """统一转为 YYYYMMDD 格式"""
        if d is None:
            return default
        if isinstance(d, date):
            return d.strftime("%Y%m%d")
        return d.replace("-", "")
