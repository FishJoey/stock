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
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        adjust: str = "",
    ) -> pd.DataFrame:
        """获取日K线数据
        Args:
            code: 股票代码，如 "600519"
            start_date: 起始日期，支持 "YYYYMMDD" 字符串或 date 对象
            end_date: 结束日期
            adjust: 复权类型 "" 不复权 / "qfq" 前复权 / "hfq" 后复权
        Returns: DataFrame with columns [code, date, open, high, low, close, volume, amount, ...]
        """

    @abstractmethod
    def get_index_daily(
        self,
        code: str,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
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

    # ---- 行业板块（可选实现，默认返回空 DataFrame）----

    def get_industry_list(self) -> pd.DataFrame:
        """获取行业板块列表"""
        return pd.DataFrame()

    def get_industry_stocks(self, industry_name: str) -> pd.DataFrame:
        """获取行业成分股"""
        return pd.DataFrame()

    def get_all_industry_mappings(self) -> pd.DataFrame:
        """批量获取所有股票的行业映射"""
        return pd.DataFrame()

    def get_industry_hist(
        self,
        industry_name: str,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
    ) -> pd.DataFrame:
        """获取行业板块历史K线"""
        return pd.DataFrame()

    # ---- 资金流向（可选实现，默认返回空 DataFrame）----

    def get_industry_fund_flow(self) -> pd.DataFrame:
        """获取行业资金流向排名"""
        return pd.DataFrame()

    def get_north_fund_flow(self) -> pd.DataFrame:
        """获取北向资金历史数据"""
        return pd.DataFrame()

    def get_market_fund_flow(self) -> pd.DataFrame:
        """获取大盘资金流向"""
        return pd.DataFrame()

    def get_stock_fund_flow(self, code: str) -> pd.DataFrame:
        """获取个股资金流向"""
        return pd.DataFrame()

    # ---- 涨停板（可选实现，默认返回空 DataFrame）----

    def get_limit_up_pool(self, date_str: str) -> pd.DataFrame:
        """涨停股池"""
        return pd.DataFrame()

    def get_limit_up_failed_pool(self, date_str: str) -> pd.DataFrame:
        """炸板股池"""
        return pd.DataFrame()

    def get_limit_down_pool(self, date_str: str) -> pd.DataFrame:
        """跌停股池"""
        return pd.DataFrame()

    def get_previous_limit_up_pool(self, date_str: str) -> pd.DataFrame:
        """昨日涨停股今日表现"""
        return pd.DataFrame()

    # ---- 财务指标（可选实现）----

    def get_financial_indicator(self, code: str) -> pd.DataFrame:
        """获取个股核心财务指标（按季度）
        Returns: DataFrame [date, roe, net_margin, gross_margin, revenue_yoy,
                 profit_yoy, eps, bps, debt_ratio, current_ratio, asset_turnover]
        """
        return pd.DataFrame()
