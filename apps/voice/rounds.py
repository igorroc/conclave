import hashlib
import hmac
import json
import os
import secrets
import subprocess
import time
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from profiles import SPECIALISTS

MAX_ENVELOPE = 128 * 1024
MAX_ROUND_BYTES = 20 * MAX_ENVELOPE
TTL_SECONDS = 7200
Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")]
Text = Annotated[str, Field(min_length=1, max_length=6000)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Intervention(StrictModel):
    intervention_id: Identifier
    specialist_id: str
    phase: Literal["analysis", "counterpoint", "synthesis"]
    text: Text
    reply_to: list[Identifier] = Field(default_factory=list, max_length=9)
    order: int = Field(ge=0, le=11)

    @field_validator("specialist_id")
    @classmethod
    def specialist(cls, value):
        if value not in SPECIALISTS:
            raise ValueError("ID canônico desconhecido.")
        return value

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, value):
        if not value.strip():
            raise ValueError("Texto vazio.")
        return value


class Failure(StrictModel):
    specialist_id: str
    phase: Literal["analysis", "counterpoint"]
    code: Literal["error", "cancelled", "invalid_response", "unavailable"]

    _specialist = field_validator("specialist_id")(Intervention.specialist.__func__)


class RoundEnvelope(StrictModel):
    schema_version: int = Field(ge=1, le=1)
    round_id: Identifier
    project_id: Identifier
    title: str = Field(min_length=1, max_length=200)
    session_id: Identifier
    status: Literal["complete", "partial"]
    interventions: list[Intervention] = Field(max_length=11)
    synthesis: Intervention
    failures: list[Failure] = Field(default_factory=list, max_length=11)

    @model_validator(mode="after")
    def links(self):
        if not self.title.strip():
            raise ValueError("Título vazio.")
        seen = set()
        analyses = set()
        counters = set()
        counterpoint_started = False
        for order, item in enumerate([*self.interventions, self.synthesis]):
            if item.intervention_id in seen or item.order != order:
                raise ValueError("IDs únicos e ordem contígua a partir de zero são obrigatórios.")
            if len(set(item.reply_to)) != len(item.reply_to) or not set(item.reply_to) <= seen:
                raise ValueError("Vínculo deve apontar para intervenção anterior.")
            if item is self.synthesis:
                if item.phase != "synthesis" or item.specialist_id != "maestro":
                    raise ValueError("Síntese deve pertencer ao Maestro.")
            elif item.specialist_id == "maestro":
                raise ValueError("Maestro participa somente na síntese.")
            elif item.phase == "analysis":
                if counterpoint_started or item.reply_to or item.specialist_id in analyses:
                    raise ValueError("Análise duplicada, vinculada ou fora de ordem.")
                analyses.add(item.specialist_id)
            elif item.phase == "counterpoint":
                counterpoint_started = True
                if not item.reply_to or item.specialist_id not in analyses or item.specialist_id in counters:
                    raise ValueError("Contraponto exige análise própria e vínculo anterior.")
                counters.add(item.specialist_id)
            else:
                raise ValueError("Síntese deve estar no campo próprio.")
            seen.add(item.intervention_id)
        if len(analyses) > 9 or len(counters) > 2:
            raise ValueError("Limite de participantes excedido.")
        if self.status == "complete" and (self.failures or not analyses):
            raise ValueError("Rodada completa exige análise e nenhuma falha.")
        return self


class RoundStore:
    def __init__(self, clock=time.time, max_bytes=MAX_ROUND_BYTES):
        self.clock = clock
        self.max_bytes = max_bytes
        self.items = OrderedDict()
        self.lock = RLock()

    def prune(self):
        with self.lock:
            now = self.clock()
            for key, (_, published, _, _) in list(self.items.items()):
                if now - published >= TTL_SECONDS:
                    del self.items[key]

    def publish(self, envelope):
        with self.lock:
            return self._publish(envelope)

    def _publish(self, envelope):
        self.prune()
        encoded = json.dumps(envelope.model_dump(), ensure_ascii=False, sort_keys=True,
                             separators=(",", ":")).encode("utf-8")
        if len(encoded) > min(MAX_ENVELOPE, self.max_bytes):
            raise OverflowError("Envelope excede o limite de bytes.")
        digest = hashlib.sha256(encoded).digest()
        key = envelope.round_id
        if key in self.items:
            if self.items[key][2] != digest:
                raise ValueError("round_id já publicado com conteúdo diferente.")
            return False
        self.items[key] = (envelope.model_copy(deep=True), self.clock(), digest, len(encoded))
        while len(self.items) > 20 or sum(item[3] for item in self.items.values()) > self.max_bytes:
            self.items.popitem(last=False)
        return True

    def reference(self, key):
        with self.lock:
            self.prune()
            return self.items[key]

    def is_current(self, key, reference):
        with self.lock:
            self.prune()
            return self.items.get(key) is reference

    def get(self, key):
        return self.reference(key)[0].model_copy(deep=True)

    def delete(self, key):
        with self.lock:
            self.prune()
            del self.items[key]

    def clear(self):
        with self.lock:
            self.items.clear()

    def listing(self):
        with self.lock:
            return self._listing()

    def _listing(self):
        self.prune()
        return {"rounds": [{"round_id": item.round_id, "project_id": item.project_id,
                            "title": item.title, "session_id": item.session_id,
                            "status": item.status, "published_at": published,
                            "expires_at": published + TTL_SECONDS,
                            "intervention_count": len(item.interventions) + 1}
                           for item, published, _, _ in reversed(self.items.values())],
                "retention": {"max_rounds": 20, "ttl_seconds": TTL_SECONDS,
                              "max_bytes": self.max_bytes, "persistent": False}}


class BridgeToken:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.path = self.directory / "bridge-token"
        self.value = None

    def start(self):
        self.value = None
        try:
            if (self.directory.is_symlink() or self.directory.is_junction()
                    or self.path.is_symlink() or self.path.is_junction()):
                raise OSError("Caminho não seguro.")
            self.directory.mkdir(parents=True, exist_ok=True)
            self.path.unlink(missing_ok=True)
            if os.name == "nt":
                script = r'''$ErrorActionPreference = 'Stop'
$p = $env:CONCLAVE_TOKEN_DIR
$sid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$a = New-Object System.Security.AccessControl.DirectorySecurity
$a.SetAccessRuleProtection($true, $false)
$a.SetOwner($sid)
$r = New-Object System.Security.AccessControl.FileSystemAccessRule($sid, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
$a.AddAccessRule($r)
$directory = New-Object System.IO.DirectoryInfo($p)
$directory.SetAccessControl($a)
$v = Get-Acl -LiteralPath $p
if (!$v.AreAccessRulesProtected -or $v.Owner -eq $null) { throw 'ACL' }
$rules = @($v.GetAccessRules($true, $true, [System.Security.Principal.SecurityIdentifier]))
if ($rules.Count -ne 1 -or $rules[0].IdentityReference.Value -ne $sid.Value -or $rules[0].AccessControlType -ne 'Allow' -or $rules[0].FileSystemRights -ne [System.Security.AccessControl.FileSystemRights]::FullControl) { throw 'ACL' }
'''
                subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                               env={**os.environ, "CONCLAVE_TOKEN_DIR": str(self.directory)},
                               check=True, capture_output=True, timeout=15)
            else:
                os.chmod(self.directory, 0o700)
                if self.directory.stat().st_uid != os.getuid() or self.directory.stat().st_mode & 0o077:
                    raise OSError("Permissões inseguras.")
            value = secrets.token_urlsafe(32)
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="ascii") as stream:
                stream.write(value)
            self.value = value
        except (OSError, subprocess.SubprocessError):
            try:
                self.path.unlink(missing_ok=True)
            except OSError:
                pass
            return False
        return True

    def authorized(self, header):
        return self.value is not None and hmac.compare_digest(
            header.encode("utf-8"), ("Bearer " + self.value).encode("ascii"))

    def close(self):
        if self.value is not None:
            try:
                if self.path.read_text(encoding="ascii") == self.value:
                    self.path.unlink()
            except OSError:
                pass
        self.value = None
