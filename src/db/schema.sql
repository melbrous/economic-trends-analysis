CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.fred_observations (
    id                BIGSERIAL PRIMARY KEY,
    series_id         TEXT NOT NULL,
    observation_date  DATE NOT NULL,
    value             TEXT,              -- kept as TEXT: FRED sends "." for missing values
    ingested_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (series_id, observation_date, ingested_at)
);

CREATE INDEX IF NOT EXISTS idx_raw_fred_series_date
    ON raw.fred_observations (series_id, observation_date);