"""量价类指标：OBV、VWAP、量比、换手率分析"""

import pandas as pd
import numpy as np


def obv(df: pd.DataFrame) -> pd.DataFrame:
    """OBV 能量潮"""
    result = df.copy()
    direction = np.sign(result["close"].diff())
    direction.iloc[0] = 0
    result["obv"] = (direction * result["volume"]).cumsum()
    return result


def vwap(df: pd.DataFrame) -> pd.DataFrame:
    """VWAP 成交量加权平均价（日内累计）"""
    result = df.copy()
    tp = (result["high"] + result["low"] + result["close"]) / 3
    result["vwap"] = (tp * result["volume"]).cumsum() / result["volume"].cumsum()
    return result


def volume_ratio(df: pd.DataFrame, period: int = 5) -> pd.DataFrame:
    """量比 = 当日成交量 / 过去N日平均成交量"""
    result = df.copy()
    avg_vol = result["volume"].rolling(window=period).mean().shift(1)
    result["volume_ratio"] = result["volume"] / avg_vol
    return result


def volume_ma(df: pd.DataFrame, periods: list[int] | None = None) -> pd.DataFrame:
    """成交量均线"""
    periods = periods or [5, 10, 20]
    result = df.copy()
    for p in periods:
        result[f"vol_ma{p}"] = result["volume"].rolling(window=p).mean()
    return result


def atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """ATR 平均真实波幅"""
    result = df.copy()
    high_low = result["high"] - result["low"]
    high_close = (result["high"] - result["close"].shift(1)).abs()
    low_close = (result["low"] - result["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    result["atr"] = tr.rolling(window=period).mean()
    return result
