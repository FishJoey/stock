"""策略基类"""

from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """策略抽象基类

    所有策略实现 generate_signals 方法，返回买卖信号 Series:
    - 1: 买入信号
    - -1: 卖出信号
    - 0: 无操作
    """

    name: str = "BaseStrategy"

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """生成交易信号

        Args:
            df: 包含 OHLCV 和所需指标的 DataFrame

        Returns:
            pd.Series: 信号序列，index 与 df 一致
        """

    def __repr__(self):
        return f"<{self.name}>"
