"""AKShare 数据适配器"""

from datetime import date

import akshare as ak
import pandas as pd
from loguru import logger

from stock.constants import get_board, get_exchange
from stock.data.provider import DataProvider


class AKShareProvider(DataProvider):
    """基于 AKShare 的免费数据源"""

    def get_stock_list(self) -> pd.DataFrame:
        """获取全部A股股票列表"""
        logger.info("正在从 AKShare 获取股票列表...")
        df = ak.stock_zh_a_spot_em()
        result = pd.DataFrame({
            "code": df["代码"],
            "name": df["名称"],
            "exchange": df["代码"].apply(get_exchange),
            "board": df["代码"].apply(get_board),
            "industry": "",
            "list_date": "",
        })
        logger.info(f"获取到 {len(result)} 只股票")
        return result

    def get_daily_kline(
        self,
        code: str,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        adjust: str = "",
    ) -> pd.DataFrame:
        """获取日K线数据"""
        start_str = (
            start_date.strftime("%Y%m%d") if isinstance(start_date, date)
            else start_date or "20200101"
        )
        end_str = (
            end_date.strftime("%Y%m%d") if isinstance(end_date, date)
            else end_date or date.today().strftime("%Y%m%d")
        )

        try:
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_str,
                end_date=end_str,
                adjust=adjust,
            )
        except Exception as e:
            logger.warning(f"获取 {code} 日K线失败: {e}")
            return pd.DataFrame()

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

    def get_index_daily(
        self,
        code: str,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
    ) -> pd.DataFrame:
        """获取指数日K线"""
        start_str = (
            start_date.strftime("%Y%m%d") if isinstance(start_date, date)
            else start_date or "20200101"
        )
        end_str = (
            end_date.strftime("%Y%m%d") if isinstance(end_date, date)
            else end_date or date.today().strftime("%Y%m%d")
        )

        try:
            df = ak.stock_zh_index_daily_em(symbol=code, start_date=start_str, end_date=end_str)
        except Exception as e:
            logger.warning(f"获取指数 {code} 失败: {e}")
            return pd.DataFrame()

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
