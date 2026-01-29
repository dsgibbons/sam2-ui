import { writable, derived } from 'svelte/store';

// Available object colors
export const COLORS = [
  '#e94560', '#4ecca3', '#ffc107', '#00d4ff', '#ff6b6b',
  '#a855f7', '#22c55e', '#f97316', '#06b6d4', '#ec4899',
];

// Current video state
export const currentVideo = writable(null);
export const videoInfo = writable(null);
export const frameStep = writable(15); // Default to every 15th frame (~2fps for 30fps video)
export const frameIndices = writable([]);
export const currentFrameIndex = writable(0);

// Annotation state
export const objects = writable([]);
export const selectedObjectId = writable(null);
export const nextObjectId = writable(1);

// Interaction mode
export const interactionMode = writable('point'); // 'point' or 'box'
export const isPositivePoint = writable(true); // For point mode

// Current prompts being built (before adding to object)
export const currentPoints = writable([]);
export const currentBox = writable(null);

// Mask results from propagation
export const maskResults = writable({}); // frame_idx -> { object_id -> base64 mask }

// UI state
export const isLoading = writable(false);
export const loadingMessage = writable('');
export const error = writable(null);

// Model state
export const availableModels = writable([]);
export const selectedModel = writable('sam2_hiera_large');
export const modelLoaded = writable(false);

// Derived stores
export const currentFrameIdx = derived(
  [frameIndices, currentFrameIndex],
  ([$frameIndices, $currentFrameIndex]) => {
    if ($frameIndices.length === 0) return 0;
    return $frameIndices[$currentFrameIndex] || 0;
  }
);

export const selectedObject = derived(
  [objects, selectedObjectId],
  ([$objects, $selectedObjectId]) => {
    return $objects.find(o => o.object_id === $selectedObjectId) || null;
  }
);

export const currentFrameMasks = derived(
  [maskResults, currentFrameIdx],
  ([$maskResults, $currentFrameIdx]) => {
    return $maskResults[$currentFrameIdx] || {};
  }
);

// Helper functions
export function addObject(name) {
  let newId;
  let color;

  objects.update(objs => {
    nextObjectId.update(id => {
      newId = id;
      return id + 1;
    });
    color = COLORS[(objs.length) % COLORS.length];
    return [...objs, {
      object_id: newId,
      name: name || `Object ${newId}`,
      color,
      points: [],
      box: null,
      frame_idx: null,
    }];
  });

  selectedObjectId.set(newId);
  return newId;
}

export function removeObject(objectId) {
  objects.update(objs => objs.filter(o => o.object_id !== objectId));
  selectedObjectId.update(id => id === objectId ? null : id);

  // Remove masks for this object
  maskResults.update(results => {
    const newResults = {};
    for (const [frameIdx, masks] of Object.entries(results)) {
      const newMasks = { ...masks };
      delete newMasks[objectId];
      if (Object.keys(newMasks).length > 0) {
        newResults[frameIdx] = newMasks;
      }
    }
    return newResults;
  });
}

export function updateObjectPrompts(objectId, points, box, frameIdx) {
  objects.update(objs => objs.map(o => {
    if (o.object_id === objectId) {
      return { ...o, points, box, frame_idx: frameIdx };
    }
    return o;
  }));
}

export function clearCurrentPrompts() {
  currentPoints.set([]);
  currentBox.set(null);
}

export function resetAnnotations() {
  objects.set([]);
  selectedObjectId.set(null);
  nextObjectId.set(1);
  maskResults.set({});
  clearCurrentPrompts();
}
