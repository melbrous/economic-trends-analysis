"""
Analysis helpers: pure functions that take DataFrames and return DataFrames.
Kept separate from the Streamlit app so they can be unit tested.
"""
import pandas as pd


def compute_yoy_change(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resample to monthly averages, then compute % change vs. the same month
    one year earlier. Works for weekly series (like mortgage rates) by first
    collapsing to monthly frequency.

    Expects columns: observation_date, value.
    Returns columns: observation_date, value, yoy_pct_change.
    """
    df = df.copy()
    df["observation_date"] = pd.to_datetime(df["observation_date"])

    monthly = (
        df.set_index("observation_date")["value"]
        .resample("MS")
        .mean()
        .to_frame()
    )
    monthly["yoy_pct_change"] = monthly["value"].pct_change(periods=12, fill_method=None) * 100
    return monthly.reset_index()
