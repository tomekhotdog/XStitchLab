/** Fill: 4-connected flood fill of the region under the pointer with the selected colour. */

import { floodFill } from '@/model/grid';
import type { CanvasTool, ToolContext, ToolEvent } from './types';

export const fill: CanvasTool = {
  onDown(ev: ToolEvent, ctx: ToolContext) {
    if (!ev.cell) return;
    const changes = floodFill(ctx.pattern.grid, ev.cell.x, ev.cell.y, ctx.selectedColour);
    if (changes.length === 0) return;
    ctx.setCells(changes);
    ctx.pushPatch({ cells: changes, backstitchAdd: [], backstitchRemove: [] });
  },
  onMove() {},
  onUp() {},
};
