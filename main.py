#!/usr/bin/env python3
"""CapCut 자동 편집 에이전트 CLI"""
import click
from capcut_agent.agent import run


@click.command()
@click.argument("input_video", type=click.Path(exists=True))
@click.option("--output-dir", "-o", default=None, help="출력 디렉토리 (기본: 입력 파일과 같은 위치)")
@click.option("--silence-db", default=-40.0, show_default=True, help="무음 판단 기준 dB")
@click.option("--min-silence", default=0.5, show_default=True, help="최소 무음 길이 (초)")
@click.option("--no-freeze", is_flag=True, help="버벅/정지 감지 비활성화")
@click.option("--freeze-threshold", default=0.98, show_default=True, help="버벅 감지 유사도 임계값 (0~1)")
@click.option("--no-subs", is_flag=True, help="자막 생성 비활성화")
@click.option(
    "--whisper-model",
    default="base",
    show_default=True,
    type=click.Choice(["tiny", "base", "small", "medium", "large"]),
    help="Whisper 모델 크기",
)
@click.option("--language", "-l", default=None, help="자막 언어 코드 (예: ko, en, ja). 기본: 자동 감지")
@click.option("--re-encode", is_flag=True, help="재인코딩 (품질 우선, 느림)")
def cli(
    input_video,
    output_dir,
    silence_db,
    min_silence,
    no_freeze,
    freeze_threshold,
    no_subs,
    whisper_model,
    language,
    re_encode,
):
    """
    영상에서 무음 구간과 버벅거리는 장면을 자동으로 제거하고 자막을 생성합니다.

    \b
    예시:
      python main.py video.mp4
      python main.py video.mp4 -o ./output --language ko --whisper-model small
      python main.py video.mp4 --no-freeze --silence-db -35
    """
    result = run(
        input_path=input_video,
        output_dir=output_dir,
        silence_db=silence_db,
        min_silence=min_silence,
        detect_freeze=not no_freeze,
        freeze_threshold=freeze_threshold,
        generate_subs=not no_subs,
        whisper_model=whisper_model,
        language=language,
        re_encode=re_encode,
    )

    click.echo(f"\n제거된 시간: {result['removed_duration']:.1f}초")
    click.echo(f"남은 구간 수: {result['kept_segments']}개")


if __name__ == "__main__":
    cli()
