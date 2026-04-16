"""个股详情页 — K线图 + 成交量"""

import sys
from datetime import date, timedelta
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# 确保 src 在 path 中
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from stock.data.akshare_provider import AKShareProvider
from stock.data.storage import Storage

st.set_page_config(page_title="个股详情", page_icon="📊", layout="wide")
st.title("个股详情")

# 初始化
storage = Storage()
storage.init_tables()
provider = AKShareProvider()

# 侧边栏：股票搜索
with st.sidebar:
    st.header("股票选择")
    keyword = st.text_input("输入代码或名称", value="600519", placeholder="如 600519 或 茅台")

    # 日期范围
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("开始日期", value=date.today() - timedelta(days=365))
    with col2:
        end = st.date_input("结束日期", value=date.today())

    adjust = st.selectbox("复权方式", ["不复权", "前复权", "后复权"], index=1)
    adjust_map = {"不复权": "", "前复权": "qfq", "后复权": "hfq"}

# 获取数据
code = keyword.strip()
if not code:
    st.info("请输入股票代码或名称")
    st.stop()

# 如果输入的是名称，尝试搜索
if not code.isdigit():
    results = storage.search_stock(code)
    if results.empty:
        st.warning(f"未找到 '{code}'，请先运行 init_db.py 初始化股票列表")
        st.stop()
    code = results.iloc[0]["code"]
    st.sidebar.success(f"匹配到: {results.iloc[0]['name']} ({code})")

with st.spinner("正在获取数据..."):
    df = provider.get_daily_kline(
        code=code,
        start_date=start,
        end_date=end,
        adjust=adjust_map[adjust],
    )

if df.empty:
    st.error(f"未获取到 {code} 的数据")
    st.stop()

# 绘制K线图 + 成交量
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.7, 0.3],
)

# K线
fig.add_trace(
    go.Candlestick(
        x=df["date"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="K线",
        increasing_line_color="#ef5350",   # 红涨
        decreasing_line_color="#26a69a",   # 绿跌
        increasing_fillcolor="#ef5350",
        decreasing_fillcolor="#26a69a",
    ),
    row=1, col=1,
)

# 成交量（红涨绿跌）
# PLACEHOLDER_VOLUME_COLORS
colors = [
    "#ef5350" if row["close"] >= row["open"] else "#26a69a"
    for _, row in df.iterrows()
]

fig.add_trace(
    go.Bar(x=df["date"], y=df["volume"], name="成交量", marker_color=colors),
    row=2, col=1,
)

fig.update_layout(
    height=700,
    xaxis_rangeslider_visible=False,
    showlegend=False,
    margin=dict(l=50, r=20, t=30, b=30),
)
fig.update_xaxes(type="category", nticks=20)
fig.update_yaxes(title_text="价格", row=1, col=1)
fig.update_yaxes(title_text="成交量", row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

# 基本信息
if "pct_change" in df.columns:
    latest = df.iloc[-1]
    cols = st.columns(6)
    cols[0].metric("最新价", f"{latest['close']:.2f}")
    cols[1].metric("涨跌幅", f"{latest['pct_change']:.2f}%")
    cols[2].metric("开盘", f"{latest['open']:.2f}")
    cols[3].metric("最高", f"{latest['high']:.2f}")
    cols[4].metric("最低", f"{latest['low']:.2f}")
    cols[5].metric("成交量", f"{latest['volume']:.0f}")
