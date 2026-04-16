"""选股器"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st

from stock.data.storage import Storage
from stock.analysis.fundamental.screener import (
    screen, ScreenerConfig, FilterCondition,
)

st.set_page_config(page_title="选股器", page_icon="🔍", layout="wide")
st.title("选股器")

storage = Storage()
storage.init_tables()

# 加载股票列表
stock_list = storage.get_stock_list()
if stock_list.empty:
    st.warning("股票列表为空，请先运行 init_db.py")
    st.stop()

st.sidebar.header("筛选条件")

# 板块筛选
boards = ["全部"] + sorted(stock_list["board"].unique().tolist())
board = st.sidebar.selectbox("板块", boards)

# 自定义条件
st.sidebar.subheader("自定义条件")
conditions = []

col_options = {
    "涨跌幅 (pct_change)": "pct_change",
    "换手率 (turnover)": "turnover",
    "振幅 (amplitude)": "amplitude",
    "成交量 (volume)": "volume",
    "PE (pe_ttm)": "pe_ttm",
    "ROE (roe)": "roe",
    "净利率 (net_margin)": "net_margin",
}

num_conditions = st.sidebar.number_input("条件数量", 0, 5, 0)
for i in range(num_conditions):
    with st.sidebar.expander(f"条件 {i + 1}"):
        col_name = st.selectbox(f"指标", list(col_options.keys()), key=f"col_{i}")
        op = st.selectbox(f"运算符", ["大于", "小于", "介于"], key=f"op_{i}")
        op_map = {"大于": "gt", "小于": "lt", "介于": "between"}

        if op == "介于":
            v1 = st.number_input("最小值", key=f"v1_{i}")
            v2 = st.number_input("最大值", key=f"v2_{i}")
            conditions.append(FilterCondition(col_options[col_name], "between", (v1, v2)))
        else:
            val = st.number_input("阈值", key=f"val_{i}")
            conditions.append(FilterCondition(col_options[col_name], op_map[op], val))

# 排序
sort_col = st.sidebar.selectbox("排序字段", ["code", "name"] + list(col_options.values()))
ascending = st.sidebar.checkbox("升序", value=False)
limit = st.sidebar.slider("显示数量", 10, 200, 50)

# 执行筛选
if st.sidebar.button("开始筛选", type="primary"):
    result = stock_list.copy()

    if board != "全部":
        result = result[result["board"] == board]

    if conditions:
        config = ScreenerConfig(
            conditions=conditions,
            sort_by=sort_col,
            ascending=ascending,
            limit=limit,
        )
        result = screen(result, config)
    else:
        result = result.sort_values(sort_col, ascending=ascending).head(limit)

    st.subheader(f"筛选结果: {len(result)} 只")
    st.dataframe(result, use_container_width=True, hide_index=True)
else:
    st.info("设置筛选条件后点击「开始筛选」")
    st.subheader(f"全部股票: {len(stock_list)} 只")
    st.dataframe(stock_list.head(50), use_container_width=True, hide_index=True)
