import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
MODELS = ROOT / "models"
RELEASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
ARTIFACTS = {
    "kokoro-v1.0.onnx": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
    "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify():
    for name, expected in ARTIFACTS.items():
        path = MODELS / name
        if not path.is_file() or digest(path) != expected:
            raise RuntimeError("Modelo ausente ou inválido. Execute: uv run python assets.py")


def download():
    MODELS.mkdir(exist_ok=True)
    for name, expected in ARTIFACTS.items():
        target = MODELS / name
        if target.exists() and digest(target) == expected:
            continue
        temporary = target.with_suffix(".part")
        try:
            with urlopen(RELEASE + name, timeout=120) as response, temporary.open("wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
            if digest(temporary) != expected:
                raise RuntimeError(f"SHA256 incorreto: {name}")
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    (MODELS / "manifest.json").write_text(json.dumps({
        "release": "model-files-v1.1", "model_license": "Apache-2.0",
        "library_license": "MIT", "artifacts": [
            {"name": name, "url": RELEASE + name, "sha256": value}
            for name, value in ARTIFACTS.items()
        ]}, indent=2), encoding="utf-8")
    print("Artefatos verificados; nenhum download ocorre na inicialização do servidor.")


if __name__ == "__main__":
    download()
