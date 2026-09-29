/** Paint: press paints one cell, drag paints the pointer's path (gaps bridged by Bresenham lines). */

import type { Cell, Change } from '@/model/grid';
import type { CanvasTool, ToolContext, ToolEvent } from './types';

interface Stroke {
  changes: Change[];
  last: Cell | null;
}

let stroke: Stroke | null = null;

/** Cells on the line from `a` (exclusive) to `b` (inclusive). */
export function lineCells(a: Cell, b: Cell): Cell[] {
  const out: Cell[] = [];
  const dx = Math.abs(b.x - a.x);
  const dy = -Math.abs(b.y - a.y);
  const sx = a.x < b.x ? 1 : -1;
  const sy = a.y < b.y ? 1 : -1;
  let err = dx + dy;
  let { x, y } = a;
  while (x !== b.x || y !== b.y) {
    const e2 = 2 * err;
    if (e2 >= dy) {
      err += dy;
      x += sx;
    }
    if (e2 <= dx) {
      err += dx;
      y += sy;
    }
    out.push({ x, y });
  }
  return out;
}

function paintCells(cells: Cell[], ctx: ToolContext): void {
  const { grid } = ctx.pattern;
  const to = ctx.selectedColour;
  const changes: Change[] = [];
  for (const c of cells) {
    const from = grid[c.y]?.[c.x];
    if (from === undefined || from === to) continue;
    changes.push({ x: c.x, y: c.y, from, to });
  }
  if (changes.length === 0) return;
  ctx.setCells(changes);
  stroke!.changes.push(...changes);
}

export const paint: CanvasTool = {
  onDown(ev: ToolEvent, ctx: ToolContext) {
    stroke = { changes: [], last: ev.cell };
    if (ev.cell) paintCells([ev.cell], ctx);
  },
  onMove(ev: ToolEvent, ctx: ToolContext) {
    if (!stroke) return;
    const cell = ev.cell;
    if (!cell) {
      stroke.last = null;
      return;
    }
    const last = stroke.last;
    paintCells(last && (last.x !== cell.x || last.y !== cell.y) ? lineCells(last, cell) : [cell], ctx);
    stroke.last = cell;
  },
  onUp(_ev: ToolEvent, ctx: ToolContext) {
    if (!stroke) return;
    if (stroke.changes.length) ctx.pushPatch({ cells: stroke.changes, backstitchAdd: [], backstitchRemove: [] });
    stroke = null;
  },
};
