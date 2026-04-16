"""均线交叉策略"""

import pandas as pd

from stock.analysis.technical.trend import ma
from stock.strategy.base import Strategy


class MACrossStrategy(Strategy):
    """双均线交叉策略

    金叉买入（短期均线上穿长期均线），死叉卖出。
    """

    name = "均线交叉"

    def __init__(self, fast: int = 5, slow: int = 20):
        self.fast = fast
        self.slow = slow

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        data = ma(df, periods=[self.fast, self.slow])
        fast_col = f"ma{self.fast}"
        slow_col = f"ma{self.slow}"

        signals = pd.Series(0, index=df.index)

        # 金叉: 短期从下方穿越长期
        cross_up = (data[fast_col] > data[slow_col]) & (data[fast_col].shift(1) <= data[slow_col].shift(1))
        # 死叉: 短期从上方穿越长期
        cross_down = (data[fast_col] < data[slow_col]) & (data[fast_col].shift(1) >= data[slow_col].shift(1))

        signals[cross_up] = 1
        signals[cross_down] = -1
        return signals
