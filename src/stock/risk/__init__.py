"""风险管理"""

import numpy as np
import pandas as pd


# ---- 仓位管理 ----

def fixed_fraction(capital: float, risk_per_trade: float = 0.02, stop_loss_pct: float = 0.05) -> float:
    """固定比例仓位: 每笔交易最大亏损 = capital * risk_per_trade"""
    return capital * risk_per_trade / stop_loss_pct


def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """凯利公式: f = (bp - q) / b
    b = avg_win / avg_loss, p = win_rate, q = 1 - p
    返回建议仓位比例 (0~1)
    """
    if avg_loss == 0 or win_rate <= 0:
        return 0
    b = avg_win / avg_loss
    q = 1 - win_rate
    f = (b * win_rate - q) / b
    return max(0, min(f, 1))  # 限制在 0~1


def equal_weight(capital: float, n_stocks: int) -> float:
    """等权重: 每只股票分配相同资金"""
    if n_stocks <= 0:
        return 0
    return capital / n_stocks


# ---- 止损 ----

def fixed_stop_loss(entry_price: float, pct: float = 0.05) -> float:
    """固定百分比止损价"""
    return entry_price * (1 - pct)


def trailing_stop(high_since_entry: float, pct: float = 0.08) -> float:
    """移动止损: 从最高点回撤 pct 触发"""
    return high_since_entry * (1 - pct)


def atr_stop_loss(entry_price: float, atr_value: float, multiplier: float = 2.0) -> float:
    """ATR 止损: entry - multiplier * ATR"""
    return entry_price - multiplier * atr_value


# ---- 组合风控 ----

def check_position_limit(
    holdings: dict[str, float],
    total_capital: float,
    max_single: float = 0.2,
    max_sector: dict[str, float] | None = None,
) -> list[str]:
    """检查持仓限制，返回违规项列表

    Args:
        holdings: {股票代码: 持仓市值}
        total_capital: 总资产
        max_single: 单只股票最大仓位比例
        max_sector: {行业: 最大仓位比例}
    """
    warnings = []
    for code, value in holdings.items():
        ratio = value / total_capital if total_capital > 0 else 0
        if ratio > max_single:
            warnings.append(f"{code} 仓位 {ratio:.1%} 超过限制 {max_single:.1%}")
    return warnings


def calc_portfolio_var(
    returns: pd.DataFrame,
    weights: np.ndarray,
    confidence: float = 0.95,
) -> float:
    """计算组合 VaR (历史模拟法)

    Args:
        returns: 各股票收益率 DataFrame
        weights: 权重数组
        confidence: 置信度

    Returns:
        VaR 值（负数表示亏损）
    """
    portfolio_returns = (returns * weights).sum(axis=1)
    var = np.percentile(portfolio_returns, (1 - confidence) * 100)
    return float(var)
