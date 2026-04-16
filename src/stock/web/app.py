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
    👈 从左侧菜单选择功能页面：

    - **个股详情** — K线图 + 技术指标
    - 更多功能开发中...
    """
)
