"""버벅거리는 장면(정지, 반복 프레임) 감지 모듈"""
import cv2
import numpy as np
from .silence_detector import Segment


def detect_stutters(
    video_path: str,
    freeze_threshold: float = 0.98,
    min_freeze_duration: float = 0.3,
    sample_interval: float = 0.05,
) -> list[Segment]:
    """
    영상에서 프레임이 거의 변하지 않는 정지/버벅 구간을 감지.

    Args:
        video_path: 영상 파일 경로
        freeze_threshold: 프레임 유사도 임계값 (0~1, 높을수록 엄격)
        min_freeze_duration: 최소 정지 구간 길이 (초)
        sample_interval: 샘플링 간격 (초)

    Returns:
        제거할 버벅 구간 목록
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_duration = total_frames / fps

    sample_step = max(1, int(fps * sample_interval))
    freeze_segments: list[Segment] = []

    prev_gray = None
    freeze_start: float | None = None
    frame_idx = 0

    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        current_time = frame_idx / fps

        if prev_gray is not None:
            # 정규화 상호상관으로 유사도 측정
            similarity = _frame_similarity(prev_gray, gray)
            is_frozen = similarity >= freeze_threshold

            if is_frozen and freeze_start is None:
                freeze_start = current_time - sample_interval
            elif not is_frozen and freeze_start is not None:
                duration = current_time - freeze_start
                if duration >= min_freeze_duration:
                    freeze_segments.append(Segment(freeze_start, current_time))
                freeze_start = None

        prev_gray = gray
        frame_idx += sample_step

    # 마지막 구간 처리
    if freeze_start is not None:
        duration = total_duration - freeze_start
        if duration >= min_freeze_duration:
            freeze_segments.append(Segment(freeze_start, total_duration))

    cap.release()
    return freeze_segments


def _frame_similarity(frame1: np.ndarray, frame2: np.ndarray) -> float:
    """두 프레임의 유사도 계산 (0~1)."""
    f1 = frame1.astype(np.float32)
    f2 = frame2.astype(np.float32)

    diff = np.abs(f1 - f2)
    mean_diff = diff.mean()
    # 평균 픽셀 차이를 유사도로 변환 (255 스케일)
    similarity = 1.0 - (mean_diff / 255.0)
    return float(similarity)


def merge_bad_segments(
    silence_segs: list[Segment],
    stutter_segs: list[Segment],
    merge_gap: float = 0.2,
) -> list[Segment]:
    """무음 + 버벅 구간을 합치고, 가까운 구간끼리 병합."""
    all_segs = sorted(silence_segs + stutter_segs, key=lambda s: s.start)

    if not all_segs:
        return []

    merged = [all_segs[0]]
    for seg in all_segs[1:]:
        last = merged[-1]
        if seg.start <= last.end + merge_gap:
            merged[-1] = Segment(last.start, max(last.end, seg.end))
        else:
            merged.append(seg)

    return merged
