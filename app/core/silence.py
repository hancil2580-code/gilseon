"""무음 구간 감지 — librosa RMS 기반"""
from __future__ import annotations

import numpy as np
import librosa
from dataclasses import dataclass


@dataclass
class Span:
    start: float  # seconds
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def detect_silence(
    path: str,
    threshold_db: float = -40.0,
    min_dur: float = 0.4,
    padding: float = 0.08,
) -> list[Span]:
    """무음 구간 목록 반환 (제거 대상)."""
    y, sr = librosa.load(path, sr=None, mono=True)
    hop = int(sr * 0.01)   # 10ms hop
    frame_len = hop * 2

    rms = librosa.feature.rms(y=y, frame_length=frame_len, hop_length=hop)[0]
    db = librosa.amplitude_to_db(rms + 1e-9, ref=np.max)
    times = librosa.frames_to_time(np.arange(len(db)), sr=sr, hop_length=hop)

    spans: list[Span] = []
    in_sil = False
    t0 = 0.0

    for t, d in zip(times, db):
        if d < threshold_db and not in_sil:
            in_sil = True
            t0 = t
        elif d >= threshold_db and in_sil:
            in_sil = False
            dur = t - t0
            if dur >= min_dur:
                spans.append(Span(max(0.0, t0 + padding), max(0.0, t - padding)))

    if in_sil:
        dur = float(times[-1]) - t0
        if dur >= min_dur:
            spans.append(Span(max(0.0, t0 + padding), float(times[-1]) - padding))

    return spans


def keep_spans(remove: list[Span], total: float) -> list[Span]:
    """제거 구간의 역집합 (남길 구간)."""
    remove = sorted(remove, key=lambda s: s.start)
    keep: list[Span] = []
    cur = 0.0
    for s in remove:
        if s.start > cur + 0.01:
            keep.append(Span(cur, s.start))
        cur = s.end
    if cur < total - 0.01:
        keep.append(Span(cur, total))
    return keep
