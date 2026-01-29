<script>
  import {
    interactionMode,
    isPositivePoint,
    selectedObjectId,
    objects,
    currentPoints,
    currentBox,
    currentFrameIdx,
    maskResults,
    currentVideo,
    frameStep,
    isLoading,
    loadingMessage,
    error,
  } from '../stores/annotation.js';
  import { propagateMasks, saveAnnotations, exportCoco } from '../api.js';

  let hasObjects = $derived($objects.length > 0);
  let hasAnnotatedObjects = $derived($objects.some(o => o.frame_idx !== null));
  let hasMasks = $derived(Object.keys($maskResults).length > 0);

  async function handlePropagate() {
    if (!hasAnnotatedObjects) return;

    try {
      isLoading.set(true);
      loadingMessage.set('Propagating masks through video...');

      const result = await propagateMasks(
        $currentVideo,
        $frameStep,
        $objects.filter(o => o.frame_idx !== null),
        $currentFrameIdx,
        'both'
      );

      // Store results
      const newMasks = {};
      for (const maskResult of result.masks) {
        newMasks[maskResult.frame_idx] = maskResult.masks;
      }
      maskResults.set(newMasks);
    } catch (e) {
      error.set(e.message);
    } finally {
      isLoading.set(false);
      loadingMessage.set('');
    }
  }

  async function handleSave() {
    if (!hasMasks) return;

    try {
      isLoading.set(true);
      loadingMessage.set('Saving annotations...');

      const masks = Object.entries($maskResults).map(([frameIdx, masksObj]) => ({
        frame_idx: parseInt(frameIdx),
        masks: masksObj,
      }));

      const result = await saveAnnotations(
        $currentVideo,
        $frameStep,
        $objects.filter(o => o.frame_idx !== null),
        masks
      );

      alert(`Annotations saved to: ${result.path}`);
    } catch (e) {
      error.set(e.message);
    } finally {
      isLoading.set(false);
      loadingMessage.set('');
    }
  }

  async function handleExportCoco() {
    if (!hasMasks) return;

    try {
      isLoading.set(true);
      loadingMessage.set('Exporting COCO format...');

      const masks = Object.entries($maskResults).map(([frameIdx, masksObj]) => ({
        frame_idx: parseInt(frameIdx),
        masks: masksObj,
      }));

      const coco = await exportCoco(
        $currentVideo,
        $frameStep,
        $objects.filter(o => o.frame_idx !== null),
        masks
      );

      // Download as JSON
      const blob = new Blob([JSON.stringify(coco, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'annotations_coco.json';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      error.set(e.message);
    } finally {
      isLoading.set(false);
      loadingMessage.set('');
    }
  }
</script>

<div class="toolbar">
  <div class="tool-group">
    <span class="group-label">Mode</span>
    <div class="button-group">
      <button
        class:active={$interactionMode === 'point'}
        onclick={() => interactionMode.set('point')}
        title="Point mode - click to add points"
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
          <circle cx="12" cy="12" r="4"/>
        </svg>
        Point
      </button>
      <button
        class:active={$interactionMode === 'box'}
        onclick={() => interactionMode.set('box')}
        title="Box mode - drag to draw bounding box"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
          <rect x="4" y="4" width="16" height="16" rx="2"/>
        </svg>
        Box
      </button>
    </div>
  </div>

  {#if $interactionMode === 'point'}
    <div class="tool-group">
      <span class="group-label">Point Type</span>
      <div class="button-group">
        <button
          class:active={$isPositivePoint}
          class="positive"
          onclick={() => isPositivePoint.set(true)}
          title="Positive point - include this region"
        >
          + Include
        </button>
        <button
          class:active={!$isPositivePoint}
          class="negative"
          onclick={() => isPositivePoint.set(false)}
          title="Negative point - exclude this region"
        >
          − Exclude
        </button>
      </div>
    </div>
  {/if}

  <div class="spacer"></div>

  <div class="tool-group">
    <button
      class="primary"
      onclick={handlePropagate}
      disabled={!hasAnnotatedObjects || $isLoading}
      title="Propagate masks through entire video"
    >
      Propagate
    </button>
    <button
      class="success"
      onclick={handleSave}
      disabled={!hasMasks || $isLoading}
      title="Save annotations to disk"
    >
      Save
    </button>
    <button
      class="secondary"
      onclick={handleExportCoco}
      disabled={!hasMasks || $isLoading}
      title="Export as COCO JSON"
    >
      Export COCO
    </button>
  </div>
</div>

<style>
  .toolbar {
    display: flex;
    align-items: center;
    gap: 24px;
    padding: 12px 20px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
  }

  .tool-group {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .group-label {
    font-size: 12px;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .button-group {
    display: flex;
    gap: 4px;
  }

  .button-group button {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    font-size: 13px;
  }

  .button-group button:hover {
    background: var(--border);
  }

  .button-group button.active {
    background: var(--accent);
    border-color: var(--accent);
    color: white;
  }

  .button-group button.positive.active {
    background: var(--success);
    border-color: var(--success);
  }

  .button-group button.negative.active {
    background: #c0392b;
    border-color: #c0392b;
  }

  .spacer {
    flex: 1;
  }

  .tool-group button.primary,
  .tool-group button.success,
  .tool-group button.secondary {
    font-size: 13px;
  }
</style>
