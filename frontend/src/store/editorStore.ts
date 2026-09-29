/**
 * Editor state (zustand). Pure setters mutate the Pattern immutably; `undo`/`redo` replay patches
 * through those same setters so every subscriber (canvas, palette, threads) sees the change.
 * Only `load` talks to the API.
 */

import { create } from 'zustand';
import { ApiError, getDesign } from '@/api/client';
import type { DesignDetail, OpCall, Pattern, Segment, Step } from '@/api/types';
import { applyChanges, invertChanges, type Change, type Rect } from '@/model/grid';
import { dedupe, segKey } from '@/model/segments';

export type Tool = 'paint' | 'fill' | 'select' | 'eyedropper' | 'backstitch';

export interface Patch {
  cells: Change[];
  backstitchAdd: Segment[];
  backstitchRemove: Segment[];
}

export interface Status {
  kind: 'idle' | 'loading' | 'error';
  message?: string;
}

export const HISTORY_CAP = 200;

export interface EditorState {
  slug: string | null;
  design: DesignDetail | null;
  pattern: Pattern | null;
  recipe: OpCall[];
  steps: Step[];
  previewStep: number | null;
  selectedColour: number;
  tool: Tool;
  selection: Rect | null;
  dirty: boolean;
  history: { undo: Patch[]; redo: Patch[] };
  status: Status;

  load(slug: string): Promise<void>;
  reset(): void;
  /** Adopt a freshly loaded / run / saved pattern: clears history and `dirty`. */
  setPattern(pattern: Pattern | null): void;
  setCells(changes: Change[]): void;
  setBackstitch(add: Segment[], remove: Segment[]): void;
  setBackground(index: number | null): void;
  pushPatch(patch: Patch): void;
  undo(): void;
  redo(): void;
  canUndo(): boolean;
  canRedo(): boolean;
  setSelectedColour(index: number): void;
  setTool(tool: Tool): void;
  setSelection(rect: Rect | null): void;
  setPreviewStep(index: number | null): void;
}

const initial = {
  slug: null,
  design: null,
  pattern: null,
  recipe: [] as OpCall[],
  steps: [] as Step[],
  previewStep: null,
  selectedColour: 0,
  tool: 'paint' as Tool,
  selection: null,
  dirty: false,
  history: { undo: [] as Patch[], redo: [] as Patch[] },
  status: { kind: 'idle' } as Status,
};

/** Legend with stitch counts adjusted for `changes` (counts are derived from the grid). */
function recount(legend: Pattern['legend'], changes: Change[]) {
  const delta = new Map<number, number>();
  for (const c of changes) {
    delta.set(c.from, (delta.get(c.from) ?? 0) - 1);
    delta.set(c.to, (delta.get(c.to) ?? 0) + 1);
  }
  return legend.map((entry, i) => {
    const d = delta.get(i) ?? 0;
    return d ? { ...entry, stitch_count: entry.stitch_count + d } : entry;
  });
}

export const useEditorStore = create<EditorState>()((set, get) => ({
  ...initial,

  async load(slug) {
    set({ ...initial, slug, status: { kind: 'loading' } });
    try {
      const design = await getDesign(slug);
      if (get().slug !== slug) return; // superseded by a later load
      set({ design, status: { kind: 'idle' } });
      get().setPattern(design.pattern);
    } catch (e) {
      const message = e instanceof ApiError ? String(e.detail) : e instanceof Error ? e.message : String(e);
      set({ status: { kind: 'error', message } });
    }
  },

  reset() {
    set({ ...initial });
  },

  setPattern(pattern) {
    set({
      pattern,
      recipe: pattern ? pattern.recipe.map((c) => ({ op: c.op, params: { ...c.params } })) : [],
      dirty: false,
      history: { undo: [], redo: [] },
      selection: null,
      previewStep: null,
      selectedColour: 0,
    });
  },

  setCells(changes) {
    const pattern = get().pattern;
    if (!pattern || changes.length === 0) return;
    set({
      pattern: { ...pattern, grid: applyChanges(pattern.grid, changes), legend: recount(pattern.legend, changes) },
      dirty: true,
    });
  },

  setBackstitch(add, remove) {
    const pattern = get().pattern;
    if (!pattern || (add.length === 0 && remove.length === 0)) return;
    const gone = new Set(remove.map(segKey));
    const kept = pattern.backstitch.filter((s) => !gone.has(segKey(s)));
    set({ pattern: { ...pattern, backstitch: dedupe([...kept, ...add]) }, dirty: true });
  },

  setBackground(index) {
    const pattern = get().pattern;
    if (!pattern || pattern.background_index === index) return;
    set({ pattern: { ...pattern, background_index: index }, dirty: true });
  },

  pushPatch(patch) {
    const undo = [...get().history.undo, patch].slice(-HISTORY_CAP);
    set({ history: { undo, redo: [] }, dirty: true });
  },

  undo() {
    const { history } = get();
    const patch = history.undo[history.undo.length - 1];
    if (!patch) return;
    get().setCells(invertChanges(patch.cells));
    get().setBackstitch(patch.backstitchRemove, patch.backstitchAdd);
    set({ history: { undo: history.undo.slice(0, -1), redo: [...history.redo, patch] }, dirty: true });
  },

  redo() {
    const { history } = get();
    const patch = history.redo[history.redo.length - 1];
    if (!patch) return;
    get().setCells(patch.cells);
    get().setBackstitch(patch.backstitchAdd, patch.backstitchRemove);
    set({ history: { undo: [...history.undo, patch], redo: history.redo.slice(0, -1) }, dirty: true });
  },

  canUndo: () => get().history.undo.length > 0,
  canRedo: () => get().history.redo.length > 0,

  setSelectedColour: (selectedColour) => set({ selectedColour }),
  setTool: (tool) => set({ tool }),
  setSelection: (selection) => set({ selection }),
  setPreviewStep: (previewStep) => set({ previewStep }),
}));
