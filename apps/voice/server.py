import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from engine import MAX_TEXT, SPECIALISTS, VOICES, KokoroEngine

ROOT = Path(__file__).resolve().parent
MAX_BODY = 32000


class Speech(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    text: str = Field(min_length=1, max_length=MAX_TEXT)
    specialist_id: str
    voice: str = "pf_dora"
    speed: float = Field(default=1.0, ge=0.8, le=1.2)

    @field_validator("text")
    @classmethod
    def valid_text(cls, value):
        if not value.strip() or any(len(word) > 350 for word in value.split()):
            raise ValueError("Texto vazio ou palavra longa demais.")
        return value

    @field_validator("specialist_id")
    @classmethod
    def valid_specialist(cls, value):
        if value not in SPECIALISTS:
            raise ValueError("Especialista desconhecido.")
        return value

    @field_validator("voice")
    @classmethod
    def valid_voice(cls, value):
        if value not in VOICES:
            raise ValueError("Voz desconhecida.")
        return value


def create_app(engine=None, timeout=180):
    engine = engine or KokoroEngine()
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kokoro")
    state = {"status": "loading", "error": None, "pending": 0}

    @asynccontextmanager
    async def lifespan(app):
        loop = asyncio.get_running_loop()

        async def load():
            try:
                await loop.run_in_executor(executor, engine.load)
                state["status"] = "ready"
            except Exception:
                state.update(status="unavailable", error="Modelo ausente ou inválido. Execute uv run python assets.py e reinicie.")

        task = asyncio.create_task(load())
        yield
        await task
        executor.shutdown(wait=True, cancel_futures=True)

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def local_only(request, call_next):
        host = request.headers.get("host", "")
        try:
            parsed = urlsplit("http://" + host)
            valid = parsed.hostname in ("127.0.0.1", "localhost") and not parsed.username
            origin = request.headers.get("origin")
            if origin and origin != "http://" + host:
                valid = False
            if request.headers.get("sec-fetch-site") == "cross-site":
                valid = False
        except ValueError:
            valid = False
        if not valid:
            return JSONResponse({"detail": "Origem não permitida."}, status_code=403)
        response = await call_next(request)
        response.headers.update({
            "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            "Referrer-Policy": "no-referrer",
        })
        return response

    @app.get("/api/health")
    async def health():
        return dict(state)

    @app.get("/api/voices")
    async def voices():
        return {"voices": VOICES, "specialists": SPECIALISTS, "default_voice": "pf_dora",
                "language": "pt-br", "max_text": MAX_TEXT, "profiles_provisional": True}

    @app.post("/api/speech")
    async def speech(request: Request):
        if request.headers.get("content-type", "").split(";")[0] != "application/json":
            return JSONResponse({"detail": "Envie JSON."}, status_code=415)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_BODY:
                return JSONResponse({"detail": "Requisição muito grande."}, status_code=413)
        try:
            data = Speech.model_validate_json(bytes(body))
        except (ValidationError, ValueError):
            return JSONResponse({"detail": "Texto, especialista, voz ou velocidade inválidos."}, status_code=422)
        if state["status"] != "ready":
            return JSONResponse({"detail": state["error"] or "Modelo carregando."}, status_code=503)
        if state["pending"] >= 3:
            return JSONResponse({"detail": "Fila cheia. Tente novamente."}, status_code=429)
        state["pending"] += 1
        cancelled = threading.Event()
        loop = asyncio.get_running_loop()
        concurrent = executor.submit(engine.synthesize, data.text, data.voice, data.speed, cancelled)

        def finished(_):
            loop.call_soon_threadsafe(release)

        def release():
            state["pending"] -= 1

        concurrent.add_done_callback(finished)
        future = asyncio.wrap_future(concurrent)
        start = loop.time()
        try:
            while not future.done():
                if await request.is_disconnected():
                    return Response(status_code=499)
                if loop.time() - start >= timeout:
                    return JSONResponse({"detail": "Tempo limite de geração excedido."}, status_code=504)
                await asyncio.sleep(0.05)
            audio = future.result()
            return Response(audio.wav, media_type="audio/wav", headers={
                "X-Audio-Seconds": str(round(audio.seconds, 3)),
                "Content-Disposition": 'attachment; filename="conclave.wav"',
            })
        except asyncio.CancelledError:
            raise
        except Exception:
            return JSONResponse({"detail": "Falha na síntese. Tente um texto menor ou reinicie o serviço."}, status_code=500)
        finally:
            cancelled.set()
            concurrent.cancel()
            if not future.done():
                future.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)

    @app.get("/api/samples")
    async def samples():
        report = ROOT / "output" / "benchmark.json"
        if not report.exists():
            return {"results": []}
        return json.loads(report.read_text(encoding="utf-8"))

    @app.get("/samples/{filename}")
    async def sample(filename: str):
        allowed = {f"{voice}-{label}.wav" for voice in VOICES for label in ("curto", "numeros", "paragrafo")}
        if filename not in allowed or not (ROOT / "output" / filename).is_file():
            return Response(status_code=404)
        return FileResponse(ROOT / "output" / filename, media_type="audio/wav")

    @app.get("/")
    async def index():
        return FileResponse(ROOT / "web" / "index.html")

    @app.get("/app.js")
    async def javascript():
        return FileResponse(ROOT / "web" / "app.js", media_type="text/javascript")

    @app.get("/style.css")
    async def stylesheet():
        return FileResponse(ROOT / "web" / "style.css", media_type="text/css")

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app(), host="127.0.0.1", port=8765, workers=1, access_log=False)
