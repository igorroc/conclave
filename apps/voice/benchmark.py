import argparse
import json
import platform
import socket
import threading
import time
from pathlib import Path

import psutil

from engine import VOICES, KokoroEngine

TEXTS = {
    "curto": "Olá. Vamos avaliar os próximos passos do Conclave com clareza e objetividade.",
    "numeros": "Em 08/11/2026, Igor Rocha estimou R$ 1.250,50 e margem de 25%. O MVP precisa validar o retorno antes de ampliar o investimento.",
    "paragrafo": "A recomendação do conselho é começar pequeno. Precisamos separar fatos, hipóteses e estimativas, verificar a demanda e definir responsáveis. A qualidade do atendimento e o controle de custos devem ser avaliados antes da expansão. " * 3,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.offline:
        def blocked(*args, **kwargs):
            raise RuntimeError("Rede bloqueada durante o benchmark.")
        socket.socket.connect = blocked
        socket.create_connection = blocked
    output = Path(__file__).resolve().parent / "output"
    output.mkdir(exist_ok=True)
    engine = KokoroEngine()
    start = time.perf_counter()
    engine.load()
    load = time.perf_counter() - start
    rows = []
    for voice in VOICES:
        for label, text in TEXTS.items():
            start = time.perf_counter()
            audio = engine.synthesize(text, voice, 1.0, threading.Event())
            elapsed = time.perf_counter() - start
            filename = f"{voice}-{label}.wav"
            (output / filename).write_bytes(audio.wav)
            row = dict(file=filename, generation_seconds=round(elapsed, 3),
                       audio_seconds=round(audio.seconds, 3), rtf=round(elapsed / audio.seconds, 3),
                       sample_rate=audio.sample_rate, rss_mb=round(psutil.Process().memory_info().rss / 2**20, 1))
            rows.append(row)
            print(json.dumps(row))
    report = dict(model_load_seconds=round(load, 3), offline_socket_guard=args.offline,
                  platform=platform.platform(), cpu=platform.processor(),
                  ram_gb=round(psutil.virtual_memory().total / 2**30, 1),
                  auditory_approval="pending", results=rows)
    (output / "benchmark.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
