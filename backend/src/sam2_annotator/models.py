"""Pydantic models for API requests and responses."""

from typing import Optional
from pydantic import BaseModel


class VideoInfo(BaseModel):
    """Information about a video file."""

    name: str
    path: str
    duration_seconds: float
    frame_count: int
    fps: float
    width: int
    height: int


class FrameRequest(BaseModel):
    """Request to extract frames from a video."""

    video_path: str
    frame_step: int = 1  # Extract every Nth frame


class PointPrompt(BaseModel):
    """A point prompt for SAM2."""

    x: float
    y: float
    label: int  # 1 for positive (include), 0 for negative (exclude)


class BoxPrompt(BaseModel):
    """A bounding box prompt for SAM2."""

    x1: float
    y1: float
    x2: float
    y2: float


class ObjectAnnotation(BaseModel):
    """An object to track."""

    object_id: int
    name: str
    color: str  # Hex color for visualization
    points: list[PointPrompt] = []
    box: Optional[BoxPrompt] = None
    frame_idx: int  # Frame where annotation was made


class PropagateRequest(BaseModel):
    """Request to propagate masks through video."""

    video_path: str
    frame_step: int
    objects: list[ObjectAnnotation]
    start_frame: int
    direction: str = "both"  # "forward", "backward", or "both"


class SegmentRequest(BaseModel):
    """Request for single-frame segmentation."""

    video_path: str
    frame_idx: int
    frame_step: int
    points: list[PointPrompt] = []
    box: Optional[BoxPrompt] = None


class MaskResult(BaseModel):
    """Result of segmentation for a single frame."""

    frame_idx: int
    masks: dict[int, str]  # object_id -> base64 encoded PNG mask


class PropagationResult(BaseModel):
    """Result of mask propagation."""

    masks: list[MaskResult]
    frame_indices: list[int]


class COCOExportRequest(BaseModel):
    """Request to export annotations in COCO format."""

    video_path: str
    frame_step: int
    objects: list[ObjectAnnotation]
    masks: list[MaskResult]


class SaveAnnotationsRequest(BaseModel):
    """Request to save annotations."""

    video_path: str
    frame_step: int
    objects: list[ObjectAnnotation]
    masks: list[MaskResult]
