# CapCut 자동 편집 에이전트

영상에서 **무음 구간**, **버벅거리는 장면**을 자동으로 감지·제거하고 **자막**을 생성합니다.

## 기능

| 기능 | 설명 |
|------|------|
| 무음 컷 | 설정한 dB 이하 구간 자동 제거 |
| 버벅 감지 | 프레임이 거의 변하지 않는 정지/반복 구간 제거 |
| 자막 생성 | OpenAI Whisper로 음성 인식 → SRT 자막 파일 출력 |
| 타임코드 보정 | 컷 편집 후 자막 타임코드 자동 보정 |

## 설치

```bash
# ffmpeg 설치 (macOS)
brew install ffmpeg

# ffmpeg 설치 (Ubuntu)
sudo apt install ffmpeg

# Python 패키지 설치
pip install -r requirements.txt
```

## 사용법

```bash
# 기본 실행 (무음 제거 + 버벅 제거 + 자막 생성)
python main.py video.mp4

# 출력 폴더 지정
python main.py video.mp4 -o ./output

# 한국어 자막 + 정확도 높은 모델
python main.py video.mp4 --language ko --whisper-model small

# 무음만 제거 (버벅 감지 끄기)
python main.py video.mp4 --no-freeze

# 무음 기준 조정 (-35dB, 0.3초 이상)
python main.py video.mp4 --silence-db -35 --min-silence 0.3

# 자막 없이 편집만
python main.py video.mp4 --no-subs

# 재인코딩 (품질 우선)
python main.py video.mp4 --re-encode
```

## 출력 파일

- `{원본이름}_edited.mp4` — 편집된 영상
- `{원본이름}_edited.srt` — SRT 자막 파일 (CapCut에 직접 임포트 가능)

## 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--silence-db` | -40.0 | 무음 판단 기준 dB (낮을수록 엄격) |
| `--min-silence` | 0.5 | 최소 무음 길이 (초) |
| `--no-freeze` | — | 버벅/정지 감지 비활성화 |
| `--freeze-threshold` | 0.98 | 버벅 감지 유사도 (0~1, 높을수록 엄격) |
| `--no-subs` | — | 자막 생성 비활성화 |
| `--whisper-model` | base | tiny / base / small / medium / large |
| `--language` | 자동 | 자막 언어 코드 (ko, en, ja ...) |
| `--re-encode` | — | 재인코딩 (느리지만 품질 좋음) |

## 모듈 구조

```
capcut_agent/
├── agent.py            # 전체 파이프라인 오케스트레이션
├── silence_detector.py # 무음 구간 감지 (librosa)
├── stutter_detector.py # 버벅/정지 구간 감지 (opencv)
├── subtitle_generator.py # 자막 생성 (Whisper)
└── editor.py           # 컷 편집 & 병합 (ffmpeg)
```

## Python API

```python
from capcut_agent.agent import run

result = run(
    input_path="video.mp4",
    output_dir="./output",
    language="ko",
    whisper_model="small",
    silence_db=-38.0,
    min_silence=0.4,
)

print(result["output_video"])  # 편집된 영상 경로
print(result["output_srt"])    # 자막 파일 경로
print(result["removed_duration"])  # 제거된 시간(초)
```
