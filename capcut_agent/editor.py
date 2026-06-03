"""영상 컷 편집 모듈 (ffmpeg 기반)"""
import subprocess
import tempfile
from pathlib import Path
from tqdm import tqdm

from .silence_detector import Segment


def cut_and_merge(
    input_path: str,
    keep_segments: list[Segment],
    output_path: str,
    re_encode: bool = False,
) -> None:
    """
    keep_segments에 해당하는 구간만 남기고 병합.

    Args:
        input_path: 원본 영상 경로
        keep_segments: 유지할 구간 목록
        output_path: 출력 영상 경로
        re_encode: True면 재인코딩 (품질↑, 속도↓), False면 스트림 복사 (빠름)
    """
    if not keep_segments:
        raise ValueError("유지할 구간이 없습니다.")

    with tempfile.TemporaryDirectory() as tmpdir:
        segment_files = []

        print(f"  총 {len(keep_segments)}개 구간 추출 중...")
        for i, seg in enumerate(tqdm(keep_segments, desc="구간 추출")):
            seg_path = str(Path(tmpdir) / f"seg_{i:04d}.mp4")
            _extract_segment(input_path, seg.start, seg.end, seg_path, re_encode)
            segment_files.append(seg_path)

        # 세그먼트 목록 파일 생성
        list_path = str(Path(tmpdir) / "segments.txt")
        with open(list_path, "w") as f:
            for p in segment_files:
                f.write(f"file '{p}'\n")

        # 병합
        print("  구간 병합 중...")
        _concat_segments(list_path, output_path, re_encode)

    print(f"  저장 완료: {output_path}")


def _extract_segment(
    input_path: str,
    start: float,
    end: float,
    output_path: str,
    re_encode: bool,
) -> None:
    duration = end - start
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", input_path,
        "-t", str(duration),
    ]

    if re_encode:
        cmd += ["-c:v", "libx264", "-c:a", "aac", "-preset", "fast"]
    else:
        cmd += ["-c", "copy"]

    cmd += ["-avoid_negative_ts", "make_zero", output_path]
    _run(cmd)


def _concat_segments(list_path: str, output_path: str, re_encode: bool) -> None:
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_path,
    ]

    if re_encode:
        cmd += ["-c:v", "libx264", "-c:a", "aac", "-preset", "fast"]
    else:
        cmd += ["-c", "copy"]

    cmd.append(output_path)
    _run(cmd)


def get_duration(video_path: str) -> float:
    """ffprobe로 영상 길이(초) 반환."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            video_path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    import json
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def _run(cmd: list[str]) -> None:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 오류:\n{result.stderr}")
