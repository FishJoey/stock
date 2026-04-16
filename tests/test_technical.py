"""技术指标单元测试"""

import numpy as np
import pandas as pd
import pytest

from stock.analysis.technical import (
    ma, ema, macd, boll,
    kdj, rsi, cci, williams_r,
    obv, vwap, volume_ratio, volume_ma, atr,
    detect_limit, consecutive_limit_up,
)


@pytest.fixture
def sample_df():
    """生成模拟K线数据"""
    np.random.seed(42)
    n = 100
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=n),
        "open": close + np.random.randn(n) * 0.3,
        "high": close + abs(np.random.randn(n) * 0.5),
        "low": close - abs(np.random.randn(n) * 0.5),
        "close": close,
        "volume": np.random.randint(1000, 10000, n).astype(float),
        "amount": np.random.randint(100000, 1000000, n).astype(float),
        "pct_change": np.concatenate([[0], np.diff(close) / close[:-1] * 100]),
    })


class TestTrend:
    def test_ma(self, sample_df):
        result = ma(sample_df, periods=[5, 10])
        assert "ma5" in result.columns
        assert "ma10" in result.columns
        assert result["ma5"].iloc[4:].notna().all()

    def test_ema(self, sample_df):
        result = ema(sample_df, periods=[5])
        assert "ema5" in result.columns
        assert result["ema5"].notna().all()

    def test_macd(self, sample_df):
        result = macd(sample_df)
        assert "macd_dif" in result.columns
        assert "macd_dea" in result.columns
        assert "macd_hist" in result.columns

    def test_boll(self, sample_df):
        result = boll(sample_df)
        assert "boll_mid" in result.columns
        assert "boll_upper" in result.columns
        assert "boll_lower" in result.columns
        valid = result.dropna(subset=["boll_mid"])
        assert (valid["boll_upper"] >= valid["boll_mid"]).all()
        assert (valid["boll_lower"] <= valid["boll_mid"]).all()


class TestOscillator:
    def test_kdj(self, sample_df):
        result = kdj(sample_df)
        assert "kdj_k" in result.columns
        assert "kdj_d" in result.columns
        assert "kdj_j" in result.columns

    def test_rsi(self, sample_df):
        result = rsi(sample_df, periods=[6, 12])
        assert "rsi6" in result.columns
        assert "rsi12" in result.columns
        valid = result["rsi6"].dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_cci(self, sample_df):
        result = cci(sample_df)
        assert "cci" in result.columns

    def test_williams_r(self, sample_df):
        result = williams_r(sample_df)
        assert "wr" in result.columns
        valid = result["wr"].dropna()
        assert (valid <= 0).all() and (valid >= -100).all()


class TestVolume:
    def test_obv(self, sample_df):
        result = obv(sample_df)
        assert "obv" in result.columns

    def test_vwap(self, sample_df):
        result = vwap(sample_df)
        assert "vwap" in result.columns

    def test_volume_ratio(self, sample_df):
        result = volume_ratio(sample_df)
        assert "volume_ratio" in result.columns

    def test_volume_ma(self, sample_df):
        result = volume_ma(sample_df, periods=[5, 10])
        assert "vol_ma5" in result.columns
        assert "vol_ma10" in result.columns

    def test_atr(self, sample_df):
        result = atr(sample_df)
        assert "atr" in result.columns
        valid = result["atr"].dropna()
        assert (valid >= 0).all()


class TestPattern:
    def test_detect_limit(self, sample_df):
        result = detect_limit(sample_df, code="600519")
        assert "is_limit_up" in result.columns
        assert "is_limit_down" in result.columns

    def test_consecutive_limit_up(self, sample_df):
        result = consecutive_limit_up(sample_df, code="600519")
        assert "limit_up_streak" in result.columns
        assert result["limit_up_streak"].min() >= 0
