"""
Streamlit dashboard for the Economic Trends Analytics Platform.

Run:
    streamlit run src/dashboard/app.py
"""
import sys
from pathlib import Path

# Streamlit runs this file directly, so it does not automatically add the
# project root to the import path the way `python -m` does. Add it manually
# so `from src...` imports work.
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


if __name__ == "__main__":
    main()
