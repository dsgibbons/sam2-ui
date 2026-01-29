"""FastAPI application for SAM2 video annotation."""

import logging
from pathlib import Path

import cv2
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .config import settings
from .coco_export import export_coco, save_annotations
from .models import (
    COCOExportRequest,
    FrameRequest,
    MaskResult,
    PropagateRequest,
    SaveAnnotationsRequest,
    SegmentRequest,
    VideoInfo,
)
from .sam2_service import (
    get_available_models,
    load_model,
    propagate_masks,
    segment_frame,
)
from .video_service import extract_frames_async, get_frame, get_video_info, list_videos

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SAM2 Video Annotator",
    description="Web application for video annotation using SAM2",
    version="0.1.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    logger.info("Starting SAM2 Video Annotator")
    logger.info(f"Video directory: {settings.video_dir.absolute()}")
    logger.info(f"Checkpoint directory: {settings.checkpoint_dir.absolute()}")
    logger.info(f"Annotations directory: {settings.annotations_dir.absolute()}")
    logger.info(f"Frame cache directory: {settings.frames_cache_dir.absolute()}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    logger.debug("Getting configuration")
    return {
        "video_dir": str(settings.video_dir.absolute()),
        "checkpoint_dir": str(settings.checkpoint_dir.absolute()),
        "annotations_dir": str(settings.annotations_dir.absolute()),
        "default_model": settings.default_model,
        "available_models": get_available_models(),
    }


@app.get("/api/videos", response_model=list[VideoInfo])
async def get_videos():
    """List all available videos."""
    logger.info("Listing videos")
    try:
        videos = list_videos()
        logger.info(f"Found {len(videos)} videos")
        return videos
    except Exception as e:
        logger.exception("Error listing videos")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/video/{video_path:path}/info", response_model=VideoInfo)
async def get_video_info_endpoint(video_path: str):
    """Get information about a specific video."""
    logger.info(f"Getting info for video: {video_path}")
    try:
        return get_video_info(video_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Video not found")
    except Exception as e:
        logger.exception(f"Error getting video info: {video_path}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/video/extract-frames")
async def extract_video_frames(request: FrameRequest):
    """Extract frames from video with given step."""
    logger.info(f"Extracting frames: {request.video_path}, step={request.frame_step}")
    try:
        # Use async version to avoid blocking
        cache_dir, frame_indices = await extract_frames_async(
            request.video_path, request.frame_step
        )
        logger.info(f"Extracted {len(frame_indices)} frames")
        return {
            "cache_dir": str(cache_dir),
            "frame_count": len(frame_indices),
            "frame_indices": frame_indices,
        }
    except FileNotFoundError:
        logger.error(f"Video not found: {request.video_path}")
        raise HTTPException(status_code=404, detail="Video not found")
    except Exception as e:
        logger.exception(f"Error extracting frames: {request.video_path}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/video/{video_path:path}/frame/{frame_idx}")
async def get_video_frame(video_path: str, frame_idx: int, frame_step: int = 1):
    """Get a specific frame as JPEG."""
    try:
        frame = get_frame(video_path, frame_idx, frame_step)
        _, buffer = cv2.imencode(".jpg", frame)
        return Response(content=buffer.tobytes(), media_type="image/jpeg")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Video not found")
    except Exception as e:
        logger.exception(f"Error getting frame {frame_idx} from {video_path}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models/load")
async def load_sam_model(model_name: str = None):
    """Load a SAM2 model."""
    logger.info(f"Loading model: {model_name or settings.default_model}")
    try:
        load_model(model_name)
        return {"status": "ok", "model": model_name or settings.default_model}
    except FileNotFoundError as e:
        logger.error(f"Model not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Error loading model")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/segment")
async def segment_single_frame(request: SegmentRequest):
    """Segment a single frame using point/box prompts."""
    logger.info(f"Segmenting frame {request.frame_idx} of {request.video_path}")
    try:
        mask_base64 = segment_frame(
            video_path=request.video_path,
            frame_idx=request.frame_idx,
            frame_step=request.frame_step,
            points=request.points,
            box=request.box,
        )
        return {"mask": mask_base64}
    except Exception as e:
        logger.exception("Error segmenting frame")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/propagate")
async def propagate_through_video(request: PropagateRequest):
    """Propagate masks through video."""
    logger.info(
        f"Propagating masks for {len(request.objects)} objects in {request.video_path}"
    )
    try:
        results = propagate_masks(
            video_path=request.video_path,
            frame_step=request.frame_step,
            objects=request.objects,
            start_frame=request.start_frame,
            direction=request.direction,
        )

        # Convert to list of MaskResult
        mask_results = []
        for frame_idx in sorted(results.keys()):
            mask_results.append(
                MaskResult(
                    frame_idx=frame_idx,
                    masks={str(k): v for k, v in results[frame_idx].items()},
                )
            )

        logger.info(f"Propagation complete: {len(mask_results)} frames with masks")
        return {
            "masks": [m.model_dump() for m in mask_results],
            "frame_indices": sorted(results.keys()),
        }
    except Exception as e:
        logger.exception("Error propagating masks")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export/coco")
async def export_coco_annotations(request: COCOExportRequest):
    """Export annotations in COCO format."""
    logger.info(f"Exporting COCO annotations for {request.video_path}")
    try:
        coco = export_coco(
            video_path=request.video_path,
            frame_step=request.frame_step,
            objects=request.objects,
            masks=request.masks,
        )
        return coco
    except Exception as e:
        logger.exception("Error exporting COCO")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/annotations/save")
async def save_annotations_endpoint(request: SaveAnnotationsRequest):
    """Save annotations to disk."""
    logger.info(f"Saving annotations for {request.video_path}")
    try:
        output_path = save_annotations(
            video_path=request.video_path,
            frame_step=request.frame_step,
            objects=request.objects,
            masks=request.masks,
        )
        logger.info(f"Annotations saved to {output_path}")
        return {"status": "ok", "path": str(output_path)}
    except Exception as e:
        logger.exception("Error saving annotations")
        raise HTTPException(status_code=500, detail=str(e))


def run():
    """Run the server."""
    uvicorn.run(
        "sam2_annotator.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    run()
