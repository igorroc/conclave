import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from engine import SPECIALISTS, Audio, normalize, segments
from server import create_app


class FakeEngine:
    def __init__(self, fail=False, delay=0):
        self.fail = fail
        self.delay = delay
        self.calls = []
        self.active = 0
        self.peak = 0
        self.started = threading.Event()

    def load(self):
        if self.fail:
            raise RuntimeError("private path")

    def synthesize(self, text, voice, speed, cancelled):
        self.active += 1
        self.peak = max(self.peak, self.active)
        self.calls.append(text)
        self.started.set()
        try:
            time.sleep(self.delay)
            if cancelled.is_set():
                raise InterruptedError()
            output = io.BytesIO()
            sf.write(output, np.zeros(240), 24000, format="WAV", subtype="PCM_16")
            return Audio(output.getvalue(), 0.01, 24000)
        finally:
            self.active -= 1


def ready(client):
    for _ in range(100):
        status = client.get("/api/health").json()["status"]
        if status != "loading":
            return status
        time.sleep(0.01)
    raise AssertionError("load timeout")


def payload(**kwargs):
    return dict(text="Olá, conselho.", specialist_id="maestro", **kwargs)


def test_normalization():
    assert normalize("R$ 1.250,50 e 25% em 08/11/2026") == "1250 reais e 50 centavos e 25 por cento em 8 de novembro de 2026"
    assert normalize("R$ 10,00") == "10 reais"


def test_segments_preserve_content():
    text = "Esta é uma frase de avaliação. " * 90
    result = segments(text)
    assert " ".join(result) == normalize(text)
    assert all(len(part) <= 350 for part in result)
    with pytest.raises(ValueError):
        segments("a" * 351)


def test_profiles_and_wav():
    with TestClient(create_app(FakeEngine()), base_url="http://127.0.0.1") as client:
        assert ready(client) == "ready"
        profiles = client.get("/api/voices").json()
        assert len(profiles["specialists"]) == 10
        for specialist in SPECIALISTS:
            response = client.post("/api/speech", json={"text": "Olá", "specialist_id": specialist})
            assert response.status_code == 200
            assert response.content[:4] == b"RIFF"
            samples, rate = sf.read(io.BytesIO(response.content))
            assert rate == 24000 and len(samples) == 240
        assert "no-store" in response.headers["cache-control"]
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


@pytest.mark.parametrize("change", [
    {"text": " "}, {"text": "a" * 6001}, {"text": "a" * 351},
    {"specialist_id": "unknown"}, {"voice": "../../file"},
    {"speed": 0}, {"speed": 2}, {"model_path": "secret"},
])
def test_invalid_inputs(change):
    with TestClient(create_app(FakeEngine()), base_url="http://localhost") as client:
        ready(client)
        data = payload()
        data.update(change)
        response = client.post("/api/speech", json=data)
        assert response.status_code == 422
        assert "secret" not in response.text


def test_security_and_body_limit():
    with TestClient(create_app(FakeEngine()), base_url="http://localhost") as client:
        ready(client)
        assert client.get("/", headers={"host": "evil.test"}).status_code == 403
        assert client.post("/api/speech", json=payload(), headers={"origin": "http://evil.test"}).status_code == 403
        assert client.get("/", headers={"sec-fetch-site": "cross-site"}).status_code == 403
        assert client.post("/api/speech", content=b"x" * 32001, headers={"content-type": "application/json"}).status_code == 413
        assert client.post("/api/speech", content="text").status_code == 415
        assert client.get("/samples/secret.wav").status_code == 404
        assert client.get("/").status_code == 200
        assert client.get("/app.js").status_code == 200
        assert client.get("/style.css").status_code == 200


def test_model_unavailable():
    with TestClient(create_app(FakeEngine(fail=True)), base_url="http://localhost") as client:
        assert ready(client) == "unavailable"
        response = client.post("/api/speech", json=payload())
        assert response.status_code == 503
        assert "private path" not in response.text


def test_timeout_keeps_capacity_until_worker_finishes():
    engine = FakeEngine(delay=0.2)
    with TestClient(create_app(engine, timeout=0.06), base_url="http://localhost") as client:
        ready(client)
        assert client.post("/api/speech", json=payload()).status_code == 504
        assert client.get("/api/health").json()["pending"] == 1
        time.sleep(0.25)
        assert client.get("/api/health").json()["pending"] == 0


def test_queue_bound_and_serialization():
    engine = FakeEngine(delay=0.3)
    with TestClient(create_app(engine), base_url="http://localhost") as client:
        ready(client)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(client.post, "/api/speech", json=payload()) for _ in range(3)]
            assert engine.started.wait(1)
            for _ in range(100):
                if client.get("/api/health").json()["pending"] == 3:
                    break
                time.sleep(0.01)
            assert client.post("/api/speech", json=payload()).status_code == 429
            assert all(f.result().status_code == 200 for f in futures)
        assert engine.peak == 1


def test_queued_timeout_is_not_synthesized():
    engine = FakeEngine(delay=0.3)
    with TestClient(create_app(engine, timeout=0.08), base_url="http://localhost") as client:
        ready(client)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(client.post, "/api/speech", json=payload())
            assert engine.started.wait(1)
            second = client.post("/api/speech", json={"text": "Queued", "specialist_id": "hater"})
            assert first.result().status_code == second.status_code == 504
        time.sleep(0.35)
        assert engine.calls == ["Olá, conselho."]
        assert client.get("/api/health").json()["pending"] == 0
