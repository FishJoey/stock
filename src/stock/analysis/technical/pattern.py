"""A股特色指标：涨跌停检测、连板统计"""

import pandas as pd
import numpy as np

from stock.constants import PRICE_LIMIT_MAIN, PRICE_LIMIT_CHINEXT, get_board


def detect_limit(df: pd.DataFrame, code: str = "") -> pd.DataFrame:
    """检测涨跌停

    添加列:
    - is_limit_up: 涨停
    - is_limit_down: 跌停
    """
    result = df.copy()
    board = get_board(code) if code else ""
    limit = float(PRICE_LIMIT_CHINEXT if board in ("创业板", "科创板") else PRICE_LIMIT_MAIN)

    if "pct_change" in result.columns:
        pct = result["pct_change"]
    else:
        pct = result["close"].pct_change() * 100

    # 涨跌停判定：涨跌幅接近限制（允许 0.5% 误差，因为四舍五入）
    threshold = limit * 100 - 0.5
    result["is_limit_up"] = pct >= threshold
    result["is_limit_down"] = pct <= -threshold
    return result


def consecutive_limit_up(df: pd.DataFrame, code: str = "") -> pd.DataFrame:
    """连板统计：计算连续涨停天数"""
    result = detect_limit(df, code) if "is_limit_up" not in df.columns else df.copy()

    count = []
    streak = 0
    for is_up in result["is_limit_up"]:
        if is_up:
            streak += 1
        else:
            streak = 0
        count.append(streak)

    result["limit_up_streak"] = count
    return result
