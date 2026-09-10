"""
Ingests economic time series from the FRED API into raw.fred_observations.

Run:
    python -m src.ingest.fred_ingest
"""
import logging
import os
import sys
import time

import requests
from dotenv import load_dotenv
from sqlalchemy import text

from src.db.connection import get_engine

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

FRED_API_KEY = os.environ.get("FRED_API_KEY")
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

SERIES_IDS = {
    "UNRATE": "Unemployment Rate",
}

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


def fetch_series(series_id: str) -> list[dict]:
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(FRED_BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data.get("observations", [])
        except requests.RequestException as exc:
            logger.warning("Attempt %d/%d failed for %s: %s", attempt, MAX_RETRIES, series_id, exc)
            if attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    return []


def load_observations(series_id: str, observations: list[dict]) -> int:
    if not observations:
        return 0

    engine = get_engine()
    insert_sql = text(
        """
        INSERT INTO raw.fred_observations (series_id, observation_date, value)
        VALUES (:series_id, :observation_date, :value)
        ON CONFLICT DO NOTHING
        """
    )

    rows = [
        {"series_id": series_id, "observation_date": obs["date"], "value": obs["value"]}
        for obs in observations
    ]

    with engine.begin() as conn:
        conn.execute(insert_sql, rows)

    return len(rows)


def run() -> None:
    if not FRED_API_KEY:
        logger.error("FRED_API_KEY is not set. Please check the .env file.")
        sys.exit(1)

    total_rows = 0
    for series_id, series_name in SERIES_IDS.items():
        logger.info("Fetching data for series: %s (%s)", series_name, series_id)
        observations = fetch_series(series_id)
        rows_inserted = load_observations(series_id, observations)
        total_rows += rows_inserted
        logger.info("Inserted %d rows for series: %s", rows_inserted, series_id)

    logger.info("Done. %d total observation rows processed.", total_rows)


if __name__ == "__main__":
    run()
