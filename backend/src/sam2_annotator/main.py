"""FastAPI application for SAM2 video annotation."""

import base64
from pathlib import Path

import cv2
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

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
from .video_service import extract_frames, get_frame, get_video_info, list_videos

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


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/api/config")
async def get_config():
    """Get current configuration."""
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
    try:
        return list_videos()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/video/{video_path:path}/info", response_model=VideoInfo)
async def get_video_info_endpoint(video_path: str):
    """Get information about a specific video."""
    try:
        return get_video_info(video_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Video not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/video/extract-frames")
async def extract_video_frames(request: FrameRequest):
    """Extract frames from video with given step."""
    try:
        cache_dir, frame_indices = extract_frames(request.video_path, request.frame_step)
        return {
            "cache_dir": str(cache_dir),
            "frame_count": len(frame_indices),
            "frame_indices": frame_indices,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Video not found")
    except Exception as e:
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
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models/load")
async def load_sam_model(model_name: str = None):
    """Load a SAM2 model."""
    try:
        load_model(model_name)
        return {"status": "ok", "model": model_name or settings.default_model}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/segment")
async def segment_single_frame(request: SegmentRequest):
    """Segment a single frame using point/box prompts."""
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
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/propagate")
async def propagate_through_video(request: PropagateRequest):
    """Propagate masks through video."""
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

        return {
            "masks": [m.model_dump() for m in mask_results],
            "frame_indices": sorted(results.keys()),
        }
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export/coco")
async def export_coco_annotations(request: COCOExportRequest):
    """Export annotations in COCO format."""
    try:
        coco = export_coco(
            video_path=request.video_path,
            frame_step=request.frame_step,
            objects=request.objects,
            masks=request.masks,
        )
        return coco
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/annotations/save")
async def save_annotations_endpoint(request: SaveAnnotationsRequest):
    """Save annotations to disk."""
    try:
        output_path = save_annotations(
            video_path=request.video_path,
            frame_step=request.frame_step,
            objects=request.objects,
            masks=request.masks,
        )
        return {"status": "ok", "path": str(output_path)}
    except Exception as e:
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
