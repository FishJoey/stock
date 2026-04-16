"""绩效指标计算"""

import numpy as np
import pandas as pd


def calc_metrics(
    equity_curve: pd.Series,
    benchmark: pd.Series | None = None,
    risk_free_rate: float = 0.03,
    trading_days: int = 242,
) -> dict:
    """计算策略绩效指标

    Args:
        equity_curve: 净值曲线（从1.0开始）
        benchmark: 基准净值曲线（可选）
        risk_free_rate: 无风险利率（年化）
        trading_days: 年交易日数

    Returns:
        dict: 绩效指标
    """
    returns = equity_curve.pct_change().dropna()

    total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    n_days = len(equity_curve)
    annual_return = (1 + total_return) ** (trading_days / max(n_days, 1)) - 1

    # 最大回撤
    cummax = equity_curve.cummax()
    drawdown = (equity_curve - cummax) / cummax
    max_drawdown = drawdown.min()
    # 最大回撤持续期
    dd_end = drawdown.idxmin()
    pre_dd = equity_curve.loc[:dd_end]
    dd_start = pre_dd.idxmax() if len(pre_dd) > 1 else dd_end

    # 夏普比率
    excess_returns = returns - risk_free_rate / trading_days
    sharpe = np.sqrt(trading_days) * excess_returns.mean() / returns.std() if returns.std() > 0 else 0

    # Sortino 比率
    downside = returns[returns < 0]
    downside_std = downside.std() if len(downside) > 0 else 0
    sortino = np.sqrt(trading_days) * excess_returns.mean() / downside_std if downside_std > 0 else 0

    # Calmar 比率
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

    # 胜率
    winning_days = (returns > 0).sum()
    total_days = len(returns)
    win_rate = winning_days / total_days if total_days > 0 else 0

    # 盈亏比
    avg_win = returns[returns > 0].mean() if winning_days > 0 else 0
    avg_loss = abs(returns[returns < 0].mean()) if (returns < 0).sum() > 0 else 0
    profit_factor = avg_win / avg_loss if avg_loss > 0 else float("inf")

    result = {
        "total_return": round(total_return * 100, 2),
        "annual_return": round(annual_return * 100, 2),
        "max_drawdown": round(max_drawdown * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "sortino_ratio": round(sortino, 3),
        "calmar_ratio": round(calmar, 3),
        "win_rate": round(win_rate * 100, 2),
        "profit_factor": round(profit_factor, 3),
        "trading_days": n_days,
    }

    # 基准对比
    if benchmark is not None and len(benchmark) == len(equity_curve):
        bench_return = benchmark.iloc[-1] / benchmark.iloc[0] - 1
        result["benchmark_return"] = round(bench_return * 100, 2)
        result["excess_return"] = round((total_return - bench_return) * 100, 2)

    return result
