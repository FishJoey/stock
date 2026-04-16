"""预警系统"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import pandas as pd
from loguru import logger


class AlertType(Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    VOLUME_SURGE = "volume_surge"
    MACD_GOLDEN_CROSS = "macd_golden_cross"
    MACD_DEATH_CROSS = "macd_death_cross"
    RSI_OVERBOUGHT = "rsi_overbought"
    RSI_OVERSOLD = "rsi_oversold"
    LIMIT_UP = "limit_up"
    LIMIT_DOWN = "limit_down"


@dataclass
class AlertRule:
    """预警规则"""
    code: str
    alert_type: AlertType
    threshold: float = 0.0
    enabled: bool = True
    description: str = ""


@dataclass
class AlertEvent:
    """触发的预警事件"""
    rule: AlertRule
    triggered_at: datetime = field(default_factory=datetime.now)
    current_value: float = 0.0
    message: str = ""


class AlertEngine:
    """预警引擎"""

    def __init__(self):
        self.rules: list[AlertRule] = []
        self.history: list[AlertEvent] = []

    def add_rule(self, rule: AlertRule):
        self.rules.append(rule)

    def remove_rule(self, code: str, alert_type: AlertType):
        self.rules = [r for r in self.rules if not (r.code == code and r.alert_type == alert_type)]

    def evaluate(self, code: str, data: pd.Series | dict) -> list[AlertEvent]:
        """评估某只股票的所有规则

        Args:
            code: 股票代码
            data: 当前数据，包含 close, volume, macd_hist, rsi 等字段

        Returns:
            触发的预警事件列表
        """
        if isinstance(data, pd.Series):
            data = data.to_dict()

        events = []
        for rule in self.rules:
            if not rule.enabled or rule.code != code:
                continue

            event = self._check_rule(rule, data)
            if event:
                events.append(event)
                self.history.append(event)
                logger.info(f"[预警] {event.message}")

        return events

    def _check_rule(self, rule: AlertRule, data: dict) -> AlertEvent | None:
        close = data.get("close", 0)
        volume = data.get("volume", 0)

        match rule.alert_type:
            case AlertType.PRICE_ABOVE:
                if close > rule.threshold:
                    return AlertEvent(rule, current_value=close, message=f"{rule.code} 价格 {close:.2f} 突破 {rule.threshold:.2f}")

            case AlertType.PRICE_BELOW:
                if close < rule.threshold:
                    return AlertEvent(rule, current_value=close, message=f"{rule.code} 价格 {close:.2f} 跌破 {rule.threshold:.2f}")

            case AlertType.VOLUME_SURGE:
                avg_vol = data.get("vol_ma5", data.get("avg_volume", 0))
                if avg_vol > 0 and volume > avg_vol * rule.threshold:
                    ratio = volume / avg_vol
                    return AlertEvent(rule, current_value=ratio, message=f"{rule.code} 成交量异动 {ratio:.1f}倍")

            case AlertType.RSI_OVERBOUGHT:
                rsi_val = data.get("rsi12", data.get("rsi6", 0))
                if rsi_val > rule.threshold:
                    return AlertEvent(rule, current_value=rsi_val, message=f"{rule.code} RSI={rsi_val:.1f} 超买")

            case AlertType.RSI_OVERSOLD:
                rsi_val = data.get("rsi12", data.get("rsi6", 0))
                if rsi_val < rule.threshold:
                    return AlertEvent(rule, current_value=rsi_val, message=f"{rule.code} RSI={rsi_val:.1f} 超卖")

            case AlertType.LIMIT_UP:
                if data.get("is_limit_up", False):
                    return AlertEvent(rule, current_value=close, message=f"{rule.code} 涨停 {close:.2f}")

            case AlertType.LIMIT_DOWN:
                if data.get("is_limit_down", False):
                    return AlertEvent(rule, current_value=close, message=f"{rule.code} 跌停 {close:.2f}")

        return None

    def get_history(self, code: str | None = None, limit: int = 50) -> list[AlertEvent]:
        """获取预警历史"""
        events = self.history if code is None else [e for e in self.history if e.rule.code == code]
        return events[-limit:]
