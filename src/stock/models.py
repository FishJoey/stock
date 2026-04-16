"""核心数据模型"""

from datetime import date, datetime

from pydantic import BaseModel


class Stock(BaseModel):
    """股票基本信息"""
    code: str  # 6位代码，如 600519
    name: str
    exchange: str  # SH / SZ
    board: str  # 主板/创业板/科创板/中小板
    industry: str = ""
    list_date: date | None = None
    is_st: bool = False


class OHLCV(BaseModel):
    """日K线数据"""
    code: str
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float  # 成交量（手）
    amount: float  # 成交额（元）
    turnover: float = 0.0  # 换手率 %
    amplitude: float = 0.0  # 振幅 %
    pct_change: float = 0.0  # 涨跌幅 %
    change: float = 0.0  # 涨跌额


class FinancialReport(BaseModel):
    """财务报表摘要"""
    code: str
    report_date: date  # 报告期
    publish_date: date | None = None
    revenue: float = 0.0  # 营业收入
    net_profit: float = 0.0  # 净利润
    total_assets: float = 0.0  # 总资产
    total_equity: float = 0.0  # 净资产
    eps: float = 0.0  # 每股收益
    roe: float = 0.0  # 净资产收益率 %
    pe_ttm: float = 0.0  # 市盈率(TTM)
    pb: float = 0.0  # 市净率


class WatchItem(BaseModel):
    """自选股"""
    code: str
    name: str
    group: str = "默认"
    note: str = ""
    added_at: datetime | None = None
