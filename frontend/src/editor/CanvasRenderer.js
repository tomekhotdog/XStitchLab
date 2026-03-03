/**
 * Canvas renderer for pattern grid
 */

export class CanvasRenderer {
  constructor(canvas, patternState) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.state = patternState;

    // View state
    this.cellSize = 20;
    this.zoom = 1;
    this.offsetX = 0;
    this.offsetY = 0;

    // Highlight
    this.highlightX = -1;
    this.highlightY = -1;

    // Settings
    this.showGrid = true;
    this.viewMode = 'color'; // 'color', 'symbol', 'backstitch'
    this.symbolZoomThreshold = 1.5;

    // Stage image (for viewing pipeline stages)
    this.stageImage = null;

    // Backstitch editing
    this.backstitchEditMode = false;
    this.highlightedEdge = null; // {start: [x,y], end: [x,y]} or null

    // Bind events
    this.state.on('load', () => this.onPatternLoad());
    this.state.on('cellChange', (change) => this.renderCell(change.x, change.y));
    this.state.on('backstitchChange', () => this.render());
  }

  /**
   * Set backstitch editing mode
   * @param {boolean} enabled
   */
  setBackstitchEditMode(enabled) {
    this.backstitchEditMode = enabled;
    this.highlightedEdge = null;
    this.render();
  }

  /**
   * Get backstitch edit mode status
   * @returns {boolean}
   */
  isBackstitchEditMode() {
    return this.backstitchEditMode;
  }

  /**
   * Set view mode
   * @param {string} mode - 'color', 'symbol', or 'backstitch'
   */
  setViewMode(mode) {
    this.viewMode = mode;
    this.render();
  }

  /**
   * Handle pattern load
   */
  onPatternLoad() {
    const { width, height } = this.state.getDimensions();
    this.resizeCanvas(width, height);
    this.centerPattern();
    this.render();
  }

  /**
   * Resize canvas to fit pattern
   * @param {number} patternWidth
   * @param {number} patternHeight
   */
  resizeCanvas(patternWidth, patternHeight) {
    const wrapper = this.canvas.parentElement;
    const maxWidth = wrapper.clientWidth - 40;
    const maxHeight = wrapper.clientHeight - 40;

    // Calculate cell size to fit
    const fitCellW = maxWidth / patternWidth;
    const fitCellH = maxHeight / patternHeight;
    this.cellSize = Math.min(Math.floor(Math.min(fitCellW, fitCellH)), 30);
    this.cellSize = Math.max(this.cellSize, 4); // Minimum cell size

    this.canvas.width = patternWidth * this.cellSize;
    this.canvas.height = patternHeight * this.cellSize;
  }

  /**
   * Center pattern in view
   */
  centerPattern() {
    this.offsetX = 0;
    this.offsetY = 0;
    this.zoom = 1;
  }

  /**
   * Main render function
   */
  render() {
    if (!this.state.isLoaded()) return;

    // If showing a stage image, render that instead
    if (this.stageImage) {
      this.renderStageImage();
      return;
    }

    const { width, height } = this.state.getDimensions();
    const ctx = this.ctx;
    const cellSize = this.cellSize * this.zoom;

    // Clear canvas
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Draw cells
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        this.renderCell(x, y, false);
      }
    }

    // Draw grid
    if (this.showGrid && cellSize >= 4) {
      this.renderGrid();
    }

    // Draw backstitch overlay (if mode is backstitch or color with backstitch enabled)
    if (this.viewMode === 'backstitch' || this.state.backstitchSegments?.length > 0) {
      this.renderBackstitch();
    }

    // Draw edge highlight (backstitch edit mode)
    if (this.backstitchEditMode && this.highlightedEdge) {
      this.renderEdgeHighlight();
    }

    // Draw cell highlight (normal edit mode)
    if (!this.backstitchEditMode && this.highlightX >= 0 && this.highlightY >= 0) {
      this.renderHighlight();
    }
  }

  /**
   * Render backstitch segments
   */
  renderBackstitch() {
    const segments = this.state.backstitchSegments;
    if (!segments || segments.length === 0) return;

    const ctx = this.ctx;
    const cellSize = this.cellSize * this.zoom;

    ctx.strokeStyle = '#000';
    ctx.lineWidth = Math.max(2, cellSize * 0.15);
    ctx.lineCap = 'round';

    for (const seg of segments) {
      // Backstitch coordinates are edge-based (not cell-center)
      const startX = seg.start[0] * cellSize + this.offsetX;
      const startY = seg.start[1] * cellSize + this.offsetY;
      const endX = seg.end[0] * cellSize + this.offsetX;
      const endY = seg.end[1] * cellSize + this.offsetY;

      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();
    }
  }

  /**
   * Render single cell
   * @param {number} x - Column
   * @param {number} y - Row
   * @param {boolean} redrawGrid - Whether to redraw grid
   */
  renderCell(x, y, redrawGrid = true) {
    const ctx = this.ctx;
    const cellSize = this.cellSize * this.zoom;
    const colorIndex = this.state.getCell(x, y);
    const rgb = this.state.getColorRGB(colorIndex);
    const color = this.state.getColor(colorIndex);

    const px = x * cellSize + this.offsetX;
    const py = y * cellSize + this.offsetY;

    if (this.viewMode === 'symbol') {
      // Symbol mode: alternating background with symbol
      const isEvenCell = (x + y) % 2 === 0;
      ctx.fillStyle = isEvenCell ? '#fff' : '#f0f0f0';
      ctx.fillRect(px, py, cellSize, cellSize);

      // Always show symbol
      if (color && color.symbol && cellSize >= 8) {
        ctx.fillStyle = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
        ctx.font = `bold ${Math.floor(cellSize * 0.7)}px monospace`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(color.symbol, px + cellSize / 2, py + cellSize / 2);
      }
    } else {
      // Color mode (default): colored cells
      ctx.fillStyle = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
      ctx.fillRect(px, py, cellSize, cellSize);

      // Draw symbol if zoomed in enough
      if (this.zoom >= this.symbolZoomThreshold && cellSize >= 16) {
        if (color && color.symbol) {
          // Determine text color based on background brightness
          const brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000;
          ctx.fillStyle = brightness > 128 ? '#000' : '#fff';
          ctx.font = `${Math.floor(cellSize * 0.6)}px monospace`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(color.symbol, px + cellSize / 2, py + cellSize / 2);
        }
      }
    }

    // Redraw grid lines if needed
    if (redrawGrid && this.showGrid) {
      ctx.strokeStyle = this.viewMode === 'symbol' ? '#ddd' : '#ccc';
      ctx.lineWidth = 1;
      ctx.strokeRect(px, py, cellSize, cellSize);
    }
  }

  /**
   * Render grid lines
   */
  renderGrid() {
    const ctx = this.ctx;
    const { width, height } = this.state.getDimensions();
    const cellSize = this.cellSize * this.zoom;

    ctx.strokeStyle = '#ddd';
    ctx.lineWidth = 1;

    // Vertical lines
    for (let x = 0; x <= width; x++) {
      const px = x * cellSize + this.offsetX;
      ctx.beginPath();
      ctx.moveTo(px, this.offsetY);
      ctx.lineTo(px, height * cellSize + this.offsetY);
      ctx.stroke();
    }

    // Horizontal lines
    for (let y = 0; y <= height; y++) {
      const py = y * cellSize + this.offsetY;
      ctx.beginPath();
      ctx.moveTo(this.offsetX, py);
      ctx.lineTo(width * cellSize + this.offsetX, py);
      ctx.stroke();
    }

    // Major grid lines every 10 cells
    ctx.strokeStyle = '#999';
    ctx.lineWidth = 2;

    for (let x = 0; x <= width; x += 10) {
      const px = x * cellSize + this.offsetX;
      ctx.beginPath();
      ctx.moveTo(px, this.offsetY);
      ctx.lineTo(px, height * cellSize + this.offsetY);
      ctx.stroke();
    }

    for (let y = 0; y <= height; y += 10) {
      const py = y * cellSize + this.offsetY;
      ctx.beginPath();
      ctx.moveTo(this.offsetX, py);
      ctx.lineTo(width * cellSize + this.offsetX, py);
      ctx.stroke();
    }
  }

  /**
   * Render cell highlight
   */
  renderHighlight() {
    const ctx = this.ctx;
    const cellSize = this.cellSize * this.zoom;
    const px = this.highlightX * cellSize + this.offsetX;
    const py = this.highlightY * cellSize + this.offsetY;

    ctx.strokeStyle = '#e94560';
    ctx.lineWidth = 3;
    ctx.strokeRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
  }

  /**
   * Set highlight position
   * @param {number} x - Column (-1 to clear)
   * @param {number} y - Row (-1 to clear)
   */
  setHighlight(x, y) {
    const oldX = this.highlightX;
    const oldY = this.highlightY;

    this.highlightX = x;
    this.highlightY = y;

    // Redraw affected cells
    if (oldX >= 0 && oldY >= 0) {
      this.renderCell(oldX, oldY);
    }
    if (x >= 0 && y >= 0) {
      this.renderCell(x, y);
      this.renderHighlight();
    }
  }

  /**
   * Set highlighted edge for backstitch editing
   * @param {Object|null} edge - {start: [x,y], end: [x,y]} or null
   */
  setHighlightedEdge(edge) {
    this.highlightedEdge = edge;
    this.render();
  }

  /**
   * Render highlighted edge during backstitch editing
   */
  renderEdgeHighlight() {
    if (!this.highlightedEdge) return;

    const ctx = this.ctx;
    const cellSize = this.cellSize * this.zoom;
    const { start, end } = this.highlightedEdge;

    const startX = start[0] * cellSize + this.offsetX;
    const startY = start[1] * cellSize + this.offsetY;
    const endX = end[0] * cellSize + this.offsetX;
    const endY = end[1] * cellSize + this.offsetY;

    // Check if this edge already exists
    const exists = this.state.hasBackstitchSegment(start, end);

    // Draw highlight (green for add, red for remove)
    ctx.strokeStyle = exists ? '#ef4444' : '#4ade80';
    ctx.lineWidth = Math.max(4, cellSize * 0.2);
    ctx.lineCap = 'round';

    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(endX, endY);
    ctx.stroke();
  }

  /**
   * Convert canvas coordinates to nearest edge (for backstitch editing)
   * @param {number} canvasX
   * @param {number} canvasY
   * @returns {{start: number[], end: number[]}|null} Edge segment or null
   */
  canvasToEdge(canvasX, canvasY) {
    if (this.stageImage) return null;

    const cellSize = this.cellSize * this.zoom;
    const { width, height } = this.state.getDimensions();

    // Get position relative to grid
    const relX = (canvasX - this.offsetX) / cellSize;
    const relY = (canvasY - this.offsetY) / cellSize;

    // Find nearest grid intersection (corner)
    const nearestCornerX = Math.round(relX);
    const nearestCornerY = Math.round(relY);

    // Distance to nearest corner
    const cornerDistX = Math.abs(relX - nearestCornerX);
    const cornerDistY = Math.abs(relY - nearestCornerY);

    // Threshold for edge detection (fraction of cell size)
    const edgeThreshold = 0.35;

    // Check if we're close to a corner (intersection of edges)
    if (cornerDistX < edgeThreshold && cornerDistY < edgeThreshold) {
      // Near a corner - find the edge the user is most likely targeting
      // Use dot-product scoring: pick the edge whose direction best matches
      // the cursor's offset from the corner (works fairly for h/v/diagonal)

      const offsetFromCornerX = relX - nearestCornerX;
      const offsetFromCornerY = relY - nearestCornerY;

      const offsetLen = Math.sqrt(offsetFromCornerX * offsetFromCornerX + offsetFromCornerY * offsetFromCornerY);

      let candidates = [];

      // Horizontal edges (left/right from corner)
      if (nearestCornerX > 0 && nearestCornerY >= 0 && nearestCornerY <= height) {
        candidates.push({
          start: [nearestCornerX - 1, nearestCornerY],
          end: [nearestCornerX, nearestCornerY],
          dirX: -1, dirY: 0
        });
      }
      if (nearestCornerX < width && nearestCornerY >= 0 && nearestCornerY <= height) {
        candidates.push({
          start: [nearestCornerX, nearestCornerY],
          end: [nearestCornerX + 1, nearestCornerY],
          dirX: 1, dirY: 0
        });
      }

      // Vertical edges (up/down from corner)
      if (nearestCornerY > 0 && nearestCornerX >= 0 && nearestCornerX <= width) {
        candidates.push({
          start: [nearestCornerX, nearestCornerY - 1],
          end: [nearestCornerX, nearestCornerY],
          dirX: 0, dirY: -1
        });
      }
      if (nearestCornerY < height && nearestCornerX >= 0 && nearestCornerX <= width) {
        candidates.push({
          start: [nearestCornerX, nearestCornerY],
          end: [nearestCornerX, nearestCornerY + 1],
          dirX: 0, dirY: 1
        });
      }

      // Diagonal edges (4 diagonals emanating from corner)
      const DIAG_INV = 1 / Math.SQRT2;
      // \ lower-right
      if (nearestCornerX < width && nearestCornerY < height) {
        candidates.push({
          start: [nearestCornerX, nearestCornerY],
          end: [nearestCornerX + 1, nearestCornerY + 1],
          dirX: DIAG_INV, dirY: DIAG_INV
        });
      }
      // \ upper-left
      if (nearestCornerX > 0 && nearestCornerY > 0) {
        candidates.push({
          start: [nearestCornerX - 1, nearestCornerY - 1],
          end: [nearestCornerX, nearestCornerY],
          dirX: -DIAG_INV, dirY: -DIAG_INV
        });
      }
      // / lower-left
      if (nearestCornerX > 0 && nearestCornerY < height) {
        candidates.push({
          start: [nearestCornerX, nearestCornerY],
          end: [nearestCornerX - 1, nearestCornerY + 1],
          dirX: -DIAG_INV, dirY: DIAG_INV
        });
      }
      // / upper-right
      if (nearestCornerX < width && nearestCornerY > 0) {
        candidates.push({
          start: [nearestCornerX, nearestCornerY],
          end: [nearestCornerX + 1, nearestCornerY - 1],
          dirX: DIAG_INV, dirY: -DIAG_INV
        });
      }

      // Score each candidate by dot product with cursor offset direction
      if (candidates.length > 0 && offsetLen > 0.001) {
        const nx = offsetFromCornerX / offsetLen;
        const ny = offsetFromCornerY / offsetLen;
        for (const c of candidates) {
          c.score = c.dirX * nx + c.dirY * ny;
        }
        candidates.sort((a, b) => b.score - a.score);
        return { start: candidates[0].start, end: candidates[0].end };
      }
    }

    // Check if we're on a horizontal edge (between two cells vertically)
    const cellY = Math.floor(relY);
    const fracY = relY - cellY;
    if (fracY < edgeThreshold || fracY > (1 - edgeThreshold)) {
      const edgeY = fracY < 0.5 ? cellY : cellY + 1;
      const cellX = Math.floor(relX);

      if (cellX >= 0 && cellX < width && edgeY >= 0 && edgeY <= height) {
        return {
          start: [cellX, edgeY],
          end: [cellX + 1, edgeY]
        };
      }
    }

    // Check if we're on a vertical edge (between two cells horizontally)
    const cellX = Math.floor(relX);
    const fracX = relX - cellX;
    if (fracX < edgeThreshold || fracX > (1 - edgeThreshold)) {
      const edgeX = fracX < 0.5 ? cellX : cellX + 1;
      const cellY2 = Math.floor(relY);

      if (cellY2 >= 0 && cellY2 < height && edgeX >= 0 && edgeX <= width) {
        return {
          start: [edgeX, cellY2],
          end: [edgeX, cellY2 + 1]
        };
      }
    }

    // Check if cursor is near a cell diagonal (interior detection)
    {
      const cx = Math.floor(relX);
      const cy = Math.floor(relY);
      if (cx >= 0 && cx < width && cy >= 0 && cy < height) {
        const fx = relX - cx;
        const fy = relY - cy;
        const diagThreshold = 0.3;

        // Distance to \ diagonal: |fx - fy| / sqrt(2)
        const distBackslash = Math.abs(fx - fy) / Math.SQRT2;
        // Distance to / diagonal: |fx + fy - 1| / sqrt(2)
        const distSlash = Math.abs(fx + fy - 1) / Math.SQRT2;

        if (distBackslash < diagThreshold || distSlash < diagThreshold) {
          if (distBackslash <= distSlash) {
            // \ diagonal: (cx, cy) -> (cx+1, cy+1)
            return { start: [cx, cy], end: [cx + 1, cy + 1] };
          } else {
            // / diagonal: (cx+1, cy) -> (cx, cy+1)
            return { start: [cx + 1, cy], end: [cx, cy + 1] };
          }
        }
      }
    }

    return null;
  }

  /**
   * Convert canvas coordinates to grid coordinates
   * @param {number} canvasX
   * @param {number} canvasY
   * @returns {{x: number, y: number}|null}
   */
  canvasToGrid(canvasX, canvasY) {
    // Disable grid interaction when viewing stage image
    if (this.stageImage) {
      return null;
    }

    const cellSize = this.cellSize * this.zoom;
    const x = Math.floor((canvasX - this.offsetX) / cellSize);
    const y = Math.floor((canvasY - this.offsetY) / cellSize);

    const { width, height } = this.state.getDimensions();
    if (x >= 0 && x < width && y >= 0 && y < height) {
      return { x, y };
    }
    return null;
  }

  /**
   * Set zoom level
   * @param {number} zoom - Zoom factor (0.25 to 4)
   * @param {number} centerX - Zoom center X (canvas coords)
   * @param {number} centerY - Zoom center Y (canvas coords)
   */
  setZoom(zoom, centerX = null, centerY = null) {
    const oldZoom = this.zoom;
    this.zoom = Math.max(0.25, Math.min(4, zoom));

    // Adjust offset to zoom around center point
    if (centerX !== null && centerY !== null) {
      const scale = this.zoom / oldZoom;
      this.offsetX = centerX - (centerX - this.offsetX) * scale;
      this.offsetY = centerY - (centerY - this.offsetY) * scale;
    }

    this.render();
    return this.zoom;
  }

  /**
   * Pan the view
   * @param {number} dx - Delta X
   * @param {number} dy - Delta Y
   */
  pan(dx, dy) {
    this.offsetX += dx;
    this.offsetY += dy;
    this.render();
  }

  /**
   * Get current zoom level
   * @returns {number}
   */
  getZoom() {
    return this.zoom;
  }

  /**
   * Set stage image to display
   * @param {string} dataUrl - Base64 data URL of the image
   */
  setStageImage(dataUrl) {
    const img = new Image();
    img.onload = () => {
      this.stageImage = img;
      this.render();
    };
    img.src = dataUrl;
  }

  /**
   * Clear stage image and return to pattern view
   */
  clearStageImage() {
    this.stageImage = null;
    this.render();
  }

  /**
   * Render stage image scaled and centered on canvas
   */
  renderStageImage() {
    const ctx = this.ctx;
    const img = this.stageImage;

    // Clear canvas
    ctx.fillStyle = '#1a1a2e';
    ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

    // Calculate scaling to fit image in canvas while maintaining aspect ratio
    // Scale up to fill canvas (same as pattern grid display)
    const scaleX = this.canvas.width / img.width;
    const scaleY = this.canvas.height / img.height;
    const scale = Math.min(scaleX, scaleY) * this.zoom;

    const drawWidth = img.width * scale;
    const drawHeight = img.height * scale;
    const drawX = (this.canvas.width - drawWidth) / 2 + this.offsetX;
    const drawY = (this.canvas.height - drawHeight) / 2 + this.offsetY;

    // Draw image with pixelated rendering
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(img, drawX, drawY, drawWidth, drawHeight);
  }
}
