"""自然语言选股

用户输入自然语言描述，LLM 解析为 ScreenerConfig 结构化筛选条件。
支持 Claude / 通义千问 / DeepSeek / 智谱 GLM / OpenAI。
"""

import json

from loguru import logger

from stock.llm import chat, is_configured
from stock.analysis.fundamental.screener import ScreenerConfig, FilterCondition


_SYSTEM_PROMPT = """你是一个A股选股条件解析器。用户会用自然语言描述选股条件，你需要将其转换为 JSON 格式的筛选配置。

可用的列名（column）：
- code: 股票代码
- name: 股票名称
- board: 板块（主板/创业板/科创板/中小板）
- exchange: 交易所（SH/SZ）
- pct_change: 涨跌幅（%）
- turnover: 换手率（%）
- amplitude: 振幅（%）
- volume: 成交量（手）
- amount: 成交额（元）
- pe_ttm: 市盈率TTM
- pb: 市净率
- ps: 市销率
- roe: 净资产收益率（%）
- roa: 总资产收益率（%）
- net_margin: 净利率（%）
- gross_margin: 毛利率（%）
- revenue_yoy: 营收同比增速（%）
- profit_yoy: 净利润同比增速（%）
- dividend_yield: 股息率（%）
- health_score: 财务健康评分（0-100）

可用的运算符（operator）：gt / lt / gte / lte / eq / between

输出格式（严格 JSON，不要其他文字）：
{
  "conditions": [
    {"column": "pe_ttm", "operator": "lt", "value": 20},
    {"column": "roe", "operator": "gt", "value": 15}
  ],
  "sort_by": "roe",
  "ascending": false,
  "limit": 50
}

如果用户提到板块筛选（如"创业板"），用 board 列和 eq 运算符。
如果用户提到交易所（如"上海"），用 exchange 列。
value 对于 between 运算符是 [min, max] 数组。"""


def parse_query(query: str) -> ScreenerConfig | None:
    """将自然语言查询解析为 ScreenerConfig

    Args:
        query: 用户输入的自然语言，如 "找PE低于20、ROE大于15的创业板股票"

    Returns:
        ScreenerConfig 或 None（解析失败时）
    """
    if not is_configured():
        logger.error("未配置 LLM API Key")
        return None

    try:
        raw = chat(query, system=_SYSTEM_PROMPT).strip()

        # 提取 JSON（处理可能的 markdown 代码块包裹）
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        data = json.loads(raw)

        conditions = []
        for c in data.get("conditions", []):
            val = c["value"]
            if isinstance(val, list) and len(val) == 2:
                val = tuple(val)
            conditions.append(FilterCondition(
                column=c["column"],
                operator=c["operator"],
                value=val,
            ))

        return ScreenerConfig(
            conditions=conditions,
            sort_by=data.get("sort_by", ""),
            ascending=data.get("ascending", False),
            limit=data.get("limit", 50),
        )

    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败: {e}")
        return None
    except Exception as e:
        logger.error(f"自然语言选股解析失败: {e}")
        return None
