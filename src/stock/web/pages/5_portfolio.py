"""持仓管理"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="持仓管理", page_icon="💼", layout="wide")
st.title("持仓管理")

# 使用 session_state 持久化持仓数据
if "portfolio" not in st.session_state:
    st.session_state.portfolio = pd.DataFrame(columns=["code", "name", "shares", "cost_price", "current_price"])

portfolio = st.session_state.portfolio

# 添加持仓
st.sidebar.header("添加持仓")
with st.sidebar.form("add_holding"):
    code = st.text_input("股票代码")
    name = st.text_input("股票名称")
    shares = st.number_input("持仓数量（股）", min_value=0, step=100)
    cost_price = st.number_input("成本价", min_value=0.0, format="%.2f")
    current_price = st.number_input("现价", min_value=0.0, format="%.2f")
    submitted = st.form_submit_button("添加")

    if submitted and code and shares > 0:
        new_row = pd.DataFrame([{
            "code": code,
            "name": name,
            "shares": shares,
            "cost_price": cost_price,
            "current_price": current_price,
        }])
        st.session_state.portfolio = pd.concat([portfolio, new_row], ignore_index=True)
        st.rerun()

# 显示持仓
if portfolio.empty:
    st.info("暂无持仓，请在左侧添加")
    st.stop()

# 计算盈亏
display = portfolio.copy()
display["market_value"] = display["shares"] * display["current_price"]
display["cost_total"] = display["shares"] * display["cost_price"]
display["pnl"] = display["market_value"] - display["cost_total"]
display["pnl_pct"] = (display["pnl"] / display["cost_total"] * 100).round(2)

# 汇总
total_value = display["market_value"].sum()
total_cost = display["cost_total"].sum()
total_pnl = total_value - total_cost
total_pnl_pct = total_pnl / total_cost * 100 if total_cost > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("总市值", f"¥{total_value:,.0f}")
col2.metric("总盈亏", f"¥{total_pnl:,.0f}", f"{total_pnl_pct:+.2f}%")
col3.metric("持仓数", f"{len(display)} 只")

# 持仓表格
st.subheader("持仓明细")
st.dataframe(
    display[["code", "name", "shares", "cost_price", "current_price", "market_value", "pnl", "pnl_pct"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "pnl": st.column_config.NumberColumn("盈亏", format="%.0f"),
        "pnl_pct": st.column_config.NumberColumn("盈亏%", format="%.2f%%"),
        "market_value": st.column_config.NumberColumn("市值", format="%.0f"),
    },
)

# 配置饼图
st.subheader("持仓分布")
fig = px.pie(display, values="market_value", names="name", hole=0.4)
fig.update_layout(height=400, margin=dict(l=20, r=20, t=30, b=20))
st.plotly_chart(fig, use_container_width=True)

# 清空按钮
if st.button("清空持仓"):
    st.session_state.portfolio = pd.DataFrame(columns=["code", "name", "shares", "cost_price", "current_price"])
    st.rerun()
