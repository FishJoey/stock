"""MACD 策略"""

import pandas as pd

from stock.analysis.technical.trend import macd as calc_macd
from stock.strategy.base import Strategy


class MACDStrategy(Strategy):
    """MACD 金叉死叉策略"""

    name = "MACD交叉"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        data = calc_macd(df, fast=self.fast, slow=self.slow, signal=self.signal)
        signals = pd.Series(0, index=df.index)

        hist = data["macd_hist"]
        # MACD 柱从负转正 -> 买入
        cross_up = (hist > 0) & (hist.shift(1) <= 0)
        # MACD 柱从正转负 -> 卖出
        cross_down = (hist < 0) & (hist.shift(1) >= 0)

        signals[cross_up] = 1
        signals[cross_down] = -1
        return signals
