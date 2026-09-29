/**
 * Rasterises a Pattern into four layers (cells, grid lines, backstitch, overlay) at the current
 * zoom and composes them onto a target context. Cells are redrawn per dirty cell or per changed
 * grid row (the store's copy-on-write rows make that cheap); a zoom change re-rasterises all layers.
 */

import type { Pattern, Segment } from '@/api/types';
import type { Cell } from '@/model/grid';

export type ViewMode = 'colour' | 'symbol';

export interface View {
  zoom: number;
  panX: number;
  panY: number;
  /** Base cell size in CSS px at zoom 1. */
  cellPx: number;
}

/** Task 11 draws selection marquees and hover highlights through this hook (device px, cell scale). */
export type OverlayPainter = (ctx: CanvasRenderingContext2D, scale: number, pattern: Pattern) => void;

export const FABRIC = '#f6f1e7';
export const SYMBOL_MIN_CSS_PX = 14;
const MAX_LAYER_PX = 8192;
const INK = '#1f1b16';

type Layer = HTMLCanvasElement | OffscreenCanvas;
type Ctx2D = CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D;

function makeLayer(): Layer {
  if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(1, 1);
  return document.createElement('canvas');
}

export class LayeredRenderer {
  private pattern: Pattern | null = null;
  private mode: ViewMode = 'colour';
  private preview: HTMLImageElement | null = null;
  private overlayPainter: OverlayPainter | null = null;
  /** Device px per cell at the last rasterisation; 0 = nothing rasterised yet. */
  private scale = 0;
  private dpr = 1;
  private dirtyCells: Cell[] = [];
  private dirtyRows = new Set<number>();
  private needs = { cells: true, grid: true, backstitch: true, overlay: true };
  private readonly layers = {
    cells: makeLayer(),
    grid: makeLayer(),
    backstitch: makeLayer(),
    overlay: makeLayer(),
  };

  setPattern(pattern: Pattern | null): void {
    const prev = this.pattern;
    this.pattern = pattern;
    if (!pattern || !prev) {
      this.needs = { cells: true, grid: true, backstitch: true, overlay: true };
      return;
    }
    const sameShape =
      prev.metadata.width === pattern.metadata.width && prev.metadata.height === pattern.metadata.height;
    if (!sameShape || prev.legend !== pattern.legend || prev.background_index !== pattern.background_index) {
      this.needs.cells = true;
      this.needs.grid = this.needs.grid || !sameShape;
    } else if (prev.grid !== pattern.grid) {
      pattern.grid.forEach((row, y) => {
        if (row !== prev.grid[y]) this.dirtyRows.add(y);
      });
    }
    if (prev.backstitch !== pattern.backstitch) this.needs.backstitch = true;
    this.needs.overlay = true;
  }

  setViewMode(mode: ViewMode): void {
    if (mode === this.mode) return;
    this.mode = mode;
    this.needs.cells = true;
  }

  /** A Step preview drawn in place of the cells (and backstitch) layer; null returns to the pattern. */
  setPreview(image: HTMLImageElement | null): void {
    this.preview = image;
  }

  setOverlay(painter: OverlayPainter | null): void {
    this.overlayPainter = painter;
    this.needs.overlay = true;
  }

  /** Repaint just these cells on the next draw. */
  markDirty(cells: Cell[]): void {
    this.dirtyCells.push(...cells);
  }

  redrawAll(): void {
    this.needs = { cells: true, grid: true, backstitch: true, overlay: true };
  }

  /** Grid width/height in CSS px for `view`, or null without a pattern. */
  size(view: View): { w: number; h: number } | null {
    if (!this.pattern) return null;
    const px = view.cellPx * view.zoom;
    return { w: this.pattern.metadata.width * px, h: this.pattern.metadata.height * px };
  }

  draw(ctx: CanvasRenderingContext2D, view: View): void {
    const pattern = this.pattern;
    if (!pattern) return;
    const { width: W, height: H } = pattern.metadata;
    const dpr = (typeof window !== 'undefined' && window.devicePixelRatio) || 1;
    const wanted = Math.min(view.cellPx * view.zoom * dpr, MAX_LAYER_PX / Math.max(W, H));
    if (wanted !== this.scale || dpr !== this.dpr) {
      this.scale = wanted;
      this.dpr = dpr;
      this.redrawAll();
    }
    this.flush();
    const w = W * view.cellPx * view.zoom;
    const h = H * view.cellPx * view.zoom;
    ctx.save();
    ctx.imageSmoothingEnabled = false;
    if (this.preview) {
      const img = this.preview;
      ctx.imageSmoothingEnabled = img.naturalWidth > w;
      ctx.drawImage(img, view.panX, view.panY, w, h);
      ctx.imageSmoothingEnabled = false;
    } else {
      ctx.drawImage(this.layers.cells, view.panX, view.panY, w, h);
    }
    ctx.drawImage(this.layers.grid, view.panX, view.panY, w, h);
    if (!this.preview) ctx.drawImage(this.layers.backstitch, view.panX, view.panY, w, h);
    ctx.drawImage(this.layers.overlay, view.panX, view.panY, w, h);
    ctx.restore();
  }

  // --- rasterisation ---------------------------------------------------------

  private flush(): void {
    const pattern = this.pattern!;
    const { width: W, height: H } = pattern.metadata;
    const s = this.scale;
    const pw = Math.max(1, Math.ceil(W * s));
    const ph = Math.max(1, Math.ceil(H * s));
    for (const layer of Object.values(this.layers)) {
      if (layer.width !== pw || layer.height !== ph) {
        layer.width = pw;
        layer.height = ph;
        this.redrawAll();
      }
    }
    if (this.needs.cells) {
      const ctx = this.ctx('cells');
      ctx.clearRect(0, 0, pw, ph);
      this.prepareCellCtx(ctx);
      for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) this.paintCell(ctx, x, y);
      this.dirtyRows.clear();
      this.dirtyCells = [];
    } else if (this.dirtyRows.size || this.dirtyCells.length) {
      const ctx = this.ctx('cells');
      this.prepareCellCtx(ctx);
      for (const y of this.dirtyRows) for (let x = 0; x < W; x++) this.paintCell(ctx, x, y);
      for (const c of this.dirtyCells) if (!this.dirtyRows.has(c.y)) this.paintCell(ctx, c.x, c.y);
      this.dirtyRows.clear();
      this.dirtyCells = [];
    }
    if (this.needs.grid) this.paintGrid(this.ctx('grid'), W, H);
    if (this.needs.backstitch) this.paintBackstitch(this.ctx('backstitch'), pattern.backstitch);
    if (this.needs.overlay) {
      const ctx = this.ctx('overlay');
      ctx.clearRect(0, 0, pw, ph);
      if (this.overlayPainter) this.overlayPainter(ctx as CanvasRenderingContext2D, s, pattern);
    }
    this.needs = { cells: false, grid: false, backstitch: false, overlay: false };
  }

  private ctx(name: keyof typeof this.layers): Ctx2D {
    const ctx = this.layers[name].getContext('2d') as Ctx2D | null;
    if (!ctx) throw new Error('2d context unavailable');
    return ctx;
  }

  private prepareCellCtx(ctx: Ctx2D): void {
    const s = this.scale;
    ctx.font = `${Math.max(1, Math.floor(s * 0.62))}px system-ui, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
  }

  private paintCell(ctx: Ctx2D, x: number, y: number): void {
    const pattern = this.pattern!;
    const s = this.scale;
    const idx = pattern.grid[y]?.[x];
    const entry = idx === undefined ? undefined : pattern.legend[idx];
    const px = Math.floor(x * s);
    const py = Math.floor(y * s);
    const pw = Math.ceil((x + 1) * s) - px;
    const ph = Math.ceil((y + 1) * s) - py;
    ctx.clearRect(px, py, pw, ph);
    if (!entry) {
      ctx.fillStyle = '#ff00ff';
      ctx.fillRect(px, py, pw, ph);
      return;
    }
    const isBackground = idx === pattern.background_index;
    if (isBackground) {
      ctx.fillStyle = FABRIC;
      ctx.fillRect(px, py, pw, ph);
      if (s >= 6) {
        ctx.fillStyle = 'rgba(0,0,0,0.18)';
        ctx.beginPath();
        ctx.arc(px + pw / 2, py + ph / 2, Math.max(0.5, s * 0.07), 0, Math.PI * 2);
        ctx.fill();
      }
      return;
    }
    const [r, g, b] = entry.rgb;
    if (this.mode === 'colour') {
      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.fillRect(px, py, pw, ph);
      return;
    }
    // symbol view: a pale tint of the colour with the glyph on top when it is legible
    ctx.fillStyle = `rgb(${tint(r)},${tint(g)},${tint(b)})`;
    ctx.fillRect(px, py, pw, ph);
    if (s / this.dpr >= SYMBOL_MIN_CSS_PX) {
      ctx.fillStyle = INK;
      ctx.fillText(entry.symbol, px + pw / 2, py + ph / 2 + s * 0.04);
    }
  }

  private paintGrid(ctx: Ctx2D, W: number, H: number): void {
    const s = this.scale;
    const pw = ctx.canvas.width;
    const ph = ctx.canvas.height;
    ctx.clearRect(0, 0, pw, ph);
    const minor = s >= 4;
    for (let x = 0; x <= W; x++) {
      const major = x % 10 === 0;
      if (!major && !minor) continue;
      line(ctx, Math.round(x * s), 0, Math.round(x * s), ph, major ? 1.6 : 1, major ? 0.5 : 0.14, x === 0 || x === W);
    }
    for (let y = 0; y <= H; y++) {
      const major = y % 10 === 0;
      if (!major && !minor) continue;
      line(ctx, 0, Math.round(y * s), pw, Math.round(y * s), major ? 1.6 : 1, major ? 0.5 : 0.14, y === 0 || y === H);
    }
  }

  private paintBackstitch(ctx: Ctx2D, segments: Segment[]): void {
    const s = this.scale;
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
    ctx.strokeStyle = '#000';
    ctx.lineWidth = Math.max(2, s * 0.12);
    ctx.lineCap = 'round';
    ctx.beginPath();
    for (const seg of segments) {
      ctx.moveTo(seg.start[0] * s, seg.start[1] * s);
      ctx.lineTo(seg.end[0] * s, seg.end[1] * s);
    }
    ctx.stroke();
  }
}

const tint = (v: number) => Math.round(255 - (255 - v) * 0.28);

function line(ctx: Ctx2D, x1: number, y1: number, x2: number, y2: number, width: number, alpha: number, edge: boolean) {
  ctx.strokeStyle = `rgba(0,0,0,${alpha})`;
  ctx.lineWidth = width;
  ctx.beginPath();
  // keep the outermost lines inside the layer so the border is visible
  const ox = x1 === x2 ? (x1 === 0 ? width / 2 : edge ? -width / 2 : 0.5) : 0;
  const oy = y1 === y2 ? (y1 === 0 ? width / 2 : edge ? -width / 2 : 0.5) : 0;
  ctx.moveTo(x1 + ox, y1 + oy);
  ctx.lineTo(x2 + ox, y2 + oy);
  ctx.stroke();
}
