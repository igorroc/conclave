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
            pytest.fail("A porta 8765 está ocupada; não interferir no servidor existente.")
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
