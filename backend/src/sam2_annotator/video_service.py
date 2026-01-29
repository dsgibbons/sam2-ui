"""Video processing service."""

import asyncio
import hashlib
import logging
from pathlib import Path

import cv2
import numpy as np

from .config import settings
from .models import VideoInfo

logger = logging.getLogger(__name__)


def get_video_hash(video_path: str) -> str:
    """Generate a hash for video path to use as cache key."""
    return hashlib.md5(video_path.encode()).hexdigest()[:12]


def get_video_info(video_path: str) -> VideoInfo:
    """Get information about a video file."""
    full_path = settings.video_dir / video_path
    logger.debug(f"Getting video info for: {full_path}")

    if not full_path.exists():
        logger.error(f"Video not found: {video_path}")
        raise FileNotFoundError(f"Video not found: {video_path}")

    cap = cv2.VideoCapture(str(full_path))
    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        raise ValueError(f"Cannot open video: {video_path}")

    try:
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps if fps > 0 else 0

        logger.info(f"Video info: {video_path} - {frame_count} frames, {fps:.1f} fps, {width}x{height}")

        return VideoInfo(
            name=Path(video_path).name,
            path=video_path,
            duration_seconds=duration,
            frame_count=frame_count,
            fps=fps,
            width=width,
            height=height,
        )
    finally:
        cap.release()


def list_videos() -> list[VideoInfo]:
    """List all MP4 videos in the video directory."""
    logger.info(f"Listing videos in: {settings.video_dir}")
    videos = []
    if not settings.video_dir.exists():
        logger.warning(f"Video directory does not exist: {settings.video_dir}")
        return videos

    for video_file in settings.video_dir.rglob("*.mp4"):
        try:
            rel_path = video_file.relative_to(settings.video_dir)
            info = get_video_info(str(rel_path))
            videos.append(info)
        except Exception as e:
            logger.warning(f"Skipping video {video_file}: {e}")

    logger.info(f"Found {len(videos)} videos")
    return videos


def _extract_frames_sync(video_path: str, frame_step: int = 1) -> tuple[Path, list[int]]:
    """
    Extract frames from video with given step (synchronous implementation).
    Returns the cache directory and list of frame indices.
    """
    full_path = settings.video_dir / video_path
    if not full_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    # Create cache directory for this video
    video_hash = get_video_hash(video_path)
    cache_dir = settings.frames_cache_dir / f"{video_hash}_step{frame_step}"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Check if frames already extracted
    index_file = cache_dir / "frame_indices.txt"
    if index_file.exists():
        with open(index_file) as f:
            indices = [int(line.strip()) for line in f.readlines() if line.strip()]
        # Verify at least first frame exists
        if indices and (cache_dir / f"frame_{indices[0]:06d}.jpg").exists():
            logger.info(f"Using cached frames from {cache_dir} ({len(indices)} frames)")
            return cache_dir, indices

    logger.info(f"Extracting frames from {video_path} with step={frame_step}")

    # Extract frames
    cap = cv2.VideoCapture(str(full_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_indices = []
    frame_idx = 0
    extracted_count = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_step == 0:
                frame_path = cache_dir / f"frame_{frame_idx:06d}.jpg"
                cv2.imwrite(str(frame_path), frame)
                frame_indices.append(frame_idx)
                extracted_count += 1

                # Log progress every 100 frames
                if extracted_count % 100 == 0:
                    logger.info(f"Extracted {extracted_count} frames ({frame_idx}/{total_frames})")

            frame_idx += 1
    finally:
        cap.release()

    # Save index file
    with open(index_file, "w") as f:
        for idx in frame_indices:
            f.write(f"{idx}\n")

    logger.info(f"Extracted {len(frame_indices)} frames to {cache_dir}")
    return cache_dir, frame_indices


async def extract_frames_async(video_path: str, frame_step: int = 1) -> tuple[Path, list[int]]:
    """
    Extract frames from video with given step (async wrapper).
    Returns the cache directory and list of frame indices.
    """
    # Run the blocking operation in a thread pool
    return await asyncio.to_thread(_extract_frames_sync, video_path, frame_step)


def extract_frames(video_path: str, frame_step: int = 1) -> tuple[Path, list[int]]:
    """Synchronous version for non-async contexts."""
    return _extract_frames_sync(video_path, frame_step)


def get_frame(video_path: str, frame_idx: int, frame_step: int = 1) -> np.ndarray:
    """Get a specific frame from the video (uses cache if available)."""
    video_hash = get_video_hash(video_path)
    cache_dir = settings.frames_cache_dir / f"{video_hash}_step{frame_step}"
    frame_path = cache_dir / f"frame_{frame_idx:06d}.jpg"

    if frame_path.exists():
        frame = cv2.imread(str(frame_path))
        if frame is not None:
            return frame
        logger.warning(f"Failed to read cached frame: {frame_path}")

    # Fall back to direct extraction
    logger.debug(f"Direct extraction of frame {frame_idx} from {video_path}")
    full_path = settings.video_dir / video_path
    cap = cv2.VideoCapture(str(full_path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise ValueError(f"Cannot read frame {frame_idx}")

    return frame


def get_frame_as_rgb(video_path: str, frame_idx: int, frame_step: int = 1) -> np.ndarray:
    """Get frame as RGB numpy array."""
    frame = get_frame(video_path, frame_idx, frame_step)
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
