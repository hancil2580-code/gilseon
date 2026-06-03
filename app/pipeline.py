"""편집 파이프라인 — SSE 이벤트 스트림으로 진행 상황 전달"""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from pathlib import Path
from typing import AsyncGenerator

import librosa

from .core.silence import detect_silence, keep_spans, Span
from .core.asr import transcribe, Transcript
from .core.filler import detect_fillers, detect_ng, merge_spans
from .core.draft import build_draft


def _event(step: str, pct: int, msg: str, data: dict | None = None) -> str:
    payload = {"step": step, "pct": pct, "msg": msg, **(data or {})}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def process(
    video_path: str,
    draft_base: str,
    silence_db: float = -40.0,
    min_silence: float = 0.4,
    whisper_model: str = "base",
    language: str = "ko",
) -> AsyncGenerator[str, None]:
    """
    Yields SSE 이벤트:
      step: silence | asr | filler | draft | done | error
      pct: 0~100
    """
    try:
        await asyncio.sleep(0)  # flush 보장

        # ── STEP 1: 무음 감지 ───────────────────────────────────
        yield _event("silence", 5, "무음 구간 분석 중…")
        await asyncio.sleep(0.5)

        duration = librosa.get_duration(path=video_path)
        silence_spans = await asyncio.to_thread(
            detect_silence, video_path,
            threshold_db=silence_db,
            min_dur=min_silence,
        )
        yield _event("silence", 20, f"무음 {len(silence_spans)}개 감지", {
            "silence_count": len(silence_spans),
            "silence_sec": round(sum(s.duration for s in silence_spans), 1),
        })
        await asyncio.sleep(0.5)

        # ── STEP 2: ASR ─────────────────────────────────────────
        yield _event("asr", 25, "음성 인식 중… (첫 실행은 모델 다운로드)")
        transcript: Transcript = await transcribe(video_path, model_size=whisper_model, language=language)
        yield _event("asr", 60, f"스크립트 추출 완료 — {len(transcript.segments)}개 세그먼트", {
            "language": transcript.language,
            "segment_count": len(transcript.segments),
            "script_preview": transcript.full_text()[:200],
        })
        await asyncio.sleep(0.5)

        # ── STEP 3: 잔말·NG 컷 ──────────────────────────────────
        yield _event("filler", 65, "잔말·NG 구간 분석 중…")
        await asyncio.sleep(0.5)

        filler_spans = detect_fillers(transcript)
        ng_spans = detect_ng(transcript)
        bad_spans = merge_spans(silence_spans + filler_spans + ng_spans)

        keep = keep_spans(bad_spans, duration)
        removed_sec = round(sum(s.duration for s in bad_spans), 1)
        kept_sec = round(sum(s.duration for s in keep), 1)

        yield _event("filler", 75, f"잔말 {len(filler_spans)}개 / NG {len(ng_spans)}개 제거", {
            "filler_count": len(filler_spans),
            "ng_count": len(ng_spans),
            "removed_sec": removed_sec,
            "kept_sec": kept_sec,
        })
        await asyncio.sleep(0.5)

        # ── STEP 4: 드래프트 빌드 ────────────────────────────────
        yield _event("draft", 80, "캡컷 드래프트 생성 중…")

        video_name = Path(video_path).stem
        draft_dir = str(Path(draft_base) / video_name)
        draft_path = await asyncio.to_thread(
            build_draft, video_path, keep, transcript, draft_dir, duration
        )

        yield _event("draft", 95, "드래프트 생성 완료", {
            "draft_path": draft_path,
            "draft_dir": draft_dir,
        })
        await asyncio.sleep(0.5)

        # ── DONE ─────────────────────────────────────────────────
        yield _event("done", 100, "편집 완료!", {
            "draft_dir": draft_dir,
            "original_sec": round(duration, 1),
            "kept_sec": kept_sec,
            "removed_sec": removed_sec,
            "silence_count": len(silence_spans),
            "filler_count": len(filler_spans),
            "ng_count": len(ng_spans),
            "segment_count": len(transcript.segments),
            "script": transcript.full_text(),
            "segments": [
                {"start": s.start, "end": s.end, "text": s.text.strip()}
                for s in transcript.segments
            ],
        })

    except Exception as e:
        yield _event("error", 0, str(e))
