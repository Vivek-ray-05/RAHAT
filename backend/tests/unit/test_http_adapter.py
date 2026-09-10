import httpx

from app.ingestion.http_adapter import HttpWeatherAdapter


def _fake_response(payload: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json=payload, request=httpx.Request("GET", "https://api.open-meteo.com/v1/forecast"))


def test_poll_or_receive_fetches_and_normalizes_real_shaped_response(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        assert params["latitude"] == 12.9591
        assert params["longitude"] == 77.6974
        return _fake_response({"current": {"precipitation": 4.2, "rain": 4.2, "temperature_2m": 24.1}})

    monkeypatch.setattr(httpx, "get", fake_get)

    adapter = HttpWeatherAdapter(zone_coords={1: (12.9591, 77.6974)})
    readings = adapter.poll_or_receive()

    assert len(readings) == 1
    assert readings[0]["zone_id"] == 1
    assert readings[0]["event_type"] == "rainfall_mm"
    assert readings[0]["value"] == 4.2


def test_normalize_produces_a_valid_event_with_real_provenance(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        return _fake_response({"current": {"precipitation": 1.5}})

    monkeypatch.setattr(httpx, "get", fake_get)

    adapter = HttpWeatherAdapter(zone_coords={1: (12.9591, 77.6974)}, simulation_run_id=7)
    raw = adapter.poll_or_receive()[0]
    event = adapter.normalize(raw)

    assert event.source == "open_meteo_http"
    assert event.zone_id == 1
    assert event.value == 1.5
    assert event.confidence == 0.9
    assert event.provenance["provider"] == "open-meteo.com"
    assert event.simulation_run_id == 7


def test_unreachable_provider_is_skipped_not_raised(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "get", fake_get)

    adapter = HttpWeatherAdapter(zone_coords={1: (12.9591, 77.6974), 2: (12.9304, 77.6784)})
    readings = adapter.poll_or_receive()

    assert readings == []


def test_non_200_response_is_skipped_not_raised(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        return _fake_response({"error": True, "reason": "bad request"}, status_code=400)

    monkeypatch.setattr(httpx, "get", fake_get)

    adapter = HttpWeatherAdapter(zone_coords={1: (12.9591, 77.6974)})
    readings = adapter.poll_or_receive()

    assert readings == []


def test_multiple_zones_each_get_their_own_reading(monkeypatch):
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(params)
        return _fake_response({"current": {"precipitation": 2.0}})

    monkeypatch.setattr(httpx, "get", fake_get)

    adapter = HttpWeatherAdapter(zone_coords={1: (12.9591, 77.6974), 2: (12.9304, 77.6784)})
    readings = adapter.poll_or_receive()

    assert len(readings) == 2
    assert len(calls) == 2
    assert {r["zone_id"] for r in readings} == {1, 2}


def test_ingest_persists_a_real_sensor_event_row(session, monkeypatch, make_run, make_zone):
    def fake_get(url, params=None, headers=None, timeout=None):
        return _fake_response({"current": {"precipitation": 3.3}})

    monkeypatch.setattr(httpx, "get", fake_get)

    run = make_run()
    zone = make_zone()
    adapter = HttpWeatherAdapter(zone_coords={zone.id: (12.9591, 77.6974)}, simulation_run_id=run.id)
    rows = adapter.ingest_batch(session)

    assert len(rows) == 1
    assert rows[0].id is not None
    assert rows[0].source_adapter == "open_meteo_http"
    assert rows[0].value == 3.3
