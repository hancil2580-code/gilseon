"""CapCut 드래프트 빌드 — draft_info.json + 자막 트랙"""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from .silence import Span
from .asr import Transcript

# CapCut 내부 시간 단위: 마이크로초
_US = 1_000_000


def _us(sec: float) -> int:
    return int(sec * _US)


def _uid() -> str:
    return uuid.uuid4().hex.upper()


def build_draft(
    video_path: str,
    keep_spans: list[Span],
    transcript: Transcript,
    draft_dir: str,
    video_duration: float,
) -> str:
    """
    CapCut 드래프트 폴더를 생성하고 draft_info.json을 반환.

    Returns: draft_info.json 경로
    """
    draft_path = Path(draft_dir)
    draft_path.mkdir(parents=True, exist_ok=True)

    # 비디오 파일 복사
    video_name = Path(video_path).name
    dst_video = draft_path / video_name
    if not dst_video.exists():
        shutil.copy2(video_path, dst_video)

    # 트랙 세그먼트 생성 (timeline 기준)
    video_segments = []
    timeline_cursor = 0  # microseconds on timeline

    for span in keep_spans:
        seg_dur = _us(span.duration)
        video_segments.append({
            "id": _uid(),
            "type": "video",
            "target_timerange": {
                "start": timeline_cursor,
                "duration": seg_dur,
            },
            "source_timerange": {
                "start": _us(span.start),
                "duration": seg_dur,
            },
            "material_id": "MAT_VIDEO",
            "clip": {
                "alpha": 1.0,
                "flip": {"horizontal": False, "vertical": False},
                "rotation": 0.0,
                "scale": {"x": 1.0, "y": 1.0},
                "transform": {"x": 0.0, "y": 0.0},
            },
        })
        timeline_cursor += seg_dur

    total_timeline_duration = timeline_cursor

    # 자막 세그먼트 생성 (타임코드 보정)
    subtitle_segments = _build_subtitles(transcript, keep_spans)

    draft = {
        "id": _uid(),
        "name": Path(video_path).stem,
        "create_time": 0,
        "duration": total_timeline_duration,
        "canvas_config": {
            "height": 1080,
            "width": 1920,
            "ratio": "original",
        },
        "fps": 30.0,
        "materials": {
            "videos": [
                {
                    "id": "MAT_VIDEO",
                    "type": "video",
                    "path": str(dst_video),
                    "duration": _us(video_duration),
                    "width": 1920,
                    "height": 1080,
                }
            ],
            "texts": [],
        },
        "tracks": [
            {
                "id": _uid(),
                "type": "video",
                "attribute": 0,
                "flag": 0,
                "segments": video_segments,
            },
            {
                "id": _uid(),
                "type": "text",
                "attribute": 0,
                "flag": 0,
                "segments": subtitle_segments,
            },
        ],
        "version": "5.9.0",
    }

    out_path = draft_path / "draft_info.json"
    out_path.write_text(json.dumps(draft, ensure_ascii=False, indent=2))
    return str(out_path)


def _build_subtitles(transcript: Transcript, keep_spans: list[Span]) -> list[dict]:
    """원본 타임코드 → 타임라인 타임코드 변환 후 자막 세그먼트 생성."""
    segs = []
    for seg in transcript.segments:
        tl_start = _source_to_timeline(seg.start, keep_spans)
        tl_end = _source_to_timeline(seg.end, keep_spans)
        if tl_start is None or tl_end is None:
            continue  # 컷된 구간
        dur = tl_end - tl_start
        if dur <= 0:
            continue

        segs.append({
            "id": _uid(),
            "type": "text",
            "target_timerange": {"start": tl_start, "duration": dur},
            "content": seg.text.strip(),
            "style": {
                "font_size": 7.0,
                "font_color": "0xFFFFFFFF",
                "stroke_color": "0xFF000000",
                "stroke_width": 0.08,
                "align": 1,
                "bold": False,
                "italic": False,
            },
            "transform_y": -0.8,  # 하단 자막
        })

    return segs


def _source_to_timeline(src_time: float, keep_spans: list[Span]) -> int | None:
    """원본 시간을 타임라인 시간(μs)으로 변환. 컷된 구간이면 None."""
    cursor = 0
    for span in keep_spans:
        if span.start <= src_time <= span.end:
            offset = src_time - span.start
            return _us(cursor + offset)
        if src_time < span.start:
            return None  # 컷 구간 이전
        cursor += span.duration
    return None
