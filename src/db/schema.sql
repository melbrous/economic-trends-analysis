CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.fred_observations (
    id                BIGSERIAL PRIMARY KEY,
    series_id         TEXT NOT NULL,
    observation_date  DATE NOT NULL,
    value             TEXT,
    ingested_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (series_id, observation_date, ingested_at)
);

CREATE INDEX IF NOT EXISTS idx_raw_fred_series_date
    ON raw.fred_observations (series_id, observation_date);

CREATE SCHEMA IF NOT EXISTS marts;

CREATE TABLE IF NOT EXISTS marts.dim_series (
    series_id     TEXT PRIMARY KEY,
    series_name   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS marts.dim_date (
    date_day      DATE PRIMARY KEY,
    year          INT NOT NULL,
    quarter       INT NOT NULL,
    month         INT NOT NULL,
    month_name    TEXT NOT NULL,
    day_of_week   INT NOT NULL
);

CREATE TABLE IF NOT EXISTS marts.fact_observations (
    series_id         TEXT NOT NULL REFERENCES marts.dim_series(series_id),
    observation_date  DATE NOT NULL REFERENCES marts.dim_date(date_day),
    value             NUMERIC,
    PRIMARY KEY (series_id, observation_date)
);

CREATE INDEX IF NOT EXISTS idx_fact_obs_date
    ON marts.fact_observations (observation_date);
