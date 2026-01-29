# SAM2 Video Annotator

A web application for video annotation using Meta's Segment Anything Model 2 (SAM2). Annotate objects in video frames and automatically track them through time using SAM2's video prediction capabilities.

## Features

- **Video browsing**: Select videos from a configurable directory
- **Frame navigation**: Navigate through video frames with configurable sampling rate
- **Interactive annotation**:
  - Point prompts (positive/negative clicks)
  - Bounding box prompts
- **Automatic tracking**: Propagate annotations forward/backward through the video using SAM2
- **Multi-object support**: Track multiple distinct objects with different colors
- **COCO export**: Export annotations in standard COCO format
- **Mask visualization**: View segmentation masks overlaid on video frames

## Prerequisites

- Python 3.10+
- Node.js 18+
- NVIDIA GPU with CUDA support (recommended for reasonable performance)
- SAM2 model checkpoints

## Installation

### 1. Clone and setup

```bash
cd sam2-ui
```

### 2. Download SAM2 checkpoints

Download the SAM2 checkpoints from [Meta's SAM2 repository](https://github.com/facebookresearch/sam2) and place them in the `checkpoints/` directory:

```bash
mkdir -p checkpoints
# Download checkpoints (example for large model):
wget -P checkpoints/ https://dl.fbaipublicfiles.com/segment_anything_2/072824/sam2_hiera_large.pt
```

Available models:
- `sam2_hiera_tiny.pt`
- `sam2_hiera_small.pt`
- `sam2_hiera_base_plus.pt`
- `sam2_hiera_large.pt` (default, recommended)

### 3. Install backend dependencies

```bash
cd backend
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
uv pip install git+https://github.com/facebookresearch/sam2.git
```

### 4. Install frontend dependencies

```bash
cd ../frontend
npm install
```

### 5. Prepare video directory

Create a directory for your videos and add MP4 files:

```bash
mkdir -p videos
# Add your .mp4 files to this directory
```

## Running the Application

### Option 1: Run both servers manually

**Terminal 1 - Backend:**
```bash
cd backend
source .venv/bin/activate
SAM2_VIDEO_DIR=../videos SAM2_CHECKPOINT_DIR=../checkpoints uvicorn sam2_annotator.main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Then open http://localhost:3000 in Chrome.

### Option 2: Use environment variables

You can configure the application using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SAM2_VIDEO_DIR` | `./videos` | Directory containing MP4 videos |
| `SAM2_CHECKPOINT_DIR` | `./checkpoints` | Directory containing SAM2 checkpoints |
| `SAM2_MODEL` | `sam2_hiera_large` | Default model to load |
| `SAM2_ANNOTATIONS_DIR` | `./annotations` | Output directory for saved annotations |
| `SAM2_FRAMES_CACHE_DIR` | `./frame_cache` | Cache directory for extracted frames |

## Usage

1. **Select a video**: Choose a video from the list on the home page
2. **Add objects**: Use the sidebar to add objects you want to track (e.g., "Person", "Car")
3. **Select an object**: Click on an object in the list to select it
4. **Annotate**:
   - **Point mode (P)**: Click on the object to add positive points (+), or switch to negative (-) to exclude regions
   - **Box mode (B)**: Draw a bounding box around the object
5. **Apply**: Click "Apply" or press Enter to confirm the annotation
6. **Navigate**: Use arrow keys or controls to move through frames and annotate on different keyframes if needed
7. **Propagate**: Click "Propagate" to track objects through the entire video
8. **Save/Export**:
   - Click "Save" to save annotations to disk (COCO format)
   - Click "Export COCO" to download the COCO JSON file

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| ← / → | Previous / Next frame |
| P | Point mode |
| B | Box mode |
| + / = | Positive point (include) |
| - | Negative point (exclude) |
| Enter | Apply current annotation |
| Escape | Clear current annotation |

## Frame Sampling

For long videos, you can increase the "Frame step" value to sample every Nth frame. This reduces memory usage and processing time while still providing good tracking results.

For a 30-minute 1080p video at 30fps (54,000 frames):
- Step 1: All frames (may require significant memory)
- Step 5: ~10,800 frames
- Step 10: ~5,400 frames
- Step 30: ~1,800 frames (1 per second)

## Output Format

Annotations are saved in COCO format with the following structure:

```json
{
  "info": { ... },
  "images": [
    {
      "id": 1,
      "file_name": "frame_000000.jpg",
      "frame_index": 0,
      "video_name": "video.mp4",
      "width": 1920,
      "height": 1080
    }
  ],
  "annotations": [
    {
      "id": 1,
      "image_id": 1,
      "category_id": 1,
      "segmentation": [[...]],
      "area": 12345,
      "bbox": [x, y, width, height],
      "iscrowd": 0
    }
  ],
  "categories": [
    { "id": 1, "name": "Person", "supercategory": "object" }
  ]
}
```

## Troubleshooting

### "No videos found"
- Ensure MP4 files are in the configured video directory
- Check that the `SAM2_VIDEO_DIR` environment variable is set correctly

### "Checkpoint not found"
- Download SAM2 checkpoints and place them in the `checkpoints/` directory
- Ensure filenames match expected format (e.g., `sam2_hiera_large.pt`)

### Out of memory errors
- Increase the frame step to reduce the number of frames processed
- Use a smaller model (tiny or small instead of large)
- Ensure no other GPU-intensive processes are running

### Slow performance
- Ensure CUDA is available and being used (check console output)
- Use a higher frame step for initial annotation, then reduce for final pass
- Consider using a smaller model for interactive preview

## License

MIT License - see LICENSE file for details.
