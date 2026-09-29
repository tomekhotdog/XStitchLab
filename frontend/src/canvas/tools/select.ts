/**
 * Select: drag a marquee; drag inside the selection to move it (live overlay preview, committed
 * on up). `deleteSelection` and `nudgeSelection` are the keyboard actions on a selection.
 */

import type { Pattern } from '@/api/types';
import { moveRect, rectCells, type Cell, type Change, type Rect } from '@/model/grid';
import { fillIndex, type CanvasTool, type ToolContext, type ToolEvent } from './types';

type Drag =
  | { kind: 'marquee'; start: Cell; end: Cell; moved: boolean }
  | { kind: 'move'; origin: Cell; rect: Rect; dx: number; dy: number };

let drag: Drag | null = null;

const inRect = (r: Rect, c: Cell) => c.x >= r.x && c.x < r.x + r.w && c.y >= r.y && c.y < r.y + r.h;

const clampCell = (p: Pattern, x: number, y: number): Cell => ({
  x: Math.min(p.metadata.width - 1, Math.max(0, Math.floor(x))),
  y: Math.min(p.metadata.height - 1, Math.max(0, Math.floor(y))),
});

const rectFrom = (a: Cell, b: Cell): Rect => ({
  x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.abs(a.x - b.x) + 1, h: Math.abs(a.y - b.y) + 1,
});

/** `rect` intersected with the grid, or null when nothing remains. */
export function clipRect(rect: Rect, p: Pattern): Rect | null {
  const x1 = Math.max(0, rect.x);
  const y1 = Math.max(0, rect.y);
  const x2 = Math.min(p.metadata.width, rect.x + rect.w);
  const y2 = Math.min(p.metadata.height, rect.y + rect.h);
  return x2 > x1 && y2 > y1 ? { x: x1, y: y1, w: x2 - x1, h: y2 - y1 } : null;
}

function commitMove(ctx: ToolContext, rect: Rect, dx: number, dy: number): void {
  if (dx === 0 && dy === 0) return;
  const changes = moveRect(ctx.pattern.grid, rect, dx, dy, fillIndex(ctx.pattern));
  if (changes.length) {
    ctx.setCells(changes);
    ctx.pushPatch({ cells: changes, backstitchAdd: [], backstitchRemove: [] });
  }
  ctx.setSelection(clipRect({ ...rect, x: rect.x + dx, y: rect.y + dy }, ctx.pattern));
}

export const select: CanvasTool = {
  onDown(ev: ToolEvent, ctx: ToolContext) {
    const sel = ctx.selection;
    if (ev.cell && sel && inRect(sel, ev.cell)) {
      drag = { kind: 'move', origin: ev.cell, rect: sel, dx: 0, dy: 0 };
      return;
    }
    if (!ev.world) return;
    const start = clampCell(ctx.pattern, ev.world.x, ev.world.y);
    drag = { kind: 'marquee', start, end: start, moved: false };
  },
  onMove(ev: ToolEvent, ctx: ToolContext) {
    if (!drag || !ev.world) return;
    const p = ctx.pattern;
    if (drag.kind === 'marquee') {
      const end = clampCell(p, ev.world.x, ev.world.y);
      if (end.x === drag.end.x && end.y === drag.end.y) return;
      drag.end = end;
      drag.moved = true;
      ctx.setOverlay({ marquee: rectFrom(drag.start, end) });
      return;
    }
    const dx = Math.floor(ev.world.x) - drag.origin.x;
    const dy = Math.floor(ev.world.y) - drag.origin.y;
    if (dx === drag.dx && dy === drag.dy) return;
    drag.dx = dx;
    drag.dy = dy;
    ctx.setOverlay(dx || dy ? { move: { rect: drag.rect, dx, dy } } : null);
  },
  onUp(_ev: ToolEvent, ctx: ToolContext) {
    if (!drag) return;
    const d = drag;
    drag = null;
    ctx.setOverlay(null);
    if (d.kind === 'marquee') ctx.setSelection(d.moved ? rectFrom(d.start, d.end) : null);
    else commitMove(ctx, d.rect, d.dx, d.dy);
  },
};

/** Clear the selected cells to the Background (0 without one); the selection stays. */
export function deleteSelection(ctx: ToolContext): void {
  const sel = ctx.selection;
  if (!sel) return;
  const { grid } = ctx.pattern;
  const to = fillIndex(ctx.pattern);
  const changes: Change[] = [];
  for (const c of rectCells(sel)) {
    const from = grid[c.y]?.[c.x];
    if (from === undefined || from === to) continue;
    changes.push({ x: c.x, y: c.y, from, to });
  }
  if (changes.length === 0) return;
  ctx.setCells(changes);
  ctx.pushPatch({ cells: changes, backstitchAdd: [], backstitchRemove: [] });
}

/** Move the selection (cells and rect) by one step. */
export function nudgeSelection(ctx: ToolContext, dx: number, dy: number): void {
  if (ctx.selection) commitMove(ctx, ctx.selection, dx, dy);
}
