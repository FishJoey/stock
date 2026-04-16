"""KDJ + RSI 组合策略"""

import pandas as pd

from stock.analysis.technical.oscillator import kdj as calc_kdj, rsi as calc_rsi
from stock.strategy.base import Strategy


class KDJRSIStrategy(Strategy):
    """KDJ + RSI 组合策略

    买入: KDJ 金叉 (K 上穿 D) 且 RSI < 超卖线
    卖出: KDJ 死叉 (K 下穿 D) 且 RSI > 超买线
    """

    name = "KDJ+RSI"

    def __init__(
        self,
        kdj_n: int = 9,
        rsi_period: int = 12,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
    ):
        self.kdj_n = kdj_n
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        data = calc_kdj(df, n=self.kdj_n)
        data = calc_rsi(data, periods=[self.rsi_period])

        rsi_col = f"rsi{self.rsi_period}"
        signals = pd.Series(0, index=df.index)

        k, d = data["kdj_k"], data["kdj_d"]
        # KDJ 金叉 + RSI 超卖区
        buy = (k > d) & (k.shift(1) <= d.shift(1)) & (data[rsi_col] < self.rsi_oversold)
        # KDJ 死叉 + RSI 超买区
        sell = (k < d) & (k.shift(1) >= d.shift(1)) & (data[rsi_col] > self.rsi_overbought)

        signals[buy] = 1
        signals[sell] = -1
        return signals
