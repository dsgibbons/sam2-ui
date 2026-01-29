<script>
  import { onMount } from 'svelte';
  import { getVideos } from '../api.js';
  import { isLoading, loadingMessage } from '../stores/annotation.js';

  let { onselect } = $props();

  let videos = $state([]);
  let loadError = $state(null);

  onMount(async () => {
    await loadVideos();
  });

  async function loadVideos() {
    try {
      isLoading.set(true);
      loadingMessage.set('Loading videos...');
      videos = await getVideos();
    } catch (e) {
      loadError = e.message;
    } finally {
      isLoading.set(false);
      loadingMessage.set('');
    }
  }

  function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  }

  function formatResolution(width, height) {
    return `${width}×${height}`;
  }

  function selectVideo(video) {
    onselect?.(video);
  }
</script>

<div class="video-selector">
  <h2>Select a Video</h2>

  {#if loadError}
    <div class="error">
      <p>Failed to load videos: {loadError}</p>
      <button class="primary" onclick={loadVideos}>Retry</button>
    </div>
  {:else if videos.length === 0}
    <div class="empty">
      <p>No videos found in the configured directory.</p>
      <p class="hint">Add MP4 files to the video directory and refresh.</p>
      <button class="secondary" onclick={loadVideos}>Refresh</button>
    </div>
  {:else}
    <div class="video-grid">
      {#each videos as video}
        <button class="video-card" onclick={() => selectVideo(video)}>
          <div class="video-preview">
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z"/>
            </svg>
          </div>
          <div class="video-info">
            <h3>{video.name}</h3>
            <div class="video-meta">
              <span>{formatDuration(video.duration_seconds)}</span>
              <span>{formatResolution(video.width, video.height)}</span>
              <span>{video.fps.toFixed(1)} fps</span>
            </div>
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .video-selector {
    padding: 40px;
    max-width: 1200px;
    margin: 0 auto;
  }

  h2 {
    margin-bottom: 24px;
    font-size: 24px;
  }

  .error, .empty {
    text-align: center;
    padding: 60px 20px;
    background: var(--bg-secondary);
    border-radius: 12px;
  }

  .error p, .empty p {
    margin-bottom: 16px;
  }

  .hint {
    color: var(--text-secondary);
    font-size: 14px;
  }

  .video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
  }

  .video-card {
    background: var(--bg-secondary);
    border-radius: 12px;
    overflow: hidden;
    text-align: left;
    padding: 0;
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .video-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
  }

  .video-preview {
    aspect-ratio: 16/9;
    background: var(--bg-tertiary);
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
  }

  .video-preview svg {
    width: 48px;
    height: 48px;
  }

  .video-info {
    padding: 16px;
  }

  .video-info h3 {
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .video-meta {
    display: flex;
    gap: 12px;
    font-size: 12px;
    color: var(--text-secondary);
  }
</style>
