import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from engine import MAX_TEXT, SPECIALISTS, VOICES, KokoroEngine
from profiles import CATALOG, ProfileEnvelope, ProfileStore, resolve_specialist
from rounds import MAX_ENVELOPE, BridgeToken, Identifier, RoundEnvelope, RoundStore

ROOT = Path(__file__).resolve().parent
MAX_BODY = 32000
PRUNE_INTERVAL = 30


class Speech(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    text: str = Field(min_length=1, max_length=MAX_TEXT)
    specialist_id: str
    voice: str | None = None
    speed: float | None = Field(default=None, ge=0.8, le=1.2)
    round_id: Identifier | None = None
    intervention_id: Identifier | None = None
    text_start: int | None = Field(default=None, ge=0, le=5999)

    @model_validator(mode="after")
    def round_reference(self):
        if (self.round_id is None) != (self.intervention_id is None):
            raise ValueError("Envie round_id e intervention_id juntos.")
        if self.text_start is not None and self.round_id is None:
            raise ValueError("Trecho exige rodada.")
        return self

    @field_validator("text")
    @classmethod
    def valid_text(cls, value):
        if not value.strip() or any(len(word) > 350 for word in value.split()):
            raise ValueError("Texto vazio ou palavra longa demais.")
        return value

    @field_validator("specialist_id")
    @classmethod
    def valid_specialist(cls, value):
        return resolve_specialist(value)

    @field_validator("voice")
    @classmethod
    def valid_voice(cls, value):
        if value is not None and value not in VOICES:
            raise ValueError("Voz desconhecida.")
        return value


def create_app(engine=None, timeout=180, data_dir=None, round_store=None):
    data_dir = Path(data_dir) if data_dir is not None else ROOT / "data"
    profiles = ProfileStore(data_dir / "profiles.json")
    rounds = round_store if round_store is not None else RoundStore()
    bridge = BridgeToken(data_dir)
    engine = engine or KokoroEngine()
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="kokoro")
    state = {"status": "loading", "error": None, "pending": 0}

    @asynccontextmanager
    async def lifespan(app):
        bridge.start()
        loop = asyncio.get_running_loop()

        async def load():
            try:
                await loop.run_in_executor(executor, engine.load)
                state["status"] = "ready"
            except Exception:
                state.update(status="unavailable", error="Modelo ausente ou inválido. Execute uv run python assets.py e reinicie.")

        async def prune_rounds():
            while True:
                rounds.prune()
                await asyncio.sleep(PRUNE_INTERVAL)

        task = asyncio.create_task(load())
        cleanup_task = asyncio.create_task(prune_rounds())
        try:
            yield
        finally:
            cleanup_task.cancel()
            with suppress(asyncio.CancelledError):
                await cleanup_task
            bridge.close()
            rounds.clear()
            await task
            executor.shutdown(wait=True, cancel_futures=True)

    app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    app.state.bridge = bridge

    @app.middleware("http")
    async def local_only(request, call_next):
        host = request.headers.get("host", "")
        try:
            parsed = urlsplit("http://" + host)
            valid = (parsed.hostname in ("127.0.0.1", "localhost")
                     and not parsed.username and not parsed.password
                     and not parsed.path and not parsed.query and not parsed.fragment
                     and parsed.netloc == host and parsed.port != 0)
            origin = request.headers.get("origin")
            if origin and origin != "http://" + host:
                valid = False
            if request.headers.get("sec-fetch-site") not in (None, "same-origin", "none"):
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
        return {**state, "bridge_available": bridge.value is not None}

    @app.get("/api/voices")
    async def voices():
        return {"voices": VOICES, "specialists": SPECIALISTS, "default_voice": "pf_dora",
                "language": "pt-br", "max_text": MAX_TEXT, "profiles_provisional": True,
                "catalog": CATALOG}

    async def bounded_json(request, model, limit):
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            return JSONResponse({"detail": "Envie JSON."}, status_code=415)
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > limit:
                return JSONResponse({"detail": "Requisição muito grande."}, status_code=413)
            body.extend(chunk)
        try:
            return model.model_validate_json(bytes(body))
        except (ValidationError, ValueError):
            return JSONResponse({"detail": "Envelope inválido."}, status_code=422)

    def same_origin(request):
        return (request.headers.get("origin") == "http://" + request.headers.get("host", "")
                or request.headers.get("sec-fetch-site") == "same-origin")

    @app.get("/api/catalog")
    async def catalog():
        return CATALOG

    @app.get("/api/profiles")
    async def get_profiles():
        return profiles.get()

    @app.put("/api/profiles")
    async def put_profiles(request: Request):
        if not same_origin(request):
            return JSONResponse({"detail": "Origem obrigatória."}, status_code=403)
        data = await bounded_json(request, ProfileEnvelope, 16384)
        if isinstance(data, Response):
            return data
        try:
            return profiles.save(data)
        except OSError:
            return JSONResponse({"detail": "Não foi possível salvar os perfis; arquivo preservado."}, status_code=503)

    @app.post("/api/rounds")
    async def publish_round(request: Request):
        if bridge.value is None:
            return JSONResponse({"detail": "Ponte indisponível: permissões privadas não verificadas."}, status_code=503)
        if not bridge.authorized(request.headers.get("authorization", "")):
            return JSONResponse({"detail": "Credencial inválida."}, status_code=401)
        data = await bounded_json(request, RoundEnvelope, MAX_ENVELOPE)
        if isinstance(data, Response):
            return data
        try:
            created = rounds.publish(data)
        except OverflowError:
            return JSONResponse({"detail": "Envelope excede o limite de bytes."}, status_code=413)
        except ValueError:
            return JSONResponse({"detail": "round_id em conflito."}, status_code=409)
        return JSONResponse({"round_id": data.round_id, "created": created}, status_code=201 if created else 200)

    @app.get("/api/rounds")
    async def list_rounds(request: Request):
        if not same_origin(request):
            return JSONResponse({"detail": "Origem obrigatória."}, status_code=403)
        return rounds.listing()

    @app.get("/api/rounds/{round_id}")
    async def get_round(round_id: str, request: Request):
        if not same_origin(request):
            return JSONResponse({"detail": "Origem obrigatória."}, status_code=403)
        try:
            return rounds.get(round_id).model_dump()
        except KeyError:
            return JSONResponse({"detail": "Rodada ausente ou expirada."}, status_code=404)

    @app.delete("/api/rounds/{round_id}")
    async def delete_round(round_id: str, request: Request):
        if not same_origin(request):
            return JSONResponse({"detail": "Origem obrigatória."}, status_code=403)
        try:
            rounds.delete(round_id)
        except KeyError:
            return JSONResponse({"detail": "Rodada ausente ou expirada."}, status_code=404)
        return Response(status_code=204)

    @app.post("/api/speech")
    async def speech(request: Request):
        data = await bounded_json(request, Speech, MAX_BODY)
        if isinstance(data, Response):
            return data
        reference = None
        if data.round_id is not None:
            try:
                reference = rounds.reference(data.round_id)
                envelope = reference[0]
            except KeyError:
                return JSONResponse({"detail": "Rodada ausente ou expirada."}, status_code=404)
            item = next((item for item in [*envelope.interventions, envelope.synthesis]
                         if item.intervention_id == data.intervention_id), None)
            start = data.text_start
            if (item is None or item.specialist_id != data.specialist_id
                    or (data.text != item.text if start is None
                        else data.text != item.text[start:start + len(data.text)])):
                return JSONResponse({"detail": "Texto ou autoria não corresponde à rodada."}, status_code=422)
        profile = profiles.resolve(data.specialist_id)
        voice = data.voice if data.voice is not None else profile.voice
        speed = data.speed if data.speed is not None else profile.speed
        if state["status"] != "ready":
            return JSONResponse({"detail": state["error"] or "Modelo carregando."}, status_code=503)
        if state["pending"] >= 3:
            return JSONResponse({"detail": "Fila cheia. Tente novamente."}, status_code=429)
        state["pending"] += 1
        cancelled = threading.Event()
        loop = asyncio.get_running_loop()
        def round_valid():
            return reference is None or rounds.is_current(data.round_id, reference)

        def synthesize():
            if cancelled.is_set() or not round_valid():
                cancelled.set()
                raise InterruptedError()
            return engine.synthesize(data.text, voice, speed, cancelled)

        def removed_response():
            cancelled.set()
            concurrent.cancel()
            return JSONResponse({"detail": "Rodada ausente ou expirada."}, status_code=404)

        concurrent = executor.submit(synthesize)

        def finished(_):
            loop.call_soon_threadsafe(release)

        def release():
            state["pending"] -= 1

        concurrent.add_done_callback(finished)
        future = asyncio.wrap_future(concurrent)
        start = loop.time()
        try:
            while not future.done():
                if not round_valid():
                    return removed_response()
                if await request.is_disconnected():
                    return Response(status_code=499)
                if loop.time() - start >= timeout:
                    return JSONResponse({"detail": "Tempo limite de geração excedido."}, status_code=504)
                await asyncio.sleep(0.05)
            if not round_valid():
                return removed_response()
            audio = future.result()
            if not round_valid():
                return removed_response()
            return Response(audio.wav, media_type="audio/wav", headers={
                "X-Audio-Seconds": str(round(audio.seconds, 3)),
                "Content-Disposition": 'attachment; filename="conclave.wav"',
            })
        except asyncio.CancelledError:
            raise
        except Exception:
            if not round_valid():
                return removed_response()
            return JSONResponse({"detail": "Falha na síntese. Tente um texto menor ou reinicie o serviço."}, status_code=500)
        finally:
            cancelled.set()
            concurrent.cancel()
            if not future.done():
                future.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)
            elif not future.cancelled():
                future.exception()

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
