"""回测引擎和策略测试"""

import numpy as np
import pandas as pd
import pytest

from stock.strategy.backtest import backtest
from stock.strategy.metrics import calc_metrics
from stock.strategy.templates import MACrossStrategy, MACDStrategy, BollBreakoutStrategy, KDJRSIStrategy
from stock.risk import fixed_fraction, kelly_criterion, equal_weight, fixed_stop_loss, trailing_stop
from stock.alert import AlertEngine, AlertRule, AlertType


@pytest.fixture
def sample_df():
    """生成模拟K线数据（带趋势）"""
    np.random.seed(42)
    n = 250
    # 模拟一个先涨后跌的走势
    trend = np.concatenate([
        np.linspace(0, 3, n // 2),
        np.linspace(3, 1, n // 2),
    ])
    noise = np.cumsum(np.random.randn(n) * 0.3)
    close = 100 + trend + noise
    close = np.maximum(close, 50)  # 确保价格为正

    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n),
        "open": close + np.random.randn(n) * 0.2,
        "high": close + abs(np.random.randn(n) * 0.5),
        "low": close - abs(np.random.randn(n) * 0.5),
        "close": close,
        "volume": np.random.randint(5000, 50000, n).astype(float),
        "amount": np.random.randint(500000, 5000000, n).astype(float),
        "pct_change": np.concatenate([[0], np.diff(close) / close[:-1] * 100]),
    })


class TestBacktest:
    def test_ma_cross_backtest(self, sample_df):
        strategy = MACrossStrategy(fast=5, slow=20)
        result = backtest(sample_df, strategy)

        assert "equity_curve" in result
        assert "trades" in result
        assert "metrics" in result
        assert len(result["equity_curve"]) == len(sample_df)
        assert result["equity_curve"].iloc[0] == 1.0  # 初始净值为1

    def test_macd_backtest(self, sample_df):
        strategy = MACDStrategy()
        result = backtest(sample_df, strategy)
        assert "total_return" in result["metrics"]
        assert "max_drawdown" in result["metrics"]
        assert "sharpe_ratio" in result["metrics"]

    def test_boll_backtest(self, sample_df):
        strategy = BollBreakoutStrategy()
        result = backtest(sample_df, strategy)
        assert len(result["equity_curve"]) == len(sample_df)

    def test_kdj_rsi_backtest(self, sample_df):
        strategy = KDJRSIStrategy()
        result = backtest(sample_df, strategy)
        assert len(result["equity_curve"]) == len(sample_df)


class TestMetrics:
    def test_calc_metrics(self):
        equity = pd.Series([1.0, 1.01, 1.03, 1.02, 1.05, 1.04, 1.08])
        metrics = calc_metrics(equity)

        assert metrics["total_return"] > 0
        assert metrics["max_drawdown"] < 0
        assert "sharpe_ratio" in metrics
        assert "win_rate" in metrics

    def test_benchmark_comparison(self):
        equity = pd.Series([1.0, 1.02, 1.05, 1.03, 1.08])
        bench = pd.Series([1.0, 1.01, 1.02, 1.01, 1.03])
        metrics = calc_metrics(equity, benchmark=bench)

        assert "excess_return" in metrics
        assert metrics["excess_return"] > 0


class TestRisk:
    def test_fixed_fraction(self):
        size = fixed_fraction(1_000_000, risk_per_trade=0.02, stop_loss_pct=0.05)
        assert size == 400_000

    def test_kelly(self):
        f = kelly_criterion(win_rate=0.6, avg_win=0.02, avg_loss=0.01)
        assert 0 < f <= 1

    def test_equal_weight(self):
        w = equal_weight(1_000_000, 5)
        assert w == 200_000

    def test_stop_loss(self):
        assert fixed_stop_loss(100, 0.05) == 95
        assert trailing_stop(110, 0.08) == pytest.approx(101.2)


class TestAlert:
    def test_price_alert(self):
        engine = AlertEngine()
        engine.add_rule(AlertRule("600519", AlertType.PRICE_ABOVE, threshold=1500))

        events = engine.evaluate("600519", {"close": 1550})
        assert len(events) == 1
        assert "突破" in events[0].message

    def test_no_trigger(self):
        engine = AlertEngine()
        engine.add_rule(AlertRule("600519", AlertType.PRICE_ABOVE, threshold=2000))

        events = engine.evaluate("600519", {"close": 1500})
        assert len(events) == 0

    def test_volume_surge(self):
        engine = AlertEngine()
        engine.add_rule(AlertRule("600519", AlertType.VOLUME_SURGE, threshold=3.0))

        events = engine.evaluate("600519", {"close": 100, "volume": 40000, "vol_ma5": 10000})
        assert len(events) == 1
        assert "异动" in events[0].message
