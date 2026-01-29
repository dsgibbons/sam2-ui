"""COCO format export functionality."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .config import settings
from .models import MaskResult, ObjectAnnotation
from .sam2_service import base64_to_mask
from .video_service import get_video_info


def mask_to_rle(mask: np.ndarray) -> dict:
    """Convert binary mask to COCO RLE format."""
    # Flatten mask in Fortran order (column-major)
    flat = mask.flatten(order="F")

    # Find runs
    runs = []
    prev = 0
    count = 0

    for val in flat:
        if val == prev:
            count += 1
        else:
            runs.append(count)
            count = 1
            prev = val

    runs.append(count)

    # If mask starts with 1, prepend 0
    if flat[0] == 1:
        runs = [0] + runs

    return {
        "counts": runs,
        "size": [mask.shape[0], mask.shape[1]],
    }


def mask_to_polygon(mask: np.ndarray) -> list[list[float]]:
    """Convert binary mask to polygon format."""
    import cv2

    contours, _ = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    polygons = []
    for contour in contours:
        if len(contour) < 3:
            continue
        # Flatten contour to list of coordinates [x1,y1,x2,y2,...]
        polygon = contour.flatten().tolist()
        if len(polygon) >= 6:  # At least 3 points
            polygons.append(polygon)

    return polygons


def mask_to_bbox(mask: np.ndarray) -> list[float]:
    """Get bounding box from mask in COCO format [x, y, width, height]."""
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)

    if not rows.any():
        return [0, 0, 0, 0]

    y_min, y_max = np.where(rows)[0][[0, -1]]
    x_min, x_max = np.where(cols)[0][[0, -1]]

    return [float(x_min), float(y_min), float(x_max - x_min + 1), float(y_max - y_min + 1)]


def export_coco(
    video_path: str,
    frame_step: int,
    objects: list[ObjectAnnotation],
    masks: list[MaskResult],
    output_path: Path = None,
) -> dict[str, Any]:
    """
    Export annotations in COCO format.

    Returns the COCO format dictionary and optionally saves to file.
    """
    video_info = get_video_info(video_path)

    # Create COCO structure
    coco = {
        "info": {
            "description": f"SAM2 Annotations for {video_info.name}",
            "url": "",
            "version": "1.0",
            "year": datetime.now().year,
            "contributor": "SAM2 Annotator",
            "date_created": datetime.now().isoformat(),
        },
        "licenses": [{"id": 1, "name": "Unknown", "url": ""}],
        "images": [],
        "annotations": [],
        "categories": [],
    }

    # Create categories from objects
    category_map = {}
    for obj in objects:
        if obj.object_id not in category_map:
            category_map[obj.object_id] = {
                "id": obj.object_id,
                "name": obj.name,
                "supercategory": "object",
            }

    coco["categories"] = list(category_map.values())

    # Create images and annotations
    annotation_id = 1
    image_id_map = {}

    for mask_result in masks:
        frame_idx = mask_result.frame_idx

        # Create image entry if not exists
        if frame_idx not in image_id_map:
            image_id = len(image_id_map) + 1
            image_id_map[frame_idx] = image_id

            coco["images"].append(
                {
                    "id": image_id,
                    "width": video_info.width,
                    "height": video_info.height,
                    "file_name": f"frame_{frame_idx:06d}.jpg",
                    "frame_index": frame_idx,
                    "video_name": video_info.name,
                }
            )

        image_id = image_id_map[frame_idx]

        # Create annotation for each object mask
        for obj_id_str, mask_base64 in mask_result.masks.items():
            obj_id = int(obj_id_str)
            mask = base64_to_mask(mask_base64)

            # Calculate area
            area = float(np.sum(mask))
            if area == 0:
                continue

            # Get bbox
            bbox = mask_to_bbox(mask)

            # Get segmentation (polygon format)
            segmentation = mask_to_polygon(mask)
            if not segmentation:
                continue

            coco["annotations"].append(
                {
                    "id": annotation_id,
                    "image_id": image_id,
                    "category_id": obj_id,
                    "segmentation": segmentation,
                    "area": area,
                    "bbox": bbox,
                    "iscrowd": 0,
                }
            )
            annotation_id += 1

    # Save to file if path provided
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(coco, f, indent=2)

    return coco


def save_annotations(
    video_path: str,
    frame_step: int,
    objects: list[ObjectAnnotation],
    masks: list[MaskResult],
) -> Path:
    """Save annotations to the annotations directory."""
    video_info = get_video_info(video_path)
    video_name = Path(video_info.name).stem

    # Create output path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = settings.annotations_dir / video_name
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"annotations_{timestamp}.json"

    export_coco(video_path, frame_step, objects, masks, output_path)

    return output_path
