"""涨停板分析"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pandas as pd
import plotly.express as px
import streamlit as st

from stock.data import get_provider
from stock.data.storage import Storage

st.set_page_config(page_title="涨停板分析", page_icon="🔥", layout="wide")
st.title("涨停板分析")

provider = get_provider()

# ---- 日期选择 ----
col_date, col_btn = st.columns([2, 1])
with col_date:
    sel_date = st.date_input("选择日期", value=date.today(), max_value=date.today())
with col_btn:
    st.write("")
    st.write("")
    fetch = st.button("获取数据", type="primary", use_container_width=True)

date_str = sel_date.strftime("%Y%m%d")

if not fetch and "limit_data" not in st.session_state:
    st.info("选择日期后点击「获取数据」")
    st.stop()

# ---- 获取数据 ----
if fetch:
    with st.spinner("正在获取涨停板数据..."):
        data = {}
        storage = Storage()
        storage.init_tables()
        db_date = sel_date.strftime("%Y-%m-%d")

        # 涨停股池：本地优先
        local_up = storage.get_limit_up_pool(db_date)
        if not local_up.empty:
            data["up"] = local_up
        else:
            try:
                df_remote = provider.get_limit_up_pool(date_str)
                data["up"] = df_remote
                if not df_remote.empty:
                    df_remote["date"] = sel_date
                    storage.upsert_limit_up_pool(df_remote)
            except Exception:
                data["up"] = pd.DataFrame()

        # 炸板股池：本地优先
        local_failed = storage.get_limit_up_failed_pool(db_date)
        if not local_failed.empty:
            data["failed"] = local_failed
        else:
            try:
                data["failed"] = provider.get_limit_up_failed_pool(date_str)
            except Exception:
                data["failed"] = pd.DataFrame()

        # 跌停股池：本地优先
        local_down = storage.get_limit_down_pool(db_date)
        if not local_down.empty:
            data["down"] = local_down
        else:
            try:
                data["down"] = provider.get_limit_down_pool(date_str)
            except Exception:
                data["down"] = pd.DataFrame()

        # 昨日涨停：本地优先
        local_prev = storage.get_previous_limit_up_pool(db_date)
        if not local_prev.empty:
            data["prev"] = local_prev
        else:
            try:
                data["prev"] = provider.get_previous_limit_up_pool(date_str)
            except Exception:
                data["prev"] = pd.DataFrame()

        storage.close()
        st.session_state["limit_data"] = data
        st.session_state["limit_date"] = date_str

data = st.session_state["limit_data"]
df_up = data.get("up", pd.DataFrame())
df_failed = data.get("failed", pd.DataFrame())
df_down = data.get("down", pd.DataFrame())
df_prev = data.get("prev", pd.DataFrame())

n_up = len(df_up)
n_failed = len(df_failed)
n_down = len(df_down)

# ---- 市场情绪概览 ----
st.markdown("### 市场情绪概览")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("涨停", f"{n_up} 只")
c2.metric("炸板", f"{n_failed} 只")
c3.metric("跌停", f"{n_down} 只")

seal_rate = n_up / (n_up + n_failed) * 100 if (n_up + n_failed) > 0 else 0
c4.metric("封板成功率", f"{seal_rate:.1f}%")

# 昨日涨停晋级率：今日涨跌幅 >= 涨停阈值的比例
promote_rate = 0.0
if not df_prev.empty and "pct_change" in df_prev.columns:
    promoted = df_prev[df_prev["pct_change"] >= 9.5]
    promote_rate = len(promoted) / len(df_prev) * 100
c5.metric("昨涨停晋级率", f"{promote_rate:.1f}%")

st.markdown("---")

# ---- Tabs ----
tab_up, tab_failed, tab_down, tab_prev, tab_ai = st.tabs(
    ["涨停股池", "炸板股池", "跌停股池", "昨日涨停", "AI 复盘"]
)
# ---- Tab: 涨停股池 ----
with tab_up:
    if df_up.empty:
        st.info("暂无涨停数据")
    else:
        # 板块聚类柱状图
        if "industry" in df_up.columns:
            ind_counts = df_up["industry"].value_counts().reset_index()
            ind_counts.columns = ["行业", "涨停数"]
            ind_counts = ind_counts.sort_values("涨停数", ascending=True)
            fig = px.bar(
                ind_counts, x="涨停数", y="行业", orientation="h",
                title="涨停板块分布", color="涨停数",
                color_continuous_scale="Reds",
            )
            fig.update_layout(height=max(400, len(ind_counts) * 25), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        # 连板梯队
        if "streak" in df_up.columns:
            st.markdown("#### 连板梯队")
            streaks = sorted(df_up["streak"].unique(), reverse=True)
            for s in streaks:
                s_int = int(s)
                if s_int < 1:
                    continue
                group = df_up[df_up["streak"] == s]
                names = " | ".join(group["name"].tolist()) if "name" in group.columns else ""
                label = f"**{s_int} 连板** ({len(group)} 只)"
                st.markdown(f"{label}：{names}")

        # 完整列表
        st.markdown("#### 涨停列表")
        show_cols = [c for c in ["code", "name", "industry", "streak", "seal_amount",
                                  "first_seal_time", "turnover", "amount"] if c in df_up.columns]
        col_labels = {
            "code": "代码", "name": "名称", "industry": "行业", "streak": "连板数",
            "seal_amount": "封板资金", "first_seal_time": "首次封板",
            "turnover": "换手率%", "amount": "成交额",
        }
        display = df_up[show_cols].rename(columns=col_labels)
        st.dataframe(display, use_container_width=True, hide_index=True)
# ---- Tab: 炸板股池 ----
with tab_failed:
    if df_failed.empty:
        st.info("暂无炸板数据")
    else:
        show_cols = [c for c in ["code", "name", "industry", "pct_change", "amplitude",
                                  "first_seal_time", "failed_count"] if c in df_failed.columns]
        col_labels = {
            "code": "代码", "name": "名称", "industry": "行业",
            "pct_change": "涨跌幅%", "amplitude": "振幅%",
            "first_seal_time": "首次封板", "failed_count": "炸板次数",
        }
        display = df_failed[show_cols].rename(columns=col_labels)
        st.dataframe(display, use_container_width=True, hide_index=True)

# ---- Tab: 跌停股池 ----
with tab_down:
    if df_down.empty:
        st.info("暂无跌停数据")
    else:
        show_cols = [c for c in ["code", "name", "industry", "pct_change",
                                  "consecutive", "seal_amount"] if c in df_down.columns]
        col_labels = {
            "code": "代码", "name": "名称", "industry": "行业",
            "pct_change": "涨跌幅%", "consecutive": "连续跌停",
            "seal_amount": "封单资金",
        }
        display = df_down[show_cols].rename(columns=col_labels)
        st.dataframe(display, use_container_width=True, hide_index=True)

# ---- Tab: 昨日涨停 ----
with tab_prev:
    if df_prev.empty:
        st.info("暂无昨日涨停数据")
    else:
        show_cols = [c for c in ["code", "name", "industry", "pct_change",
                                  "prev_streak", "prev_seal_time"] if c in df_prev.columns]
        col_labels = {
            "code": "代码", "name": "名称", "industry": "行业",
            "pct_change": "今日涨跌幅%", "prev_streak": "昨日连板数",
            "prev_seal_time": "昨日封板时间",
        }
        # 分组：晋级 vs 未晋级
        if "pct_change" in df_prev.columns:
            promoted = df_prev[df_prev["pct_change"] >= 9.5]
            not_promoted = df_prev[df_prev["pct_change"] < 9.5]
            st.markdown(f"#### 今日晋级（{len(promoted)} 只）")
            if not promoted.empty:
                st.dataframe(
                    promoted[show_cols].rename(columns=col_labels),
                    use_container_width=True, hide_index=True,
                )
            else:
                st.caption("无")
            st.markdown(f"#### 未晋级（{len(not_promoted)} 只）")
            if not not_promoted.empty:
                st.dataframe(
                    not_promoted[show_cols].rename(columns=col_labels),
                    use_container_width=True, hide_index=True,
                )
        else:
            st.dataframe(
                df_prev[show_cols].rename(columns=col_labels),
                use_container_width=True, hide_index=True,
            )
# ---- Tab: AI 复盘 ----
with tab_ai:
    from stock.llm import chat, is_configured, get_provider_name

    if not is_configured():
        st.warning("未配置 LLM，请设置 LLM_PROVIDER 和对应 API Key 环境变量")
    else:
        st.caption(f"当前模型: {get_provider_name()}")
        if st.button("生成 AI 复盘", type="primary"):
            # 构建 prompt 上下文
            summary_parts = [
                f"日期: {st.session_state.get('limit_date', date_str)}",
                f"涨停 {n_up} 只，炸板 {n_failed} 只，跌停 {n_down} 只",
                f"封板成功率 {seal_rate:.1f}%",
            ]
            if not df_up.empty and "industry" in df_up.columns:
                top_ind = df_up["industry"].value_counts().head(5)
                summary_parts.append("涨停板块 TOP5: " + ", ".join(
                    f"{k}({v}只)" for k, v in top_ind.items()
                ))
            if not df_up.empty and "streak" in df_up.columns:
                high = df_up[df_up["streak"] >= 2].sort_values("streak", ascending=False)
                if not high.empty:
                    leaders = high.head(10).apply(
                        lambda r: f"{r['name']}({int(r['streak'])}板)", axis=1
                    ).tolist()
                    summary_parts.append("连板股: " + ", ".join(leaders))

            # 注入近 5 天情绪趋势
            try:
                storage = Storage()
                storage.init_tables()
                five_days_ago = (sel_date - timedelta(days=7)).strftime("%Y-%m-%d")
                today_str = sel_date.strftime("%Y-%m-%d")
                sentiment_df = storage.get_market_sentiment(five_days_ago, today_str)
                storage.close()
                if not sentiment_df.empty:
                    trend_lines = []
                    for _, row in sentiment_df.iterrows():
                        trend_lines.append(
                            f"{row['date']}: 涨停{row['limit_up_count']}只 "
                            f"炸板{row['limit_up_failed_count']}只 "
                            f"封板率{row['seal_rate']:.1f}% "
                            f"晋级率{row['promote_rate']:.1f}%"
                        )
                    summary_parts.append("近期情绪趋势:\n" + "\n".join(trend_lines))
            except Exception:
                pass

            prompt = "\n".join(summary_parts)
            system = (
                "你是一位资深A股短线交易复盘分析师。根据提供的涨停板数据和近期情绪趋势，"
                "分析当日市场情绪、主线方向、板块轮动、连板梯队强度，"
                "结合多日情绪变化判断市场所处阶段（冰点/回暖/高潮/退潮），"
                "并给出次日关注方向。语言简洁专业，400字以内。"
            )
            with st.spinner("AI 复盘生成中..."):
                result = chat(prompt, system)
            st.markdown(result)
