/** Eyedropper: picks the colour under the pointer and returns to the previous tool. */

import type { CanvasTool, ToolContext, ToolEvent } from './types';

export const eyedropper: CanvasTool = {
  onDown(ev: ToolEvent, ctx: ToolContext) {
    if (!ev.cell) return;
    const index = ctx.pattern.grid[ev.cell.y]?.[ev.cell.x];
    if (index === undefined) return;
    ctx.setSelectedColour(index);
    ctx.setTool(ctx.previousTool === 'eyedropper' ? 'paint' : ctx.previousTool);
  },
  onMove() {},
  onUp() {},
};
