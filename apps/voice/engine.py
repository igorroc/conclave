import io
import re
import threading
from dataclasses import dataclass

import numpy as np
import soundfile as sf

from assets import MODELS, verify
from profiles import SPECIALISTS as SPECIALISTS
from profiles import VOICES as VOICES

MAX_TEXT = 6000


def normalize(text):
    months = ("janeiro", "fevereiro", "março", "abril", "maio", "junho",
              "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
    text = re.sub(r"\b(\d{2})/(0[1-9]|1[0-2])/(\d{4})\b", lambda m:
                  f"{int(m[1])} de {months[int(m[2]) - 1]} de {m[3]}", text)
    text = re.sub(r"R\$\s*([\d.]+)(?:,(\d{2}))?", lambda m:
                  m[1].replace(".", "") + " reais" +
                  (" e " + m[2] + " centavos" if m[2] and m[2] != "00" else ""), text)
    text = re.sub(r"(\d+(?:,\d+)?)\s*%", r"\1 por cento", text)
    return " ".join(text.split())


def segments(text, limit=350):
    text = normalize(text)
    words = text.split()
    result, current = [], ""
    for word in words:
        if len(word) > limit:
            raise ValueError("Uma palavra excede o limite de síntese.")
        if current and len(current) + len(word) + 1 > limit:
            result.append(current)
            current = ""
        current = f"{current} {word}".strip()
        if current.endswith((".", "!", "?", ";")) and len(current) >= 100:
            result.append(current)
            current = ""
    if current:
        result.append(current)
    return result


@dataclass
class Audio:
    wav: bytes
    seconds: float
    sample_rate: int


class KokoroEngine:
    def __init__(self):
        self.model = None

    def load(self):
        import onnxruntime as ort
        from kokoro_onnx import Kokoro

        verify()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 4
        options.inter_op_num_threads = 1
        session = ort.InferenceSession(str(MODELS / "kokoro-v1.0.onnx"),
                                       sess_options=options, providers=["CPUExecutionProvider"])
        self.model = Kokoro.from_session(session, str(MODELS / "voices-v1.0.bin"))
        if not set(VOICES).issubset(self.model.get_voices()):
            raise RuntimeError("O arquivo de vozes não contém as três vozes pt-BR.")

    def synthesize(self, text, voice, speed, cancelled: threading.Event):
        chunks = []
        rate = 24000
        for part in segments(text):
            if cancelled.is_set():
                raise InterruptedError("Solicitação cancelada.")
            samples, rate = self.model.create(part, voice=voice, speed=speed, lang="pt-br")
            if cancelled.is_set():
                raise InterruptedError("Solicitação cancelada.")
            chunks.append(samples)
        audio = np.concatenate(chunks)
        if not len(audio) or not np.isfinite(audio).all():
            raise RuntimeError("Áudio inválido.")
        buffer = io.BytesIO()
        sf.write(buffer, audio, rate, format="WAV", subtype="PCM_16")
        return Audio(buffer.getvalue(), len(audio) / rate, rate)
