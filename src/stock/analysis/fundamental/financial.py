"""基本面财务分析"""

import pandas as pd
import numpy as np


def calc_valuation(df: pd.DataFrame) -> pd.DataFrame:
    """计算估值指标

    输入 DataFrame 需包含: close, eps, total_equity, revenue, net_profit, total_assets
    """
    result = df.copy()

    if "eps" in result.columns and "close" in result.columns:
        result["pe_ttm"] = result["close"] / result["eps"].replace(0, np.nan)

    if "total_equity" in result.columns and "close" in result.columns:
        # 假设 total_equity 是净资产总额，需要每股净资产
        if "bps" in result.columns:
            result["pb"] = result["close"] / result["bps"].replace(0, np.nan)

    if "revenue" in result.columns and "close" in result.columns and "total_shares" in result.columns:
        rps = result["revenue"] / result["total_shares"].replace(0, np.nan)
        result["ps"] = result["close"] / rps.replace(0, np.nan)

    return result


def calc_profitability(df: pd.DataFrame) -> pd.DataFrame:
    """计算盈利能力指标"""
    result = df.copy()

    if "net_profit" in result.columns and "revenue" in result.columns:
        result["net_margin"] = result["net_profit"] / result["revenue"].replace(0, np.nan) * 100

    if "gross_profit" in result.columns and "revenue" in result.columns:
        result["gross_margin"] = result["gross_profit"] / result["revenue"].replace(0, np.nan) * 100

    if "net_profit" in result.columns and "total_equity" in result.columns:
        result["roe"] = result["net_profit"] / result["total_equity"].replace(0, np.nan) * 100

    if "net_profit" in result.columns and "total_assets" in result.columns:
        result["roa"] = result["net_profit"] / result["total_assets"].replace(0, np.nan) * 100

    return result


def calc_growth(df: pd.DataFrame) -> pd.DataFrame:
    """计算成长性指标（需要按时间排序的多期数据）"""
    result = df.copy()

    if "revenue" in result.columns:
        result["revenue_yoy"] = result["revenue"].pct_change() * 100

    if "net_profit" in result.columns:
        result["profit_yoy"] = result["net_profit"].pct_change() * 100

    if "eps" in result.columns:
        result["eps_yoy"] = result["eps"].pct_change() * 100

    return result


def dupont_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """杜邦分析: ROE = 净利率 × 资产周转率 × 权益乘数"""
    result = df.copy()

    has_cols = all(c in result.columns for c in ["net_profit", "revenue", "total_assets", "total_equity"])
    if not has_cols:
        return result

    revenue = result["revenue"].replace(0, np.nan)
    total_assets = result["total_assets"].replace(0, np.nan)
    total_equity = result["total_equity"].replace(0, np.nan)

    result["dupont_net_margin"] = result["net_profit"] / revenue * 100
    result["dupont_asset_turnover"] = revenue / total_assets
    result["dupont_equity_multiplier"] = total_assets / total_equity
    result["dupont_roe"] = (
        result["dupont_net_margin"] / 100
        * result["dupont_asset_turnover"]
        * result["dupont_equity_multiplier"]
        * 100
    )
    return result


def financial_health_score(df: pd.DataFrame) -> pd.DataFrame:
    """财务健康评分（简化版，0-100分）

    评分维度:
    - 盈利能力 (ROE, 净利率)
    - 偿债能力 (资产负债率)
    - 成长性 (营收增速, 利润增速)
    """
    result = df.copy()
    score = pd.Series(0.0, index=result.index)
    count = pd.Series(0, index=result.index)

    # ROE 评分: >15% 满分, 0-15% 线性
    if "roe" in result.columns:
        roe_score = (result["roe"].clip(0, 20) / 20 * 100).fillna(0)
        score += roe_score
        count += 1

    # 净利率评分
    if "net_margin" in result.columns:
        margin_score = (result["net_margin"].clip(0, 30) / 30 * 100).fillna(0)
        score += margin_score
        count += 1

    # 资产负债率评分: 越低越好, <50% 满分
    if "total_assets" in result.columns and "total_equity" in result.columns:
        debt_ratio = (1 - result["total_equity"] / result["total_assets"].replace(0, np.nan)) * 100
        debt_score = ((100 - debt_ratio.clip(0, 100)) / 100 * 100).fillna(0)
        score += debt_score
        count += 1

    # 营收增速评分
    if "revenue_yoy" in result.columns:
        growth_score = (result["revenue_yoy"].clip(-20, 50) + 20) / 70 * 100
        score += growth_score.fillna(0)
        count += 1

    result["health_score"] = (score / count.replace(0, 1)).round(1)
    return result
