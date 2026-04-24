"""大盘分析模块

提供市场状态判断、市场情绪评估等宏观分析功能。
"""

import pandas as pd
import numpy as np

from stock.constants import INDEX_CODES
from stock.data.akshare_provider import AKShareProvider
from stock.data.storage import Storage


def market_regime(index_df: pd.DataFrame) -> dict:
    """判断市场状态（牛市/熊市/震荡）

    基于均线排列和趋势方向判断：
    - 牛市: 价格在 MA20 上方，MA20 > MA60
    - 熊市: 价格在 MA20 下方，MA20 < MA60
    - 震荡: 其他情况

    Args:
        index_df: 指数日线数据（需要 close 列，至少 60 行）

    Returns:
        dict with keys: regime, ma20, ma60, close, description
    """
    if len(index_df) < 60:
        return {"regime": "数据不足", "description": "需要至少60个交易日数据"}

    close = index_df["close"].astype(float)
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()

    latest_close = close.iloc[-1]
    latest_ma20 = ma20.iloc[-1]
    latest_ma60 = ma60.iloc[-1]

    # 20日均线方向
    ma20_slope = (ma20.iloc[-1] - ma20.iloc[-5]) / ma20.iloc[-5] * 100

    if latest_close > latest_ma20 and latest_ma20 > latest_ma60:
        if ma20_slope > 0.5:
            regime = "牛市"
            desc = "多头排列，均线向上发散"
        else:
            regime = "震荡偏强"
            desc = "价格在均线上方，但上攻动能减弱"
    elif latest_close < latest_ma20 and latest_ma20 < latest_ma60:
        if ma20_slope < -0.5:
            regime = "熊市"
            desc = "空头排列，均线向下发散"
        else:
            regime = "震荡偏弱"
            desc = "价格在均线下方，但下跌动能减弱"
    else:
        regime = "震荡"
        desc = "均线交织，方向不明"

    return {
        "regime": regime,
        "close": round(latest_close, 2),
        "ma20": round(latest_ma20, 2),
        "ma60": round(latest_ma60, 2),
        "ma20_slope": round(ma20_slope, 2),
        "description": desc,
    }


def market_summary(provider: AKShareProvider, storage: Storage) -> dict:
    """生成大盘环境摘要（供 AI 研报使用）

    Returns:
        dict with keys: regime, index_changes, north_fund, description
    """
    result = {}

    # 1. 上证指数状态
    sh_df = storage.get_index_daily("sh000001")
    if sh_df.empty:
        sh_df = provider.get_index_daily("sh000001")
    if not sh_df.empty:
        result["regime"] = market_regime(sh_df)

        # 近期涨跌幅
        close = sh_df["close"].astype(float)
        if len(close) >= 20:
            result["index_pct_5d"] = round((close.iloc[-1] / close.iloc[-5] - 1) * 100, 2)
            result["index_pct_20d"] = round((close.iloc[-1] / close.iloc[-20] - 1) * 100, 2)

    # 2. 北向资金（尝试获取，失败不影响）
    try:
        north_df = provider.get_north_fund_flow()
        if not north_df.empty:
            recent = north_df.tail(5)
            result["north_net_5d"] = round(recent["north_net"].sum(), 2)
            result["north_net_latest"] = round(recent.iloc[-1]["north_net"], 2)
    except Exception:
        pass

    # 3. 大盘资金流向
    try:
        flow_df = provider.get_market_fund_flow()
        if not flow_df.empty:
            latest = flow_df.iloc[-1]
            result["main_net_latest"] = round(latest["main_net"], 2)
    except Exception:
        pass

    return result


def format_market_summary(summary: dict) -> str:
    """将大盘摘要格式化为文本（供 prompt 注入）"""
    lines = []

    regime = summary.get("regime", {})
    if regime:
        lines.append(f"市场状态: {regime.get('regime', '未知')} — {regime.get('description', '')}")
        lines.append(f"上证指数: {regime.get('close', 'N/A')}（MA20={regime.get('ma20', 'N/A')}, MA60={regime.get('ma60', 'N/A')}）")

    if "index_pct_5d" in summary:
        lines.append(f"上证近5日涨跌: {summary['index_pct_5d']:+.2f}%")
    if "index_pct_20d" in summary:
        lines.append(f"上证近20日涨跌: {summary['index_pct_20d']:+.2f}%")
    if "north_net_5d" in summary:
        lines.append(f"北向资金近5日净流入: {summary['north_net_5d']:.2f}亿")
    if "main_net_latest" in summary:
        lines.append(f"大盘主力资金净流入: {summary['main_net_latest']:.2f}亿")

    return "\n".join(lines) if lines else "暂无大盘数据"
