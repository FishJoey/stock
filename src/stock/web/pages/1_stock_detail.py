"""个股详情页 — K线图 + 成交量"""

import sys
from datetime import date, timedelta
from pathlib import Path

import plotly.graph_objects as go
import pandas as pd
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
    st.header("技术指标")
    show_ma = st.checkbox("均线 MA", value=True)
    show_boll = st.checkbox("布林带 BOLL", value=False)
    show_macd = st.checkbox("MACD", value=True)
    show_kdj = st.checkbox("KDJ", value=False)

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

# 计算技术指标
from stock.analysis.technical import ma as calc_ma, macd as calc_macd, boll as calc_boll, kdj as calc_kdj

ma_periods = [5, 10, 20, 60]
if show_ma:
    df = calc_ma(df, periods=ma_periods)
if show_boll:
    df = calc_boll(df)
if show_macd or show_kdj:
    if show_macd:
        df = calc_macd(df)
    if show_kdj:
        df = calc_kdj(df)

# 确定子图数量
sub_rows = [("K线", 0.55)]
sub_rows.append(("成交量", 0.15))
if show_macd:
    sub_rows.append(("MACD", 0.15))
if show_kdj:
    sub_rows.append(("KDJ", 0.15))

row_heights = [r[1] for r in sub_rows]
total = sum(row_heights)
row_heights = [h / total for h in row_heights]

fig = make_subplots(
    rows=len(sub_rows), cols=1,
    shared_xaxes=True,
    vertical_spacing=0.02,
    row_heights=row_heights,
)

# K线
_pct = df["pct_change"] if "pct_change" in df.columns else [0.0] * len(df)
_chg = df["change"] if "change" in df.columns else [0.0] * len(df)
import numpy as np
_customdata = np.column_stack([_pct, _chg])

fig.add_trace(
    go.Candlestick(
        x=df["date"],
        open=df["open"],
        high=df["high"],
        low=df["low"],
        close=df["close"],
        name="K线",
        increasing_line_color="#ef5350",
        decreasing_line_color="#26a69a",
        increasing_fillcolor="#ef5350",
        decreasing_fillcolor="#26a69a",
        customdata=_customdata,
        hovertext=[
            f"涨跌幅: {p:.2f}%<br>涨跌额: {c:.2f}"
            for p, c in zip(_pct, _chg)
        ],
        hoverinfo="text+x+y",
    ),
    row=1, col=1,
)

# 均线
if show_ma:
    ma_colors = {"ma5": "#FF9800", "ma10": "#2196F3", "ma20": "#E91E63", "ma60": "#9C27B0"}
    for p in ma_periods:
        col_name = f"ma{p}"
        if col_name in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["date"], y=df[col_name], name=f"MA{p}",
                    line=dict(color=ma_colors.get(col_name, "#888"), width=1),
                ),
                row=1, col=1,
            )

# 布林带
if show_boll and "boll_upper" in df.columns:
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["boll_upper"], name="BOLL上轨",
                   line=dict(color="#90CAF9", width=1, dash="dot")),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["boll_mid"], name="BOLL中轨",
                   line=dict(color="#64B5F6", width=1)),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["boll_lower"], name="BOLL下轨",
                   line=dict(color="#90CAF9", width=1, dash="dot"),
                   fill="tonexty", fillcolor="rgba(144,202,249,0.08)"),
        row=1, col=1,
    )

# 成交量（红涨绿跌）
vol_row = 2
vol_colors = [
    "#ef5350" if row["close"] >= row["open"] else "#26a69a"
    for _, row in df.iterrows()
]
fig.add_trace(
    go.Bar(x=df["date"], y=df["volume"], name="成交量", marker_color=vol_colors),
    row=vol_row, col=1,
)

# MACD
if show_macd and "macd_dif" in df.columns:
    macd_row = 3
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["macd_dif"], name="DIF",
                   line=dict(color="#2196F3", width=1)),
        row=macd_row, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["macd_dea"], name="DEA",
                   line=dict(color="#FF9800", width=1)),
        row=macd_row, col=1,
    )
    macd_colors = ["#ef5350" if v >= 0 else "#26a69a" for v in df["macd_hist"]]
    fig.add_trace(
        go.Bar(x=df["date"], y=df["macd_hist"], name="MACD柱",
               marker_color=macd_colors),
        row=macd_row, col=1,
    )

# KDJ
if show_kdj and "kdj_k" in df.columns:
    kdj_row = len(sub_rows)
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["kdj_k"], name="K",
                   line=dict(color="#2196F3", width=1)),
        row=kdj_row, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["kdj_d"], name="D",
                   line=dict(color="#FF9800", width=1)),
        row=kdj_row, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df["date"], y=df["kdj_j"], name="J",
                   line=dict(color="#E91E63", width=1)),
        row=kdj_row, col=1,
    )

fig.update_layout(
    height=250 + 200 * (len(sub_rows) - 1),
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    margin=dict(l=50, r=20, t=30, b=30),
)
fig.update_xaxes(type="category", nticks=20)
fig.update_yaxes(title_text="价格", row=1, col=1)
fig.update_yaxes(title_text="成交量", row=vol_row, col=1)
if show_macd and "macd_dif" in df.columns:
    fig.update_yaxes(title_text="MACD", row=3, col=1)
if show_kdj and "kdj_k" in df.columns:
    fig.update_yaxes(title_text="KDJ", row=len(sub_rows), col=1)

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


# ---- Tab 页 ----
from stock.llm import is_configured, get_provider_name
from stock.data.news import fetch_stock_news

tab_ai, tab_fund, tab_fundamental, tab_backtest, tab_news, tab_chat = st.tabs(
    ["AI 智能研报", "资金流向", "基本面", "快速回测", "个股资讯", "AI 对话"]
)

# ---- AI 智能研报 Tab ----
with tab_ai:
    if not is_configured():
        st.info("配置 LLM API Key 后可使用 AI 研报功能。参考 .env.example 设置。")
    else:
        import uuid

        user_input = st.text_area(
            "补充分析要点（可选）",
            placeholder="输入补充信息，如：东芯股份投资了砺算科技，关注AI芯片赛道",
            height=80,
            key="user_input",
        )

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

                new_skill_text = st.text_input("手动添加技能", placeholder="如：分析时关注公司在AI芯片领域的布局", key="new_skill")
                if new_skill_text and st.button("添加", key="add_skill"):
                    storage.save_skill(
                        skill_id=str(uuid.uuid4())[:8],
                        skill_text=new_skill_text,
                        reason="用户手动添加",
                        code=code,
                    )
                    st.rerun()

# ---- 资金流向 Tab ----
with tab_fund:
    if st.button("获取资金流向", key="fetch_fund_flow"):
        with st.spinner("正在获取资金流向数据..."):
            fund_df = provider.get_stock_fund_flow(code)
        st.session_state["fund_flow_df"] = fund_df

    if "fund_flow_df" in st.session_state and not st.session_state["fund_flow_df"].empty:
        fund_df = st.session_state["fund_flow_df"]

        # 主力资金净流入柱状图
        st.subheader("主力资金净流入")
        _fund_colors = ["#ef5350" if v >= 0 else "#26a69a" for v in fund_df["main_net"]]
        fig_fund = go.Figure()
        fig_fund.add_trace(go.Bar(
            x=fund_df["date"], y=fund_df["main_net"],
            name="主力净流入", marker_color=_fund_colors,
        ))
        fig_fund.update_layout(height=300, margin=dict(l=50, r=20, t=30, b=30), yaxis_title="万元")
        fig_fund.update_xaxes(type="category", nticks=20)
        st.plotly_chart(fig_fund, use_container_width=True)

        # 各类资金趋势折线图
        st.subheader("分类资金净流入趋势")
        fig_detail = go.Figure()
        fig_detail.add_trace(go.Scatter(
            x=fund_df["date"], y=fund_df["super_large_net"], name="超大单",
            line=dict(color="#E91E63", width=1.5),
        ))
        fig_detail.add_trace(go.Scatter(
            x=fund_df["date"], y=fund_df["large_net"], name="大单",
            line=dict(color="#FF9800", width=1.5),
        ))
        fig_detail.add_trace(go.Scatter(
            x=fund_df["date"], y=fund_df["medium_net"], name="中单",
            line=dict(color="#2196F3", width=1.5),
        ))
        fig_detail.add_trace(go.Scatter(
            x=fund_df["date"], y=fund_df["small_net"], name="小单",
            line=dict(color="#9C27B0", width=1.5),
        ))
        fig_detail.update_layout(height=280, margin=dict(l=50, r=20, t=30, b=30), yaxis_title="万元")
        fig_detail.update_xaxes(type="category", nticks=20)
        st.plotly_chart(fig_detail, use_container_width=True)

        # 累计统计
        _cols = st.columns(4)
        _cols[0].metric("近5日主力净流入", f"{fund_df['main_net'].head(5).sum():.0f} 万")
        _cols[1].metric("近10日主力净流入", f"{fund_df['main_net'].head(10).sum():.0f} 万")
        _cols[2].metric("近20日主力净流入", f"{fund_df['main_net'].head(20).sum():.0f} 万")
        _cols[3].metric("近5日散户净流入", f"{(fund_df['medium_net'].head(5) + fund_df['small_net'].head(5)).sum():.0f} 万")
    elif "fund_flow_df" in st.session_state:
        st.info("未获取到资金流向数据")

# ---- 基本面 Tab ----
with tab_fundamental:
    if st.button("获取财务指标", key="fetch_financial"):
        with st.spinner("正在获取财务数据..."):
            fin_df = provider.get_financial_indicator(code)
        st.session_state["financial_df"] = fin_df

    if "financial_df" in st.session_state and not st.session_state["financial_df"].empty:
        fin_df = st.session_state["financial_df"]
        latest_fin = fin_df.iloc[0]

        # 核心指标卡片
        st.subheader("最新财务指标")
        _fin_cols = st.columns(6)
        _fin_cols[0].metric("ROE", f"{latest_fin.get('roe', 0):.2f}%")
        _fin_cols[1].metric("净利率", f"{latest_fin.get('net_margin', 0):.2f}%")
        _fin_cols[2].metric("毛利率", f"{latest_fin.get('gross_margin', 0):.2f}%")
        _fin_cols[3].metric("营收增速", f"{latest_fin.get('revenue_yoy', 0):.2f}%")
        _fin_cols[4].metric("净利润增速", f"{latest_fin.get('profit_yoy', 0):.2f}%")
        _fin_cols[5].metric("EPS", f"{latest_fin.get('eps', 0):.4f}")

        _fin_cols2 = st.columns(4)
        _fin_cols2[0].metric("每股净资产", f"{latest_fin.get('bps', 0):.2f}")
        _fin_cols2[1].metric("资产负债率", f"{latest_fin.get('debt_ratio', 0):.2f}%")
        _fin_cols2[2].metric("流动比率", f"{latest_fin.get('current_ratio', 0):.2f}")
        _fin_cols2[3].metric("资产周转率", f"{latest_fin.get('asset_turnover', 0):.4f}")

        # 盈利能力趋势图（近8期）
        trend_df = fin_df.head(8).iloc[::-1]  # 时间正序
        if "roe" in trend_df.columns and "net_margin" in trend_df.columns:
            st.subheader("盈利能力趋势")
            fig_profit = go.Figure()
            fig_profit.add_trace(go.Scatter(
                x=trend_df["date"], y=trend_df["roe"], name="ROE(%)",
                line=dict(color="#E91E63", width=2),
            ))
            fig_profit.add_trace(go.Scatter(
                x=trend_df["date"], y=trend_df["net_margin"], name="净利率(%)",
                line=dict(color="#2196F3", width=2),
            ))
            if "gross_margin" in trend_df.columns:
                fig_profit.add_trace(go.Scatter(
                    x=trend_df["date"], y=trend_df["gross_margin"], name="毛利率(%)",
                    line=dict(color="#FF9800", width=2),
                ))
            fig_profit.update_layout(height=300, margin=dict(l=50, r=20, t=30, b=30))
            st.plotly_chart(fig_profit, use_container_width=True)

        # 增长趋势图
        if "revenue_yoy" in trend_df.columns and "profit_yoy" in trend_df.columns:
            st.subheader("增长趋势")
            fig_growth = go.Figure()
            fig_growth.add_trace(go.Bar(
                x=trend_df["date"], y=trend_df["revenue_yoy"], name="营收增速(%)",
                marker_color="#2196F3",
            ))
            fig_growth.add_trace(go.Bar(
                x=trend_df["date"], y=trend_df["profit_yoy"], name="净利润增速(%)",
                marker_color="#FF9800",
            ))
            fig_growth.update_layout(
                height=280, margin=dict(l=50, r=20, t=30, b=30), barmode="group",
            )
            st.plotly_chart(fig_growth, use_container_width=True)

        # 完整数据表
        with st.expander("完整财务数据", expanded=False):
            display_cols = {
                "date": "日期", "roe": "ROE(%)", "net_margin": "净利率(%)",
                "gross_margin": "毛利率(%)", "revenue_yoy": "营收增速(%)",
                "profit_yoy": "净利润增速(%)", "eps": "EPS",
                "bps": "每股净资产", "debt_ratio": "资产负债率(%)",
                "current_ratio": "流动比率", "asset_turnover": "资产周转率",
            }
            _show_cols = [c for c in display_cols if c in fin_df.columns]
            st.dataframe(
                fin_df[_show_cols].rename(columns=display_cols).head(12),
                use_container_width=True, hide_index=True,
            )
    elif "financial_df" in st.session_state:
        st.info("未获取到财务数据")

# ---- 快速回测 Tab ----
with tab_backtest:
    from stock.strategy.backtest import backtest as run_backtest
    from stock.strategy.templates import (
        MACrossStrategy, MACDStrategy, BollBreakoutStrategy, KDJRSIStrategy,
    )

    st.subheader("策略回测")
    _bt_col1, _bt_col2 = st.columns([2, 3])
    with _bt_col1:
        _bt_strategy = st.selectbox("选择策略", ["均线交叉", "MACD交叉", "布林带突破", "KDJ+RSI"], key="bt_strategy")
    with _bt_col2:
        if _bt_strategy == "均线交叉":
            _c1, _c2 = st.columns(2)
            _bt_fast = _c1.number_input("短期", 3, 60, 5, key="bt_fast")
            _bt_slow = _c2.number_input("长期", 10, 250, 20, key="bt_slow")
        elif _bt_strategy == "MACD交叉":
            _c1, _c2, _c3 = st.columns(3)
            _bt_macd_fast = _c1.number_input("快线", 5, 30, 12, key="bt_mf")
            _bt_macd_slow = _c2.number_input("慢线", 15, 50, 26, key="bt_ms")
            _bt_macd_sig = _c3.number_input("信号", 5, 20, 9, key="bt_sig")
        elif _bt_strategy == "布林带突破":
            _c1, _c2 = st.columns(2)
            _bt_boll_p = _c1.number_input("周期", 10, 50, 20, key="bt_bp")
            _bt_boll_std = _c2.number_input("标准差", 1.0, 3.0, 2.0, 0.1, key="bt_bs")
        else:
            _c1, _c2 = st.columns(2)
            _bt_kdj_n = _c1.number_input("KDJ周期", 5, 20, 9, key="bt_kn")
            _bt_rsi_p = _c2.number_input("RSI周期", 5, 30, 12, key="bt_rp")

    if st.button("运行回测", type="primary", key="run_backtest"):
        if _bt_strategy == "均线交叉":
            _strategy = MACrossStrategy(fast=_bt_fast, slow=_bt_slow)
        elif _bt_strategy == "MACD交叉":
            _strategy = MACDStrategy(fast=_bt_macd_fast, slow=_bt_macd_slow, signal=_bt_macd_sig)
        elif _bt_strategy == "布林带突破":
            _strategy = BollBreakoutStrategy(period=_bt_boll_p, std_dev=_bt_boll_std)
        else:
            _strategy = KDJRSIStrategy(kdj_n=_bt_kdj_n, rsi_period=_bt_rsi_p)

        with st.spinner("回测中..."):
            _bt_result = run_backtest(df, _strategy, initial_capital=1_000_000, code=code)
        st.session_state["bt_result"] = _bt_result

    if "bt_result" in st.session_state:
        _bt_result = st.session_state["bt_result"]
        _metrics = _bt_result["metrics"]

        # 绩效指标
        _m_cols = st.columns(5)
        _m_cols[0].metric("总收益", f"{_metrics['total_return']:.2f}%")
        _m_cols[1].metric("年化收益", f"{_metrics['annual_return']:.2f}%")
        _m_cols[2].metric("最大回撤", f"{_metrics['max_drawdown']:.2f}%")
        _m_cols[3].metric("夏普比率", f"{_metrics['sharpe_ratio']:.3f}")
        _m_cols[4].metric("胜率", f"{_metrics['win_rate']:.1f}%")

        # 净值曲线
        fig_eq = go.Figure()
        fig_eq.add_trace(go.Scatter(
            x=df["date"], y=_bt_result["equity_curve"],
            name="策略净值", line=dict(color="#1f77b4"),
        ))
        fig_eq.add_hline(y=1.0, line_dash="dash", line_color="gray", annotation_text="初始净值")
        fig_eq.update_layout(height=350, margin=dict(l=50, r=20, t=30, b=30), yaxis_title="净值")
        fig_eq.update_xaxes(type="category", nticks=20)
        st.plotly_chart(fig_eq, use_container_width=True)

        # 交易记录
        _trades = _bt_result["trades"]
        if not _trades.empty:
            with st.expander(f"交易记录（{len(_trades)} 笔）", expanded=False):
                st.dataframe(_trades, use_container_width=True, hide_index=True)
        else:
            st.info("本次回测无交易信号触发")

# ---- 个股资讯 Tab ----
with tab_news:
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

# ---- AI 对话 Tab ----
with tab_chat:
    if not is_configured():
        st.info("配置 LLM API Key 后可使用 AI 对话功能。参考 .env.example 设置。")
    else:
        from stock.llm import chat_messages

        # 构建个股上下文 system prompt
        _chat_stock_name = code
        try:
            _info = storage.search_stock(code)
            if not _info.empty:
                _chat_stock_name = _info.iloc[0]["name"]
        except Exception:
            pass

        _latest = df.iloc[-1]
        _recent = df.tail(30)
        _ctx_lines = [
            f"你是一位专业的A股证券分析师助手。当前用户正在查看 {_chat_stock_name}（{code}）。",
            f"最新价: {_latest['close']:.2f}",
            f"30日最高: {_recent['high'].max():.2f}，30日最低: {_recent['low'].min():.2f}",
            f"30日涨跌幅: {((_latest['close'] / _recent.iloc[0]['close']) - 1) * 100:.2f}%",
            f"最新成交量: {_latest['volume']:.0f} 手",
        ]
        if "pct_change" in _latest.index:
            _ctx_lines.append(f"最新涨跌幅: {_latest['pct_change']:.2f}%")
        for _col in ["ma5", "ma10", "ma20", "ma60", "macd_dif", "macd_dea", "kdj_k", "kdj_d", "kdj_j"]:
            if _col in _latest.index and not pd.isna(_latest[_col]):
                _ctx_lines.append(f"{_col}: {_latest[_col]:.2f}")
        _ctx_lines.append("请用中文回答，保持专业客观。这是辅助分析，不构成投资建议。")
        _system_prompt = "\n".join(_ctx_lines)

        # 切换股票时清空对话
        if st.session_state.get("chat_stock_code") != code:
            st.session_state["chat_stock_code"] = code
            st.session_state["chat_history"] = []

        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        # 清空按钮
        if st.button("清空对话", key="clear_chat"):
            st.session_state["chat_history"] = []
            st.rerun()

        # 显示历史消息
        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # 用户输入
        if user_prompt := st.chat_input(f"向 AI 提问关于 {_chat_stock_name} 的问题...", key="chat_input"):
            st.session_state["chat_history"].append({"role": "user", "content": user_prompt})
            with st.chat_message("user"):
                st.markdown(user_prompt)

            with st.chat_message("assistant"):
                with st.spinner("思考中..."):
                    reply = chat_messages(
                        st.session_state["chat_history"],
                        system=_system_prompt,
                    )
                st.markdown(reply)
            st.session_state["chat_history"].append({"role": "assistant", "content": reply})
