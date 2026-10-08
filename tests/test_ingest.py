import pytest
import requests

from src.ingest import fred_ingest


def test_series_ids_are_configured():
    assert len(fred_ingest.SERIES_IDS) > 0
    for series_id, series_name in fred_ingest.SERIES_IDS.items():
        assert series_id.isupper()
        assert series_name


class _FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"observations": [{"date": "2024-01-01", "value": "4.1"}]}


def test_fetch_series_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_get(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] < 3:
            raise requests.ConnectionError("temporary failure")
        return _FakeResponse()

    monkeypatch.setattr(fred_ingest.requests, "get", fake_get)
    monkeypatch.setattr(fred_ingest.time, "sleep", lambda seconds: None)

    result = fred_ingest.fetch_series("UNRATE")

    assert calls["n"] == 3
    assert result == [{"date": "2024-01-01", "value": "4.1"}]


def test_fetch_series_gives_up_after_max_retries(monkeypatch):
    calls = {"n": 0}

    def always_fail(*args, **kwargs):
        calls["n"] += 1
        raise requests.ConnectionError("down")

    monkeypatch.setattr(fred_ingest.requests, "get", always_fail)
    monkeypatch.setattr(fred_ingest.time, "sleep", lambda seconds: None)

    with pytest.raises(requests.ConnectionError):
        fred_ingest.fetch_series("UNRATE")

    assert calls["n"] == fred_ingest.MAX_RETRIES


def test_load_observations_with_no_data_returns_zero():
    # Early return, so no database connection is attempted
    assert fred_ingest.load_observations("UNRATE", []) == 0
