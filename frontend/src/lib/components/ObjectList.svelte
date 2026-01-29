<script>
  import {
    objects,
    selectedObjectId,
    addObject,
    removeObject,
    currentFrameIdx,
  } from '../stores/annotation.js';

  let newObjectName = $state('');

  function handleAddObject() {
    const name = newObjectName.trim() || undefined;
    addObject(name);
    newObjectName = '';
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      handleAddObject();
    }
  }

  function selectObject(id) {
    selectedObjectId.set(id);
  }

  function handleRemove(e, id) {
    e.stopPropagation();
    if (confirm('Remove this object and its annotations?')) {
      removeObject(id);
    }
  }
</script>

<div class="object-list">
  <div class="header">
    <h3>Objects</h3>
  </div>

  <div class="add-object">
    <input
      type="text"
      placeholder="Object name..."
      bind:value={newObjectName}
      onkeydown={handleKeydown}
    />
    <button class="primary" onclick={handleAddObject}>Add</button>
  </div>

  <div class="objects">
    {#if $objects.length === 0}
      <p class="empty">No objects yet. Add an object to start annotating.</p>
    {:else}
      {#each $objects as obj}
        <div
          class="object-item"
          class:selected={$selectedObjectId === obj.object_id}
          role="button"
          tabindex="0"
          onclick={() => selectObject(obj.object_id)}
          onkeydown={(e) => e.key === 'Enter' && selectObject(obj.object_id)}
        >
          <span
            class="color-dot"
            style="background: {obj.color}"
          ></span>
          <span class="object-name">{obj.name}</span>
          {#if obj.frame_idx !== null}
            <span class="annotated-badge" title="Annotated on frame {obj.frame_idx}">
              ✓
            </span>
          {/if}
          <button
            class="remove-btn"
            onclick={(e) => handleRemove(e, obj.object_id)}
            title="Remove object"
          >
            ×
          </button>
        </div>
      {/each}
    {/if}
  </div>

  <div class="instructions">
    <h4>How to annotate:</h4>
    <ol>
      <li>Add an object above</li>
      <li>Select it from the list</li>
      <li>Click points or draw a box on the video</li>
      <li>Click "Apply" to confirm</li>
      <li>Click "Propagate" to track through video</li>
    </ol>
  </div>
</div>

<style>
  .object-list {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .header {
    padding: 16px;
    border-bottom: 1px solid var(--border);
  }

  .header h3 {
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
  }

  .add-object {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
  }

  .add-object input {
    flex: 1;
    min-width: 0;
  }

  .add-object button {
    flex-shrink: 0;
  }

  .objects {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  .empty {
    padding: 20px;
    text-align: center;
    color: var(--text-secondary);
    font-size: 13px;
  }

  .object-item {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px 12px;
    background: transparent;
    border-radius: 6px;
    margin-bottom: 4px;
    text-align: left;
    cursor: pointer;
    border: 1px solid transparent;
  }

  .object-item:hover {
    background: var(--bg-tertiary);
  }

  .object-item.selected {
    background: var(--bg-tertiary);
    border: 1px solid var(--accent);
  }

  .color-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .object-name {
    flex: 1;
    font-size: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .annotated-badge {
    color: var(--success);
    font-size: 12px;
  }

  .remove-btn {
    opacity: 0;
    background: transparent;
    color: var(--text-secondary);
    font-size: 18px;
    padding: 0 4px;
    line-height: 1;
  }

  .object-item:hover .remove-btn {
    opacity: 1;
  }

  .remove-btn:hover {
    color: var(--accent);
  }

  .instructions {
    padding: 16px;
    border-top: 1px solid var(--border);
    font-size: 12px;
    color: var(--text-secondary);
  }

  .instructions h4 {
    font-weight: 600;
    margin-bottom: 8px;
  }

  .instructions ol {
    padding-left: 16px;
  }

  .instructions li {
    margin-bottom: 4px;
  }
</style>
