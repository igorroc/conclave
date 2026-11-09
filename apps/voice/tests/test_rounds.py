import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from test_voice import FakeEngine, ready

from profiles import (
    CATALOG,
    ProfileEnvelope,
    ProfileStore,
    default_profiles,
    resolve_specialist,
)
from rounds import MAX_ENVELOPE, TTL_SECONDS, BridgeToken, RoundEnvelope, RoundStore
from server import create_app

ORIGIN = {"origin": "http://localhost"}


def envelope(key="r1"):
    return {"schema_version": 1, "round_id": key, "project_id": "QG-BRAINS-01",
            "title": "Rodada", "session_id": "s1", "status": "complete",
            "interventions": [{"intervention_id": "a1", "specialist_id": "hater",
                               "phase": "analysis", "text": "<script>texto</script>", "order": 0}],
            "synthesis": {"intervention_id": "synthesis", "specialist_id": "maestro",
                          "phase": "synthesis", "text": "Conclusão final.", "order": 1}}


def test_catalog_and_aliases():
    assert len(CATALOG["specialists"]) == 10
    for item in CATALOG["specialists"]:
        for name in [item["id"], item["name"], *item["aliases"]]:
            assert resolve_specialist(name) == item["id"]
        assert item["defaults"]["voice"] == ("pf_dora" if item["gender"] == "feminino"
                                             else {"maestro": "pm_santa", "professor-pardal": "pm_alex",
                                                   "tio-patinhas": "pm_santa", "pablo": "pm_alex",
                                                   "seu-ze": "pm_santa", "tubarao": "pm_alex"}[item["id"]])


def test_profiles_atomic_restart_corruption(tmp_path, monkeypatch):
    path = tmp_path / "profiles.json"
    store = ProfileStore(path)
    value = default_profiles()
    value.profiles["maestro"].speed = 1.1
    store.save(value)
    assert ProfileStore(path).resolve("maestro").speed == 1.1
    before = path.read_bytes()
    def fail(*args):
        raise OSError("simulated")
    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        store.save(default_profiles())
    assert path.read_bytes() == before
    assert store.resolve("maestro").speed == 1.1
    assert list(tmp_path.iterdir()) == [path]
    path.write_text("corrupt", encoding="utf-8")
    bad = ProfileStore(path)
    assert bad.get()["load_error"]
    with pytest.raises(OSError):
        bad.save(default_profiles())
    assert path.read_text() == "corrupt"


@pytest.mark.parametrize("change", [
    {"speed": True}, {"speed": "1.0"}, {"speed": float("nan")}, {"speed": 1.3},
    {"voice": "unknown"}, {"extra": 1},
])
def test_strict_profiles(change):
    data = default_profiles().model_dump()
    data["profiles"]["maestro"].update(change)
    with pytest.raises(ValidationError):
        ProfileEnvelope.model_validate(data)


def test_retention_idempotence_and_bytes():
    now = [0]
    store = RoundStore(clock=lambda: now[0])
    item = RoundEnvelope.model_validate(envelope())
    assert store.publish(item)
    now[0] = 100
    assert not store.publish(item)
    assert store.listing()["rounds"][0]["published_at"] == 0
    changed = item.model_copy(update={"title": "Diferente"})
    with pytest.raises(ValueError):
        store.publish(changed)
    now[0] = 7200
    with pytest.raises(KeyError):
        store.get("r1")
    for i in range(21):
        store.publish(RoundEnvelope.model_validate(envelope(f"r{i}")))
    assert len(store.items) == 20 and "r0" not in store.items
    size = store.items["r1"][3]
    small = RoundStore(max_bytes=size + 10)
    small.publish(item)
    small.publish(RoundEnvelope.model_validate(envelope("r2")))
    assert list(small.items) == ["r2"]
    with pytest.raises(OverflowError):
        RoundStore(max_bytes=1).publish(item)


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(schema_version=True),
    lambda d: d.update(status="pending"),
    lambda d: d.update(extra="x"),
    lambda d: d["interventions"][0].update(specialist_id="Hater"),
    lambda d: d["interventions"][0].update(specialist_id="maestro"),
    lambda d: d["interventions"][0].update(order=True),
    lambda d: d["interventions"][0].update(text=" " ),
    lambda d: d["interventions"][0].update(reply_to=["missing"]),
    lambda d: d["synthesis"].update(specialist_id="hater"),
    lambda d: d["synthesis"].update(intervention_id="a1"),
    lambda d: d["synthesis"].update(order=3),
    lambda d: d.update(failures=[{"specialist_id": "hater", "phase": "analysis", "code": "error"}]),
])
def test_invalid_rounds(mutation):
    data = envelope()
    mutation(data)
    with pytest.raises(ValidationError):
        RoundEnvelope.model_validate(data)


def test_counterpoint():
    data = envelope()
    data["interventions"].append({"intervention_id": "c1", "specialist_id": "hater",
                                  "phase": "counterpoint", "text": "Ressalva.",
                                  "reply_to": ["a1"], "order": 1})
    data["synthesis"]["order"] = 2
    assert RoundEnvelope.model_validate(data)
    data["interventions"][1]["reply_to"] = []
    with pytest.raises(ValidationError):
        RoundEnvelope.model_validate(data)


def test_api_contract_and_speech(tmp_path):
    class RecordingEngine(FakeEngine):
        def synthesize(self, text, voice, speed, cancelled):
            self.parameters = (voice, speed)
            return super().synthesize(text, voice, speed, cancelled)
    engine = RecordingEngine()
    with TestClient(create_app(engine, data_dir=tmp_path), base_url="http://localhost") as client:
        ready(client)
        token = (tmp_path / "bridge-token").read_text()
        auth = {"authorization": "Bearer " + token}
        assert client.get("/api/catalog").json() == CATALOG
        assert token not in client.get("/api/health").text
        assert client.post("/api/rounds", json=envelope()).status_code == 401
        assert client.post("/api/rounds", json=envelope(), headers=auth).status_code == 201
        assert client.post("/api/rounds", json=envelope(), headers=auth).json()["created"] is False
        changed = envelope()
        changed["title"] = "Outra"
        assert client.post("/api/rounds", json=changed, headers=auth).status_code == 409
        assert client.get("/api/rounds").status_code == 403
        listing = client.get("/api/rounds", headers=ORIGIN)
        assert "script" not in listing.text
        assert len(listing.json()["rounds"]) == 1
        detail = client.get("/api/rounds/r1", headers=ORIGIN).json()
        assert detail["interventions"][0]["text"] == envelope()["interventions"][0]["text"]
        settings = default_profiles().model_dump()
        settings["profiles"]["hater"] = {"voice": "pm_alex", "speed": 1.1}
        assert client.put("/api/profiles", json=settings).status_code == 403
        assert client.put("/api/profiles", json=settings, headers=ORIGIN).status_code == 200
        speech = {"text": "texto", "specialist_id": "Hater", "round_id": "r1",
                  "intervention_id": "a1", "text_start": 8}
        assert client.post("/api/speech", json=speech).status_code == 200
        assert engine.parameters == ("pm_alex", 1.1)
        speech["text"] = "inventado"
        assert client.post("/api/speech", json=speech).status_code == 422
        speech["text"] = "texto"
        speech["specialist_id"] = "maestro"
        assert client.post("/api/speech", json=speech).status_code == 422
        assert client.delete("/api/rounds/r1").status_code == 403
        assert client.delete("/api/rounds/r1", headers=ORIGIN).status_code == 204
        assert client.post("/api/speech", json=speech).status_code == 404
        assert client.get("/api/rounds/r1", headers=ORIGIN).status_code == 404
        assert client.post("/api/rounds", content=b"x" * (MAX_ENVELOPE + 1),
                           headers={**auth, "content-type": "application/json"}).status_code == 413
        assert client.post("/api/rounds", json=envelope(),
                           headers={**auth, "origin": "http://evil.test"}).status_code == 403
        assert client.get("/api/rounds", headers={"sec-fetch-site": "same-site"}).status_code == 403
        for host in ["localhost/evil", "localhost?x", "localhost@evil", "localhost:bad"]:
            assert client.get("/api/catalog", headers={"host": host}).status_code == 403
        assert sorted(p.name for p in tmp_path.iterdir()) == ["bridge-token", "profiles.json"]
    assert not (tmp_path / "bridge-token").exists()
    with TestClient(create_app(FakeEngine(), data_dir=tmp_path), base_url="http://localhost") as client:
        assert (tmp_path / "bridge-token").read_text() != token
        assert client.get("/api/rounds", headers=ORIGIN).json()["rounds"] == []
        assert client.get("/api/profiles").json()["profiles"]["hater"]["speed"] == 1.1


def test_bridge_fail_closed(tmp_path, monkeypatch):
    import rounds
    if os.name == "nt":
        def fail(*args, **kwargs):
            raise OSError("ACL failed")
        monkeypatch.setattr(rounds.subprocess, "run", fail)
    else:
        monkeypatch.setattr(rounds.os, "chmod", lambda *args: (_ for _ in ()).throw(OSError()))
    bridge = BridgeToken(tmp_path)
    assert not bridge.start()
    assert not bridge.authorized("Bearer anything")
    assert not bridge.path.exists()
    with TestClient(create_app(FakeEngine(), data_dir=tmp_path), base_url="http://localhost") as client:
        assert client.post("/api/rounds", json=envelope()).status_code == 503


def test_profile_body_and_types(tmp_path):
    with TestClient(create_app(FakeEngine(), data_dir=tmp_path), base_url="http://localhost") as client:
        assert client.put("/api/profiles", content=b"x" * 16385,
                          headers={**ORIGIN, "content-type": "application/json"}).status_code == 413
        assert client.put("/api/profiles", content="x", headers=ORIGIN).status_code == 415
        data = default_profiles().model_dump()
        del data["profiles"]["hater"]
        assert client.put("/api/profiles", json=data, headers=ORIGIN).status_code == 422
        assert client.post("/api/speech", json={"text": "Olá", "specialist_id": "maestro",
                                               "speed": "1.0"}).status_code == 422
        assert not (tmp_path / "profiles.json").exists()
        assert json.loads(client.get("/api/catalog").content)["schema_version"] == 1


def round_speech():
    return {"text": "Conclusão final.", "specialist_id": "maestro",
            "round_id": "r1", "intervention_id": "synthesis"}


def invalidate_round(store, now, reason):
    if reason == "expired":
        now[0] = TTL_SECONDS
    else:
        store.delete("r1")
        if reason == "republished":
            store.publish(RoundEnvelope.model_validate(envelope()))


@pytest.mark.parametrize("reason", ["deleted", "expired", "republished"])
def test_running_round_speech_cancelled(tmp_path, reason):
    now = [0]
    store = RoundStore(clock=lambda: now[0])
    store.publish(RoundEnvelope.model_validate(envelope()))
    release = threading.Event()

    class BlockingEngine(FakeEngine):
        def synthesize(self, text, voice, speed, cancelled):
            self.cancelled = cancelled
            self.started.set()
            assert release.wait(5)
            return super().synthesize(text, voice, speed, cancelled)

    engine = BlockingEngine()
    with TestClient(create_app(engine, data_dir=tmp_path, round_store=store),
                    base_url="http://localhost") as client, ThreadPoolExecutor() as requests:
        ready(client)
        response = requests.submit(client.post, "/api/speech", json=round_speech())
        try:
            assert engine.started.wait(2)
            if reason == "deleted":
                assert client.delete("/api/rounds/r1", headers=ORIGIN).status_code == 204
            else:
                invalidate_round(store, now, reason)
            result = response.result(timeout=2)
            assert result.status_code == 404
            assert result.headers["content-type"] == "application/json"
            assert engine.cancelled.is_set()
        finally:
            release.set()
        for _ in range(100):
            if client.get("/api/health").json()["pending"] == 0:
                break
            time.sleep(0.01)
        assert client.get("/api/health").json()["pending"] == 0


@pytest.mark.parametrize("reason", ["deleted", "expired"])
def test_queued_round_speech_not_synthesized(tmp_path, reason):
    now = [0]
    store = RoundStore(clock=lambda: now[0])
    store.publish(RoundEnvelope.model_validate(envelope()))
    release = threading.Event()

    class BlockingEngine(FakeEngine):
        def synthesize(self, text, voice, speed, cancelled):
            self.started.set()
            assert release.wait(5)
            return super().synthesize(text, voice, speed, cancelled)

    engine = BlockingEngine()
    with TestClient(create_app(engine, data_dir=tmp_path, round_store=store),
                    base_url="http://localhost") as client, ThreadPoolExecutor() as requests:
        ready(client)
        first = requests.submit(client.post, "/api/speech",
                                json={"text": "Manual", "specialist_id": "maestro"})
        try:
            assert engine.started.wait(2)
            queued = requests.submit(client.post, "/api/speech", json=round_speech())
            for _ in range(100):
                if client.get("/api/health").json()["pending"] == 2:
                    break
                time.sleep(0.01)
            assert client.get("/api/health").json()["pending"] == 2
            invalidate_round(store, now, reason)
            assert queued.result(timeout=2).status_code == 404
        finally:
            release.set()
        assert first.result(timeout=2).status_code == 200
        assert engine.calls == ["Manual"]


@pytest.mark.parametrize("reason", ["deleted", "expired"])
def test_completed_round_speech_discarded(tmp_path, reason):
    now = [0]
    store = RoundStore(clock=lambda: now[0])
    store.publish(RoundEnvelope.model_validate(envelope()))

    class RemovingEngine(FakeEngine):
        def synthesize(self, text, voice, speed, cancelled):
            audio = super().synthesize(text, voice, speed, cancelled)
            self.cancelled = cancelled
            invalidate_round(store, now, reason)
            return audio

    engine = RemovingEngine()
    with TestClient(create_app(engine, data_dir=tmp_path, round_store=store),
                    base_url="http://localhost") as client:
        ready(client)
        response = client.post("/api/speech", json=round_speech())
        assert response.status_code == 404
        assert response.headers["content-type"] == "application/json"
        assert engine.cancelled.is_set()


def test_worker_validates_round_before_synthesis(tmp_path, monkeypatch):
    import server

    store = RoundStore()
    store.publish(RoundEnvelope.model_validate(envelope()))

    class RemovingExecutor(ThreadPoolExecutor):
        def submit(self, fn, *args, **kwargs):
            if fn.__name__ == "synthesize":
                def removed():
                    store.delete("r1")
                    return fn(*args, **kwargs)
                return super().submit(removed)
            return super().submit(fn, *args, **kwargs)

    monkeypatch.setattr(server, "ThreadPoolExecutor", RemovingExecutor)
    engine = FakeEngine()
    with TestClient(create_app(engine, data_dir=tmp_path, round_store=store),
                    base_url="http://localhost") as client:
        ready(client)
        assert client.post("/api/speech", json=round_speech()).status_code == 404
        assert engine.calls == []


def test_lifespan_prunes_without_requests_and_cancels_cleanup(tmp_path, monkeypatch):
    import server

    now = [0]
    expired = threading.Event()

    class ObservedStore(RoundStore):
        def prune(self):
            super().prune()
            if now[0] >= TTL_SECONDS and not self.items:
                expired.set()

    store = ObservedStore(clock=lambda: now[0])
    store.publish(RoundEnvelope.model_validate(envelope()))
    assert 0 < server.PRUNE_INTERVAL <= 30
    monkeypatch.setattr(server, "PRUNE_INTERVAL", 0.01)
    app = create_app(FakeEngine(), data_dir=tmp_path, round_store=store)
    with TestClient(app, base_url="http://localhost"):
        now[0] = TTL_SECONDS
        assert expired.wait(2)
        assert not store.items
    store.publish(RoundEnvelope.model_validate(envelope("after_shutdown")))
    now[0] += TTL_SECONDS
    time.sleep(0.05)
    assert "after_shutdown" in store.items
