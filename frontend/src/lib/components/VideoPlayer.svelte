<script>
  import { onMount, onDestroy } from 'svelte';
  import {
    currentVideo,
    videoInfo,
    frameStep,
    frameIndices,
    currentFrameIndex,
    currentFrameIdx,
    interactionMode,
    isPositivePoint,
    selectedObjectId,
    selectedObject,
    objects,
    currentPoints,
    currentBox,
    currentFrameMasks,
    maskResults,
    isLoading,
    loadingMessage,
    error,
    updateObjectPrompts,
    clearCurrentPrompts,
  } from '../stores/annotation.js';
  import { extractFrames, getFrameUrl, segmentFrame } from '../api.js';

  let container = $state(null);
  let canvas = $state(null);
  let ctx = $state(null);
  let frameImage = new Image();
  let maskImages = $state({});
  let isDrawingBox = $state(false);
  let boxStart = $state(null);
  let previewMask = $state(null);

  // Dimensions
  let displayWidth = $state(0);
  let displayHeight = $state(0);
  let scale = $state(1);
  let offsetX = $state(0);
  let offsetY = $state(0);

  // Effects for reactive updates
  $effect(() => {
    if ($currentVideo && $frameStep) {
      loadFrames();
    }
  });

  $effect(() => {
    if ($frameIndices.length > 0) {
      loadCurrentFrame();
    }
  });

  $effect(() => {
    // Load mask images when masks change
    loadMaskImages($currentFrameMasks);
  });

  onMount(() => {
    if (canvas) {
      ctx = canvas.getContext('2d');
    }
    window.addEventListener('resize', handleResize);
    handleResize();
  });

  onDestroy(() => {
    window.removeEventListener('resize', handleResize);
  });

  function handleResize() {
    if (!container || !canvas) return;
    const rect = container.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
    calculateDisplayDimensions();
    draw();
  }

  function calculateDisplayDimensions() {
    if (!$videoInfo || !canvas) return;

    const canvasWidth = canvas.width;
    const canvasHeight = canvas.height;
    const videoWidth = $videoInfo.width;
    const videoHeight = $videoInfo.height;

    // Fit video to canvas while maintaining aspect ratio
    const scaleX = canvasWidth / videoWidth;
    const scaleY = canvasHeight / videoHeight;
    scale = Math.min(scaleX, scaleY);

    displayWidth = videoWidth * scale;
    displayHeight = videoHeight * scale;
    offsetX = (canvasWidth - displayWidth) / 2;
    offsetY = (canvasHeight - displayHeight) / 2;
  }

  async function loadFrames() {
    try {
      isLoading.set(true);
      loadingMessage.set('Extracting frames...');

      const result = await extractFrames($currentVideo, $frameStep);
      frameIndices.set(result.frame_indices);
      currentFrameIndex.set(0);
    } catch (e) {
      error.set(e.message);
    } finally {
      isLoading.set(false);
      loadingMessage.set('');
    }
  }

  function loadCurrentFrame() {
    const frameIdx = $frameIndices[$currentFrameIndex];
    if (frameIdx === undefined) return;

    const url = getFrameUrl($currentVideo, frameIdx, $frameStep);
    frameImage.onload = () => {
      calculateDisplayDimensions();
      draw();
    };
    frameImage.src = url;
  }

  async function loadMaskImages(masks) {
    maskImages = {};
    for (const [objId, base64] of Object.entries(masks)) {
      const img = new Image();
      img.src = `data:image/png;base64,${base64}`;
      await new Promise(resolve => { img.onload = resolve; });
      maskImages[objId] = img;
    }
    draw();
  }

  function draw() {
    if (!ctx || !canvas) return;

    // Clear canvas
    ctx.fillStyle = '#0a0a0a';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw frame
    if (frameImage.complete && frameImage.naturalWidth > 0) {
      ctx.drawImage(frameImage, offsetX, offsetY, displayWidth, displayHeight);
    }

    // Draw masks
    for (const [objId, img] of Object.entries(maskImages)) {
      if (img.complete) {
        ctx.globalAlpha = 0.5;
        ctx.drawImage(img, offsetX, offsetY, displayWidth, displayHeight);
        ctx.globalAlpha = 1;
      }
    }

    // Draw preview mask
    if (previewMask) {
      ctx.globalAlpha = 0.5;
      ctx.drawImage(previewMask, offsetX, offsetY, displayWidth, displayHeight);
      ctx.globalAlpha = 1;
    }

    // Draw current points
    for (const point of $currentPoints) {
      const x = offsetX + point.x * displayWidth;
      const y = offsetY + point.y * displayHeight;

      ctx.beginPath();
      ctx.arc(x, y, 8, 0, Math.PI * 2);
      ctx.fillStyle = point.label === 1 ? '#4ecca3' : '#e94560';
      ctx.fill();
      ctx.strokeStyle = 'white';
      ctx.lineWidth = 2;
      ctx.stroke();

      // Draw +/- symbol
      ctx.fillStyle = 'white';
      ctx.font = 'bold 12px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(point.label === 1 ? '+' : '−', x, y);
    }

    // Draw current box
    if ($currentBox || (isDrawingBox && boxStart)) {
      const box = $currentBox || {
        x1: boxStart.x,
        y1: boxStart.y,
        x2: boxStart.x,
        y2: boxStart.y,
      };

      const x1 = offsetX + box.x1 * displayWidth;
      const y1 = offsetY + box.y1 * displayHeight;
      const x2 = offsetX + box.x2 * displayWidth;
      const y2 = offsetY + box.y2 * displayHeight;

      ctx.strokeStyle = $selectedObject?.color || '#e94560';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      ctx.setLineDash([]);
    }
  }

  function getRelativeCoords(e) {
    const rect = canvas.getBoundingClientRect();
    const canvasX = e.clientX - rect.left;
    const canvasY = e.clientY - rect.top;

    // Convert to relative coordinates (0-1)
    const relX = (canvasX - offsetX) / displayWidth;
    const relY = (canvasY - offsetY) / displayHeight;

    return { x: Math.max(0, Math.min(1, relX)), y: Math.max(0, Math.min(1, relY)) };
  }

  function handleMouseDown(e) {
    if (!$selectedObjectId) {
      error.set('Please select an object first');
      return;
    }

    const coords = getRelativeCoords(e);

    if ($interactionMode === 'box') {
      isDrawingBox = true;
      boxStart = coords;
      currentBox.set(null);
    }
  }

  function handleMouseMove(e) {
    if (isDrawingBox && boxStart) {
      const coords = getRelativeCoords(e);
      currentBox.set({
        x1: Math.min(boxStart.x, coords.x),
        y1: Math.min(boxStart.y, coords.y),
        x2: Math.max(boxStart.x, coords.x),
        y2: Math.max(boxStart.y, coords.y),
      });
      draw();
    }
  }

  function handleMouseUp(e) {
    if (isDrawingBox && boxStart) {
      isDrawingBox = false;
      const coords = getRelativeCoords(e);
      currentBox.set({
        x1: Math.min(boxStart.x, coords.x),
        y1: Math.min(boxStart.y, coords.y),
        x2: Math.max(boxStart.x, coords.x),
        y2: Math.max(boxStart.y, coords.y),
      });
      boxStart = null;
      draw();
      previewSegmentation();
    }
  }

  function handleClick(e) {
    if ($interactionMode !== 'point') return;
    if (!$selectedObjectId) {
      error.set('Please select an object first');
      return;
    }

    const coords = getRelativeCoords(e);
    const point = {
      x: coords.x,
      y: coords.y,
      label: $isPositivePoint ? 1 : 0,
    };

    currentPoints.update(pts => [...pts, point]);
    draw();
    previewSegmentation();
  }

  async function previewSegmentation() {
    if ($currentPoints.length === 0 && !$currentBox) return;

    try {
      const result = await segmentFrame(
        $currentVideo,
        $currentFrameIdx,
        $frameStep,
        $currentPoints,
        $currentBox
      );

      if (result.mask) {
        const img = new Image();
        // Tint with selected object color
        img.src = `data:image/png;base64,${result.mask}`;
        await new Promise(resolve => { img.onload = resolve; });
        previewMask = img;
        draw();
      }
    } catch (e) {
      console.error('Preview failed:', e);
    }
  }

  function handleApply() {
    if (!$selectedObjectId) return;
    if ($currentPoints.length === 0 && !$currentBox) return;

    // Update the object with current prompts
    updateObjectPrompts(
      $selectedObjectId,
      [...$currentPoints],
      $currentBox ? { ...$currentBox } : null,
      $currentFrameIdx
    );

    // Add preview mask to results
    if (previewMask) {
      maskResults.update(results => {
        const frameIdx = $currentFrameIdx;
        const objId = $selectedObjectId;

        // Get base64 from preview mask (extract from src)
        const base64 = previewMask.src.replace('data:image/png;base64,', '');

        return {
          ...results,
          [frameIdx]: {
            ...(results[frameIdx] || {}),
            [objId]: base64,
          },
        };
      });
    }

    // Clear current prompts and preview
    clearCurrentPrompts();
    previewMask = null;
    draw();
  }

  function handleClear() {
    clearCurrentPrompts();
    previewMask = null;
    draw();
  }

  function handleFrameChange(delta) {
    currentFrameIndex.update(idx => {
      const newIdx = idx + delta;
      return Math.max(0, Math.min($frameIndices.length - 1, newIdx));
    });
    previewMask = null;
    loadCurrentFrame();
  }

  function handleFrameStepChange(e) {
    const newStep = parseInt(e.target.value);
    if (newStep > 0) {
      frameStep.set(newStep);
      maskResults.set({});
    }
  }

  // Keyboard shortcuts
  function handleKeydown(e) {
    if (e.target.tagName === 'INPUT') return;

    switch (e.key) {
      case 'ArrowLeft':
        handleFrameChange(-1);
        break;
      case 'ArrowRight':
        handleFrameChange(1);
        break;
      case 'Enter':
        handleApply();
        break;
      case 'Escape':
        handleClear();
        break;
      case 'p':
        interactionMode.set('point');
        break;
      case 'b':
        interactionMode.set('box');
        break;
      case '+':
      case '=':
        isPositivePoint.set(true);
        break;
      case '-':
        isPositivePoint.set(false);
        break;
    }
  }

  function handleMouseLeave() {
    isDrawingBox = false;
    boxStart = null;
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="video-player" bind:this={container}>
  <canvas
    bind:this={canvas}
    onclick={handleClick}
    onmousedown={handleMouseDown}
    onmousemove={handleMouseMove}
    onmouseup={handleMouseUp}
    onmouseleave={handleMouseLeave}
  ></canvas>

  <div class="controls">
    <div class="nav-controls">
      <button class="secondary" onclick={() => handleFrameChange(-10)} title="Back 10 frames">
        ⏪
      </button>
      <button class="secondary" onclick={() => handleFrameChange(-1)} title="Previous frame (←)">
        ◀
      </button>
      <span class="frame-info">
        Frame {$currentFrameIndex + 1} / {$frameIndices.length}
        <span class="frame-idx">(#{$currentFrameIdx})</span>
      </span>
      <button class="secondary" onclick={() => handleFrameChange(1)} title="Next frame (→)">
        ▶
      </button>
      <button class="secondary" onclick={() => handleFrameChange(10)} title="Forward 10 frames">
        ⏩
      </button>
    </div>

    <div class="frame-step-control">
      <label>
        Frame step:
        <input
          type="number"
          min="1"
          max="60"
          value={$frameStep}
          onchange={handleFrameStepChange}
        />
      </label>
    </div>

    <div class="annotation-controls">
      {#if $currentPoints.length > 0 || $currentBox}
        <button class="secondary" onclick={handleClear}>
          Clear (Esc)
        </button>
        <button class="primary" onclick={handleApply}>
          Apply (Enter)
        </button>
      {/if}
    </div>
  </div>

  <div class="shortcuts-hint">
    <span>← → Navigate</span>
    <span>P Point mode</span>
    <span>B Box mode</span>
    <span>+/− Include/Exclude</span>
  </div>
</div>

<style>
  .video-player {
    flex: 1;
    display: flex;
    flex-direction: column;
    position: relative;
    overflow: hidden;
  }

  canvas {
    flex: 1;
    cursor: crosshair;
  }

  .controls {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 20px;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border);
  }

  .nav-controls {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .nav-controls button {
    padding: 6px 12px;
    font-size: 16px;
  }

  .frame-info {
    min-width: 150px;
    text-align: center;
    font-size: 14px;
  }

  .frame-idx {
    color: var(--text-secondary);
    font-size: 12px;
  }

  .frame-step-control {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .frame-step-control label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    color: var(--text-secondary);
  }

  .frame-step-control input {
    width: 60px;
    padding: 4px 8px;
  }

  .annotation-controls {
    display: flex;
    gap: 8px;
  }

  .shortcuts-hint {
    position: absolute;
    bottom: 70px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: 16px;
    padding: 8px 16px;
    background: rgba(0, 0, 0, 0.7);
    border-radius: 20px;
    font-size: 11px;
    color: var(--text-secondary);
  }
</style>
