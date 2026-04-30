"""AKShare 数据适配器"""

import os
import socket
import time
from datetime import date
from functools import wraps

import requests
import urllib3.util.connection

# ── 在 import akshare 之前完成所有网络补丁 ──
# AKShare 访问东方财富等国内站点，不应走代理，且 IPv6 不通

# 1) 强制 IPv4
urllib3.util.connection.HAS_IPV6 = False


def _allowed_gai_family():
    return socket.AF_INET


urllib3.util.connection.allowed_gai_family = _allowed_gai_family

# 2) 模块级清除代理环境变量 + 设置 NO_PROXY 兜底
_PROXY_KEYS = [
    "http_proxy", "https_proxy", "all_proxy",
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
]
_saved_proxies: dict[str, str] = {}
for _k in _PROXY_KEYS:
    if _k in os.environ:
        _saved_proxies[_k] = os.environ.pop(_k)
os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") or "*"
os.environ["no_proxy"] = os.environ.get("no_proxy", "") or "*"

# 3) 让 requests.Session 默认不信任系统代理
_orig_session_init = requests.Session.__init__


def _patched_session_init(self, *args, **kwargs):
    _orig_session_init(self, *args, **kwargs)
    self.trust_env = False


requests.Session.__init__ = _patched_session_init  # type: ignore[method-assign]

# ── 补丁完成，安全 import akshare ──
import akshare as ak  # noqa: E402
import pandas as pd  # noqa: E402
from loguru import logger  # noqa: E402

from stock.constants import get_board, get_exchange  # noqa: E402
from stock.data.provider import DataProvider  # noqa: E402


def retry(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器，指数退避"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        raise
                    wait = delay * (2 ** (attempt - 1))
                    logger.warning(f"{func.__name__} 第{attempt}次失败: {e}，{wait:.0f}s 后重试")
                    time.sleep(wait)
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
        """获取日K线数据（东方财富优先，失败时回退到腾讯数据源）"""
        start_str = self._to_date_str(start_date, "20200101")
        end_str = self._to_date_str(end_date, date.today().strftime("%Y%m%d"))

        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_str,
                end_date=end_str,
                adjust=adjust,
            )
        except Exception as e:
            logger.warning(f"{code} 东方财富源失败: {e}，切换腾讯数据源")
            df = None

        if df is not None and not df.empty:
            return self._parse_em_kline(code, df)

        # fallback: 腾讯数据源（字段较少，无换手率/振幅/涨跌额）
        return self._fetch_kline_tx(code, start_str, end_str)

    def _parse_em_kline(self, code: str, df: pd.DataFrame) -> pd.DataFrame:
        """解析东方财富日K线"""
        return pd.DataFrame({
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

    def _fetch_kline_tx(self, code: str, start_str: str, end_str: str) -> pd.DataFrame:
        """腾讯数据源获取日K线"""
        exchange = get_exchange(code)
        symbol = f"{'sh' if exchange == 'SH' else 'sz'}{code}"
        start_fmt = f"{start_str[:4]}-{start_str[4:6]}-{start_str[6:]}"
        end_fmt = f"{end_str[:4]}-{end_str[4:6]}-{end_str[6:]}"

        df = ak.stock_zh_a_hist_tx(
            symbol=symbol, start_date=start_fmt, end_date=end_fmt,
        )
        if df.empty:
            return pd.DataFrame()

        result = pd.DataFrame({
            "code": code,
            "date": pd.to_datetime(df["date"]).dt.date,
            "open": df["open"].astype(float),
            "high": df["high"].astype(float),
            "low": df["low"].astype(float),
            "close": df["close"].astype(float),
            "volume": 0.0,
            "amount": df["amount"].astype(float) if "amount" in df.columns else 0.0,
            "turnover": 0.0,
            "amplitude": 0.0,
            "pct_change": 0.0,
            "change": 0.0,
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

    # ---- 行业板块 ----

    @retry()
    def get_industry_list(self) -> pd.DataFrame:
        """获取东方财富行业板块列表
        Returns: DataFrame [industry_name, code, pct_change, turnover, amount, ...]
        """
        logger.info("正在获取行业板块列表...")
        df = ak.stock_board_industry_name_em()
        result = pd.DataFrame({
            "industry_name": df["板块名称"],
            "board_code": df["板块代码"] if "板块代码" in df.columns else "",
            "pct_change": pd.to_numeric(df.get("涨跌幅", 0), errors="coerce").fillna(0),
            "turnover": pd.to_numeric(df.get("换手率", 0), errors="coerce").fillna(0),
            "amount": pd.to_numeric(df.get("总成交额", 0), errors="coerce").fillna(0),
            "leading_stock": df.get("领涨股票", ""),
        })
        logger.info(f"获取到 {len(result)} 个行业板块")
        return result

    @retry()
    def get_industry_stocks(self, industry_name: str) -> pd.DataFrame:
        """获取行业成分股
        Returns: DataFrame [code, name, industry_name]
        """
        df = ak.stock_board_industry_cons_em(symbol=industry_name)
        result = pd.DataFrame({
            "code": df["代码"].astype(str).str.zfill(6),
            "name": df["名称"],
            "industry_name": industry_name,
        })
        return result

    @retry()
    def get_industry_hist(
        self,
        industry_name: str,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
    ) -> pd.DataFrame:
        """获取行业板块历史K线
        Returns: DataFrame [industry_name, date, close, pct_change, turnover, amount]
        """
        start_str = self._to_date_str(start_date, "20220101")
        end_str = self._to_date_str(end_date, date.today().strftime("%Y%m%d"))

        df = ak.stock_board_industry_hist_em(
            symbol=industry_name, period="日k",
            start_date=start_str, end_date=end_str,
            adjust="",
        )
        if df.empty:
            return pd.DataFrame()

        result = pd.DataFrame({
            "industry_name": industry_name,
            "date": pd.to_datetime(df["日期"]).dt.date,
            "close": pd.to_numeric(df["收盘"], errors="coerce"),
            "pct_change": pd.to_numeric(df["涨跌幅"], errors="coerce"),
            "turnover": pd.to_numeric(df.get("换手率", 0), errors="coerce").fillna(0),
            "amount": pd.to_numeric(df.get("成交额", 0), errors="coerce").fillna(0),
        })
        return result

    # ---- 资金流向 ----

    @retry()
    def get_industry_fund_flow(self) -> pd.DataFrame:
        """获取行业资金流向排名
        Returns: DataFrame [industry_name, main_net, super_large_net, large_net, ...]
        """
        df = ak.stock_fund_flow_industry(symbol="今日")
        result = pd.DataFrame({
            "industry_name": df.iloc[:, 1],
            "pct_change": pd.to_numeric(df.iloc[:, 2], errors="coerce").fillna(0),
            "main_net": pd.to_numeric(df.iloc[:, 3], errors="coerce").fillna(0),
            "super_large_net": pd.to_numeric(df.iloc[:, 5], errors="coerce").fillna(0),
            "large_net": pd.to_numeric(df.iloc[:, 7], errors="coerce").fillna(0),
            "medium_net": pd.to_numeric(df.iloc[:, 9], errors="coerce").fillna(0),
            "small_net": pd.to_numeric(df.iloc[:, 11], errors="coerce").fillna(0),
        })
        return result

    @retry()
    def get_north_fund_flow(self) -> pd.DataFrame:
        """获取北向资金（沪深港通）历史数据
        Returns: DataFrame [date, north_net]
        """
        df = ak.stock_hsgt_fund_flow_summary_em()
        if df.empty:
            return pd.DataFrame()
        result = pd.DataFrame({
            "date": pd.to_datetime(df.iloc[:, 0]).dt.date,
            "north_net": pd.to_numeric(df.iloc[:, 1], errors="coerce").fillna(0),
        })
        return result

    @retry()
    def get_market_fund_flow(self) -> pd.DataFrame:
        """获取大盘资金流向
        Returns: DataFrame [date, main_net, super_large_net, large_net, medium_net, small_net]
        """
        df = ak.stock_market_fund_flow()
        if df.empty:
            return pd.DataFrame()
        result = pd.DataFrame({
            "date": pd.to_datetime(df.iloc[:, 0]).dt.date,
            "main_net": pd.to_numeric(df.iloc[:, 1], errors="coerce").fillna(0),
            "super_large_net": pd.to_numeric(df.iloc[:, 3], errors="coerce").fillna(0),
            "large_net": pd.to_numeric(df.iloc[:, 5], errors="coerce").fillna(0),
            "medium_net": pd.to_numeric(df.iloc[:, 7], errors="coerce").fillna(0),
            "small_net": pd.to_numeric(df.iloc[:, 9], errors="coerce").fillna(0),
        })
        return result

    @retry()
    def get_stock_fund_flow(self, code: str) -> pd.DataFrame:
        """获取个股资金流向
        Returns: DataFrame [date, main_net, super_large_net, large_net, medium_net, small_net]
        """
        df = ak.stock_individual_fund_flow(stock=code, market="")
        if df.empty:
            return pd.DataFrame()
        result = pd.DataFrame({
            "date": pd.to_datetime(df.iloc[:, 0]).dt.date,
            "main_net": pd.to_numeric(df.iloc[:, 1], errors="coerce").fillna(0),
            "super_large_net": pd.to_numeric(df.iloc[:, 3], errors="coerce").fillna(0),
            "large_net": pd.to_numeric(df.iloc[:, 5], errors="coerce").fillna(0),
            "medium_net": pd.to_numeric(df.iloc[:, 7], errors="coerce").fillna(0),
            "small_net": pd.to_numeric(df.iloc[:, 9], errors="coerce").fillna(0),
        })
        return result
