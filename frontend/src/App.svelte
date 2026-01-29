<script>
  import { onMount } from 'svelte';
  import VideoSelector from './lib/components/VideoSelector.svelte';
  import VideoPlayer from './lib/components/VideoPlayer.svelte';
  import Toolbar from './lib/components/Toolbar.svelte';
  import ObjectList from './lib/components/ObjectList.svelte';
  import StatusBar from './lib/components/StatusBar.svelte';
  import {
    currentVideo,
    videoInfo,
    isLoading,
    loadingMessage,
    error,
    availableModels,
    selectedModel,
    modelLoaded,
    resetAnnotations,
  } from './lib/stores/annotation.js';
  import { getConfig, loadModel } from './lib/api.js';

  let configLoaded = false;

  onMount(async () => {
    try {
      isLoading.set(true);
      loadingMessage.set('Loading configuration...');

      const config = await getConfig();
      availableModels.set(config.available_models);
      selectedModel.set(config.default_model);

      configLoaded = true;

      // Pre-load model
      loadingMessage.set('Loading SAM2 model...');
      await loadModel(config.default_model);
      modelLoaded.set(true);
    } catch (e) {
      error.set(e.message);
    } finally {
      isLoading.set(false);
      loadingMessage.set('');
    }
  });

  function handleVideoSelect(event) {
    const video = event.detail;
    resetAnnotations();
    currentVideo.set(video.path);
    videoInfo.set(video);
  }

  function handleBack() {
    currentVideo.set(null);
    videoInfo.set(null);
    resetAnnotations();
  }
</script>

<div class="app">
  <header>
    <h1>SAM2 Video Annotator</h1>
    {#if $currentVideo}
      <button class="secondary" on:click={handleBack}>
        ← Back to Videos
      </button>
    {/if}
  </header>

  <main>
    {#if $isLoading && !configLoaded}
      <div class="loading-screen">
        <div class="spinner"></div>
        <p>{$loadingMessage}</p>
      </div>
    {:else if !$currentVideo}
      <VideoSelector on:select={handleVideoSelect} />
    {:else}
      <div class="workspace">
        <aside class="sidebar">
          <ObjectList />
        </aside>
        <div class="main-area">
          <Toolbar />
          <VideoPlayer />
        </div>
      </div>
    {/if}
  </main>

  <StatusBar />

  {#if $error}
    <div class="error-toast">
      <span>{$error}</span>
      <button on:click={() => error.set(null)}>×</button>
    </div>
  {/if}
</div>

<style>
  .app {
    display: flex;
    flex-direction: column;
    height: 100vh;
    overflow: hidden;
  }

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 20px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
  }

  header h1 {
    font-size: 20px;
    font-weight: 600;
  }

  main {
    flex: 1;
    overflow: hidden;
  }

  .loading-screen {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 16px;
  }

  .loading-screen .spinner {
    width: 40px;
    height: 40px;
  }

  .workspace {
    display: flex;
    height: 100%;
  }

  .sidebar {
    width: 280px;
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
    overflow-y: auto;
  }

  .main-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .error-toast {
    position: fixed;
    bottom: 60px;
    left: 50%;
    transform: translateX(-50%);
    background: #c0392b;
    color: white;
    padding: 12px 20px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    gap: 12px;
    z-index: 1000;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  }

  .error-toast button {
    background: transparent;
    color: white;
    font-size: 20px;
    padding: 0 4px;
  }
</style>
