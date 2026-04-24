"""产业/行业分析模块

提供行业排名、板块轮动、个股行业定位等分析功能。
"""

import pandas as pd
import numpy as np
from loguru import logger

from stock.data.akshare_provider import AKShareProvider
from stock.data.storage import Storage


# 主要产业链映射
INDUSTRY_CHAINS = {
    "新能源车": {
        "上游": ["锂矿", "钴镍", "正极材料", "负极材料", "电解液", "隔膜"],
        "中游": ["动力电池", "电机电控", "热管理"],
        "下游": ["整车制造", "充电桩"],
    },
    "半导体": {
        "上游": ["半导体设备", "半导体材料", "EDA"],
        "中游": ["芯片设计", "晶圆代工", "封装测试"],
        "下游": ["消费电子", "汽车电子", "工业控制"],
    },
    "光伏": {
        "上游": ["硅料", "硅片"],
        "中游": ["电池片", "组件"],
        "下游": ["光伏电站", "逆变器", "储能"],
    },
    "白酒": {
        "上游": ["粮食种植", "包装材料"],
        "中游": ["白酒酿造"],
        "下游": ["商超零售", "餐饮"],
    },
    "医药": {
        "上游": ["原料药", "医药中间体"],
        "中游": ["化学制药", "中药", "生物制品"],
        "下游": ["医药商业", "医疗器械", "医疗服务"],
    },
}


def industry_ranking(provider: AKShareProvider) -> pd.DataFrame:
    """获取行业板块强弱排名

    Returns:
        DataFrame [industry_name, pct_change, turnover, amount, leading_stock]
        按涨跌幅降序排列
    """
    try:
        df = provider.get_industry_list()
        return df.sort_values("pct_change", ascending=False).reset_index(drop=True)
    except Exception as e:
        logger.error(f"获取行业排名失败: {e}")
        return pd.DataFrame()


def industry_fund_flow_ranking(provider: AKShareProvider) -> pd.DataFrame:
    """获取行业资金流向排名

    Returns:
        DataFrame [industry_name, pct_change, main_net, ...]
        按主力净流入降序排列
    """
    try:
        df = provider.get_industry_fund_flow()
        return df.sort_values("main_net", ascending=False).reset_index(drop=True)
    except Exception as e:
        logger.error(f"获取行业资金流向失败: {e}")
        return pd.DataFrame()


def stock_industry_position(
    code: str,
    provider: AKShareProvider,
    storage: Storage,
) -> dict:
    """分析个股在行业中的定位

    Returns:
        dict with keys:
        - industry_name: 所属行业
        - industry_rank: 行业在全市场的排名
        - industry_total: 行业总数
        - industry_pct_change: 行业涨跌幅
        - stock_vs_industry: 个股相对行业的超额收益
        - industry_fund_net: 行业主力资金净流入
    """
    result = {"industry_name": "", "found": False}

    # 查找所属行业
    industry_name = storage.get_industry_for_stock(code)
    if not industry_name:
        return result

    result["industry_name"] = industry_name
    result["found"] = True

    # 行业排名
    try:
        ranking = industry_ranking(provider)
        if not ranking.empty:
            idx = ranking[ranking["industry_name"] == industry_name].index
            if len(idx) > 0:
                result["industry_rank"] = int(idx[0]) + 1
                result["industry_total"] = len(ranking)
                result["industry_pct_change"] = float(ranking.loc[idx[0], "pct_change"])
    except Exception:
        pass

    # 行业资金流向
    try:
        fund_flow = industry_fund_flow_ranking(provider)
        if not fund_flow.empty:
            row = fund_flow[fund_flow["industry_name"] == industry_name]
            if not row.empty:
                result["industry_fund_net"] = float(row.iloc[0]["main_net"])
    except Exception:
        pass

    return result


def get_industry_chain(industry_name: str) -> dict | None:
    """查找行业所属的产业链

    Returns:
        dict {"chain_name": str, "position": str, "upstream": [...], "midstream": [...], "downstream": [...]}
        or None if not found
    """
    industry_lower = industry_name.lower()
    for chain_name, chain in INDUSTRY_CHAINS.items():
        for position, industries in chain.items():
            for ind in industries:
                if ind in industry_name or industry_name in ind:
                    return {
                        "chain_name": chain_name,
                        "position": position,
                        "upstream": chain.get("上游", []),
                        "midstream": chain.get("中游", []),
                        "downstream": chain.get("下游", []),
                    }
    return None


def format_industry_summary(position: dict) -> str:
    """将行业定位格式化为文本（供 prompt 注入）"""
    if not position.get("found"):
        return "暂无行业归属数据（需要先运行行业数据初始化）"

    lines = [f"所属行业: {position['industry_name']}"]

    if "industry_rank" in position:
        lines.append(
            f"行业排名: {position['industry_rank']}/{position['industry_total']}"
            f"（今日涨跌 {position.get('industry_pct_change', 0):+.2f}%）"
        )

    if "industry_fund_net" in position:
        lines.append(f"行业主力资金净流入: {position['industry_fund_net']:.2f}亿")

    # 产业链
    chain = get_industry_chain(position["industry_name"])
    if chain:
        lines.append(f"所属产业链: {chain['chain_name']}（{chain['position']}）")
        lines.append(f"  上游: {', '.join(chain['upstream'])}")
        lines.append(f"  中游: {', '.join(chain['midstream'])}")
        lines.append(f"  下游: {', '.join(chain['downstream'])}")

    return "\n".join(lines)
