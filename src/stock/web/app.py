"""Streamlit 应用入口"""

import streamlit as st

st.set_page_config(
    page_title="A股分析平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("A股综合分析平台")
st.markdown("---")
st.markdown(
    """
    从左侧菜单选择功能页面:

    - **个股详情** — K线图 + 成交量 + 技术指标
    - **大盘总览** — 主要指数走势对比
    - **选股器** — 多条件筛选选股
    - **策略实验室** — 策略回测 + 绩效分析
    - **持仓管理** — 持仓盈亏 + 配置分布
    - **预警中心** — 价格/指标/异动预警
    """
)
