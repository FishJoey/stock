"""大盘总览"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from stock.data.akshare_provider import AKShareProvider
from stock.data.storage import Storage
from stock.constants import INDEX_CODES

st.set_page_config(page_title="大盘总览", page_icon="📈", layout="wide")
st.title("大盘总览")

storage = Storage()
storage.init_tables()
provider = AKShareProvider()

# 指数选择
selected = st.multiselect(
    "选择指数",
    list(INDEX_CODES.keys()),
    default=["上证指数", "沪深300", "创业板指"],
)

if not selected:
    st.info("请选择至少一个指数")
    st.stop()

# 获取数据并绘图
cols = st.columns(len(selected))
for i, name in enumerate(selected):
    code = INDEX_CODES[name]
    try:
        df = provider.get_index_daily(code)
    except Exception:
        df = storage.get_index_daily(code)

    if df.empty:
        cols[i].warning(f"{name} 暂无数据")
        continue

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    pct = (latest["close"] - prev["close"]) / prev["close"] * 100

    with cols[i]:
        st.metric(name, f"{latest['close']:.2f}", f"{pct:+.2f}%")

# 叠加走势图
fig = go.Figure()
for name in selected:
    code = INDEX_CODES[name]
    try:
        df = provider.get_index_daily(code)
    except Exception:
        df = storage.get_index_daily(code)

    if df.empty:
        continue

    # 归一化为百分比变化
    base = df["close"].iloc[0]
    normalized = (df["close"] / base - 1) * 100

    fig.add_trace(go.Scatter(
        x=df["date"],
        y=normalized,
        name=name,
        mode="lines",
    ))

fig.update_layout(
    height=500,
    yaxis_title="涨跌幅 %",
    hovermode="x unified",
    margin=dict(l=50, r=20, t=30, b=30),
)
st.plotly_chart(fig, use_container_width=True)
