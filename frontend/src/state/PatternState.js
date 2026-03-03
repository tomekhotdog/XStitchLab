/**
 * Pattern state management with event emitter
 */

export class PatternState {
  constructor() {
    this.id = null;
    this.grid = [];
    this.legend = [];
    this.metadata = null;
    this.backstitchSegments = [];
    this.pipelineStages = {};
    this.adjustmentStats = null;
    this.selectedColorIndex = 0;
    this.backgroundColorIndex = -1; // -1 = auto-detect (lightest), >= 0 = user override
    this.listeners = new Map();

    // Stage navigation
    this.currentStageIndex = -1;  // -1 = pattern (editable), 0+ = pipeline stage index
    this.stageKeys = [];          // Populated on load: ['original', 'pixelated', 'adjusted', ..., 'pattern']
  }

  /**
   * Load pattern from API response data
   * @param {Object} data - Pattern data from API
   */
  load(data) {
    this.id = data.id;
    this.grid = data.grid.map(row => [...row]); // Deep copy
    this.legend = data.legend;
    this.metadata = data.metadata;
    // Split merged backstitch segments into unit segments for easier editing
    this.backstitchSegments = this.splitMergedSegments(data.backstitch_segments || []);
    this.pipelineStages = data.pipeline_stages || {};
    this.adjustmentStats = data.adjustment_stats || null;
    this.selectedColorIndex = 0;
    // Load background override if saved, otherwise auto-detect
    this.backgroundColorIndex = data.background_color_index ?? -1;

    // Build stage keys and reset to pattern view
    this.buildStageKeys();
    this.currentStageIndex = this.stageKeys.length - 1;  // Start at 'pattern'

    this.emit('load', this);
  }

  /**
   * Split merged backstitch segments into individual unit segments.
   * The pipeline merges adjacent segments for efficiency, but for editing
   * we need individual segments so users can click to remove specific parts.
   * @param {Object[]} segments - Array of segments (may be merged)
   * @returns {Object[]} Array of unit segments
   */
  splitMergedSegments(segments) {
    const unitSegments = [];

    for (const seg of segments) {
      const [x1, y1] = seg.start;
      const [x2, y2] = seg.end;

      // Check if this is a horizontal segment spanning multiple units
      if (y1 === y2 && Math.abs(x2 - x1) > 1) {
        const minX = Math.min(x1, x2);
        const maxX = Math.max(x1, x2);
        for (let x = minX; x < maxX; x++) {
          unitSegments.push({ start: [x, y1], end: [x + 1, y1] });
        }
      }
      // Check if this is a vertical segment spanning multiple units
      else if (x1 === x2 && Math.abs(y2 - y1) > 1) {
        const minY = Math.min(y1, y2);
        const maxY = Math.max(y1, y2);
        for (let y = minY; y < maxY; y++) {
          unitSegments.push({ start: [x1, y], end: [x1, y + 1] });
        }
      }
      // Check if this is a diagonal segment spanning multiple units
      else if (Math.abs(x2 - x1) === Math.abs(y2 - y1) && Math.abs(x2 - x1) > 1) {
        const steps = Math.abs(x2 - x1);
        const dx = Math.sign(x2 - x1);
        const dy = Math.sign(y2 - y1);
        for (let i = 0; i < steps; i++) {
          unitSegments.push({
            start: [x1 + i * dx, y1 + i * dy],
            end: [x1 + (i + 1) * dx, y1 + (i + 1) * dy]
          });
        }
      }
      // Already a unit segment
      else {
        unitSegments.push({ start: [...seg.start], end: [...seg.end] });
      }
    }

    return unitSegments;
  }

  /**
   * Get pattern dimensions
   * @returns {{width: number, height: number}}
   */
  getDimensions() {
    return {
      width: this.grid[0]?.length || 0,
      height: this.grid.length,
    };
  }

  /**
   * Get cell value at position
   * @param {number} x - Column
   * @param {number} y - Row
   * @returns {number} Color index
   */
  getCell(x, y) {
    if (y >= 0 && y < this.grid.length && x >= 0 && x < this.grid[0].length) {
      return this.grid[y][x];
    }
    return -1;
  }

  /**
   * Set cell value at position
   * @param {number} x - Column
   * @param {number} y - Row
   * @param {number} colorIndex - New color index
   * @returns {Object|null} Change info or null if no change
   */
  setCell(x, y, colorIndex) {
    if (y >= 0 && y < this.grid.length && x >= 0 && x < this.grid[0].length) {
      const oldValue = this.grid[y][x];
      if (oldValue !== colorIndex) {
        this.grid[y][x] = colorIndex;
        const change = { x, y, oldValue, newValue: colorIndex };
        this.emit('cellChange', change);
        return change;
      }
    }
    return null;
  }

  /**
   * Get color info for index
   * @param {number} index - Color index
   * @returns {Object|null} Legend entry
   */
  getColor(index) {
    return this.legend[index] || null;
  }

  /**
   * Get RGB color for index
   * @param {number} index - Color index
   * @returns {number[]} RGB array
   */
  getColorRGB(index) {
    const entry = this.legend[index];
    return entry ? entry.rgb : [128, 128, 128];
  }

  /**
   * Set selected color
   * @param {number} index - Color index
   */
  setSelectedColor(index) {
    if (index >= 0 && index < this.legend.length) {
      this.selectedColorIndex = index;
      this.emit('colorSelect', index);
    }
  }

  /**
   * Get number of colors
   * @returns {number}
   */
  getColorCount() {
    return this.legend.length;
  }

  /**
   * Get the background color index (auto-detected or user override)
   * @returns {number} Background color index
   */
  getBackgroundColorIndex() {
    // If user has set an override, use it
    if (this.backgroundColorIndex >= 0 && this.backgroundColorIndex < this.legend.length) {
      return this.backgroundColorIndex;
    }
    // Auto-detect: find lightest color by luminance
    let maxBrightness = -1;
    let backgroundIdx = 0;
    this.legend.forEach((entry, idx) => {
      const brightness = 0.299 * entry.rgb[0] + 0.587 * entry.rgb[1] + 0.114 * entry.rgb[2];
      if (brightness > maxBrightness) {
        maxBrightness = brightness;
        backgroundIdx = idx;
      }
    });
    return backgroundIdx;
  }

  /**
   * Set background color index (user override)
   * @param {number} index - Color index, or -1 to reset to auto-detect
   */
  setBackgroundColorIndex(index) {
    if (index === -1 || (index >= 0 && index < this.legend.length)) {
      this.backgroundColorIndex = index;
      this.emit('backgroundChange', index);
    }
  }

  /**
   * Check if background is manually set or auto-detected
   * @returns {boolean} True if user has manually set the background
   */
  isBackgroundManuallySet() {
    return this.backgroundColorIndex >= 0;
  }

  /**
   * Subscribe to events
   * @param {string} event - Event name
   * @param {Function} callback - Callback function
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
  }

  /**
   * Unsubscribe from events
   * @param {string} event - Event name
   * @param {Function} callback - Callback function
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback);
    }
  }

  /**
   * Emit event
   * @param {string} event - Event name
   * @param {*} data - Event data
   */
  emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => callback(data));
    }
  }

  /**
   * Get grid as 2D array (for API updates)
   * @returns {number[][]}
   */
  getGrid() {
    return this.grid.map(row => [...row]);
  }

  /**
   * Check if pattern is loaded
   * @returns {boolean}
   */
  isLoaded() {
    return this.grid.length > 0;
  }

  /**
   * Add a backstitch segment
   * @param {number[]} start - Start point [x, y]
   * @param {number[]} end - End point [x, y]
   * @returns {Object|null} The added segment or null if duplicate
   */
  addBackstitchSegment(start, end) {
    // Normalize segment direction (smaller coord first for consistency)
    const [s, e] = this.normalizeSegment(start, end);

    // Check for duplicate
    if (this.hasBackstitchSegment(s, e)) {
      return null;
    }

    const segment = { start: s, end: e };
    this.backstitchSegments.push(segment);
    this.emit('backstitchChange', { action: 'add', segment });
    return segment;
  }

  /**
   * Remove a backstitch segment
   * @param {number[]} start - Start point [x, y]
   * @param {number[]} end - End point [x, y]
   * @returns {Object|null} The removed segment or null if not found
   */
  removeBackstitchSegment(start, end) {
    const [s, e] = this.normalizeSegment(start, end);

    const index = this.backstitchSegments.findIndex(seg => {
      const [ns, ne] = this.normalizeSegment(seg.start, seg.end);
      return ns[0] === s[0] && ns[1] === s[1] && ne[0] === e[0] && ne[1] === e[1];
    });

    if (index !== -1) {
      const segment = this.backstitchSegments.splice(index, 1)[0];
      this.emit('backstitchChange', { action: 'remove', segment });
      return segment;
    }
    return null;
  }

  /**
   * Toggle a backstitch segment (add if missing, remove if present)
   * @param {number[]} start - Start point [x, y]
   * @param {number[]} end - End point [x, y]
   * @returns {Object} {action: 'add'|'remove', segment}
   */
  toggleBackstitchSegment(start, end) {
    const [s, e] = this.normalizeSegment(start, end);

    if (this.hasBackstitchSegment(s, e)) {
      const segment = this.removeBackstitchSegment(s, e);
      return { action: 'remove', segment };
    } else {
      const segment = this.addBackstitchSegment(s, e);
      return { action: 'add', segment };
    }
  }

  /**
   * Check if a backstitch segment exists
   * @param {number[]} start - Start point [x, y]
   * @param {number[]} end - End point [x, y]
   * @returns {boolean}
   */
  hasBackstitchSegment(start, end) {
    const [s, e] = this.normalizeSegment(start, end);

    return this.backstitchSegments.some(seg => {
      const [ns, ne] = this.normalizeSegment(seg.start, seg.end);
      return ns[0] === s[0] && ns[1] === s[1] && ne[0] === e[0] && ne[1] === e[1];
    });
  }

  /**
   * Normalize segment so smaller point comes first (for comparison)
   * @param {number[]} start
   * @param {number[]} end
   * @returns {[number[], number[]]}
   */
  normalizeSegment(start, end) {
    // Compare by y first, then by x
    if (start[1] < end[1] || (start[1] === end[1] && start[0] <= end[0])) {
      return [[...start], [...end]];
    }
    return [[...end], [...start]];
  }

  /**
   * Merge adjacent unit segments back into longer segments for cleaner export.
   * @param {Object[]} segments - Array of unit segments
   * @returns {Object[]} Array of merged segments
   */
  mergeAdjacentSegments(segments) {
    if (segments.length === 0) return [];

    // Classify segments
    const horizontal = [];
    const vertical = [];
    const backslash = []; // \ diagonals (dx === dy)
    const slash = [];     // / diagonals (dx === -dy)
    const other = [];

    for (const s of segments) {
      const dx = s.end[0] - s.start[0];
      const dy = s.end[1] - s.start[1];
      if (dy === 0) {
        horizontal.push(s);
      } else if (dx === 0) {
        vertical.push(s);
      } else if (dx === dy) {
        backslash.push(s);
      } else if (dx === -dy) {
        slash.push(s);
      } else {
        other.push(s);
      }
    }

    const merged = [];

    // Merge horizontal segments by row
    const hByRow = {};
    for (const s of horizontal) {
      const row = s.start[1];
      if (!hByRow[row]) hByRow[row] = [];
      hByRow[row].push(s);
    }
    for (const row in hByRow) {
      const segs = hByRow[row].sort((a, b) => a.start[0] - b.start[0]);
      let current = { start: [...segs[0].start], end: [...segs[0].end] };
      for (let i = 1; i < segs.length; i++) {
        if (segs[i].start[0] === current.end[0]) {
          current.end = [...segs[i].end];
        } else {
          merged.push(current);
          current = { start: [...segs[i].start], end: [...segs[i].end] };
        }
      }
      merged.push(current);
    }

    // Merge vertical segments by column
    const vByCol = {};
    for (const s of vertical) {
      const col = s.start[0];
      if (!vByCol[col]) vByCol[col] = [];
      vByCol[col].push(s);
    }
    for (const col in vByCol) {
      const segs = vByCol[col].sort((a, b) => a.start[1] - b.start[1]);
      let current = { start: [...segs[0].start], end: [...segs[0].end] };
      for (let i = 1; i < segs.length; i++) {
        if (segs[i].start[1] === current.end[1]) {
          current.end = [...segs[i].end];
        } else {
          merged.push(current);
          current = { start: [...segs[i].start], end: [...segs[i].end] };
        }
      }
      merged.push(current);
    }

    // Merge \ diagonal segments by diagonal identity (start[0] - start[1])
    const bsByDiag = {};
    for (const s of backslash) {
      const key = s.start[0] - s.start[1];
      if (!bsByDiag[key]) bsByDiag[key] = [];
      bsByDiag[key].push(s);
    }
    for (const key in bsByDiag) {
      const segs = bsByDiag[key].sort((a, b) => a.start[0] - b.start[0]);
      let current = { start: [...segs[0].start], end: [...segs[0].end] };
      for (let i = 1; i < segs.length; i++) {
        if (segs[i].start[0] === current.end[0] && segs[i].start[1] === current.end[1]) {
          current.end = [...segs[i].end];
        } else {
          merged.push(current);
          current = { start: [...segs[i].start], end: [...segs[i].end] };
        }
      }
      merged.push(current);
    }

    // Merge / diagonal segments by diagonal identity (start[0] + start[1])
    const slByDiag = {};
    for (const s of slash) {
      const key = s.start[0] + s.start[1];
      if (!slByDiag[key]) slByDiag[key] = [];
      slByDiag[key].push(s);
    }
    for (const key in slByDiag) {
      const segs = slByDiag[key].sort((a, b) => a.start[0] - b.start[0]);
      let current = { start: [...segs[0].start], end: [...segs[0].end] };
      for (let i = 1; i < segs.length; i++) {
        if (segs[i].start[0] === current.end[0] && segs[i].start[1] === current.end[1]) {
          current.end = [...segs[i].end];
        } else {
          merged.push(current);
          current = { start: [...segs[i].start], end: [...segs[i].end] };
        }
      }
      merged.push(current);
    }

    // Add other segments as-is
    merged.push(...other.map(s => ({ start: [...s.start], end: [...s.end] })));

    return merged;
  }

  /**
   * Export pattern data for JSON download (includes current edits)
   * @returns {Object}
   */
  toExportData() {
    const data = {
      id: this.id,
      metadata: this.metadata ? { ...this.metadata } : {},
      legend: (this.legend || []).map(entry => ({
        symbol: entry.symbol || '',
        dmc_code: entry.dmc_code || '',
        dmc_name: entry.dmc_name || '',
        rgb: entry.rgb ? [...entry.rgb] : [128, 128, 128],
        stitch_count: entry.stitch_count || 0,
      })),
      grid: this.getGrid(),
      backstitch_segments: this.mergeAdjacentSegments(this.backstitchSegments || []),
    };
    // Only include optional fields if they exist
    if (this.pipelineStages && Object.keys(this.pipelineStages).length > 0) {
      data.pipeline_stages = this.pipelineStages;
    }
    if (this.adjustmentStats) {
      data.adjustment_stats = this.adjustmentStats;
    }
    // Only include background override if manually set
    if (this.backgroundColorIndex >= 0) {
      data.background_color_index = this.backgroundColorIndex;
    }
    return data;
  }

  /**
   * Build stage keys from available pipeline stages
   * Order: original → quantized/pixelated → resized → pre_adjust → adjusted → pattern
   */
  buildStageKeys() {
    const stageOrder = ['original', 'quantized', 'pixelated', 'resized', 'adjusted'];
    this.stageKeys = [];

    for (const key of stageOrder) {
      if (this.pipelineStages[key]) {
        this.stageKeys.push(key);
      }
    }

    // Always add 'pattern' as the final editable stage
    this.stageKeys.push('pattern');
  }

  /**
   * Get current stage key
   * @returns {string} Current stage key ('original', 'pattern', etc.)
   */
  getCurrentStageKey() {
    return this.stageKeys[this.currentStageIndex] || 'pattern';
  }

  /**
   * Set stage index and emit event
   * @param {number} index - New stage index
   */
  setStageIndex(index) {
    const clamped = Math.max(0, Math.min(this.stageKeys.length - 1, index));
    if (clamped !== this.currentStageIndex) {
      this.currentStageIndex = clamped;
      this.emit('stageChange', this.getCurrentStageKey());
    }
  }

  /**
   * Navigate to next stage
   */
  nextStage() {
    this.setStageIndex(this.currentStageIndex + 1);
  }

  /**
   * Navigate to previous stage
   */
  prevStage() {
    this.setStageIndex(this.currentStageIndex - 1);
  }

  /**
   * Check if editing is enabled (only on 'pattern' stage)
   * @returns {boolean}
   */
  isEditingEnabled() {
    return this.getCurrentStageKey() === 'pattern';
  }

  /**
   * Set stage by key name
   * @param {string} key - Stage key to navigate to
   */
  setStageByKey(key) {
    const index = this.stageKeys.indexOf(key);
    if (index !== -1) {
      this.setStageIndex(index);
    }
  }
}

// Singleton instance
export const patternState = new PatternState();
