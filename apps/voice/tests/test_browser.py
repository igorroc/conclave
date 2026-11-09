import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.skipif(os.environ.get("VOICE_BROWSER_TEST") != "1", reason="Teste real opt-in: VOICE_BROWSER_TEST=1")


def test_real_browser():
    from playwright.sync_api import sync_playwright

    root = Path(__file__).resolve().parents[1]
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", 8765)) == 0:
            pytest.skip("A porta 8765 está ocupada; servidor existente preservado.")
    process = subprocess.Popen([sys.executable, "-X", "utf8", "server.py"], cwd=root,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                if httpx.get("http://127.0.0.1:8765/api/health").json()["status"] == "ready":
                    break
            except httpx.HTTPError:
                pass
            if process.poll() is not None:
                pytest.fail("Servidor encerrou antes de ficar pronto.")
            time.sleep(0.2)
        else:
            pytest.fail("Servidor não ficou pronto.")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(channel="msedge", headless=True)
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto("http://127.0.0.1:8765")
            page.wait_for_function("!document.querySelector('#generate').disabled")
            assert page.locator("#specialist option").count() == 10
            assert page.locator("#samples audio").count() == 9
            page.locator("#voice").select_option("pm_alex")
            page.locator("#text").fill("Olá. Vamos avaliar o Conclave com clareza e objetividade.")
            page.locator("#enqueue").click()
            page.locator("#specialist").select_option("hater")
            page.locator("#voice").select_option("pm_santa")
            page.locator("#text").fill("Precisamos verificar as hipóteses antes de ampliar o investimento.")
            page.locator("#enqueue").click()
            page.locator("#specialist").select_option("maestro")
            assert page.locator("#voice").input_value() == "pm_alex"
            assert page.locator("#queue li").count() == 2
            speakers = []
            page.on("request", lambda request: speakers.append(request.post_data_json["specialist_id"])
                    if request.url.endswith("/api/speech") else None)
            page.locator("#playQueue").click()
            page.wait_for_function("() => document.querySelector('#audio').currentTime > 0", timeout=30000)
            page.locator("#audio").evaluate("audio => audio.pause()")
            paused = page.locator("#audio").evaluate("audio => audio.currentTime")
            page.wait_for_timeout(250)
            assert page.locator("#audio").evaluate("audio => audio.currentTime") == paused
            page.locator("#audio").evaluate("audio => audio.play()")
            page.wait_for_function("() => document.querySelector('#status').textContent.startsWith('Reprodução concluída')", timeout=60000)
            assert speakers == ["maestro", "hater"]
            with page.expect_download() as download:
                page.locator("#download").click()
            path = download.value.path()
            assert Path(path).read_bytes()[:4] == b"RIFF"
            page.locator("#generate").click()
            page.wait_for_function("() => document.querySelector('#status').textContent.startsWith('Gerando')")
            page.locator("#stop").click()
            assert page.locator("#download").is_hidden()
            assert not page.locator("#audio").get_attribute("src")
            page.locator("#text").fill("Esta é uma nova solicitação após cancelar a geração anterior.")
            page.locator("#generate").click()
            page.wait_for_function("() => document.querySelector('#audio').currentTime > 0", timeout=30000)
            page.locator("#stop").click()
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
            assert errors == []
            browser.close()
    finally:
        process.terminate()
        process.wait(timeout=30)


def test_browser_rounds_and_profiles():
    import json

    from playwright.sync_api import expect, sync_playwright

    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    saved = {item["id"]: dict(item["defaults"]) for item in catalog["specialists"]}
    long_text = "😀 Evidência conservadora, sem omitir ressalvas. " * 40
    envelope = {
        "schema_version": 1, "round_id": "round-one", "project_id": "QG-BRAINS-01",
        "title": "<img src=x onerror=alert(1)> Conselho", "session_id": "test",
        "status": "partial", "interventions": [
            {"intervention_id": "a", "specialist_id": "hater", "phase": "analysis",
             "text": long_text, "reply_to": [], "order": 0},
            {"intervention_id": "c", "specialist_id": "hater", "phase": "counterpoint",
             "text": "Contraponto <script>indesejado()</script> literal.", "reply_to": ["a"], "order": 1},
        ], "synthesis": {
            "intervention_id": "s", "specialist_id": "maestro", "phase": "synthesis",
            "text": "Síntese com incertezas e próximo passo.", "reply_to": [], "order": 2,
        }, "failures": [{"specialist_id": "mvpzinho", "phase": "analysis", "code": "unavailable"}],
    }
    rounds = {}
    speech = []
    writes = []
    reject_save = False

    def route_request(route):
        nonlocal saved
        request = route.request
        path = request.url.split("127.0.0.1:18765", 1)[1]
        headers = {"Cache-Control": "no-store"}

        def respond(value, status=200):
            route.fulfill(status=status, json=value, headers=headers)

        if path in ("/", "/app.js", "/style.css"):
            filename = "index.html" if path == "/" else path[1:]
            media = {"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css"}
            route.fulfill(body=(root / "web" / filename).read_text(encoding="utf-8"),
                          content_type=media[filename], headers=headers)
        elif path == "/api/catalog":
            respond(catalog)
        elif path == "/api/health":
            respond({"status": "ready", "pending": 0})
        elif path == "/api/samples":
            respond({"results": []})
        elif path == "/api/profiles":
            if request.method == "PUT":
                writes.append(request)
                if reject_save:
                    respond({"detail": "Échec local"}, 503)
                    return
                saved = request.post_data_json["profiles"]
            respond({"schema_version": 1, "profiles": saved, "load_error": False})
        elif path == "/api/rounds":
            respond({"rounds": [
                {**{key: item[key] for key in ("round_id", "project_id", "title", "status")},
                 "expires_at": time.time() + 7200} for item in reversed(list(rounds.values()))
            ], "retention": {"max_rounds": 20, "ttl_seconds": 7200, "max_bytes": 2621440}})
        elif path.startswith("/api/rounds/"):
            key = path.rsplit("/", 1)[1]
            if request.method == "DELETE":
                rounds.pop(key, None)
                route.fulfill(status=204)
            elif key in rounds:
                respond(rounds[key])
            else:
                respond({"detail": "Rodada ausente ou expirada."}, 404)
        elif path == "/api/speech":
            speech.append(request.post_data_json)
            route.fulfill(body=b"RIFF-fake-audio", content_type="audio/wav")
        else:
            route.fulfill(status=404)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.route("**/*", route_request)
        page.add_init_script("""
            window.playCalls = 0;
            document.addEventListener('error', event => {
                if (event.target.tagName === 'AUDIO') event.stopImmediatePropagation();
            }, true);
            HTMLMediaElement.prototype.play = function() {
                window.playCalls++;
                this.dispatchEvent(new Event('play'));
                return Promise.resolve();
            };
        """)
        page.goto("http://127.0.0.1:18765")
        expect(page.locator("#generate")).to_be_enabled()
        assert page.locator("#voice").input_value() == "pm_santa"
        assert page.locator("#speed").input_value() == "0.95"
        for name in ("Dona do Contra", "Sherlocka", "MVPzinha", "Doutora B.O."):
            assert name in page.locator("#specialist").inner_text()
        page.locator("#voice").select_option("pm_alex")
        page.locator("#speed").fill("1.07")
        page.locator("#speed").dispatch_event("change")
        page.locator("#saveProfiles").click()
        expect(page.locator("#profileStatus")).to_have_text("Perfis salvos no serviço local.")
        assert len(writes[-1].post_data_json["profiles"]) == 10
        assert writes[-1].headers["origin"] == "http://127.0.0.1:18765"
        page.reload()
        expect(page.locator("#speed")).to_have_value("1.07")
        expect(page.locator("#voice")).to_have_value("pm_alex")
        reject_save = True
        page.locator("#voice").select_option("pf_dora")
        page.locator("#saveProfiles").click()
        expect(page.locator("#profileStatus")).to_contain_text("Edições preservadas")
        assert page.locator("#voice").input_value() == "pf_dora"
        assert saved["maestro"]["voice"] == "pm_alex"
        reject_save = False
        page.locator("#resetProfiles").click()
        expect(page.locator("#profileStatus")).to_have_text("Padrões restaurados e salvos.")
        assert saved["maestro"] == {"voice": "pm_santa", "speed": 0.95}
        page.reload()
        expect(page.locator("#speed")).to_have_value("0.95")

        rounds[envelope["round_id"]] = envelope
        expect(page.locator("#roundSelect option")).to_have_count(2, timeout=6000)
        assert speech == []
        assert page.evaluate("window.playCalls") == 0
        page.locator("#roundSelect").select_option("round-one")
        expect(page.locator("#roundDetail article")).to_have_count(3)
        assert page.locator("#roundDetail img, #roundDetail script").count() == 0
        expect(page.locator("#roundDetail")).to_contain_text("Responde a: Dona do Contra (Análise)")
        expect(page.locator("#roundDetail")).to_contain_text("MVPzinha")
        page.locator("#roundMode").select_option("synthesis")
        assert speech == []
        page.locator("#playRound").click()
        page.wait_for_function("window.playCalls === 1")
        assert [item["intervention_id"] for item in speech] == ["s"]
        assert "voice" not in speech[0] and "speed" not in speech[0]
        expect(page.locator("#roundSelect")).to_be_disabled()
        second = {**envelope, "round_id": "round-two", "title": "Nova rodada"}
        rounds["round-two"] = second
        expect(page.locator("#roundSelect option")).to_have_count(3, timeout=6000)
        assert page.locator("#roundSelect").input_value() == "round-one"
        assert len(speech) == 1
        page.locator("#audio").evaluate("a => a.dispatchEvent(new Event('ended'))")
        expect(page.locator("#status")).to_contain_text("Reprodução concluída")
        page.locator("#roundMode").select_option("full")
        page.locator("#playRound").click()
        expected = page.evaluate("roundItems(selectedRound)")
        for index in range(len(expected)):
            page.wait_for_function("n => window.playCalls === n", arg=index + 2)
            page.locator("#audio").evaluate("a => a.dispatchEvent(new Event('ended'))")
        expect(page.locator("#status")).to_contain_text("Reprodução concluída")
        assert speech[1:] == expected
        assert [item["intervention_id"] for item in speech[1:]][-2:] == ["c", "s"]
        reconstructed = "".join(item["text"] for item in speech[1:] if item["intervention_id"] == "a")
        assert reconstructed == long_text
        for item in speech[1:]:
            original = next(entry for entry in [*envelope["interventions"], envelope["synthesis"]]
                            if entry["intervention_id"] == item["intervention_id"])["text"]
            start = item["text_start"]
            assert item["text"] == original[start:start + len(item["text"])]
            assert len(item["text"]) <= 1000

        page.locator("#playRound").click()
        page.wait_for_function("n => window.playCalls === n", arg=len(expected) + 2)
        rounds.pop("round-one")  # Simulate TTL eviction while audio is active.
        expect(page.locator("#status")).to_contain_text("reprodução interrompida", timeout=6000)
        assert not page.locator("#audio").get_attribute("src")
        assert page.locator("#download").is_hidden()
        assert page.locator("#roundDetail").inner_text() == ""
        page.locator("#roundSelect").select_option("round-two")
        expect(page.locator("#playRound")).to_be_enabled()
        page.locator("#playRound").click()
        page.wait_for_function("n => window.playCalls === n", arg=len(expected) + 3)
        page.locator("#deleteRound").click()
        expect(page.locator("#status")).to_contain_text("reprodução interrompida")
        assert not page.locator("#audio").get_attribute("src")
        assert rounds == {}
        assert page.evaluate("localStorage.length + sessionStorage.length") == 0
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        assert errors == []
        browser.close()
