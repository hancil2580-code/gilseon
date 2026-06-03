"""무음 구간 감지 모듈"""
import numpy as np
import librosa
from dataclasses import dataclass


@dataclass
class Segment:
    start: float  # seconds
    end: float    # seconds

    @property
    def duration(self) -> float:
        return self.end - self.start

    def __repr__(self):
        return f"Segment({self.start:.2f}s ~ {self.end:.2f}s)"


def detect_silence(
    audio_path: str,
    silence_threshold_db: float = -40.0,
    min_silence_duration: float = 0.5,
    padding: float = 0.1,
) -> list[Segment]:
    """
    무음 구간을 감지하고 제거할 세그먼트 목록을 반환.

    Args:
        audio_path: 오디오/영상 파일 경로
        silence_threshold_db: 무음 판단 기준 dB (기본 -40dB)
        min_silence_duration: 최소 무음 길이 (초, 기본 0.5초)
        padding: 컷 전후 여유 시간 (초)

    Returns:
        제거할 무음 구간 목록
    """
    y, sr = librosa.load(audio_path, sr=None, mono=True)

    # RMS 에너지 계산 (프레임 단위)
    frame_length = int(sr * 0.02)  # 20ms 프레임
    hop_length = frame_length // 2
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]

    # dB 변환
    rms_db = librosa.amplitude_to_db(rms, ref=np.max)

    # 무음 프레임 마스크
    is_silent = rms_db < silence_threshold_db

    # 연속된 무음 구간 추출
    silent_segments: list[Segment] = []
    in_silence = False
    silence_start = 0.0

    times = librosa.frames_to_time(np.arange(len(is_silent)), sr=sr, hop_length=hop_length)

    for i, (t, silent) in enumerate(zip(times, is_silent)):
        if silent and not in_silence:
            in_silence = True
            silence_start = t
        elif not silent and in_silence:
            in_silence = False
            duration = t - silence_start
            if duration >= min_silence_duration:
                start = max(0.0, silence_start + padding)
                end = max(start, t - padding)
                if end > start:
                    silent_segments.append(Segment(start, end))

    # 마지막 구간 처리
    if in_silence:
        duration = times[-1] - silence_start
        if duration >= min_silence_duration:
            start = max(0.0, silence_start + padding)
            end = max(start, times[-1] - padding)
            if end > start:
                silent_segments.append(Segment(start, end))

    return silent_segments


def silence_to_keep_segments(
    silent_segments: list[Segment],
    total_duration: float,
) -> list[Segment]:
    """무음 제거 후 남길 구간 계산."""
    keep: list[Segment] = []
    cursor = 0.0

    for seg in sorted(silent_segments, key=lambda s: s.start):
        if seg.start > cursor:
            keep.append(Segment(cursor, seg.start))
        cursor = seg.end

    if cursor < total_duration:
        keep.append(Segment(cursor, total_duration))

    return keep
