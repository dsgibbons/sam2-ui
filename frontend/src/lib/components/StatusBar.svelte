<script>
  import {
    isLoading,
    loadingMessage,
    modelLoaded,
    selectedModel,
    currentVideo,
    frameStep,
    frameIndices,
    currentFrameIdx,
  } from '../stores/annotation.js';
</script>

<footer class="status-bar">
  <div class="left">
    {#if $isLoading}
      <div class="loading">
        <div class="spinner"></div>
        <span>{$loadingMessage}</span>
      </div>
    {:else}
      <span class="status-item" class:success={$modelLoaded}>
        Model: {$selectedModel} {$modelLoaded ? '(loaded)' : '(not loaded)'}
      </span>
    {/if}
  </div>

  <div class="right">
    {#if $currentVideo}
      <span class="status-item">Step: {$frameStep}</span>
      <span class="status-item">Frames: {$frameIndices.length}</span>
      <span class="status-item">Current: {$currentFrameIdx}</span>
    {/if}
  </div>
</footer>

<style>
  .status-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 20px;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border);
    font-size: 12px;
    color: var(--text-secondary);
  }

  .left, .right {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .loading {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .spinner {
    width: 14px;
    height: 14px;
  }

  .status-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .status-item.success {
    color: var(--success);
  }
</style>
