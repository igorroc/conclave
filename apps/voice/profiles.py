import json
import os
import tempfile
import threading
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

CATALOG = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))
SPECIALISTS = {item["id"]: item["name"] for item in CATALOG["specialists"]}
VOICES = tuple(CATALOG["voices"])
ALIASES = {name.casefold(): item["id"] for item in CATALOG["specialists"]
           for name in [item["id"], item["name"], *item["aliases"]]}
DEFAULTS = {item["id"]: item["defaults"] for item in CATALOG["specialists"]}


def resolve_specialist(value):
    try:
        return ALIASES[value.casefold()]
    except KeyError:
        raise ValueError("Especialista desconhecido.") from None


class VoiceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    voice: str
    speed: float = Field(ge=0.8, le=1.2)

    @field_validator("voice")
    @classmethod
    def valid_voice(cls, value):
        if value not in VOICES:
            raise ValueError("Voz desconhecida.")
        return value


class ProfileEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: int = Field(ge=1, le=1)
    profiles: dict[str, VoiceProfile]

    @field_validator("profiles")
    @classmethod
    def valid_ids(cls, value):
        if set(value) != set(SPECIALISTS):
            raise ValueError("Envie os dez IDs canônicos.")
        return value


def default_profiles():
    return ProfileEnvelope(schema_version=1, profiles=DEFAULTS)


class ProfileStore:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.error = False
        self.value = default_profiles()
        if self.path.exists():
            try:
                if self.path.stat().st_size > 16384:
                    raise ValueError("Arquivo grande demais.")
                self.value = ProfileEnvelope.model_validate_json(self.path.read_bytes())
            except (OSError, ValueError):
                self.error = True

    def get(self):
        with self.lock:
            return {**self.value.model_dump(), "load_error": self.error}

    def resolve(self, specialist_id):
        with self.lock:
            return self.value.profiles[specialist_id].model_copy()

    def save(self, value):
        with self.lock:
            if self.error:
                raise OSError("Perfis não puderam ser lidos; preserve e recupere o arquivo antes de salvar.")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=self.path.parent, delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(value.model_dump_json().encode("utf-8"))
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, self.path)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            self.value = value.model_copy(deep=True)
            return self.get()
