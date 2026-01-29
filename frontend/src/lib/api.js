/**
 * API client for SAM2 annotator backend.
 */

const API_BASE = '/api';

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

export async function getConfig() {
  return fetchJson(`${API_BASE}/config`);
}

export async function getVideos() {
  return fetchJson(`${API_BASE}/videos`);
}

export async function getVideoInfo(videoPath) {
  return fetchJson(`${API_BASE}/video/${encodeURIComponent(videoPath)}/info`);
}

export async function extractFrames(videoPath, frameStep) {
  return fetchJson(`${API_BASE}/video/extract-frames`, {
    method: 'POST',
    body: JSON.stringify({ video_path: videoPath, frame_step: frameStep }),
  });
}

export function getFrameUrl(videoPath, frameIdx, frameStep = 1) {
  return `${API_BASE}/video/${encodeURIComponent(videoPath)}/frame/${frameIdx}?frame_step=${frameStep}`;
}

export async function loadModel(modelName = null) {
  const url = modelName
    ? `${API_BASE}/models/load?model_name=${encodeURIComponent(modelName)}`
    : `${API_BASE}/models/load`;
  return fetchJson(url, { method: 'POST' });
}

export async function segmentFrame(videoPath, frameIdx, frameStep, points = [], box = null) {
  return fetchJson(`${API_BASE}/segment`, {
    method: 'POST',
    body: JSON.stringify({
      video_path: videoPath,
      frame_idx: frameIdx,
      frame_step: frameStep,
      points,
      box,
    }),
  });
}

export async function propagateMasks(videoPath, frameStep, objects, startFrame, direction = 'both') {
  return fetchJson(`${API_BASE}/propagate`, {
    method: 'POST',
    body: JSON.stringify({
      video_path: videoPath,
      frame_step: frameStep,
      objects,
      start_frame: startFrame,
      direction,
    }),
  });
}

export async function exportCoco(videoPath, frameStep, objects, masks) {
  return fetchJson(`${API_BASE}/export/coco`, {
    method: 'POST',
    body: JSON.stringify({
      video_path: videoPath,
      frame_step: frameStep,
      objects,
      masks,
    }),
  });
}

export async function saveAnnotations(videoPath, frameStep, objects, masks) {
  return fetchJson(`${API_BASE}/annotations/save`, {
    method: 'POST',
    body: JSON.stringify({
      video_path: videoPath,
      frame_step: frameStep,
      objects,
      masks,
    }),
  });
}
