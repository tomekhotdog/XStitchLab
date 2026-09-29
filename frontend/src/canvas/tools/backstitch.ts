/**
 * Backstitch: press toggles the unit edge under the pointer; dragging adds unit edges along the
 * path (never removes). The pattern may hold merged multi-unit segments, so removing one unit
 * replaces its parent segment with the parent's other units.
 */

import type { Segment } from '@/api/types';
import { segKey, splitToUnits } from '@/model/segments';
import type { CanvasTool, ToolContext, ToolEvent } from './types';

interface Stroke {
  add: Segment[];
  remove: Segment[];
  /** Keys of units already added in this stroke, so a wobbling drag records each once. */
  keys: Set<string>;
}

let stroke: Stroke | null = null;

/** Unit key -> the pattern segment that contains it. Odd segments (not axis/45°) count as one unit. */
function unitParents(segments: Segment[]): Map<string, Segment> {
  const parents = new Map<string, Segment>();
  for (const s of segments) for (const u of unitsOf(s)) parents.set(segKey(u), s);
  return parents;
}

function unitsOf(s: Segment): Segment[] {
  try {
    return splitToUnits([s]);
  } catch {
    return [s];
  }
}

function toggle(edge: Segment, ctx: ToolContext): void {
  const parents = unitParents(ctx.pattern.backstitch);
  const key = segKey(edge);
  const parent = parents.get(key);
  if (!parent) {
    add(edge, ctx, parents);
    return;
  }
  const rest = unitsOf(parent).filter((u) => segKey(u) !== key);
  ctx.setBackstitch(rest, [parent]);
  stroke!.remove.push(parent);
  stroke!.add.push(...rest);
}

function add(edge: Segment, ctx: ToolContext, parents = unitParents(ctx.pattern.backstitch)): void {
  const key = segKey(edge);
  if (parents.has(key) || stroke!.keys.has(key)) return;
  ctx.setBackstitch([edge], []);
  stroke!.add.push(edge);
  stroke!.keys.add(key);
}

export const backstitch: CanvasTool = {
  onDown(ev: ToolEvent, ctx: ToolContext) {
    stroke = { add: [], remove: [], keys: new Set() };
    if (ev.edge) toggle(ev.edge, ctx);
  },
  onMove(ev: ToolEvent, ctx: ToolContext) {
    if (!stroke || !ev.edge) return;
    add(ev.edge, ctx);
  },
  onUp(_ev: ToolEvent, ctx: ToolContext) {
    if (!stroke) return;
    if (stroke.add.length || stroke.remove.length) {
      ctx.pushPatch({ cells: [], backstitchAdd: stroke.add, backstitchRemove: stroke.remove });
    }
    stroke = null;
  },
};
