/**
 * Editing tools. The canvas turns pointer events into `ToolEvent`s and hands them, with a
 * `ToolContext` (a snapshot of the editor store taken at that moment), to the active tool.
 * Tools read the snapshot before writing through its actions and push one `HistoryPatch` per
 * stroke at pointer-up. They never draw: transient feedback goes through `setOverlay`.
 */

import type { Pattern, Segment } from '@/api/types';
import type { Cell } from '@/model/grid';
import type { EditorState } from '@/store/editorStore';

export interface ToolEvent {
  /** Cell under the pointer, null when off the grid. */
  cell: Cell | null;
  /** Nearest unit edge (normalised) when the pointer is close to one, else null. */
  edge: Segment | null;
  /** Pointer position in fractional cell coordinates, unclamped (may lie outside the grid). */
  world: { x: number; y: number } | null;
  native: PointerEvent;
}

export type ToolContext = Pick<
  EditorState,
  | 'selectedColour'
  | 'selection'
  | 'tool'
  | 'previousTool'
  | 'setCells'
  | 'setBackstitch'
  | 'pushPatch'
  | 'setSelection'
  | 'setSelectedColour'
  | 'setTool'
  | 'setOverlay'
> & { pattern: Pattern };

export interface CanvasTool {
  onDown(ev: ToolEvent, ctx: ToolContext): void;
  onMove(ev: ToolEvent, ctx: ToolContext): void;
  onUp(ev: ToolEvent, ctx: ToolContext): void;
}

/** Index cells are cleared to: the Background, or 0 when the pattern has none. */
export const fillIndex = (pattern: Pattern) => pattern.background_index ?? 0;
