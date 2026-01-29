"""SAM2 model service for video segmentation."""

import base64
import io
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from PIL import Image

from .config import settings
from .models import BoxPrompt, ObjectAnnotation, PointPrompt
from .video_service import extract_frames, get_frame_as_rgb

# Global model instance
_predictor = None
_current_model = None


# SAM2 model configurations
SAM2_CONFIGS = {
    "sam2_hiera_tiny": "sam2_hiera_t.yaml",
    "sam2_hiera_small": "sam2_hiera_s.yaml",
    "sam2_hiera_base_plus": "sam2_hiera_b+.yaml",
    "sam2_hiera_large": "sam2_hiera_l.yaml",
}


def get_available_models() -> list[str]:
    """Get list of available SAM2 models based on checkpoint files."""
    available = []
    for model_name in SAM2_CONFIGS:
        checkpoint_path = settings.checkpoint_dir / f"{model_name}.pt"
        if checkpoint_path.exists():
            available.append(model_name)
    return available


def load_model(model_name: str = None) -> None:
    """Load SAM2 model."""
    global _predictor, _current_model

    if model_name is None:
        model_name = settings.default_model

    if _predictor is not None and _current_model == model_name:
        return

    if model_name not in SAM2_CONFIGS:
        raise ValueError(f"Unknown model: {model_name}")

    checkpoint_path = settings.checkpoint_dir / f"{model_name}.pt"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

    config_name = SAM2_CONFIGS[model_name]

    # Import SAM2 and build predictor
    try:
        from sam2.build_sam import build_sam2_video_predictor
    except ImportError:
        raise ImportError(
            "SAM2 not installed. Please install it with: "
            "pip install git+https://github.com/facebookresearch/sam2.git"
        )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading SAM2 model '{model_name}' on {device}...")

    _predictor = build_sam2_video_predictor(
        config_name,
        str(checkpoint_path),
        device=device,
    )
    _current_model = model_name
    print(f"Model loaded successfully.")


def get_predictor():
    """Get the loaded predictor, loading default model if needed."""
    if _predictor is None:
        load_model()
    return _predictor


def mask_to_base64_png(mask: np.ndarray, color: str = "#FF0000") -> str:
    """Convert binary mask to base64 encoded PNG with transparency."""
    # Parse hex color
    color = color.lstrip("#")
    r, g, b = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))

    # Create RGBA image
    h, w = mask.shape
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    rgba[mask > 0] = [r, g, b, 180]  # Semi-transparent

    # Convert to PNG
    img = Image.fromarray(rgba, mode="RGBA")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.read()).decode("utf-8")


def base64_to_mask(base64_str: str) -> np.ndarray:
    """Convert base64 PNG back to binary mask."""
    img_data = base64.b64decode(base64_str)
    img = Image.open(io.BytesIO(img_data))
    rgba = np.array(img)
    # Mask is where alpha > 0
    return (rgba[:, :, 3] > 0).astype(np.uint8)


def segment_frame(
    video_path: str,
    frame_idx: int,
    frame_step: int,
    points: list[PointPrompt] = None,
    box: BoxPrompt = None,
    object_id: int = 1,
    color: str = "#FF0000",
) -> Optional[str]:
    """
    Segment a single frame using point/box prompts.
    Returns base64 encoded mask PNG.
    """
    predictor = get_predictor()

    # Get frame
    frame = get_frame_as_rgb(video_path, frame_idx, frame_step)
    h, w = frame.shape[:2]

    # Initialize predictor with single frame
    # For single frame, we use the image predictor mode
    try:
        from sam2.build_sam import build_sam2
        from sam2.sam2_image_predictor import SAM2ImagePredictor
    except ImportError:
        raise ImportError("SAM2 not properly installed")

    # Build image predictor for single frame segmentation
    checkpoint_path = settings.checkpoint_dir / f"{_current_model}.pt"
    config_name = SAM2_CONFIGS[_current_model]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    sam2_model = build_sam2(config_name, str(checkpoint_path), device=device)
    image_predictor = SAM2ImagePredictor(sam2_model)

    image_predictor.set_image(frame)

    # Prepare prompts
    point_coords = None
    point_labels = None
    box_input = None

    if points:
        point_coords = np.array([[p.x * w, p.y * h] for p in points])
        point_labels = np.array([p.label for p in points])

    if box:
        box_input = np.array([box.x1 * w, box.y1 * h, box.x2 * w, box.y2 * h])

    # Run prediction
    masks, scores, _ = image_predictor.predict(
        point_coords=point_coords,
        point_labels=point_labels,
        box=box_input,
        multimask_output=False,
    )

    if masks is None or len(masks) == 0:
        return None

    # Take the best mask
    mask = masks[0].astype(np.uint8)

    return mask_to_base64_png(mask, color)


def propagate_masks(
    video_path: str,
    frame_step: int,
    objects: list[ObjectAnnotation],
    start_frame: int,
    direction: str = "both",
) -> dict[int, dict[int, str]]:
    """
    Propagate masks through video using SAM2 video predictor.
    Returns dict mapping frame_idx -> {object_id -> base64 mask}.
    """
    predictor = get_predictor()

    # Extract frames first
    cache_dir, frame_indices = extract_frames(video_path, frame_step)

    # Find the index of start_frame in our extracted frames
    if start_frame not in frame_indices:
        # Find nearest frame
        start_frame = min(frame_indices, key=lambda x: abs(x - start_frame))

    start_idx_in_list = frame_indices.index(start_frame)

    # Initialize video state
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
        state = predictor.init_state(video_path=str(cache_dir))

        # Add prompts for each object on their annotation frame
        for obj in objects:
            # Find the frame index in our list
            obj_frame = obj.frame_idx
            if obj_frame not in frame_indices:
                obj_frame = min(frame_indices, key=lambda x: abs(x - obj_frame))

            frame_list_idx = frame_indices.index(obj_frame)

            # Prepare prompts
            points = None
            labels = None
            box = None

            if obj.points:
                # Get frame dimensions
                frame = get_frame_as_rgb(video_path, obj_frame, frame_step)
                h, w = frame.shape[:2]

                points = np.array(
                    [[p.x * w, p.y * h] for p in obj.points], dtype=np.float32
                )
                labels = np.array([p.label for p in obj.points], dtype=np.int32)

            if obj.box:
                frame = get_frame_as_rgb(video_path, obj_frame, frame_step)
                h, w = frame.shape[:2]
                box = np.array(
                    [
                        obj.box.x1 * w,
                        obj.box.y1 * h,
                        obj.box.x2 * w,
                        obj.box.y2 * h,
                    ],
                    dtype=np.float32,
                )

            # Add object to tracking
            _, out_obj_ids, out_mask_logits = predictor.add_new_points_or_box(
                inference_state=state,
                frame_idx=frame_list_idx,
                obj_id=obj.object_id,
                points=points,
                labels=labels,
                box=box,
            )

        # Propagate through video
        results = {}

        # Create object color map
        color_map = {obj.object_id: obj.color for obj in objects}

        # Propagate in requested direction
        if direction in ("forward", "both"):
            for (
                out_frame_idx,
                out_obj_ids,
                out_mask_logits,
            ) in predictor.propagate_in_video(state):
                actual_frame_idx = frame_indices[out_frame_idx]
                if actual_frame_idx not in results:
                    results[actual_frame_idx] = {}

                for i, obj_id in enumerate(out_obj_ids):
                    mask = (out_mask_logits[i] > 0.0).cpu().numpy().squeeze()
                    if mask.any():
                        color = color_map.get(obj_id.item(), "#FF0000")
                        results[actual_frame_idx][obj_id.item()] = mask_to_base64_png(
                            mask.astype(np.uint8), color
                        )

        if direction in ("backward", "both"):
            # Reset and propagate backward
            predictor.reset_state(state)

            # Re-add prompts
            for obj in objects:
                obj_frame = obj.frame_idx
                if obj_frame not in frame_indices:
                    obj_frame = min(frame_indices, key=lambda x: abs(x - obj_frame))

                frame_list_idx = frame_indices.index(obj_frame)

                points = None
                labels = None
                box = None

                if obj.points:
                    frame = get_frame_as_rgb(video_path, obj_frame, frame_step)
                    h, w = frame.shape[:2]
                    points = np.array(
                        [[p.x * w, p.y * h] for p in obj.points], dtype=np.float32
                    )
                    labels = np.array([p.label for p in obj.points], dtype=np.int32)

                if obj.box:
                    frame = get_frame_as_rgb(video_path, obj_frame, frame_step)
                    h, w = frame.shape[:2]
                    box = np.array(
                        [
                            obj.box.x1 * w,
                            obj.box.y1 * h,
                            obj.box.x2 * w,
                            obj.box.y2 * h,
                        ],
                        dtype=np.float32,
                    )

                predictor.add_new_points_or_box(
                    inference_state=state,
                    frame_idx=frame_list_idx,
                    obj_id=obj.object_id,
                    points=points,
                    labels=labels,
                    box=box,
                )

            for (
                out_frame_idx,
                out_obj_ids,
                out_mask_logits,
            ) in predictor.propagate_in_video(state, reverse=True):
                actual_frame_idx = frame_indices[out_frame_idx]
                if actual_frame_idx not in results:
                    results[actual_frame_idx] = {}

                for i, obj_id in enumerate(out_obj_ids):
                    mask = (out_mask_logits[i] > 0.0).cpu().numpy().squeeze()
                    if mask.any():
                        color = color_map.get(obj_id.item(), "#FF0000")
                        # Only add if not already present (forward takes precedence)
                        if obj_id.item() not in results[actual_frame_idx]:
                            results[actual_frame_idx][
                                obj_id.item()
                            ] = mask_to_base64_png(mask.astype(np.uint8), color)

    return results
