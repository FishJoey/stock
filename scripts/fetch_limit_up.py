"""涨停板全量池子每日拉取 + 情绪汇总"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd
from loguru import logger

from stock.data import get_provider
from stock.data.storage import Storage

LIMIT_UP_COLS = [
    "date", "code", "name", "pct_change", "price", "amount",
    "float_mv", "turnover", "seal_amount", "first_seal_time",
    "last_seal_time", "failed_count", "streak", "industry",
]

LIMIT_UP_FAILED_COLS = [
    "date", "code", "name", "pct_change", "price", "limit_price",
    "amount", "float_mv", "turnover", "first_seal_time",
    "failed_count", "amplitude", "industry",
]

LIMIT_DOWN_COLS = [
    "date", "code", "name", "pct_change", "price", "amount",
    "float_mv", "turnover", "seal_amount", "consecutive",
    "open_count", "industry",
]

PREVIOUS_LIMIT_UP_COLS = [
    "date", "code", "name", "pct_change", "price", "limit_price",
    "amount", "float_mv", "turnover", "amplitude",
    "prev_seal_time", "prev_streak", "industry",
]


def _normalize(df: pd.DataFrame, cols: list[str], date_val) -> pd.DataFrame:
    """补齐缺失列、设置 date、按列顺序截取"""
    if df.empty:
        return df
    df = df.copy()
    df["date"] = date_val
    for c in cols:
        if c not in df.columns:
            df[c] = None
    return df[cols]


def fetch_all_limit_pools(date_str: str | None = None):
    """拉取四个池子 + 计算情绪汇总"""
    storage = Storage()
    provider = get_provider()
    storage.init_tables()

    if not date_str:
        date_str = date.today().strftime("%Y%m%d")

    date_val = pd.to_datetime(date_str).date()
    logger.info(f"拉取涨停板全量数据: {date_str}")

    # 1. 涨停池
    df_up = provider.get_limit_up_pool(date_str)
    if not df_up.empty:
        df_up = _normalize(df_up, LIMIT_UP_COLS, date_val)
        storage.upsert_limit_up_pool(df_up)
        logger.info(f"涨停股池: {len(df_up)} 只")

    # 2. 炸板池
    df_failed = provider.get_limit_up_failed_pool(date_str)
    if not df_failed.empty:
        df_failed = _normalize(df_failed, LIMIT_UP_FAILED_COLS, date_val)
        storage.upsert_limit_up_failed_pool(df_failed)
        logger.info(f"炸板股池: {len(df_failed)} 只")

    # 3. 跌停池
    df_down = provider.get_limit_down_pool(date_str)
    if not df_down.empty:
        df_down = _normalize(df_down, LIMIT_DOWN_COLS, date_val)
        storage.upsert_limit_down_pool(df_down)
        logger.info(f"跌停股池: {len(df_down)} 只")

    # 4. 昨日涨停池
    df_prev = provider.get_previous_limit_up_pool(date_str)
    if not df_prev.empty:
        df_prev = _normalize(df_prev, PREVIOUS_LIMIT_UP_COLS, date_val)
        storage.upsert_previous_limit_up_pool(df_prev)
        logger.info(f"昨日涨停池: {len(df_prev)} 只")

    # 5. 计算情绪汇总
    n_up = len(df_up)
    n_failed = len(df_failed)
    n_down = len(df_down)
    seal_rate = n_up / (n_up + n_failed) * 100 if (n_up + n_failed) > 0 else 0
    promote_rate = 0.0
    if not df_prev.empty and "pct_change" in df_prev.columns:
        promoted = df_prev[df_prev["pct_change"] >= 9.5]
        promote_rate = len(promoted) / len(df_prev) * 100
    avg_streak = df_up["streak"].mean() if not df_up.empty and "streak" in df_up.columns else 0
    top_industry = ""
    if not df_up.empty and "industry" in df_up.columns:
        vc = df_up["industry"].value_counts()
        if not vc.empty:
            top_industry = vc.index[0]

    sentiment = pd.DataFrame([{
        "date": date_val,
        "limit_up_count": n_up,
        "limit_up_failed_count": n_failed,
        "limit_down_count": n_down,
        "seal_rate": round(seal_rate, 2),
        "promote_rate": round(promote_rate, 2),
        "avg_streak": round(avg_streak, 2),
        "top_industry": top_industry,
    }])
    storage.upsert_market_sentiment(sentiment)
    logger.info(f"情绪汇总: 涨停{n_up} 炸板{n_failed} 跌停{n_down} 封板率{seal_rate:.1f}%")

    if n_up == 0 and n_failed == 0 and n_down == 0:
        logger.warning(f"所有池子为空: {date_str}（可能非交易日）")

    storage.close()


def fetch_limit_up_pool(date_str: str | None = None):
    """向后兼容入口"""
    fetch_all_limit_pools(date_str)


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else None
    fetch_all_limit_pools(d)
