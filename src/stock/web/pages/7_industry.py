"""产业分析页 — 行业排名 + 资金流向 + 板块轮动"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from stock.data.akshare_provider import AKShareProvider
from stock.data.storage import Storage
from stock.analysis.industry import (
    industry_ranking,
    industry_fund_flow_ranking,
    get_industry_chain,
    INDUSTRY_CHAINS,
)

st.set_page_config(page_title="产业分析", page_icon="🏭", layout="wide")
st.title("产业分析")

provider = AKShareProvider()
storage = Storage()
storage.init_tables()

# ---- 行业板块排名 ----
st.subheader("行业板块涨跌排名")

with st.spinner("正在获取行业数据..."):
    try:
        ranking = industry_ranking(provider)
    except Exception as e:
        st.error(f"获取行业数据失败: {e}")
        ranking = None

if ranking is not None and not ranking.empty:
    # 涨跌幅热力图
    top_n = st.slider("显示行业数量", 10, len(ranking), min(30, len(ranking)))
    display = ranking.head(top_n)

    fig = px.bar(
        display,
        x="industry_name",
        y="pct_change",
        color="pct_change",
        color_continuous_scale=["#26a69a", "#ffffff", "#ef5350"],
        color_continuous_midpoint=0,
        labels={"industry_name": "行业", "pct_change": "涨跌幅(%)"},
    )
    fig.update_layout(height=400, xaxis_tickangle=-45, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # 详细表格
    with st.expander("查看完整排名表"):
        st.dataframe(ranking, use_container_width=True, hide_index=True)

# ---- 行业资金流向 ----
st.markdown("---")
st.subheader("行业资金流向")

with st.spinner("正在获取资金流向..."):
    try:
        fund_flow = industry_fund_flow_ranking(provider)
    except Exception as e:
        st.error(f"获取资金流向失败: {e}")
        fund_flow = None

if fund_flow is not None and not fund_flow.empty:
    col1, col2 = st.columns(2)

    with col1:
        st.caption("主力资金净流入 TOP 10")
        top_inflow = fund_flow.head(10)
        fig_in = px.bar(
            top_inflow, x="main_net", y="industry_name",
            orientation="h", color="main_net",
            color_continuous_scale=["#ffffff", "#ef5350"],
            labels={"main_net": "净流入(亿)", "industry_name": "行业"},
        )
        fig_in.update_layout(height=350, showlegend=False, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_in, use_container_width=True)

    with col2:
        st.caption("主力资金净流出 TOP 10")
        top_outflow = fund_flow.tail(10).iloc[::-1]
        fig_out = px.bar(
            top_outflow, x="main_net", y="industry_name",
            orientation="h", color="main_net",
            color_continuous_scale=["#26a69a", "#ffffff"],
            labels={"main_net": "净流出(亿)", "industry_name": "行业"},
        )
        fig_out.update_layout(height=350, showlegend=False, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_out, use_container_width=True)

# ---- 产业链查看 ----
st.markdown("---")
st.subheader("产业链地图")

chain_name = st.selectbox("选择产业链", list(INDUSTRY_CHAINS.keys()))
if chain_name:
    chain = INDUSTRY_CHAINS[chain_name]
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**上游**")
        for ind in chain.get("上游", []):
            st.markdown(f"- {ind}")
    with col2:
        st.markdown("**中游**")
        for ind in chain.get("中游", []):
            st.markdown(f"- {ind}")
    with col3:
        st.markdown("**下游**")
        for ind in chain.get("下游", []):
            st.markdown(f"- {ind}")

# ---- 行业成分股查看 ----
st.markdown("---")
st.subheader("行业成分股")

industry_names = storage.get_all_industry_names()
if industry_names:
    selected_industry = st.selectbox("选择行业", industry_names)
    if selected_industry:
        stocks = storage.get_stocks_in_industry(selected_industry)
        if not stocks.empty:
            st.caption(f"{selected_industry} 共 {len(stocks)} 只成分股")
            st.dataframe(stocks, use_container_width=True, hide_index=True)
        else:
            st.info("暂无成分股数据")
else:
    st.info("暂无行业数据，请先运行行业数据初始化脚本")
