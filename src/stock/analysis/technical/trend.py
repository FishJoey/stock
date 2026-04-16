"""趋势类指标：MA、EMA、MACD、BOLL、SAR"""

import pandas as pd
import numpy as np


def ma(df: pd.DataFrame, periods: list[int] | None = None, col: str = "close") -> pd.DataFrame:
    """简单移动平均线"""
    periods = periods or [5, 10, 20, 60, 120, 250]
    result = df.copy()
    for p in periods:
        result[f"ma{p}"] = result[col].rolling(window=p).mean()
    return result


def ema(df: pd.DataFrame, periods: list[int] | None = None, col: str = "close") -> pd.DataFrame:
    """指数移动平均线"""
    periods = periods or [5, 10, 20, 60]
    result = df.copy()
    for p in periods:
        result[f"ema{p}"] = result[col].ewm(span=p, adjust=False).mean()
    return result


def macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    col: str = "close",
) -> pd.DataFrame:
    """MACD 指标
    Returns: 添加 macd_dif, macd_dea, macd_hist 列
    """
    result = df.copy()
    ema_fast = result[col].ewm(span=fast, adjust=False).mean()
    ema_slow = result[col].ewm(span=slow, adjust=False).mean()
    result["macd_dif"] = ema_fast - ema_slow
    result["macd_dea"] = result["macd_dif"].ewm(span=signal, adjust=False).mean()
    result["macd_hist"] = 2 * (result["macd_dif"] - result["macd_dea"])
    return result


def boll(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
    col: str = "close",
) -> pd.DataFrame:
    """布林带"""
    result = df.copy()
    result["boll_mid"] = result[col].rolling(window=period).mean()
    rolling_std = result[col].rolling(window=period).std()
    result["boll_upper"] = result["boll_mid"] + std_dev * rolling_std
    result["boll_lower"] = result["boll_mid"] - std_dev * rolling_std
    return result
