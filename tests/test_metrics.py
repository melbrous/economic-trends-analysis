import datetime as dt

import pandas as pd

from src.analysis.metrics import compute_yoy_change


def _monthly_df(values, start="2020-01-01"):
    dates = pd.date_range(start=start, periods=len(values), freq="MS")
    return pd.DataFrame({"observation_date": dates, "value": values})


def test_yoy_computes_expected_percent_change():
    # 12 months at 100, then 12 months at 110 -> +10% YoY from month 13 onward
    df = _monthly_df([100.0] * 12 + [110.0] * 12)
    result = compute_yoy_change(df).dropna(subset=["yoy_pct_change"])
    assert len(result) == 12
    assert all(abs(v - 10.0) < 1e-6 for v in result["yoy_pct_change"])


def test_first_year_has_no_yoy_value():
    df = _monthly_df([100.0] * 24)
    result = compute_yoy_change(df)
    assert result["yoy_pct_change"].iloc[:12].isna().all()


def test_accepts_python_date_objects():
    # Regression test: Postgres DATE columns arrive as plain date objects,
    # which broke .resample() until we converted them with pd.to_datetime.
    dates = [dt.date(2020 + i // 12, i % 12 + 1, 1) for i in range(24)]
    df = pd.DataFrame({"observation_date": dates, "value": [100.0] * 12 + [110.0] * 12})
    result = compute_yoy_change(df)
    assert len(result) == 24


def test_weekly_data_is_collapsed_to_monthly():
    # 104 weekly points (~2 years) should become 24 monthly rows
    dates = pd.date_range("2020-01-05", periods=104, freq="W")
    df = pd.DataFrame({"observation_date": dates, "value": range(104)})
    result = compute_yoy_change(df)
    assert len(result) == 24
    assert result["observation_date"].dt.day.eq(1).all()


def test_input_dataframe_is_not_mutated():
    df = _monthly_df([100.0] * 24)
    before = df.copy()
    compute_yoy_change(df)
    pd.testing.assert_frame_equal(df, before)
