"""AI 智能研报生成

基于 宏观大盘 + 产业行业 + 个股技术面/基本面 三维数据，
调用 LLM 自动生成综合分析报告。
支持 Claude / 通义千问 / DeepSeek / 智谱 GLM / OpenAI。
"""

import pandas as pd

from stock.llm import chat, is_configured


def _build_prompt(
    code: str,
    name: str,
    kline: pd.DataFrame,
    fundamentals: dict | None = None,
    market_context: str = "",
    industry_context: str = "",
    news_context: str = "",
    user_input: str = "",
    skills_context: str = "",
) -> str:
    """构建三维研报 prompt"""
    # 取最近 30 个交易日的数据摘要
    recent = kline.tail(30)
    latest = recent.iloc[-1]

    price_info = (
        f"最新价: {latest['close']:.2f}\n"
        f"30日最高: {recent['high'].max():.2f}\n"
        f"30日最低: {recent['low'].min():.2f}\n"
        f"30日涨跌幅: {((latest['close'] / recent.iloc[0]['close']) - 1) * 100:.2f}%\n"
        f"最新成交量: {latest['volume']:.0f} 手\n"
        f"30日平均成交量: {recent['volume'].mean():.0f} 手\n"
    )

    # 技术指标摘要
    tech_info = ""
    for col in ["ma5", "ma10", "ma20", "ma60", "macd_dif", "macd_dea", "macd_hist",
                 "kdj_k", "kdj_d", "kdj_j", "rsi6", "rsi12", "boll_upper", "boll_mid", "boll_lower"]:
        if col in latest.index and pd.notna(latest[col]):
            tech_info += f"{col}: {latest[col]:.2f}\n"

    # 基本面摘要
    fund_info = ""
    if fundamentals:
        for k, v in fundamentals.items():
            fund_info += f"{k}: {v}\n"

    # 构建三维 prompt
    sections = [f"你是一位专业的A股证券分析师。请根据以下多维度数据，为 {name}（{code}）生成一份综合分析报告。"]

    # 注入分析技能（历史经验）
    if skills_context:
        sections.append(f"\n## 分析指南（基于历史报告总结的经验）\n{skills_context}")

    # 宏观大盘
    if market_context:
        sections.append(f"\n## 宏观大盘环境\n{market_context}")

    # 行业定位
    if industry_context:
        sections.append(f"\n## 行业定位\n{industry_context}")

    # 个股数据
    sections.append(f"\n## 个股行情数据\n{price_info}")
    sections.append(f"\n## 技术指标（最新值）\n{tech_info if tech_info else '暂无技术指标数据'}")

    if fund_info:
        sections.append(f"\n## 基本面数据\n{fund_info}")

    # 近期新闻事件
    if news_context:
        sections.append(f"\n## 近期重要新闻/事件\n{news_context}")

    # 用户补充信息
    if user_input:
        sections.append(f"\n## 用户补充信息\n{user_input}")

    # 报告要求 — 根据有无宏观/行业数据调整
    if market_context or industry_context:
        report_req = """
## 报告要求
请用中文输出，包含以下部分：
1. **宏观环境评估**：当前市场处于什么阶段，对个股的影响
2. **行业景气度分析**：所属行业的强弱、资金偏好、产业链位置
3. **近期重大事件**：结合新闻资讯分析近期重要事件对公司的影响
4. **个股技术面分析**：基于均线、MACD、KDJ、RSI等指标的分析
5. **支撑与压力**：关键价位判断
6. **综合研判**：结合大盘环境、行业趋势、新闻事件和个股走势的综合判断
7. **风险提示**：宏观风险、行业风险、个股风险、事件风险
8. **操作建议**：短期操作方向建议

注意：这是辅助分析，不构成投资建议。保持客观，自上而下分析。"""
    else:
        report_req = """
## 报告要求
请用中文输出，包含以下部分：
1. **走势概述**：近期价格走势和成交量变化
2. **近期重大事件**：结合新闻资讯分析近期重要事件对公司的影响
3. **技术面分析**：基于均线、MACD、KDJ、RSI等指标的分析
4. **支撑与压力**：关键价位判断
5. **风险提示**：需要关注的风险因素
6. **操作建议**：短期操作方向建议

注意：这是辅助分析，不构成投资建议。保持客观，不要过度乐观或悲观。"""

    sections.append(report_req)
    return "\n".join(sections)


def generate_report(
    code: str,
    name: str,
    kline: pd.DataFrame,
    fundamentals: dict | None = None,
    market_context: str = "",
    industry_context: str = "",
    news_context: str = "",
    user_input: str = "",
    skills_context: str = "",
) -> str:
    """生成智能研报"""
    if not is_configured():
        return "未配置 LLM API Key，请在 .env 文件中设置。参考 .env.example。"

    if kline.empty:
        return "数据不足，无法生成报告。"

    prompt = _build_prompt(
        code, name, kline, fundamentals,
        market_context, industry_context, news_context,
        user_input, skills_context,
    )
    return chat(prompt)
