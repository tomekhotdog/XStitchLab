/**
 * API client for XStitchLab backend
 */

const BASE_URL = '/api';

/**
 * Upload an image and create a pattern
 * @param {File} file - Image file
 * @param {Object} settings - Processing settings
 * @returns {Promise<Object>} Pattern data
 */
export async function uploadImage(file, settings = {}) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', settings.title || file.name.replace(/\.[^.]+$/, ''));
  formData.append('grid_size', settings.gridSize || 50);
  formData.append('num_colors', settings.numColors || 8);
  formData.append('mode', settings.mode || 'photo');
  formData.append('quantize_method', settings.quantizeMethod || 'kmeans');
  formData.append('dithering', settings.dithering || false);
  formData.append('color_space', settings.colorSpace || 'lab');
  formData.append('resize_method', settings.resizeMethod || 'lanczos');
  formData.append('resize_steps', settings.resizeSteps || 1);
  formData.append('merge_threshold', settings.mergeThreshold || 0);
  formData.append('fabric_count', settings.fabricCount || 14);

  // Adjustment settings (all default to false)
  formData.append('fill_holes', settings.fillHoles || false);
  formData.append('snap_diagonals', settings.snapDiagonals || false);
  formData.append('connect_lines', settings.connectLines || false);
  formData.append('rectangularize', settings.rectangularize || false);
  formData.append('remove_isolated', settings.removeIsolated || false);
  formData.append('min_region_size', settings.minRegionSize || 1);
  formData.append('smoothing_iterations', settings.smoothingIterations || 0);
  formData.append('straighten_edges', settings.straightenEdges || false);

  // Regularity settings
  formData.append('regularize_rectangles', settings.regularizeRectangles || false);
  formData.append('min_rectangle_group_size', settings.minRectangleGroupSize || 3);
  formData.append('enforce_repetition', settings.enforceRepetition || false);
  formData.append('repetition_similarity_threshold', settings.repetitionSimilarityThreshold || 0.8);

  // Backstitch settings
  formData.append('backstitch_enabled', settings.backstitchEnabled || false);
  formData.append('backstitch_color', settings.backstitchColor || 'auto');
  formData.append('backstitch_contrast', settings.backstitchContrast || 50);
  formData.append('backstitch_diagonals', settings.backstitchDiagonals || false);

  const response = await fetch(`${BASE_URL}/patterns/from-image`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to process image');
  }

  return response.json();
}

/**
 * Get pattern by ID
 * @param {string} id - Pattern ID
 * @returns {Promise<Object>} Pattern data
 */
export async function getPattern(id) {
  const response = await fetch(`${BASE_URL}/patterns/${id}`);

  if (!response.ok) {
    throw new Error('Pattern not found');
  }

  return response.json();
}

/**
 * Update pattern grid
 * @param {string} id - Pattern ID
 * @param {number[][]} grid - Updated grid
 * @returns {Promise<Object>} Updated pattern data
 */
export async function updatePattern(id, grid) {
  const response = await fetch(`${BASE_URL}/patterns/${id}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ grid }),
  });

  if (!response.ok) {
    throw new Error('Failed to update pattern');
  }

  return response.json();
}

/**
 * Export pattern as PNG
 * @param {string} id - Pattern ID
 * @param {string} mode - Export mode (color, symbol, sheet, realistic)
 * @returns {Promise<Blob>} PNG image blob
 */
export async function exportPNG(id, mode = 'color') {
  const response = await fetch(`${BASE_URL}/patterns/${id}/export/png?mode=${mode}`);

  if (!response.ok) {
    throw new Error('Failed to export pattern');
  }

  return response.blob();
}

/**
 * Export pattern as PNG from data (for imported patterns)
 * @param {Object} patternData - Full pattern data
 * @param {string} mode - Export mode (color, symbol, sheet, realistic)
 * @returns {Promise<Blob>} PNG image blob
 */
export async function exportPNGDirect(patternData, mode = 'color') {
  const response = await fetch(`${BASE_URL}/patterns/direct/export/png?mode=${mode}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(patternData),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to export pattern' }));
    throw new Error(error.detail || 'Failed to export pattern');
  }

  return response.blob();
}

/**
 * Export pattern as JSON
 * @param {string} id - Pattern ID
 * @returns {Promise<Object>} Pattern JSON
 */
export async function exportJSON(id) {
  const response = await fetch(`${BASE_URL}/patterns/${id}/export/json`);

  if (!response.ok) {
    throw new Error('Failed to export pattern');
  }

  return response.json();
}

/**
 * Download a blob as a file
 * @param {Blob} blob - File blob
 * @param {string} filename - Download filename
 */
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Download JSON as a file
 * @param {Object} data - JSON data
 * @param {string} filename - Download filename
 */
export function downloadJSON(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  downloadBlob(blob, filename);
}

/**
 * Export pattern as PDF
 * @param {string} id - Pattern ID
 * @returns {Promise<Blob>} PDF blob
 */
export async function exportPDF(id) {
  const response = await fetch(`${BASE_URL}/patterns/${id}/export/pdf`);

  if (!response.ok) {
    throw new Error('Failed to export PDF');
  }

  return response.blob();
}

/**
 * Export pattern as PDF from data (for imported patterns)
 * @param {Object} patternData - Full pattern data
 * @returns {Promise<Blob>} PDF blob
 */
export async function exportPDFDirect(patternData) {
  const response = await fetch(`${BASE_URL}/patterns/direct/export/pdf`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(patternData),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to export PDF' }));
    throw new Error(error.detail || 'Failed to export PDF');
  }

  return response.blob();
}

/**
 * Get thread estimates for pattern
 * @param {string} id - Pattern ID
 * @param {number} fabricCount - Fabric count
 * @returns {Promise<Object>} Thread estimates
 */
export async function getThreadEstimates(id, fabricCount = 14) {
  const response = await fetch(`${BASE_URL}/patterns/${id}/threads?fabric_count=${fabricCount}`);

  if (!response.ok) {
    throw new Error('Failed to get thread estimates');
  }

  return response.json();
}

/**
 * Check API health
 * @returns {Promise<Object>} Health status
 */
export async function checkHealth() {
  const response = await fetch(`${BASE_URL}/health`);
  return response.json();
}
