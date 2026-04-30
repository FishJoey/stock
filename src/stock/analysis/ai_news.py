"""AI 新闻分析

基于个股新闻列表，调用 LLM 进行情绪分析、关键事件提取和影响评估。
"""

from stock.llm import chat, is_configured


def _build_news_prompt(code: str, name: str, news_list: list[dict]) -> str:
    news_text = ""
    for i, n in enumerate(news_list, 1):
        news_text += (
            f"### 新闻{i}\n"
            f"- 标题: {n['title']}\n"
            f"- 时间: {n['time']}\n"
            f"- 来源: {n['source']}\n"
            f"- 摘要: {n['content'][:200]}\n\n"
        )

    return (
        f"你是一位专业的A股证券分析师。以下是 {name}（{code}）的最新新闻资讯，"
        f"请进行综合分析。\n\n"
        f"## 新闻列表\n\n{news_text}"
        f"## 分析要求\n\n"
        f"请用中文输出，包含以下部分：\n"
        f"1. **舆情情绪**：整体偏利好/利空/中性，给出判断依据\n"
        f"2. **关键事件**：提取最重要的2-3个事件，说明其对公司的潜在影响\n"
        f"3. **资金面影响**：这些消息可能对短期资金流向产生什么影响\n"
        f"4. **风险提示**：需要关注的负面信号或不确定性\n"
        f"5. **综合建议**：结合以上分析给出简要操作参考\n\n"
        f"注意：这是辅助分析，不构成投资建议。保持客观。"
    )


def analyze_news(code: str, name: str, news_list: list[dict]) -> str:
    """对个股新闻进行 AI 分析

    Args:
        code: 股票代码
        name: 股票名称
        news_list: fetch_stock_news 返回的新闻列表

    Returns:
        分析报告文本
    """
    if not is_configured():
        return "未配置 LLM API Key，请在 .env 文件中设置。参考 .env.example。"

    if not news_list:
        return "暂无新闻数据，无法进行分析。"

    prompt = _build_news_prompt(code, name, news_list)
    return chat(prompt)
