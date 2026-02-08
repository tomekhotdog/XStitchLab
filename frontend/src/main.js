/**
 * XStitchLab - Main entry point
 */

import { patternState } from './state/PatternState.js';
import { undoManager } from './state/UndoManager.js';
import { CanvasRenderer } from './editor/CanvasRenderer.js';
import {
  uploadImage,
  checkHealth,
  updatePattern,
  exportPNG,
  exportPNGDirect,
  exportJSON,
  exportPDF,
  exportPDFDirect,
  getThreadEstimates,
  downloadBlob,
  downloadJSON,
} from './api/client.js';

// DOM elements - Upload
const imageInput = document.getElementById('image-input');
const jsonInput = document.getElementById('json-input');
const patternTitleInput = document.getElementById('pattern-title');
const processBtn = document.getElementById('process-btn');

// DOM elements - Processing Settings
const processingModeSelect = document.getElementById('processing-mode');
const gridSizeInput = document.getElementById('grid-size');
const numColorsInput = document.getElementById('num-colors');
const quantizeMethodSelect = document.getElementById('quantize-method');
const useDitheringCheckbox = document.getElementById('use-dithering');
const colorSpaceSelect = document.getElementById('color-space');

// DOM elements - Resize Settings
const resizeMethodSelect = document.getElementById('resize-method');
const mergeThresholdInput = document.getElementById('merge-threshold');

// DOM elements - Fabric Settings
const fabricCountSelect = document.getElementById('fabric-count');

// DOM elements - Adjustment Settings
const fillHolesCheckbox = document.getElementById('fill-holes');
const snapDiagonalsCheckbox = document.getElementById('snap-diagonals');
const connectLinesCheckbox = document.getElementById('connect-lines');
const rectangularizeCheckbox = document.getElementById('rectangularize');
const removeIsolatedCheckbox = document.getElementById('remove-isolated');
const minRegionSizeInput = document.getElementById('min-region-size');
const smoothingIterationsInput = document.getElementById('smoothing-iterations');
const straightenEdgesCheckbox = document.getElementById('straighten-edges');

// DOM elements - Regularity Settings
const regularizeRectanglesCheckbox = document.getElementById('regularize-rectangles');
const minRectangleGroupSizeInput = document.getElementById('min-rectangle-group-size');
const enforceRepetitionCheckbox = document.getElementById('enforce-repetition');
const repetitionSimilarityThresholdInput = document.getElementById('repetition-similarity-threshold');

// DOM elements - Backstitch Settings
const backstitchEnabledCheckbox = document.getElementById('backstitch-enabled');
const backstitchColorSelect = document.getElementById('backstitch-color');
const backstitchContrastInput = document.getElementById('backstitch-contrast');
const backstitchDiagonalsCheckbox = document.getElementById('backstitch-diagonals');

// DOM elements - Canvas & UI
const canvas = document.getElementById('pattern-canvas');
const paletteContainer = document.getElementById('palette-container');
const patternInfoPanel = document.getElementById('pattern-info');
const infoContent = document.getElementById('info-content');
const cursorPosSpan = document.getElementById('cursor-pos');
const zoomLevelSpan = document.getElementById('zoom-level');
const statusMessage = document.getElementById('status-message');

// DOM elements - Toolbar
const btnUndo = document.getElementById('btn-undo');
const btnRedo = document.getElementById('btn-redo');
const btnSave = document.getElementById('btn-save');
const btnExport = document.getElementById('btn-export');
const viewModeSelect = document.getElementById('view-mode');
const btnEditBackstitch = document.getElementById('btn-edit-backstitch');
const btnFitCanvas = document.getElementById('btn-fit-canvas');

// DOM elements - Pipeline & Stats
const pipelinePanel = document.getElementById('pipeline-panel');
const pipelineStages = document.getElementById('pipeline-stages');
const statsPanel = document.getElementById('stats-panel');
const statsContent = document.getElementById('stats-content');

// DOM elements - Stage Navigation
const stageIndicator = document.getElementById('stage-indicator');
const stageName = document.getElementById('stage-name');

// DOM elements - Export
const threadPanel = document.getElementById('thread-panel');
const threadList = document.getElementById('thread-list');
const exportPanel = document.getElementById('export-panel');
const exportColorPNG = document.getElementById('export-color-png');
const exportSymbolPNG = document.getElementById('export-symbol-png');
const exportSheetPNG = document.getElementById('export-sheet-png');
const exportPDFBtn = document.getElementById('export-pdf');
const exportJSONBtn = document.getElementById('export-json');

// Initialize renderer
const renderer = new CanvasRenderer(canvas, patternState);

// Selected file
let selectedFile = null;

// Cursor position for keyboard navigation
let cursorX = 0;
let cursorY = 0;

// Track changes for batch undo during drag
let dragChanges = [];

/**
 * Initialize the application
 */
async function init() {
  // Check backend health
  try {
    await checkHealth();
    console.log('Backend connected');
    showStatus('Backend connected');
  } catch (e) {
    console.warn('Backend not available:', e.message);
    showStatus('Backend not available', true);
  }

  // Setup event listeners
  setupEventListeners();
}

/**
 * Show status message
 */
function showStatus(message, isError = false) {
  statusMessage.textContent = message;
  statusMessage.style.color = isError ? '#ef4444' : '#4ade80';
  if (!isError) {
    setTimeout(() => {
      statusMessage.textContent = '';
    }, 3000);
  }
}

/**
 * Get all processing settings from UI
 */
function getProcessingSettings() {
  return {
    title: patternTitleInput.value || 'Untitled',
    mode: processingModeSelect.value,
    gridSize: parseInt(gridSizeInput.value),
    numColors: parseInt(numColorsInput.value),
    quantizeMethod: quantizeMethodSelect.value,
    dithering: useDitheringCheckbox.checked,
    colorSpace: colorSpaceSelect.value,
    // Resize options
    resizeMethod: resizeMethodSelect.value,
    resizeSteps: 1,  // Single-step resize works best for majority voting
    mergeThreshold: parseInt(mergeThresholdInput.value),
    // Fabric
    fabricCount: parseInt(fabricCountSelect.value),
    // Adjustments
    fillHoles: fillHolesCheckbox.checked,
    snapDiagonals: snapDiagonalsCheckbox.checked,
    connectLines: connectLinesCheckbox.checked,
    rectangularize: rectangularizeCheckbox.checked,
    removeIsolated: removeIsolatedCheckbox.checked,
    minRegionSize: parseInt(minRegionSizeInput.value),
    smoothingIterations: parseInt(smoothingIterationsInput.value),
    straightenEdges: straightenEdgesCheckbox.checked,
    // Regularity
    regularizeRectangles: regularizeRectanglesCheckbox.checked,
    minRectangleGroupSize: parseInt(minRectangleGroupSizeInput.value),
    enforceRepetition: enforceRepetitionCheckbox.checked,
    repetitionSimilarityThreshold: parseFloat(repetitionSimilarityThresholdInput.value),
    // Backstitch
    backstitchEnabled: backstitchEnabledCheckbox.checked,
    backstitchColor: backstitchColorSelect.value,
    backstitchContrast: parseInt(backstitchContrastInput.value),
    backstitchDiagonals: backstitchDiagonalsCheckbox.checked,
  };
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
  // File input
  imageInput.addEventListener('change', (e) => {
    selectedFile = e.target.files[0];
    processBtn.disabled = !selectedFile;
    if (selectedFile) {
      // Set default title from filename
      const name = selectedFile.name.replace(/\.[^.]+$/, '');
      patternTitleInput.value = name;
    }
  });

  // JSON import
  jsonInput.addEventListener('change', handleJSONImport);

  // Process button
  processBtn.addEventListener('click', handleProcessImage);

  // Canvas mouse events
  canvas.addEventListener('mousemove', handleCanvasMouseMove);
  canvas.addEventListener('mousedown', handleCanvasMouseDown);
  canvas.addEventListener('mouseleave', () => {
    renderer.setHighlight(-1, -1);
    renderer.setHighlightedEdge(null);
    cursorPosSpan.textContent = '-';
  });

  // Canvas wheel for zoom
  canvas.addEventListener('wheel', handleCanvasWheel, { passive: false });

  // Pattern state events
  patternState.on('load', updateUI);
  patternState.on('load', () => undoManager.clear());
  patternState.on('colorSelect', updatePaletteSelection);
  patternState.on('stageChange', handleStageChange);
  patternState.on('backstitchChange', loadThreadEstimates);
  patternState.on('backgroundChange', handleBackgroundChange);

  // Undo manager state
  undoManager.subscribe((state) => {
    btnUndo.disabled = !state.canUndo;
    btnRedo.disabled = !state.canRedo;
  });

  // Toolbar buttons
  btnUndo.addEventListener('click', handleUndo);
  btnRedo.addEventListener('click', handleRedo);
  btnSave.addEventListener('click', savePattern);
  btnExport.addEventListener('click', () => {
    // Open and scroll to export panel
    exportPanel.open = true;
    exportPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });

  // View mode
  viewModeSelect.addEventListener('change', (e) => {
    renderer.setViewMode(e.target.value);
  });

  // Backstitch edit mode toggle
  btnEditBackstitch.addEventListener('click', toggleBackstitchEditMode);

  // Fit to canvas button
  btnFitCanvas.addEventListener('click', () => {
    renderer.centerPattern();
    renderer.render();
    zoomLevelSpan.textContent = '100%';
    showStatus('View reset');
  });

  // Export buttons
  exportColorPNG.addEventListener('click', () => handleExport('color'));
  exportSymbolPNG.addEventListener('click', () => handleExport('symbol'));
  exportSheetPNG.addEventListener('click', () => handleExport('sheet'));
  exportPDFBtn.addEventListener('click', handleExportPDF);
  exportJSONBtn.addEventListener('click', handleExportJSON);

  // Keyboard shortcuts
  document.addEventListener('keydown', handleKeyDown);
}

/**
 * Handle JSON import
 */
async function handleJSONImport(e) {
  const file = e.target.files[0];
  if (!file) return;

  try {
    showStatus('Loading pattern...');
    const text = await file.text();
    const data = JSON.parse(text);

    // Validate required fields
    if (!data.grid || !data.legend || !data.metadata) {
      throw new Error('Invalid pattern file: missing required fields');
    }

    // Generate a local ID for this imported pattern
    data.id = 'imported-' + Date.now();

    // Load into pattern state
    patternState.load(data);

    // Update UI
    showPatternUI();
    buildPalette();
    displayPatternInfo();

    // Show pipeline stages if available
    if (data.pipeline_stages) {
      displayPipelineStages();
    }

    showStatus('Pattern loaded successfully');
  } catch (error) {
    console.error('Failed to load pattern:', error);
    showStatus('Failed to load pattern: ' + error.message, true);
  }

  // Reset input so same file can be loaded again
  jsonInput.value = '';
}

/**
 * Handle image processing
 */
async function handleProcessImage() {
  if (!selectedFile) return;

  processBtn.disabled = true;
  processBtn.textContent = 'Processing...';
  showStatus('Processing image...');

  try {
    const settings = getProcessingSettings();
    const patternData = await uploadImage(selectedFile, settings);
    patternState.load(patternData);
    showStatus('Pattern generated successfully');
  } catch (error) {
    console.error('Processing failed:', error);
    showStatus('Processing failed: ' + error.message, true);
  } finally {
    processBtn.disabled = false;
    processBtn.textContent = 'Generate Pattern';
  }
}

/**
 * Toggle backstitch edit mode
 */
function toggleBackstitchEditMode() {
  // Only allow backstitch editing on pattern stage
  if (!patternState.isEditingEnabled()) {
    showStatus('Switch to Pattern view to edit backstitch', true);
    return;
  }

  const isActive = renderer.isBackstitchEditMode();
  renderer.setBackstitchEditMode(!isActive);
  btnEditBackstitch.classList.toggle('active', !isActive);

  if (!isActive) {
    showStatus('Backstitch edit mode: click edges to add/remove');
  } else {
    showStatus('Backstitch edit mode disabled');
  }
}

/**
 * Handle canvas mouse move
 */
function handleCanvasMouseMove(e) {
  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;

  // Backstitch edit mode - highlight edges
  if (renderer.isBackstitchEditMode()) {
    const edge = renderer.canvasToEdge(x, y);
    renderer.setHighlightedEdge(edge);
    if (edge) {
      cursorPosSpan.textContent = `Edge (${edge.start[0]},${edge.start[1]})→(${edge.end[0]},${edge.end[1]})`;
    } else {
      cursorPosSpan.textContent = '-';
    }
    return;
  }

  // Normal mode - highlight cells
  const gridPos = renderer.canvasToGrid(x, y);
  if (gridPos) {
    renderer.setHighlight(gridPos.x, gridPos.y);
    cursorPosSpan.textContent = `(${gridPos.x}, ${gridPos.y})`;
  } else {
    renderer.setHighlight(-1, -1);
    cursorPosSpan.textContent = '-';
  }
}

/**
 * Paint at position and track for undo
 */
function paintAt(x, y, colorIndex) {
  const change = patternState.setCell(x, y, colorIndex);
  if (change) {
    return change;
  }
  return null;
}

/**
 * Handle canvas mouse down (paint or backstitch edit)
 */
function handleCanvasMouseDown(e) {
  if (e.button !== 0) return; // Left click only

  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;

  // Backstitch edit mode - toggle edge on click
  if (renderer.isBackstitchEditMode()) {
    const edge = renderer.canvasToEdge(x, y);
    if (edge) {
      const result = patternState.toggleBackstitchSegment(edge.start, edge.end);
      if (result.action === 'add') {
        undoManager.push({
          type: 'backstitch',
          action: 'add',
          start: [...edge.start],
          end: [...edge.end]
        });
        showStatus('Backstitch added');
      } else {
        undoManager.push({
          type: 'backstitch',
          action: 'remove',
          start: [...edge.start],
          end: [...edge.end]
        });
        showStatus('Backstitch removed');
      }
    }
    return;
  }

  // Disable painting when not in pattern editing mode
  if (!patternState.isEditingEnabled()) return;

  const gridPos = renderer.canvasToGrid(x, y);
  if (gridPos) {
    // Update keyboard cursor
    cursorX = gridPos.x;
    cursorY = gridPos.y;

    // Start drag painting
    dragChanges = [];
    const change = paintAt(gridPos.x, gridPos.y, patternState.selectedColorIndex);
    if (change) dragChanges.push(change);
  }

  // Drag painting
  const handleDrag = (moveEvent) => {
    const mx = moveEvent.clientX - rect.left;
    const my = moveEvent.clientY - rect.top;
    const pos = renderer.canvasToGrid(mx, my);
    if (pos) {
      const change = paintAt(pos.x, pos.y, patternState.selectedColorIndex);
      if (change) dragChanges.push(change);
      renderer.setHighlight(pos.x, pos.y);
      cursorX = pos.x;
      cursorY = pos.y;
    }
  };

  const handleUp = () => {
    document.removeEventListener('mousemove', handleDrag);
    document.removeEventListener('mouseup', handleUp);

    // Push all drag changes as a batch
    if (dragChanges.length > 0) {
      undoManager.pushBatch(dragChanges);
      dragChanges = [];
    }
  };

  document.addEventListener('mousemove', handleDrag);
  document.addEventListener('mouseup', handleUp);
}

/**
 * Handle canvas wheel (zoom)
 */
function handleCanvasWheel(e) {
  e.preventDefault();

  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;

  const zoomDelta = e.deltaY > 0 ? 0.9 : 1.1;
  const newZoom = renderer.setZoom(renderer.getZoom() * zoomDelta, x, y);
  zoomLevelSpan.textContent = `${Math.round(newZoom * 100)}%`;
}

/**
 * Handle undo
 */
function handleUndo() {
  undoManager.undo((x, y, value, change) => {
    // Check if this is a backstitch change
    if (change && change.type === 'backstitch') {
      if (change.action === 'add') {
        // Undo add = remove
        patternState.removeBackstitchSegment(change.start, change.end);
      } else {
        // Undo remove = add
        patternState.addBackstitchSegment(change.start, change.end);
      }
      return;
    }
    // Regular cell change
    patternState.grid[y][x] = value;
    renderer.renderCell(x, y);
  });
}

/**
 * Handle redo
 */
function handleRedo() {
  undoManager.redo((x, y, value, change) => {
    // Check if this is a backstitch change
    if (change && change.type === 'backstitch') {
      if (change.action === 'add') {
        // Redo add = add
        patternState.addBackstitchSegment(change.start, change.end);
      } else {
        // Redo remove = remove
        patternState.removeBackstitchSegment(change.start, change.end);
      }
      return;
    }
    // Regular cell change
    patternState.grid[y][x] = value;
    renderer.renderCell(x, y);
  });
}

/**
 * Handle keyboard shortcuts
 */
function handleKeyDown(e) {
  // J key - previous stage
  if (e.key === 'j' && patternState.isLoaded() && !e.ctrlKey && !e.metaKey) {
    e.preventDefault();
    patternState.prevStage();
    return;
  }

  // K key - next stage
  if (e.key === 'k' && patternState.isLoaded() && !e.ctrlKey && !e.metaKey) {
    e.preventDefault();
    patternState.nextStage();
    return;
  }

  // Undo: Ctrl+Z
  if (e.key === 'z' && (e.ctrlKey || e.metaKey) && !e.shiftKey) {
    e.preventDefault();
    handleUndo();
    return;
  }

  // Redo: Ctrl+Shift+Z or Ctrl+Y
  if ((e.key === 'z' && (e.ctrlKey || e.metaKey) && e.shiftKey) ||
      (e.key === 'y' && (e.ctrlKey || e.metaKey))) {
    e.preventDefault();
    handleRedo();
    return;
  }

  // Save: Ctrl+S
  if (e.key === 's' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    savePattern();
    return;
  }

  // Arrow keys for cursor navigation
  if (e.key.startsWith('Arrow') && patternState.isLoaded()) {
    e.preventDefault();
    const { width, height } = patternState.getDimensions();

    switch (e.key) {
      case 'ArrowUp':
        cursorY = Math.max(0, cursorY - 1);
        break;
      case 'ArrowDown':
        cursorY = Math.min(height - 1, cursorY + 1);
        break;
      case 'ArrowLeft':
        cursorX = Math.max(0, cursorX - 1);
        break;
      case 'ArrowRight':
        cursorX = Math.min(width - 1, cursorX + 1);
        break;
    }

    renderer.setHighlight(cursorX, cursorY);
    cursorPosSpan.textContent = `(${cursorX}, ${cursorY})`;
    return;
  }

  // Space or Enter to paint at cursor (only when editing enabled)
  if ((e.key === ' ' || e.key === 'Enter') && patternState.isLoaded() && patternState.isEditingEnabled()) {
    e.preventDefault();
    const change = paintAt(cursorX, cursorY, patternState.selectedColorIndex);
    if (change) {
      undoManager.push(change);
    }
    return;
  }

  // Number keys 1-9 for color selection
  if (e.key >= '1' && e.key <= '9' && !e.ctrlKey && !e.metaKey) {
    const index = parseInt(e.key) - 1;
    if (index < patternState.getColorCount()) {
      patternState.setSelectedColor(index);
    }
    return;
  }

  // Zoom controls
  if (e.key === '+' || e.key === '=') {
    const newZoom = renderer.setZoom(renderer.getZoom() * 1.2);
    zoomLevelSpan.textContent = `${Math.round(newZoom * 100)}%`;
    return;
  }

  if (e.key === '-' && !e.ctrlKey && !e.metaKey) {
    const newZoom = renderer.setZoom(renderer.getZoom() / 1.2);
    zoomLevelSpan.textContent = `${Math.round(newZoom * 100)}%`;
    return;
  }

  // Reset view (zoom and pan)
  if (e.key === '0' && !e.ctrlKey && !e.metaKey) {
    renderer.centerPattern();
    renderer.render();
    zoomLevelSpan.textContent = '100%';
    return;
  }
}

/**
 * Save pattern to backend
 */
async function savePattern() {
  if (!patternState.id) return;

  try {
    await updatePattern(patternState.id, patternState.getGrid());
    showStatus('Pattern saved');
  } catch (error) {
    console.error('Save failed:', error);
    showStatus('Save failed', true);
  }
}

/**
 * Handle PNG export
 */
async function handleExport(mode) {
  if (!patternState.isLoaded()) {
    showStatus('No pattern loaded', true);
    return;
  }

  try {
    showStatus(`Exporting ${mode} PNG...`);

    let blob;
    // Use direct export for imported patterns, regular API for backend patterns
    if (!patternState.id || patternState.id.startsWith('imported-')) {
      const patternData = patternState.toExportData();
      blob = await exportPNGDirect(patternData, mode);
    } else {
      blob = await exportPNG(patternState.id, mode);
    }

    const filename = `${patternState.metadata?.title || 'pattern'}_${mode}.png`;
    downloadBlob(blob, filename);
    showStatus('Export complete');
  } catch (error) {
    console.error('Export failed:', error);
    showStatus('Export failed: ' + error.message, true);
  }
}

/**
 * Handle JSON export
 */
function handleExportJSON() {
  if (!patternState.isLoaded()) {
    showStatus('No pattern loaded', true);
    return;
  }

  try {
    showStatus('Exporting JSON...');
    // Export directly from frontend state (includes unsaved edits)
    const data = patternState.toExportData();
    const filename = `${patternState.metadata?.title || 'pattern'}.json`;
    downloadJSON(data, filename);
    showStatus('Export complete');
  } catch (error) {
    console.error('Export failed:', error);
    showStatus('Export failed: ' + error.message, true);
  }
}

/**
 * Handle PDF export
 */
async function handleExportPDF() {
  if (!patternState.isLoaded()) {
    showStatus('No pattern loaded', true);
    return;
  }

  try {
    showStatus('Exporting PDF...');

    let blob;
    // Use direct export for imported patterns, regular API for backend patterns
    if (!patternState.id || patternState.id.startsWith('imported-')) {
      const patternData = patternState.toExportData();
      blob = await exportPDFDirect(patternData);
    } else {
      blob = await exportPDF(patternState.id);
    }

    const filename = `${patternState.metadata?.title || 'pattern'}_pattern.pdf`;
    downloadBlob(blob, filename);
    showStatus('Export complete');
  } catch (error) {
    console.error('Export failed:', error);
    showStatus('Export failed: ' + error.message, true);
  }
}

/**
 * Handle stage change event
 */
function handleStageChange(stageKey) {
  // Update stage indicator text
  const isPattern = stageKey === 'pattern';
  stageName.textContent = isPattern ? 'Pattern (Editable)' : stageKey.replace('_', ' ');
  stageIndicator.style.display = 'inline-flex';

  // Disable backstitch edit mode when leaving pattern view
  if (!isPattern && renderer.isBackstitchEditMode()) {
    renderer.setBackstitchEditMode(false);
    btnEditBackstitch.classList.remove('active');
  }

  // Update canvas
  if (isPattern) {
    renderer.clearStageImage();
  } else {
    renderer.setStageImage(patternState.pipelineStages[stageKey]);
  }

  // Update thumbnail selection
  updateThumbnailSelection(stageKey);
}

/**
 * Update thumbnail selection highlighting
 */
function updateThumbnailSelection(stageKey) {
  // Remove selected from all thumbnails
  const thumbnails = pipelineStages.querySelectorAll('.pipeline-stage');
  thumbnails.forEach((thumb) => {
    thumb.classList.remove('selected');
    if (thumb.dataset.stage === stageKey) {
      thumb.classList.add('selected');
    }
  });
}

/**
 * Update UI after pattern load
 */
function updateUI() {
  // Show pattern info
  patternInfoPanel.style.display = 'block';
  const meta = patternState.metadata;
  infoContent.innerHTML = `
    <p><strong>Size:</strong> ${meta.width} × ${meta.height}</p>
    <p><strong>Colors:</strong> ${meta.color_count}</p>
    <p><strong>Stitches:</strong> ${meta.total_stitches.toLocaleString()}</p>
    <p><strong>Difficulty:</strong> ${meta.difficulty}</p>
  `;

  // Show export panel
  exportPanel.style.display = 'block';

  // Show thread panel and load estimates
  threadPanel.style.display = 'block';
  loadThreadEstimates();

  // Show pipeline stages
  displayPipelineStages();

  // Show adjustment stats
  displayAdjustmentStats();

  // Reset cursor
  cursorX = 0;
  cursorY = 0;

  // Build color palette
  buildPalette();

  // Initialize stage indicator (pattern is default)
  handleStageChange(patternState.getCurrentStageKey());
}

/**
 * Display pipeline stages
 */
function displayPipelineStages() {
  const stages = patternState.pipelineStages;
  if (!stages || Object.keys(stages).length === 0) {
    pipelinePanel.style.display = 'none';
    return;
  }

  pipelinePanel.style.display = 'block';

  // Define stage order and labels
  const stageOrder = [
    { key: 'original', label: 'Original' },
    { key: 'quantized', label: 'Quantized' },
    { key: 'pixelated', label: 'Pixelated' },
    { key: 'resized', label: 'Resized' },
    { key: 'adjusted', label: 'Adjusted' },
  ];

  let html = '<div class="pipeline-grid">';

  for (const stage of stageOrder) {
    if (stages[stage.key]) {
      const isSelected = patternState.getCurrentStageKey() === stage.key;
      html += `
        <div class="pipeline-stage${isSelected ? ' selected' : ''}" data-stage="${stage.key}">
          <img src="${stages[stage.key]}" alt="${stage.label}" />
          <span class="stage-label">${stage.label}</span>
        </div>
      `;
    }
  }

  // Add "Pattern" as the final clickable stage
  const isPatternSelected = patternState.getCurrentStageKey() === 'pattern';
  html += `
    <div class="pipeline-stage${isPatternSelected ? ' selected' : ''}" data-stage="pattern">
      <div class="pattern-thumbnail">
        <span class="pattern-icon">&#9998;</span>
      </div>
      <span class="stage-label">Pattern (Edit)</span>
    </div>
  `;

  html += '</div>';
  pipelineStages.innerHTML = html;

  // Add click handlers
  const thumbnails = pipelineStages.querySelectorAll('.pipeline-stage');
  thumbnails.forEach((thumb) => {
    thumb.addEventListener('click', () => {
      const stageKey = thumb.dataset.stage;
      patternState.setStageByKey(stageKey);
    });
  });
}

/**
 * Display adjustment stats
 */
function displayAdjustmentStats() {
  const stats = patternState.adjustmentStats;
  if (!stats) {
    statsPanel.style.display = 'none';
    return;
  }

  statsPanel.style.display = 'block';

  const totalPixels = patternState.metadata.width * patternState.metadata.height;
  const changeRate = ((stats.pixels_changed / totalPixels) * 100).toFixed(1);

  let html = `
    <p><strong>Pixels Changed:</strong> ${stats.pixels_changed.toLocaleString()}</p>
    <p><strong>Change Rate:</strong> ${changeRate}%</p>
  `;

  if (stats.colors_removed > 0) {
    html += `<p><strong>Colors Removed:</strong> ${stats.colors_removed}</p>`;
  }

  if (stats.operations_applied && stats.operations_applied.length > 0) {
    html += `<p><strong>Operations:</strong> ${stats.operations_applied.join(' → ')}</p>`;
  }

  statsContent.innerHTML = html;
}

/**
 * Calculate thread estimates locally
 * @param {number} fabricCount - Fabric count (stitches per inch)
 * @returns {Object} Thread estimates data
 */
function calculateThreadEstimates(fabricCount) {
  // Constants for thread calculation
  const STITCH_LENGTH_CM = 2.54 / fabricCount * 5; // ~5x the stitch width for cross stitch
  const SKEIN_LENGTH_M = 8; // Standard DMC skein length
  const SAFETY_MARGIN = 1.15; // 15% extra

  // Get background index from state (handles auto-detect and manual override)
  const backgroundIdx = patternState.getBackgroundColorIndex();

  // Calculate thread for each color
  const threads = patternState.legend.map((entry, idx) => {
    const isBackground = idx === backgroundIdx;
    const stitchCount = entry.stitch_count || 0;
    const meters = isBackground ? 0 : (stitchCount * STITCH_LENGTH_CM / 100) * SAFETY_MARGIN;
    const skeins = isBackground ? 0 : Math.ceil(meters / SKEIN_LENGTH_M);

    return {
      dmc_code: entry.dmc_code,
      dmc_name: entry.dmc_name,
      rgb: entry.rgb,
      stitch_count: stitchCount,
      meters: Math.round(meters * 10) / 10,
      skeins: skeins,
      is_background: isBackground,
    };
  });

  // Calculate backstitch thread (DMC 310 - Black)
  const backstitchSegments = patternState.backstitchSegments || [];
  let backstitchThread = null;

  if (backstitchSegments.length > 0) {
    // Calculate total backstitch length in grid units
    let totalLength = 0;
    for (const seg of backstitchSegments) {
      const dx = seg.end[0] - seg.start[0];
      const dy = seg.end[1] - seg.start[1];
      totalLength += Math.sqrt(dx * dx + dy * dy);
    }

    // Convert to meters (1 grid unit = 1 stitch width = 2.54cm / fabricCount)
    const stitchWidthCm = 2.54 / fabricCount;
    const backstitchLengthCm = totalLength * stitchWidthCm * 2; // x2 for front and back
    const backstitchMeters = (backstitchLengthCm / 100) * SAFETY_MARGIN;

    backstitchThread = {
      dmc_code: '310',
      dmc_name: 'Black (Backstitch)',
      rgb: [0, 0, 0],
      stitch_count: backstitchSegments.length,
      meters: Math.round(backstitchMeters * 10) / 10,
      skeins: Math.max(1, Math.ceil(backstitchMeters / SKEIN_LENGTH_M)),
      is_backstitch: true,
      strand_count: 1, // Single strand for backstitch
    };
  }

  // Calculate totals (excluding background)
  let totalStitches = 0;
  let totalMeters = 0;
  let totalSkeins = 0;

  for (const t of threads) {
    if (!t.is_background) {
      totalStitches += t.stitch_count;
      totalMeters += t.meters;
      totalSkeins += t.skeins;
    }
  }

  // Add backstitch to totals
  if (backstitchThread) {
    totalMeters += backstitchThread.meters;
    totalSkeins += backstitchThread.skeins;
  }

  return {
    fabric_count: fabricCount,
    threads: threads,
    backstitch_thread: backstitchThread,
    totals: {
      stitches: totalStitches,
      meters: Math.round(totalMeters * 10) / 10,
      skeins: totalSkeins,
    }
  };
}

/**
 * Load and display thread estimates
 */
async function loadThreadEstimates() {
  if (!patternState.isLoaded()) return;

  try {
    const fabricCount = parseInt(fabricCountSelect.value);

    // Try backend first, fall back to local calculation
    let data;
    if (patternState.id && !patternState.id.startsWith('imported-')) {
      try {
        data = await getThreadEstimates(patternState.id, fabricCount);
        // Add backstitch if present (backend doesn't include it)
        if (patternState.backstitchSegments?.length > 0) {
          const localData = calculateThreadEstimates(fabricCount);
          data.backstitch_thread = localData.backstitch_thread;
          if (data.backstitch_thread) {
            data.totals.meters = Math.round((data.totals.meters + data.backstitch_thread.meters) * 10) / 10;
            data.totals.skeins += data.backstitch_thread.skeins;
          }
        }
      } catch (e) {
        // Fall back to local calculation
        data = calculateThreadEstimates(fabricCount);
      }
    } else {
      // Local calculation for imported patterns
      data = calculateThreadEstimates(fabricCount);
    }

    // Build thread list HTML
    let html = `
      <div class="thread-totals">
        <p><strong>Total:</strong> ${data.totals.stitches.toLocaleString()} stitches</p>
        <p><strong>Thread:</strong> ${data.totals.meters}m (${data.totals.skeins} skeins)</p>
      </div>
      <table class="thread-table">
        <thead>
          <tr>
            <th>Color</th>
            <th>DMC</th>
            <th>Stitches</th>
            <th>Skeins</th>
          </tr>
        </thead>
        <tbody>
    `;

    for (const thread of data.threads) {
      const bgLabel = thread.is_background ? ' <span class="bg-label">(bg)</span>' : '';
      const rowClass = thread.is_background ? 'class="background-row"' : '';
      html += `
        <tr ${rowClass}>
          <td>
            <span class="thread-swatch" style="background-color: rgb(${thread.rgb.join(',')});"></span>
          </td>
          <td>${thread.dmc_code} - ${thread.dmc_name}${bgLabel}</td>
          <td>${thread.is_background ? '-' : thread.stitch_count.toLocaleString()}</td>
          <td>${thread.is_background ? '-' : thread.skeins}</td>
        </tr>
      `;
    }

    // Add backstitch thread row if present
    if (data.backstitch_thread) {
      const bs = data.backstitch_thread;
      html += `
        <tr class="backstitch-row">
          <td>
            <span class="thread-swatch" style="background-color: rgb(${bs.rgb.join(',')});"></span>
          </td>
          <td>${bs.dmc_code} - ${bs.dmc_name} <span class="bs-label">(1 strand)</span></td>
          <td>${bs.stitch_count} segs</td>
          <td>${bs.skeins}</td>
        </tr>
      `;
    }

    html += '</tbody></table>';
    threadList.innerHTML = html;
  } catch (error) {
    console.error('Failed to load thread estimates:', error);
    threadList.innerHTML = '<p class="error">Failed to load thread estimates</p>';
  }
}

/**
 * Build color palette UI
 */
function buildPalette() {
  paletteContainer.innerHTML = '';

  // Get background color index from state (handles auto-detect and manual override)
  const backgroundIndex = patternState.getBackgroundColorIndex();
  const isManualBackground = patternState.isBackgroundManuallySet();

  patternState.legend.forEach((entry, index) => {
    const isBackground = index === backgroundIndex;
    const swatch = document.createElement('div');
    swatch.className = 'color-swatch' + (isBackground ? ' background' : '');
    swatch.style.backgroundColor = `rgb(${entry.rgb[0]}, ${entry.rgb[1]}, ${entry.rgb[2]})`;

    if (index < 9) {
      const shortcut = document.createElement('span');
      shortcut.className = 'shortcut';
      shortcut.textContent = index + 1;
      swatch.appendChild(shortcut);
    }

    const dmcCode = document.createElement('span');
    dmcCode.className = 'dmc-code';
    dmcCode.textContent = entry.dmc_code;
    swatch.appendChild(dmcCode);

    const stitchCount = document.createElement('span');
    stitchCount.className = 'stitch-count';
    stitchCount.textContent = isBackground ? 'bg' : entry.stitch_count.toLocaleString();
    swatch.appendChild(stitchCount);

    const bgLabel = isBackground
      ? (isManualBackground ? ' (background - manually set, double-click to reset)' : ' (background - auto-detected, double-click another to change)')
      : ' (double-click to set as background)';
    swatch.title = `${entry.dmc_code} - ${entry.dmc_name}${isBackground ? ' - not stitched' : ` (${entry.stitch_count} stitches)`}${bgLabel}`;

    // Single click: select color for painting
    swatch.addEventListener('click', () => patternState.setSelectedColor(index));

    // Double-click: set as background
    swatch.addEventListener('dblclick', (e) => {
      e.preventDefault();
      if (isBackground && isManualBackground) {
        // If already manual background, reset to auto-detect
        patternState.setBackgroundColorIndex(-1);
        showStatus('Background reset to auto-detect');
      } else {
        patternState.setBackgroundColorIndex(index);
        showStatus(`Background set to ${entry.dmc_code} - ${entry.dmc_name}`);
      }
    });

    if (index === patternState.selectedColorIndex) {
      swatch.classList.add('selected');
    }

    paletteContainer.appendChild(swatch);
  });
}

/**
 * Update palette selection highlight
 */
function updatePaletteSelection(index) {
  const swatches = paletteContainer.querySelectorAll('.color-swatch');
  swatches.forEach((swatch, i) => {
    swatch.classList.toggle('selected', i === index);
  });
}

/**
 * Handle background color change
 */
function handleBackgroundChange() {
  buildPalette();
  loadThreadEstimates();
}

// Initialize app
init();
