/**
 * One <canvas> that fills its container and shows the store's Pattern through a LayeredRenderer.
 * Handles zoom (wheel, about the cursor), pan (space+drag or middle drag), F to fit, and forwards
 * pointer events to a pluggable `CanvasTool` (Task 11). Exposes coordinate helpers through a ref.
 */

import {
  forwardRef, useCallback, useEffect, useImperativeHandle, useLayoutEffect, useRef, useState,
} from 'react';
import { pngSrc } from '@/api/client';
import type { Segment } from '@/api/types';
import type { Cell } from '@/model/grid';
import { normalise } from '@/model/segments';
import { useEditorStore } from '@/store/editorStore';
import { LayeredRenderer, type View, type ViewMode } from './LayeredRenderer';

export const CELL_PX = 16;
export const MIN_ZOOM = 0.25;
export const MAX_ZOOM = 8;
const FIT_MARGIN = 24;
const EDGE_SNAP = 0.3;

export interface ToolEvent {
  cell: Cell | null;
  edge: Segment | null;
  native: PointerEvent;
}

/** Editing tools implement this; the default is a no-op. */
export interface CanvasTool {
  onDown?(ev: ToolEvent): void;
  onMove?(ev: ToolEvent): void;
  onUp?(ev: ToolEvent): void;
}

export interface PatternCanvasHandle {
  toCell(clientX: number, clientY: number): Cell | null;
  toEdge(clientX: number, clientY: number): Segment | null;
  fit(): void;
  setZoom(zoom: number): void;
  getView(): View;
  renderer: LayeredRenderer;
}

interface Props {
  viewMode: ViewMode;
  tool?: CanvasTool;
  onViewChange?(view: View): void;
}

const clampZoom = (z: number) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z));

const isTyping = (target: EventTarget | null) =>
  target instanceof HTMLElement && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable);

export const PatternCanvas = forwardRef<PatternCanvasHandle, Props>(function PatternCanvas(
  { viewMode, tool, onViewChange }, ref,
) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rendererRef = useRef<LayeredRenderer | null>(null);
  if (!rendererRef.current) rendererRef.current = new LayeredRenderer();
  const renderer = rendererRef.current;
  const viewRef = useRef<View>({ zoom: 1, panX: 0, panY: 0, cellPx: CELL_PX });
  const drawQueued = useRef(false);
  const spaceRef = useRef(false);
  const dragRef = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const toolRef = useRef(tool);
  toolRef.current = tool;
  const onViewChangeRef = useRef(onViewChange);
  onViewChangeRef.current = onViewChange;
  const [panning, setPanning] = useState(false);

  const pattern = useEditorStore((s) => s.pattern);
  const previewStep = useEditorStore((s) => s.previewStep);
  const steps = useEditorStore((s) => s.steps);

  /** Coalesce draws within one task; the canvas is repainted synchronously after it. */
  const schedule = useCallback(() => {
    if (drawQueued.current) return;
    drawQueued.current = true;
    queueMicrotask(() => {
      drawQueued.current = false;
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext('2d');
      if (!canvas || !ctx) return;
      const dpr = window.devicePixelRatio || 1;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, canvas.width / dpr, canvas.height / dpr);
      renderer.draw(ctx, viewRef.current);
    });
  }, [renderer]);

  const setView = useCallback((next: Partial<View>) => {
    viewRef.current = { ...viewRef.current, ...next };
    onViewChangeRef.current?.(viewRef.current);
    schedule();
  }, [schedule]);

  const fit = useCallback(() => {
    const wrap = wrapRef.current;
    const size = renderer.size({ ...viewRef.current, zoom: 1 });
    if (!wrap || !size) return;
    const cw = wrap.clientWidth;
    const ch = wrap.clientHeight;
    const zoom = clampZoom(Math.min((cw - 2 * FIT_MARGIN) / size.w, (ch - 2 * FIT_MARGIN) / size.h));
    setView({ zoom, panX: (cw - size.w * zoom) / 2, panY: (ch - size.h * zoom) / 2 });
  }, [renderer, setView]);

  const zoomAt = useCallback((zoom: number, cx: number, cy: number) => {
    const v = viewRef.current;
    const next = clampZoom(zoom);
    const wx = (cx - v.panX) / (v.cellPx * v.zoom);
    const wy = (cy - v.panY) / (v.cellPx * v.zoom);
    setView({ zoom: next, panX: cx - wx * v.cellPx * next, panY: cy - wy * v.cellPx * next });
  }, [setView]);

  const toWorld = useCallback((clientX: number, clientY: number) => {
    const rect = canvasRef.current?.getBoundingClientRect();
    if (!rect) return null;
    const v = viewRef.current;
    const px = v.cellPx * v.zoom;
    return { x: (clientX - rect.left - v.panX) / px, y: (clientY - rect.top - v.panY) / px };
  }, []);

  const toCell = useCallback((clientX: number, clientY: number): Cell | null => {
    const p = pattern;
    const w = toWorld(clientX, clientY);
    if (!p || !w) return null;
    const x = Math.floor(w.x);
    const y = Math.floor(w.y);
    return x >= 0 && y >= 0 && x < p.metadata.width && y < p.metadata.height ? { x, y } : null;
  }, [pattern, toWorld]);

  const toEdge = useCallback((clientX: number, clientY: number): Segment | null => {
    const p = pattern;
    const w = toWorld(clientX, clientY);
    if (!p || !w) return null;
    const { width: W, height: H } = p.metadata;
    const candidates: { d: number; seg: Segment }[] = [];
    const hy = Math.round(w.y);
    const hx = Math.floor(w.x);
    if (hy >= 0 && hy <= H && hx >= 0 && hx < W) {
      candidates.push({ d: Math.abs(w.y - hy), seg: { start: [hx, hy], end: [hx + 1, hy] } });
    }
    const vx = Math.round(w.x);
    const vy = Math.floor(w.y);
    if (vx >= 0 && vx <= W && vy >= 0 && vy < H) {
      candidates.push({ d: Math.abs(w.x - vx), seg: { start: [vx, vy], end: [vx, vy + 1] } });
    }
    const best = candidates.filter((c) => c.d <= EDGE_SNAP).sort((a, b) => a.d - b.d)[0];
    return best ? normalise(best.seg) : null;
  }, [pattern, toWorld]);

  useImperativeHandle(ref, () => ({
    toCell,
    toEdge,
    fit,
    setZoom: (zoom) => {
      const wrap = wrapRef.current;
      zoomAt(zoom, (wrap?.clientWidth ?? 0) / 2, (wrap?.clientHeight ?? 0) / 2);
    },
    getView: () => viewRef.current,
    renderer,
  }), [toCell, toEdge, fit, zoomAt, renderer]);

  // pattern → renderer (fit when the grid shape changes)
  const shapeRef = useRef<string>('');
  useLayoutEffect(() => {
    renderer.setPattern(pattern);
    const shape = pattern ? `${pattern.metadata.width}x${pattern.metadata.height}` : '';
    if (shape !== shapeRef.current) {
      shapeRef.current = shape;
      fit();
    }
    schedule();
  }, [pattern, renderer, fit, schedule]);

  useEffect(() => {
    renderer.setViewMode(viewMode);
    schedule();
  }, [viewMode, renderer, schedule]);

  // step preview image
  useEffect(() => {
    const step = previewStep === null ? undefined : steps[previewStep];
    if (!step) {
      renderer.setPreview(null);
      schedule();
      return;
    }
    const img = new Image();
    let alive = true;
    img.onload = () => {
      if (!alive) return;
      renderer.setPreview(img);
      schedule();
    };
    img.src = pngSrc(step.preview_png);
    return () => {
      alive = false;
    };
  }, [previewStep, steps, renderer, schedule]);

  // size the canvas to its container
  useLayoutEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return;
    let first = true;
    const resize = () => {
      const dpr = window.devicePixelRatio || 1;
      const cw = wrap.clientWidth;
      const ch = wrap.clientHeight;
      const w = Math.max(1, Math.round(cw * dpr));
      const h = Math.max(1, Math.round(ch * dpr));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w; // resizing clears the bitmap, so only do it on a real change
        canvas.height = h;
        canvas.style.width = `${cw}px`;
        canvas.style.height = `${ch}px`;
      }
      if (first) {
        first = false;
        fit();
      }
      schedule();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(wrap);
    return () => ro.disconnect();
  }, [fit, schedule]);

  // keyboard: space (pan), F (fit)
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (isTyping(e.target)) return;
      if (e.code === 'Space') {
        spaceRef.current = true;
        setPanning(true);
        e.preventDefault();
      } else if ((e.key === 'f' || e.key === 'F') && !e.metaKey && !e.ctrlKey && !e.altKey) {
        fit();
        e.preventDefault();
      }
    };
    const up = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        spaceRef.current = false;
        setPanning(false);
      }
    };
    window.addEventListener('keydown', down);
    window.addEventListener('keyup', up);
    return () => {
      window.removeEventListener('keydown', down);
      window.removeEventListener('keyup', up);
    };
  }, [fit]);

  // wheel zoom needs a non-passive listener
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const factor = Math.exp(-e.deltaY * 0.0015);
      zoomAt(viewRef.current.zoom * factor, e.clientX - rect.left, e.clientY - rect.top);
    };
    canvas.addEventListener('wheel', onWheel, { passive: false });
    return () => canvas.removeEventListener('wheel', onWheel);
  }, [zoomAt]);

  const toolEvent = (e: React.PointerEvent): ToolEvent => ({
    cell: toCell(e.clientX, e.clientY),
    edge: toEdge(e.clientX, e.clientY),
    native: e.nativeEvent,
  });

  const onPointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (e.button === 1 || (e.button === 0 && spaceRef.current)) {
      const v = viewRef.current;
      dragRef.current = { x: e.clientX, y: e.clientY, panX: v.panX, panY: v.panY };
      e.currentTarget.setPointerCapture(e.pointerId);
      e.preventDefault();
      return;
    }
    if (e.button === 0) {
      e.currentTarget.setPointerCapture(e.pointerId);
      toolRef.current?.onDown?.(toolEvent(e));
    }
  };

  const onPointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const drag = dragRef.current;
    if (drag) {
      setView({ panX: drag.panX + (e.clientX - drag.x), panY: drag.panY + (e.clientY - drag.y) });
      return;
    }
    toolRef.current?.onMove?.(toolEvent(e));
  };

  const onPointerUp = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (dragRef.current) {
      dragRef.current = null;
      return;
    }
    toolRef.current?.onUp?.(toolEvent(e));
  };

  return (
    <div ref={wrapRef} className="pattern-canvas-wrap" data-panning={panning || undefined}>
      <canvas
        ref={canvasRef}
        className="pattern-canvas"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onContextMenu={(e) => e.preventDefault()}
      />
    </div>
  );
});
