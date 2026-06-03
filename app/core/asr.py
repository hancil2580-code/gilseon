"""faster-whisper ASR — 전체 스크립트 추출 (세그먼트 + 단어)"""
from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from dataclasses import dataclass, asdict

from faster_whisper import WhisperModel

# ASR은 numba 비안전 — 항상 직렬화
_LOCK = asyncio.Lock()
_MODEL: WhisperModel | None = None
_CACHE_DIR = Path("/tmp/capcut_asr_cache")
_CACHE_DIR.mkdir(exist_ok=True)


def _get_model(size: str = "base") -> WhisperModel:
    global _MODEL
    if _MODEL is None:
        _MODEL = WhisperModel(size, device="cpu", compute_type="int8")
    return _MODEL


@dataclass
class Word:
    start: float
    end: float
    word: str
    prob: float


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: list[Word]


@dataclass
class Transcript:
    language: str
    segments: list[Segment]

    def full_text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments)

    def to_dict(self) -> dict:
        return asdict(self)


def _content_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()[:16]


async def transcribe(path: str, model_size: str = "base", language: str = "ko") -> Transcript:
    """ASR 실행 (캐시 + 직렬화 잠금)."""
    cache_key = _content_hash(path) + f"_{model_size}_{language}"
    cache_file = _CACHE_DIR / f"{cache_key}.json"

    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        segs = [
            Segment(
                s["start"], s["end"], s["text"],
                [Word(**w) for w in s["words"]],
            )
            for s in data["segments"]
        ]
        return Transcript(language=data["language"], segments=segs)

    async with _LOCK:
        # double-check after acquiring lock
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            segs = [
                Segment(
                    s["start"], s["end"], s["text"],
                    [Word(**w) for w in s["words"]],
                )
                for s in data["segments"]
            ]
            return Transcript(language=data["language"], segments=segs)

        model = _get_model(model_size)
        raw_segs, info = model.transcribe(
            path,
            language=language,
            word_timestamps=True,
            vad_filter=False,  # 우리가 직접 무음 처리
        )

        segments: list[Segment] = []
        for seg in raw_segs:
            words = [
                Word(w.start, w.end, w.word, w.probability)
                for w in (seg.words or [])
            ]
            segments.append(Segment(seg.start, seg.end, seg.text, words))

        transcript = Transcript(language=info.language, segments=segments)
        cache_file.write_text(json.dumps(transcript.to_dict(), ensure_ascii=False))
        return transcript
