import argparse
import os
import stat
import tempfile
import tomllib
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "maki"
PROJECT = Path(__file__).resolve().parents[2]


def _reject_links(path: Path) -> None:
    for component in (*reversed(path.parents), path):
        try:
            metadata = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode) or getattr(metadata, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError(f"Recusando link/reparse point: {component}")


def _validate_target(project: Path, path: Path) -> None:
    _reject_links(path)
    if not path.resolve().is_relative_to(project):
        raise ValueError(f"Destino fora do projeto: {path}")


def install(project: Path = PROJECT, source: Path = SOURCE) -> list[Path]:
    project = Path(os.path.abspath(project))
    _reject_links(project)
    project = project.resolve()
    target = project / ".maki"
    destinations = (target / "init.lua", target / "plugin.toml", target / "lua/conclave.lua")
    for path in (target, target / "lua", *destinations):
        _validate_target(project, path)
    init = (source / "init.lua").read_bytes()
    manifest = (source / "plugin.toml").read_bytes()
    module = (source / "conclave.lua").read_bytes()
    for name, expected in (("init.lua", init), ("plugin.toml", manifest)):
        path = target / name
        _validate_target(project, path)
        if path.exists():
            existing = path.read_bytes()
            if name == "init.lua" and existing != expected:
                raise ValueError(f"init.lua existente difere do template; integração manual necessária: {path}")
            if name == "plugin.toml":
                actual = tomllib.loads(existing.decode("utf-8"))
                wanted = tomllib.loads(expected.decode("utf-8"))
                if actual != wanted:
                    raise ValueError(f"Permissões existentes diferem do manifesto restrito: {path}")
    for path in (target, target / "lua", *destinations):
        _validate_target(project, path)
    target.mkdir(parents=True, exist_ok=True)
    (target / "lua").mkdir(exist_ok=True)
    changed = []
    for path, data in zip(destinations, (init, manifest, module), strict=True):
        _validate_target(project, path)
        if path.exists() and (path.name != "conclave.lua" or path.read_bytes() == data):
            continue
        fd, temporary = tempfile.mkstemp(prefix=".conclave-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
            _validate_target(project, path)
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        changed.append(path)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="Instala fonte local Conclave; não altera configuração global.")
    parser.parse_args()
    changed = install()
    print(f"Plugin local validado; {len(changed)} arquivo(s) atualizado(s). Execute /reload no Maki; integração live não verificada.")


if __name__ == "__main__":
    main()
