"""策略实验室"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from stock.data import get_provider
from stock.data.storage import Storage
from stock.strategy.backtest import backtest
from stock.strategy.templates import (
    MACrossStrategy, MACDStrategy, BollBreakoutStrategy, KDJRSIStrategy,
)

st.set_page_config(page_title="策略实验室", page_icon="🧪", layout="wide")
st.title("策略实验室")

storage = Storage()
storage.init_tables()
provider = get_provider()

# 侧边栏配置
with st.sidebar:
    st.header("回测配置")
    code = st.text_input("股票代码", value="600519")

    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("开始", value=date.today() - timedelta(days=365))
    with col2:
        end = st.date_input("结束", value=date.today())

    strategy_name = st.selectbox("策略", ["均线交叉", "MACD交叉", "布林带突破", "KDJ+RSI"])

    # 策略参数
    st.subheader("策略参数")
    if strategy_name == "均线交叉":
        fast = st.number_input("短期均线", 3, 60, 5)
        slow = st.number_input("长期均线", 10, 250, 20)
        strategy = MACrossStrategy(fast=fast, slow=slow)
    elif strategy_name == "MACD交叉":
        fast = st.number_input("快线", 5, 30, 12)
        slow = st.number_input("慢线", 15, 50, 26)
        signal = st.number_input("信号线", 5, 20, 9)
        strategy = MACDStrategy(fast=fast, slow=slow, signal=signal)
    elif strategy_name == "布林带突破":
        period = st.number_input("周期", 10, 50, 20)
        std_dev = st.number_input("标准差倍数", 1.0, 3.0, 2.0, 0.1)
        strategy = BollBreakoutStrategy(period=period, std_dev=std_dev)
    else:
        kdj_n = st.number_input("KDJ周期", 5, 20, 9)
        rsi_p = st.number_input("RSI周期", 5, 30, 12)
        strategy = KDJRSIStrategy(kdj_n=kdj_n, rsi_period=rsi_p)

    initial_capital = st.number_input("初始资金", 100000, 10000000, 1000000, 100000)
    run = st.button("运行回测", type="primary")

if not run:
    st.info("配置参数后点击「运行回测」")
    st.stop()

# 获取数据
with st.spinner("获取数据中..."):
    try:
        df = provider.get_daily_kline(code, start_date=start, end_date=end, adjust="qfq")
    except Exception:
        df = storage.get_daily_kline(code)

if df.empty:
    st.error(f"未获取到 {code} 的数据")
    st.stop()

# 运行回测
with st.spinner("回测中..."):
    result = backtest(df, strategy, initial_capital=initial_capital, code=code)

metrics = result["metrics"]
trades = result["trades"]

# 绩效指标
st.subheader("绩效指标")
cols = st.columns(5)
cols[0].metric("总收益", f"{metrics['total_return']:.2f}%")
cols[1].metric("年化收益", f"{metrics['annual_return']:.2f}%")
cols[2].metric("最大回撤", f"{metrics['max_drawdown']:.2f}%")
cols[3].metric("夏普比率", f"{metrics['sharpe_ratio']:.3f}")
cols[4].metric("胜率", f"{metrics['win_rate']:.1f}%")

col1, col2 = st.columns(2)
with col1:
    st.metric("Sortino", f"{metrics['sortino_ratio']:.3f}")
with col2:
    st.metric("盈亏比", f"{metrics['profit_factor']:.3f}")

# 净值曲线
st.subheader("净值曲线")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=df["date"],
    y=result["equity_curve"],
    name="策略净值",
    line=dict(color="#1f77b4"),
))
fig.add_hline(y=1.0, line_dash="dash", line_color="gray", annotation_text="初始净值")
fig.update_layout(height=400, margin=dict(l=50, r=20, t=30, b=30), yaxis_title="净值")
st.plotly_chart(fig, use_container_width=True)

# 交易记录
if not trades.empty:
    st.subheader(f"交易记录 ({len(trades)} 笔)")
    st.dataframe(trades, use_container_width=True, hide_index=True)
else:
    st.info("本次回测无交易信号触发")
