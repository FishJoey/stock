"""个股详情页 — K线图 + 成交量"""

import sys
from datetime import date, timedelta
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# 确保 src 在 path 中
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from stock.data import get_provider
from stock.data.storage import Storage

st.set_page_config(page_title="个股详情", page_icon="📊", layout="wide")
st.title("个股详情")

# 初始化
storage = Storage()
storage.init_tables()
provider = get_provider()

# 侧边栏：股票搜索
with st.sidebar:
    st.header("股票选择")
    keyword = st.text_input("输入代码或名称", value="688110", placeholder="如 688110 或 东芯股份")

    # 日期范围
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input("开始日期", value=date.today() - timedelta(days=365))
    with col2:
        end = st.date_input("结束日期", value=date.today())

    adjust = st.selectbox("复权方式", ["不复权", "前复权", "后复权"], index=1)
    adjust_map = {"不复权": "", "前复权": "qfq", "后复权": "hfq"}

    st.markdown("---")
    related_companies = st.text_input(
        "关联公司（可选）",
        placeholder="如 砺算科技,东芯半导体",
        help="逗号分隔，AI 研报和新闻会同时搜索这些关联公司",
    )

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

# AI 智能研报
st.markdown("---")
st.subheader("AI 智能研报")

from stock.llm import is_configured, get_provider_name

if not is_configured():
    st.info("配置 LLM API Key 后可使用 AI 研报功能。参考 .env.example 设置。")
else:
    import uuid
    from stock.data.news import fetch_stock_news

    # 用户补充信息输入
    user_input = st.text_area(
        "补充分析要点（可选）",
        placeholder="输入补充信息，如：东芯股份投资了砺算科技，关注AI芯片赛道",
        height=80,
        key="user_input",
    )

    # 获取股票名称和行业
    stock_name = code
    stock_industry = ""
    try:
        info = storage.search_stock(code)
        if not info.empty:
            stock_name = info.iloc[0]["name"]
    except Exception:
        pass
    try:
        stock_industry = storage.get_industry_for_stock(code)
    except Exception:
        pass

    # 加载已有技能
    skills_df = storage.get_active_skills(code, stock_industry)
    skills_ctx = ""
    skills_used = ""
    if not skills_df.empty:
        skills_ctx = "\n".join(f"- {row['skill_text']}" for _, row in skills_df.iterrows())
        skills_used = ",".join(str(row["id"]) for _, row in skills_df.iterrows())

    btn_cols = st.columns([2, 2])
    with btn_cols[0]:
        gen_report = st.button(f"生成 AI 分析报告（{get_provider_name()}）", type="primary")
    with btn_cols[1]:
        report_count = storage.get_report_count(code)
        can_optimize = report_count >= 3
        optimize = st.button(
            f"AI 优化分析能力（{report_count}份报告）",
            disabled=not can_optimize,
            help="需要至少3份历史报告才能优化" if not can_optimize else "基于历史报告提炼分析技能",
        )

    if gen_report:
        from stock.analysis.technical import ma, macd, kdj, rsi, boll
        from stock.analysis.ai_report import generate_report
        from stock.analysis.market import market_summary, format_market_summary
        from stock.analysis.industry import stock_industry_position, format_industry_summary

        with st.spinner("正在采集大盘+行业+新闻+个股数据并生成报告..."):
            enriched = ma(df, periods=[5, 10, 20, 60])
            enriched = macd(enriched)
            enriched = kdj(enriched)
            enriched = rsi(enriched, periods=[6, 12])
            enriched = boll(enriched)

            market_ctx = ""
            try:
                ms = market_summary(provider, storage)
                market_ctx = format_market_summary(ms)
            except Exception:
                pass

            industry_ctx = ""
            try:
                pos = stock_industry_position(code, provider, storage)
                industry_ctx = format_industry_summary(pos)
            except Exception:
                pass

            news_ctx = ""
            try:
                extra_kw = [k.strip() for k in related_companies.split(",") if k.strip()] if related_companies else None
                news = fetch_stock_news(code, count=15, keywords=extra_kw)
                if news:
                    lines = []
                    for n in news[:15]:
                        lines.append(f"- [{n['time'][:10]}] {n['title']}: {n['content'][:100]}")
                    news_ctx = "\n".join(lines)
            except Exception:
                pass

            report = generate_report(
                code, stock_name, enriched,
                market_context=market_ctx,
                industry_context=industry_ctx,
                news_context=news_ctx,
                user_input=user_input,
                skills_context=skills_ctx,
            )

        # 保存到 DuckDB
        report_id = str(uuid.uuid4())[:8]
        try:
            storage.save_report(
                report_id=report_id,
                code=code,
                stock_name=stock_name,
                report_text=report,
                market_context=market_ctx,
                industry_context=industry_ctx,
                news_context=news_ctx,
                user_input=user_input,
                skills_used=skills_used,
                llm_provider=get_provider_name(),
            )
        except Exception:
            pass

        st.session_state["latest_report"] = report
        st.session_state["latest_report_ctx"] = {
            "market": market_ctx, "industry": industry_ctx, "news": news_ctx,
        }

    # 显示最新报告
    if "latest_report" in st.session_state:
        ctx = st.session_state.get("latest_report_ctx", {})
        if any(ctx.values()):
            with st.expander("分析上下文（大盘+行业+新闻）", expanded=False):
                if ctx.get("market"):
                    st.text(ctx["market"])
                if ctx.get("industry"):
                    st.markdown("---")
                    st.text(ctx["industry"])
                if ctx.get("news"):
                    st.markdown("---")
                    st.text(ctx["news"])
        st.markdown(st.session_state["latest_report"])

    # AI 优化分析能力
    if optimize:
        from stock.analysis.report_agent import review_reports

        with st.spinner("正在审查历史报告，提炼分析技能..."):
            new_skills = review_reports(code, stock_name, storage, stock_industry)

        if new_skills:
            st.success(f"提炼了 {len(new_skills)} 条新技能")
            for s in new_skills:
                st.markdown(f"- **{s['text']}**\n  原因: {s['reason']}")
        else:
            st.info("未发现新的可改进之处")

    # 历史报告
    history_df = storage.get_reports(code, limit=10)
    if not history_df.empty:
        with st.expander(f"历史报告（{len(history_df)} 份）", expanded=False):
            for _, row in history_df.iterrows():
                ts = str(row["created_at"])[:19]
                label = f"{ts}"
                if row.get("user_input"):
                    label += f" | 补充: {str(row['user_input'])[:30]}"
                with st.expander(label):
                    st.markdown(row["report_text"])

    # 分析技能管理
    all_skills = storage.get_active_skills(code, stock_industry)
    if not all_skills.empty or can_optimize:
        with st.expander(f"分析技能（{len(all_skills)} 条）", expanded=False):
            if not all_skills.empty:
                for _, skill in all_skills.iterrows():
                    scol1, scol2 = st.columns([8, 1])
                    with scol1:
                        scope_tag = ""
                        if skill["code"]:
                            scope_tag = f"[{skill['code']}] "
                        elif skill["industry"]:
                            scope_tag = f"[{skill['industry']}] "
                        else:
                            scope_tag = "[全局] "
                        st.markdown(f"{scope_tag}**{skill['skill_text']}**")
                        if skill.get("reason"):
                            st.caption(f"原因: {skill['reason']}")
                    with scol2:
                        if st.button("删除", key=f"del_skill_{skill['id']}"):
                            storage.delete_skill(skill["id"])
                            st.rerun()

            # 手动添加技能
            new_skill_text = st.text_input("手动添加技能", placeholder="如：分析时关注公司在AI芯片领域的布局", key="new_skill")
            if new_skill_text and st.button("添加", key="add_skill"):
                storage.save_skill(
                    skill_id=str(uuid.uuid4())[:8],
                    skill_text=new_skill_text,
                    reason="用户手动添加",
                    code=code,
                )
                st.rerun()

# 个股资讯
st.markdown("---")
st.subheader("个股资讯")

from stock.data.news import fetch_stock_news

if st.button("获取最新资讯", key="fetch_news"):
    with st.spinner("正在获取新闻..."):
        extra_kw = [k.strip() for k in related_companies.split(",") if k.strip()] if related_companies else None
        news_list = fetch_stock_news(code, count=20, keywords=extra_kw)
    st.session_state["news_list"] = news_list

if "news_list" in st.session_state and st.session_state["news_list"]:
    news_list = st.session_state["news_list"]
    st.caption(f"共 {len(news_list)} 条资讯")

    for n in news_list:
        with st.expander(f"**{n['title']}**　{n['source']} · {n['time'][:10]}"):
            st.write(n["content"])
            if n["url"]:
                st.markdown(f"[查看原文]({n['url']})")

    # AI 新闻分析
    if is_configured():
        if st.button(f"AI 分析新闻舆情（{get_provider_name()}）", key="ai_news"):
            from stock.analysis.ai_news import analyze_news

            stock_name_for_news = code
            try:
                info = storage.search_stock(code)
                if not info.empty:
                    stock_name_for_news = info.iloc[0]["name"]
            except Exception:
                pass

            with st.spinner("正在分析新闻舆情..."):
                analysis = analyze_news(code, stock_name_for_news, news_list)
            st.markdown(analysis)
elif "news_list" in st.session_state:
    st.info("未获取到相关新闻")
