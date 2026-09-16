"""
Transforms data from the `raw` schema into the analysis-ready `marts` star
schema: dim_series, dim_date, fact_observations.

Run:
    python -m src.transform.transform
"""
import logging

from sqlalchemy import text

from src.db.connection import get_engine
from src.ingest.fred_ingest import SERIES_IDS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def upsert_dim_series() -> None:
    engine = get_engine()
    upsert_sql = text(
        """
        INSERT INTO marts.dim_series (series_id, series_name)
        VALUES (:series_id, :series_name)
        ON CONFLICT (series_id) DO UPDATE SET series_name = EXCLUDED.series_name
        """
    )
    with engine.begin() as conn:
        for series_id, series_name in SERIES_IDS.items():
            conn.execute(upsert_sql, {"series_id": series_id, "series_name": series_name})
    logger.info("dim_series updated (%d series)", len(SERIES_IDS))


def populate_dim_date() -> None:
    engine = get_engine()
    sql = text(
        """
        INSERT INTO marts.dim_date (date_day, year, quarter, month, month_name, day_of_week)
        SELECT DISTINCT
            observation_date::date,
            EXTRACT(YEAR FROM observation_date::date)::int,
            EXTRACT(QUARTER FROM observation_date::date)::int,
            EXTRACT(MONTH FROM observation_date::date)::int,
            TO_CHAR(observation_date::date, 'Month'),
            EXTRACT(DOW FROM observation_date::date)::int
        FROM raw.fred_observations
        ON CONFLICT (date_day) DO NOTHING
        """
    )
    with engine.begin() as conn:
        result = conn.execute(sql)
    logger.info("dim_date populated (%d new rows)", result.rowcount)


def populate_fact_observations() -> None:
    engine = get_engine()
    sql = text(
        """
        INSERT INTO marts.fact_observations (series_id, observation_date, value)
        SELECT DISTINCT ON (series_id, observation_date)
            series_id,
            observation_date,
            NULLIF(value, '.')::numeric
        FROM raw.fred_observations
        ORDER BY series_id, observation_date, ingested_at DESC
        ON CONFLICT (series_id, observation_date)
        DO UPDATE SET value = EXCLUDED.value
        """
    )
    with engine.begin() as conn:
        result = conn.execute(sql)
    logger.info("fact_observations upserted (%d rows affected)", result.rowcount)


def run() -> None:
    upsert_dim_series()
    populate_dim_date()
    populate_fact_observations()
    logger.info("Transform complete.")


if __name__ == "__main__":
    run()
