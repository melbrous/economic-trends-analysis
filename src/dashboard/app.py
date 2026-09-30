"""
Streamlit dashboard for the Economic Trends Analytics Platform.

Run:
    streamlit run src/dashboard/app.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.db.connection import get_engine

st.set_page_config(page_title="Economic Trends Dashboard", layout="wide")


@st.cache_data(ttl=3600)
def load_series_list() -> pd.DataFrame:
    engine = get_engine()
    return pd.read_sql("SELECT series_id, series_name FROM marts.dim_series ORDER BY series_name", engine)


@st.cache_data(ttl=3600)
def load_observations(series_id: str) -> pd.DataFrame:
    engine = get_engine()
    query = """
        SELECT observation_date, value
        FROM marts.fact_observations
        WHERE series_id = %(series_id)s
        ORDER BY observation_date
    """
    return pd.read_sql(query, engine, params={"series_id": series_id})


def compute_yoy_change(df: pd.DataFrame) -> pd.DataFrame:
    """
    Resample to monthly averages, then compute % change vs. the same month
    one year earlier. Works even for weekly series (like mortgage rates)
    by first collapsing to monthly frequency.
    """
    df = df.copy()
    df["observation_date"] = pd.to_datetime(df["observation_date"])

    monthly = (
        df.set_index("observation_date")["value"]
        .resample("MS")
        .mean()
        .to_frame()
    )
    monthly["yoy_pct_change"] = monthly["value"].pct_change(periods=12) * 100
    return monthly.reset_index()


def main() -> None:
    st.title("Economic Trends Dashboard")
    st.caption("Data sourced from FRED (Federal Reserve Economic Data)")

    series_df = load_series_list()

    if series_df.empty:
        st.warning(
            "No data found. Run the ingestion and transform jobs first:\n\n"
            "python -m src.ingest.fred_ingest\n"
            "python -m src.transform.transform"
        )
        return

    series_options = dict(zip(series_df["series_name"], series_df["series_id"]))
    selected_names = st.multiselect(
        "Choose one or more series to view",
        options=list(series_options.keys()),
        default=[list(series_options.keys())[0]],
    )

    show_yoy = st.checkbox("Show year-over-year % change", value=False)

    if not selected_names:
        st.info("Select at least one series above.")
        return

    for name in selected_names:
        series_id = series_options[name]
        df = load_observations(series_id)

        st.subheader(name)
        if df.empty:
            st.write("No data available.")
            continue

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        delta = latest["value"] - prev["value"]
        st.metric(label=f"Latest ({latest['observation_date']})", value=f"{latest['value']:.2f}", delta=f"{delta:+.2f}")

        fig = px.line(df, x="observation_date", y="value")
        fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=350)
        st.plotly_chart(fig, use_container_width=True)

        if show_yoy:
            yoy_df = compute_yoy_change(df)
            yoy_df = yoy_df.dropna(subset=["yoy_pct_change"])

            if yoy_df.empty:
                st.caption("Not enough history yet to compute a year-over-year change.")
            else:
                latest_yoy = yoy_df.iloc[-1]
                st.caption(
                    f"Year-over-year change as of {latest_yoy['observation_date'].date()}: "
                    f"{latest_yoy['yoy_pct_change']:+.2f}%"
                )
                yoy_fig = px.line(
                    yoy_df, x="observation_date", y="yoy_pct_change",
                    labels={"yoy_pct_change": "YoY % change"},
                )
                yoy_fig.add_hline(y=0, line_dash="dot", line_color="gray")
                yoy_fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250)
                st.plotly_chart(yoy_fig, use_container_width=True)


if __name__ == "__main__":
    main()
