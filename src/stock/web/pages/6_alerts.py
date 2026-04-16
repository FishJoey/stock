"""预警中心"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import streamlit as st

from stock.data.storage import Storage
from stock.alert import AlertEngine, AlertRule, AlertType

st.set_page_config(page_title="预警中心", page_icon="🔔", layout="wide")
st.title("预警中心")

# 使用 session_state 持久化预警引擎
if "alert_engine" not in st.session_state:
    st.session_state.alert_engine = AlertEngine()

engine = st.session_state.alert_engine
storage = Storage()
storage.init_tables()

# 添加预警规则
st.sidebar.header("添加预警规则")
code = st.sidebar.text_input("股票代码", value="600519")

alert_type_map = {
    "价格突破": AlertType.PRICE_ABOVE,
    "价格跌破": AlertType.PRICE_BELOW,
    "成交量异动": AlertType.VOLUME_SURGE,
    "RSI超买": AlertType.RSI_OVERBOUGHT,
    "RSI超卖": AlertType.RSI_OVERSOLD,
    "涨停": AlertType.LIMIT_UP,
    "跌停": AlertType.LIMIT_DOWN,
}

alert_name = st.sidebar.selectbox("预警类型", list(alert_type_map.keys()))
threshold = st.sidebar.number_input("阈值", value=0.0, format="%.2f")

if st.sidebar.button("添加规则"):
    rule = AlertRule(
        code=code,
        alert_type=alert_type_map[alert_name],
        threshold=threshold,
        description=f"{code} {alert_name} {threshold}",
    )
    engine.add_rule(rule)
    st.sidebar.success(f"已添加: {rule.description}")

# 当前规则列表
st.subheader("当前预警规则")
if engine.rules:
    for i, rule in enumerate(engine.rules):
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        col1.write(rule.code)
        col2.write(rule.alert_type.value)
        col3.write(f"阈值: {rule.threshold}")
        if col4.button("删除", key=f"del_{i}"):
            engine.remove_rule(rule.code, rule.alert_type)
            st.rerun()
else:
    st.info("暂无预警规则，请在左侧添加")

# 预警历史
st.subheader("预警历史")
history = engine.get_history()
if history:
    for event in reversed(history):
        st.write(f"**{event.triggered_at:%Y-%m-%d %H:%M}** — {event.message}")
else:
    st.info("暂无触发记录")
