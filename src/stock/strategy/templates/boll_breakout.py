"""布林带突破策略"""

import pandas as pd

from stock.analysis.technical.trend import boll as calc_boll
from stock.strategy.base import Strategy


class BollBreakoutStrategy(Strategy):
    """布林带突破策略

    价格突破上轨买入，跌破中轨卖出。
    """

    name = "布林带突破"

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        data = calc_boll(df, period=self.period, std_dev=self.std_dev)
        signals = pd.Series(0, index=df.index)

        # 突破上轨买入
        break_up = (data["close"] > data["boll_upper"]) & (data["close"].shift(1) <= data["boll_upper"].shift(1))
        # 跌破中轨卖出
        break_mid = (data["close"] < data["boll_mid"]) & (data["close"].shift(1) >= data["boll_mid"].shift(1))

        signals[break_up] = 1
        signals[break_mid] = -1
        return signals
