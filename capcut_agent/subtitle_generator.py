"""Whisper 기반 자막 자동 생성 모듈"""
import whisper
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SubtitleEntry:
    index: int
    start: float  # seconds
    end: float    # seconds
    text: str

    def to_srt(self) -> str:
        return (
            f"{self.index}\n"
            f"{_format_time(self.start)} --> {_format_time(self.end)}\n"
            f"{self.text.strip()}\n"
        )


def generate_subtitles(
    audio_path: str,
    model_size: str = "base",
    language: str | None = None,
    time_offset: float = 0.0,
) -> list[SubtitleEntry]:
    """
    Whisper로 자막을 생성.

    Args:
        audio_path: 오디오/영상 파일 경로
        model_size: whisper 모델 크기 (tiny/base/small/medium/large)
        language: 언어 코드 (None이면 자동 감지, 'ko'는 한국어)
        time_offset: 타임코드 오프셋 (컷 편집 후 보정용)

    Returns:
        자막 엔트리 목록
    """
    model = whisper.load_model(model_size)

    options: dict = {"task": "transcribe"}
    if language:
        options["language"] = language

    result = model.transcribe(audio_path, **options)

    entries: list[SubtitleEntry] = []
    for i, seg in enumerate(result["segments"], start=1):
        entries.append(SubtitleEntry(
            index=i,
            start=seg["start"] + time_offset,
            end=seg["end"] + time_offset,
            text=seg["text"],
        ))

    return entries


def adjust_subtitle_timing(
    entries: list[SubtitleEntry],
    cut_segments,  # list[Segment] — 제거된 구간
) -> list[SubtitleEntry]:
    """
    컷 편집으로 제거된 구간만큼 자막 타임코드를 앞당김.

    Args:
        entries: 원본 자막 엔트리
        cut_segments: 제거된 구간 목록

    Returns:
        보정된 자막 엔트리
    """
    adjusted: list[SubtitleEntry] = []
    new_index = 1

    for entry in entries:
        # 제거된 구간과 겹치는 자막은 스킵
        removed = False
        for seg in cut_segments:
            if entry.start >= seg.start and entry.end <= seg.end:
                removed = True
                break
            # 제거 구간과 일부 겹치면 부분 포함
            if entry.start < seg.end and entry.end > seg.start:
                removed = True
                break

        if removed:
            continue

        # 제거된 구간들의 총 길이만큼 타임코드 보정
        offset = sum(
            min(seg.end, entry.start) - seg.start
            for seg in cut_segments
            if seg.start < entry.start
        )

        adjusted.append(SubtitleEntry(
            index=new_index,
            start=max(0.0, entry.start - offset),
            end=max(0.0, entry.end - offset),
            text=entry.text,
        ))
        new_index += 1

    return adjusted


def save_srt(entries: list[SubtitleEntry], output_path: str) -> None:
    """SRT 파일로 저장."""
    Path(output_path).write_text(
        "\n".join(e.to_srt() for e in entries),
        encoding="utf-8",
    )


def _format_time(seconds: float) -> str:
    """초를 SRT 타임코드 형식으로 변환 (HH:MM:SS,mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
