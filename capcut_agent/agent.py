"""CapCut 에이전트 — 전체 파이프라인 오케스트레이션"""
from pathlib import Path

from .silence_detector import detect_silence, silence_to_keep_segments
from .stutter_detector import detect_stutters, merge_bad_segments
from .subtitle_generator import generate_subtitles, adjust_subtitle_timing, save_srt
from .editor import cut_and_merge, get_duration


def run(
    input_path: str,
    output_dir: str | None = None,
    # 무음 설정
    silence_db: float = -40.0,
    min_silence: float = 0.5,
    silence_padding: float = 0.1,
    # 버벅 설정
    detect_freeze: bool = True,
    freeze_threshold: float = 0.98,
    min_freeze: float = 0.3,
    # 자막 설정
    generate_subs: bool = True,
    whisper_model: str = "base",
    language: str | None = None,
    # 인코딩
    re_encode: bool = False,
) -> dict:
    """
    영상 자동 편집 파이프라인 실행.

    Returns:
        {"output_video": str, "output_srt": str | None, "removed_duration": float}
    """
    input_path = str(Path(input_path).resolve())
    video_name = Path(input_path).stem

    if output_dir is None:
        output_dir = str(Path(input_path).parent)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    output_video = str(Path(output_dir) / f"{video_name}_edited.mp4")
    output_srt = str(Path(output_dir) / f"{video_name}_edited.srt") if generate_subs else None

    print(f"\n[1/4] 영상 분석 중: {input_path}")
    total_duration = get_duration(input_path)
    print(f"  영상 길이: {total_duration:.1f}초")

    # 무음 구간 감지
    print("\n[2/4] 무음 구간 감지 중...")
    silence_segs = detect_silence(
        input_path,
        silence_threshold_db=silence_db,
        min_silence_duration=min_silence,
        padding=silence_padding,
    )
    print(f"  무음 구간 {len(silence_segs)}개 발견")

    # 버벅/정지 구간 감지
    stutter_segs = []
    if detect_freeze:
        print("\n[2/4] 버벅/정지 구간 감지 중...")
        stutter_segs = detect_stutters(
            input_path,
            freeze_threshold=freeze_threshold,
            min_freeze_duration=min_freeze,
        )
        print(f"  버벅 구간 {len(stutter_segs)}개 발견")

    # 제거할 구간 병합
    bad_segs = merge_bad_segments(silence_segs, stutter_segs)
    removed_duration = sum(s.duration for s in bad_segs)
    print(f"\n  총 제거 구간: {len(bad_segs)}개 ({removed_duration:.1f}초)")

    # 남길 구간 계산
    keep_segs = silence_to_keep_segments(bad_segs, total_duration)
    print(f"  편집 후 예상 길이: {total_duration - removed_duration:.1f}초")

    # 자막 생성 (원본 기준)
    subtitles = None
    if generate_subs:
        print("\n[3/4] 자막 생성 중 (Whisper)...")
        subtitles = generate_subtitles(input_path, model_size=whisper_model, language=language)
        subtitles = adjust_subtitle_timing(subtitles, bad_segs)
        print(f"  자막 {len(subtitles)}개 생성")

    # 컷 편집 & 병합
    print("\n[4/4] 영상 편집 중...")
    cut_and_merge(input_path, keep_segs, output_video, re_encode=re_encode)

    # 자막 저장
    if subtitles and output_srt:
        save_srt(subtitles, output_srt)
        print(f"  자막 저장: {output_srt}")

    print("\n✓ 편집 완료!")
    print(f"  영상: {output_video}")
    if output_srt:
        print(f"  자막: {output_srt}")

    return {
        "output_video": output_video,
        "output_srt": output_srt,
        "removed_duration": removed_duration,
        "kept_segments": len(keep_segs),
    }
