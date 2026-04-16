"""震荡类指标：KDJ、RSI、CCI、Williams %R"""

import pandas as pd
import numpy as np


def kdj(
    df: pd.DataFrame,
    n: int = 9,
    m1: int = 3,
    m2: int = 3,
) -> pd.DataFrame:
    """KDJ 随机指标（国内标准参数 9,3,3）"""
    result = df.copy()
    low_n = result["low"].rolling(window=n).min()
    high_n = result["high"].rolling(window=n).max()

    rsv = (result["close"] - low_n) / (high_n - low_n) * 100
    rsv = rsv.fillna(50)

    k = pd.Series(np.nan, index=result.index, dtype=float)
    d = pd.Series(np.nan, index=result.index, dtype=float)

    # 初始值
    k.iloc[n - 1] = 50.0
    d.iloc[n - 1] = 50.0

    for i in range(n, len(result)):
        k.iloc[i] = (m1 - 1) / m1 * k.iloc[i - 1] + 1 / m1 * rsv.iloc[i]
        d.iloc[i] = (m2 - 1) / m2 * d.iloc[i - 1] + 1 / m2 * k.iloc[i]

    result["kdj_k"] = k
    result["kdj_d"] = d
    result["kdj_j"] = 3 * k - 2 * d
    return result


def rsi(
    df: pd.DataFrame,
    periods: list[int] | None = None,
    col: str = "close",
) -> pd.DataFrame:
    """RSI 相对强弱指标"""
    periods = periods or [6, 12, 24]
    result = df.copy()
    delta = result[col].diff()

    for p in periods:
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        avg_gain = gain.ewm(alpha=1 / p, min_periods=p, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / p, min_periods=p, adjust=False).mean()
        rs = avg_gain / avg_loss
        result[f"rsi{p}"] = 100 - 100 / (1 + rs)

    return result


def cci(
    df: pd.DataFrame,
    period: int = 14,
) -> pd.DataFrame:
    """CCI 顺势指标"""
    result = df.copy()
    tp = (result["high"] + result["low"] + result["close"]) / 3
    ma_tp = tp.rolling(window=period).mean()
    md = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    result["cci"] = (tp - ma_tp) / (0.015 * md)
    return result


def williams_r(
    df: pd.DataFrame,
    period: int = 14,
) -> pd.DataFrame:
    """威廉指标 %R"""
    result = df.copy()
    high_n = result["high"].rolling(window=period).max()
    low_n = result["low"].rolling(window=period).min()
    result["wr"] = (high_n - result["close"]) / (high_n - low_n) * -100
    return result
