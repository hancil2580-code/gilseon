"""잔말·NG 구간 감지 — 전체 스크립트 기반"""
from __future__ import annotations

import re
from .silence import Span
from .asr import Transcript, Segment


# 한국어 잔말 패턴 (세그먼트 전체 텍스트 기준)
_FILLER_PATTERNS = [
    r"^(어+|음+|아+|에+|그+|뭐+|저+|근데|아니|맞다|자|이제|그래서|그러니까|뭐냐|있잖아)[\.，,\s]*$",
    r"^\s*$",
]
_FILLER_RE = re.compile("|".join(_FILLER_PATTERNS), re.IGNORECASE)

# NG 마커 (말하다 멈추고 재시작 패턴)
_NG_MARKERS = ["죄송", "다시", "컷", "NG", "ng", "잠깐", "잠시만", "아 틀렸"]


def detect_fillers(transcript: Transcript, padding: float = 0.05) -> list[Span]:
    """잔말 구간 반환."""
    spans: list[Span] = []
    for seg in transcript.segments:
        text = seg.text.strip()
        if _FILLER_RE.match(text):
            spans.append(Span(
                max(0.0, seg.start - padding),
                seg.end + padding,
            ))
    return spans


def detect_ng(transcript: Transcript, padding: float = 0.3) -> list[Span]:
    """NG 마커가 포함된 구간 + 직전 문장 반환."""
    spans: list[Span] = []
    segs = transcript.segments

    for i, seg in enumerate(segs):
        if any(m in seg.text for m in _NG_MARKERS):
            # NG 발화 자체 + 직전 세그먼트 (잘못 말한 부분)
            prev_start = segs[i - 1].start if i > 0 else seg.start
            spans.append(Span(
                max(0.0, prev_start - padding),
                seg.end + padding,
            ))

    return spans


def merge_spans(spans: list[Span], gap: float = 0.15) -> list[Span]:
    """인접 구간 병합."""
    if not spans:
        return []
    sorted_spans = sorted(spans, key=lambda s: s.start)
    merged = [sorted_spans[0]]
    for s in sorted_spans[1:]:
        last = merged[-1]
        if s.start <= last.end + gap:
            merged[-1] = Span(last.start, max(last.end, s.end))
        else:
            merged.append(s)
    return merged
