"""数据提供者抽象接口"""

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class DataProvider(ABC):
    """数据源适配器基类，所有数据源实现此接口"""

    @abstractmethod
    def get_stock_list(self) -> pd.DataFrame:
        """获取全部A股股票列表
        Returns: DataFrame with columns [code, name, exchange, board, industry, list_date]
        """

    @abstractmethod
    def get_daily_kline(
        self,
        code: str,
        start_date: str = "",
        end_date: str = "",
        adjust: str = "",
    ) -> pd.DataFrame:
        """获取日K线数据
        Args:
            code: 股票代码，如 "600519"
            start_date: 起始日期 "YYYYMMDD"
            end_date: 结束日期 "YYYYMMDD"
            adjust: 复权类型 "" 不复权 / "qfq" 前复权 / "hfq" 后复权
        Returns: DataFrame with columns [code, date, open, high, low, close, volume, amount, ...]
        """

    @abstractmethod
    def get_index_daily(
        self,
        code: str,
        start_date: str = "",
        end_date: str = "",
    ) -> pd.DataFrame:
        """获取指数日K线"""

    def get_minute_kline(
        self,
        code: str,
        period: str = "5",
        adjust: str = "",
    ) -> pd.DataFrame:
        """获取分钟K线（可选实现）"""
        raise NotImplementedError
