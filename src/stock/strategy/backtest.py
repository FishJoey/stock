"""回测引擎

A股特性:
- T+1: 今日信号，次日开盘执行
- 佣金: 万2.5 双向，最低5元
- 印花税: 千分之0.5 仅卖出
- 涨跌停: 涨停无法买入，跌停无法卖出
"""

import pandas as pd
import numpy as np

from stock.constants import (
    COMMISSION_RATE, COMMISSION_MIN, STAMP_TAX_RATE,
    get_price_limit, PRICE_LIMIT_MAIN,
)
from stock.strategy.base import Strategy
from stock.strategy.metrics import calc_metrics


def _calc_commission(amount: float) -> float:
    """计算佣金"""
    fee = abs(amount) * float(COMMISSION_RATE)
    return max(fee, float(COMMISSION_MIN))


def _calc_sell_tax(amount: float) -> float:
    """计算卖出印花税"""
    return abs(amount) * float(STAMP_TAX_RATE)


def backtest(
    df: pd.DataFrame,
    strategy: Strategy,
    initial_capital: float = 1_000_000,
    slippage: float = 0.001,
    code: str = "",
) -> dict:
    """执行回测

    Args:
        df: K线数据（需包含 open/high/low/close/volume，以及策略所需指标）
        strategy: 策略实例
        initial_capital: 初始资金
        slippage: 滑点比例
        code: 股票代码（用于判断涨跌停幅度）

    Returns:
        dict: {
            "equity_curve": pd.Series,  # 净值曲线
            "trades": pd.DataFrame,     # 交易记录
            "metrics": dict,            # 绩效指标
            "signals": pd.Series,       # 原始信号
        }
    """
    signals = strategy.generate_signals(df)
    price_limit = float(get_price_limit(code)) if code else float(PRICE_LIMIT_MAIN)

    cash = initial_capital
    position = 0  # 持仓股数
    equity = []
    trades = []

    for i in range(len(df)):
        row = df.iloc[i]
        current_price = row["close"]

        # T+1: 用前一天的信号，今天开盘执行
        if i > 0:
            prev_signal = signals.iloc[i - 1]
            exec_price = row["open"] * (1 + slippage if prev_signal > 0 else 1 - slippage)

            # 检查涨跌停
            if i >= 2:
                prev_close = df.iloc[i - 1]["close"]
                pct = (row["open"] - prev_close) / prev_close
                is_limit_up = pct >= price_limit - 0.005
                is_limit_down = pct <= -(price_limit - 0.005)
            else:
                is_limit_up = False
                is_limit_down = False

            # 买入
            if prev_signal > 0 and position == 0 and not is_limit_up:
                shares = int(cash * 0.95 / exec_price / 100) * 100  # 整手买入，留5%余量
                if shares > 0:
                    cost = shares * exec_price
                    commission = _calc_commission(cost)
                    cash -= cost + commission
                    position = shares
                    trades.append({
                        "date": row["date"],
                        "action": "buy",
                        "price": exec_price,
                        "shares": shares,
                        "cost": cost + commission,
                    })

            # 卖出
            elif prev_signal < 0 and position > 0 and not is_limit_down:
                revenue = position * exec_price
                commission = _calc_commission(revenue)
                tax = _calc_sell_tax(revenue)
                cash += revenue - commission - tax
                trades.append({
                    "date": row["date"],
                    "action": "sell",
                    "price": exec_price,
                    "shares": position,
                    "revenue": revenue - commission - tax,
                })
                position = 0

        total = cash + position * current_price
        equity.append(total)

    equity_series = pd.Series(equity, index=df.index)
    equity_curve = equity_series / initial_capital  # 归一化为净值

    trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
    metrics = calc_metrics(equity_curve)

    return {
        "equity_curve": equity_curve,
        "trades": trades_df,
        "metrics": metrics,
        "signals": signals,
    }
