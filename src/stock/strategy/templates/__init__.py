"""内置策略模板"""

from stock.strategy.templates.ma_cross import MACrossStrategy
from stock.strategy.templates.macd_strategy import MACDStrategy
from stock.strategy.templates.boll_breakout import BollBreakoutStrategy
from stock.strategy.templates.kdj_rsi import KDJRSIStrategy

__all__ = ["MACrossStrategy", "MACDStrategy", "BollBreakoutStrategy", "KDJRSIStrategy"]
