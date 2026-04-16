"""选股筛选器"""

import pandas as pd
from dataclasses import dataclass, field


@dataclass
class FilterCondition:
    """筛选条件"""
    column: str          # 列名
    operator: str        # gt / lt / gte / lte / eq / between
    value: float | tuple = 0.0  # 阈值，between 时为 (min, max)


@dataclass
class ScreenerConfig:
    """选股器配置"""
    conditions: list[FilterCondition] = field(default_factory=list)
    sort_by: str = ""
    ascending: bool = False
    limit: int = 50


def apply_filter(df: pd.DataFrame, condition: FilterCondition) -> pd.DataFrame:
    """应用单个筛选条件"""
    col = condition.column
    if col not in df.columns:
        return df

    op = condition.operator
    val = condition.value

    if op == "gt":
        return df[df[col] > val]
    elif op == "lt":
        return df[df[col] < val]
    elif op == "gte":
        return df[df[col] >= val]
    elif op == "lte":
        return df[df[col] <= val]
    elif op == "eq":
        return df[df[col] == val]
    elif op == "between" and isinstance(val, tuple) and len(val) == 2:
        return df[df[col].between(val[0], val[1])]
    return df


def screen(df: pd.DataFrame, config: ScreenerConfig) -> pd.DataFrame:
    """执行选股筛选

    Args:
        df: 包含所有股票数据的 DataFrame（需要预先计算好指标列）
        config: 筛选配置

    Returns:
        筛选后的 DataFrame
    """
    result = df.copy()

    for cond in config.conditions:
        result = apply_filter(result, cond)
        if result.empty:
            return result

    if config.sort_by and config.sort_by in result.columns:
        result = result.sort_values(config.sort_by, ascending=config.ascending)

    if config.limit > 0:
        result = result.head(config.limit)

    return result.reset_index(drop=True)


# 预置策略
def low_pe_high_roe(df: pd.DataFrame, pe_max: float = 20, roe_min: float = 15) -> pd.DataFrame:
    """低估值高盈利选股: PE < pe_max 且 ROE > roe_min"""
    config = ScreenerConfig(
        conditions=[
            FilterCondition("pe_ttm", "gt", 0),
            FilterCondition("pe_ttm", "lt", pe_max),
            FilterCondition("roe", "gt", roe_min),
        ],
        sort_by="roe",
        ascending=False,
    )
    return screen(df, config)


def high_growth(df: pd.DataFrame, growth_min: float = 20) -> pd.DataFrame:
    """高成长选股: 营收增速和利润增速均 > growth_min%"""
    config = ScreenerConfig(
        conditions=[
            FilterCondition("revenue_yoy", "gt", growth_min),
            FilterCondition("profit_yoy", "gt", growth_min),
        ],
        sort_by="profit_yoy",
        ascending=False,
    )
    return screen(df, config)


def dividend_yield(df: pd.DataFrame, yield_min: float = 3.0) -> pd.DataFrame:
    """高股息选股: 股息率 > yield_min%"""
    config = ScreenerConfig(
        conditions=[
            FilterCondition("dividend_yield", "gt", yield_min),
        ],
        sort_by="dividend_yield",
        ascending=False,
    )
    return screen(df, config)
