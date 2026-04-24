"""AI 智能研报生成

基于技术面+基本面数据，调用 LLM 自动生成个股分析报告。
支持 Claude / 通义千问 / DeepSeek / 智谱 GLM / OpenAI。
"""

import pandas as pd

from stock.llm import chat, is_configured


def _build_prompt(code: str, name: str, kline: pd.DataFrame, fundamentals: dict | None = None) -> str:
    """构建研报生成 prompt"""
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

    prompt = f"""你是一位专业的A股证券分析师。请根据以下数据，为 {name}（{code}）生成一份简洁的分析报告。

## 行情数据
{price_info}

## 技术指标（最新值）
{tech_info if tech_info else "暂无技术指标数据"}

## 基本面数据
{fund_info if fund_info else "暂无基本面数据"}

## 报告要求
请用中文输出，包含以下部分：
1. **走势概述**：近期价格走势和成交量变化
2. **技术面分析**：基于均线、MACD、KDJ、RSI等指标的分析
3. **支撑与压力**：关键价位判断
4. **风险提示**：需要关注的风险因素
5. **操作建议**：短期操作方向建议

注意：这是辅助分析，不构成投资建议。保持客观，不要过度乐观或悲观。"""

    return prompt


def generate_report(
    code: str,
    name: str,
    kline: pd.DataFrame,
    fundamentals: dict | None = None,
) -> str:
    """生成智能研报

    Args:
        code: 股票代码
        name: 股票名称
        kline: K线数据（建议包含技术指标列）
        fundamentals: 基本面数据字典（可选）

    Returns:
        str: 分析报告文本
    """
    if not is_configured():
        return "未配置 LLM API Key，请在 .env 文件中设置。参考 .env.example。"

    prompt = _build_prompt(code, name, kline, fundamentals)
    return chat(prompt)
