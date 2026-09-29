/** Fixtures for tool tests: a store-backed ToolContext and ToolEvents in cell coordinates. */

import type { Pattern, Segment } from '@/api/types';
import type { ToolContext, ToolEvent } from '@/canvas/tools/types';
import { useEditorStore } from '@/store/editorStore';

/** A w×h pattern with `colours` legend entries; every cell starts as `initial`. */
export function makePattern(w: number, h: number, colours = 3, initial = 0, background: number | null = null): Pattern {
  const legend = Array.from({ length: colours }, (_, i) => ({
    symbol: String(i), dmc_code: `C${i}`, dmc_name: `Colour ${i}`, rgb: [i * 40, i * 40, i * 40] as [number, number, number],
    stitch_count: i === initial ? w * h : 0,
  }));
  return {
    metadata: {
      title: 't', width: w, height: h, color_count: colours, total_stitches: w * h, difficulty: 'easy',
      fabric_count: 14, fabric_width_inches: 1, fabric_height_inches: 1, source_image: null,
    },
    legend,
    grid: Array.from({ length: h }, () => new Array<number>(w).fill(initial)),
    backstitch: [],
    background_index: background,
    recipe: [],
  };
}

/** Load `pattern` into the (reset) store; the context is always read fresh via `ctx()`. */
export function loadPattern(pattern: Pattern): void {
  useEditorStore.getState().reset();
  useEditorStore.getState().setPattern(pattern);
}

/** The live store snapshot as a ToolContext (the canvas does exactly this). */
export const ctx = (): ToolContext => useEditorStore.getState() as ToolContext;

/** jsdom has no PointerEvent; tools never read `native`, so a MouseEvent stands in. */
const nativeEvent = () => new MouseEvent('pointerdown', { button: 0 }) as PointerEvent;

/** An event at cell (x, y); coordinates outside the grid give `cell: null` but keep `world`. */
export function at(x: number, y: number, edge: Segment | null = null): ToolEvent {
  const p = useEditorStore.getState().pattern;
  const inside = !!p && x >= 0 && y >= 0 && x < p.metadata.width && y < p.metadata.height;
  return { cell: inside ? { x, y } : null, edge, world: { x: x + 0.5, y: y + 0.5 }, native: nativeEvent() };
}

/** An event snapped to a unit edge, with `cell` set to the cell below/right of it. */
export const onEdge = (edge: Segment): ToolEvent => ({
  cell: { x: edge.start[0], y: edge.start[1] }, edge, world: { x: edge.start[0], y: edge.start[1] }, native: nativeEvent(),
});

export const grid = () => useEditorStore.getState().pattern!.grid;
