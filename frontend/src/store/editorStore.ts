/**
 * Editor state (zustand). Pure setters mutate the Pattern immutably; `undo`/`redo` replay patches
 * through those same setters so every subscriber (canvas, palette, threads) sees the change.
 * `load`, `runRecipe`, `applyOp` and `save` talk to the API.
 */

import { create } from 'zustand';
import {
  ApiError, applyOp as applyOpApi, defaultRecipes, getDesign, listOps, runRecipe as runRecipeApi,
  saveHistory as saveHistoryApi, savePattern, savePrompt as savePromptApi, uploadInput as uploadInputApi,
} from '@/api/client';
import type { DesignDetail, JsonSchema, OpCall, OpKind, OpSchema, Pattern, Segment, Step } from '@/api/types';
import { applyChanges, invertChanges, type Change, type Rect } from '@/model/grid';
import { dedupe, segKey } from '@/model/segments';
import { useToast } from './toast';

export type Tool = 'paint' | 'fill' | 'select' | 'eyedropper' | 'backstitch';

/** Which left-column tab is showing; kept across designs so `?panel=` survives the load. */
export type Panel = 'brief' | 'recipe';

/**
 * One undoable edit. Cell/backstitch deltas come from a tool stroke; `replace` is a whole-pattern
 * swap (an Operation applied through the API) and takes precedence when present.
 */
export interface HistoryPatch {
  cells: Change[];
  backstitchAdd: Segment[];
  backstitchRemove: Segment[];
  replace?: { before: Pattern; after: Pattern };
}

/** Transient tool feedback drawn on the canvas overlay: a marquee being dragged or a selection being moved. */
export interface ToolOverlay {
  marquee?: Rect;
  move?: { rect: Rect; dx: number; dy: number };
}

export interface Status {
  kind: 'idle' | 'loading' | 'error';
  message?: string;
}

export const HISTORY_CAP = 200;

export interface RunError {
  step_index?: number;
  op?: string;
  message: string;
}

export interface EditorState {
  slug: string | null;
  design: DesignDetail | null;
  /** The Brief (`prompt.md`), the History paragraph printed on the sheet (`history` is undo/redo), and whether `input.png` exists. */
  prompt: string;
  historyText: string;
  /** design.json version from the last load/save; guards against overwriting a newer file. */
  version: string | null;
  hasInput: boolean;
  /** Bumped after each upload so `inputUrl(slug) + '?v=' + inputVersion` bypasses the browser cache. */
  inputVersion: number;
  panel: Panel;
  pattern: Pattern | null;
  recipe: OpCall[];
  steps: Step[];
  previewStep: number | null;
  selectedColour: number;
  tool: Tool;
  /** The tool active before the current one; the eyedropper returns to it. */
  previousTool: Tool;
  selection: Rect | null;
  overlay: ToolOverlay | null;
  dirty: boolean;
  saving: boolean;
  history: { undo: HistoryPatch[]; redo: HistoryPatch[] };
  status: Status;
  /** Op catalogue and default recipes; fetched once, kept across designs. */
  opSchemas: OpSchema[];
  defaults: Record<string, OpCall[]>;
  running: boolean;
  runError: RunError | null;

  load(slug: string): Promise<void>;
  reset(): void;
  /** Adopt a freshly loaded / run / saved pattern: clears history and `dirty`. */
  setPattern(pattern: Pattern | null): void;
  /** Swap the whole pattern as an edit (history kept, `dirty` set); used by `applyOp` and undo/redo of it. */
  replacePattern(pattern: Pattern): void;
  setCells(changes: Change[]): void;
  setBackstitch(add: Segment[], remove: Segment[]): void;
  setBackground(index: number | null): void;
  pushPatch(patch: HistoryPatch): void;
  undo(): void;
  redo(): void;
  canUndo(): boolean;
  canRedo(): boolean;
  setSelectedColour(index: number): void;
  setTool(tool: Tool): void;
  setSelection(rect: Rect | null): void;
  setOverlay(overlay: ToolOverlay | null): void;
  setPreviewStep(index: number | null): void;
  /** Apply one Operation to the current pattern through the API as an undoable edit; false (with a toast) on failure. */
  applyOp(op: string, params?: Record<string, unknown>): Promise<boolean>;
  /** `PUT /designs/{slug}`; adopts the canonical pattern and clears `dirty`; false (with a toast) on failure. */
  save(): Promise<boolean>;
  /** `PUT .../prompt`; adopts the saved text; false (with a toast) on failure. */
  savePrompt(text: string): Promise<boolean>;
  /** `PUT .../history`; adopts the saved text; false (with a toast) on failure. */
  saveHistory(text: string): Promise<boolean>;
  /** `PUT .../input`; sets `hasInput` and bumps `inputVersion`; false (with a toast) on failure. */
  uploadInput(file: File | Blob): Promise<boolean>;
  setPanel(panel: Panel): void;

  loadOps(): Promise<void>;
  setRecipe(recipe: OpCall[]): void;
  loadDefault(name: string): void;
  /** Insert with the schema's defaults, keeping stage order; false when refused (unknown op, second pixelate). */
  addOp(name: string, atIndex?: number): boolean;
  removeOp(index: number): void;
  moveOp(from: number, to: number): void;
  /** `null`/`undefined` removes the key so the backend applies its default. */
  setParam(index: number, key: string, value: unknown): void;
  runRecipe(): Promise<void>;
}

const initial = {
  slug: null,
  design: null,
  prompt: '',
  historyText: '',
  version: null as string | null,
  hasInput: false,
  inputVersion: 0,
  pattern: null,
  recipe: [] as OpCall[],
  steps: [] as Step[],
  previewStep: null,
  selectedColour: 0,
  tool: 'paint' as Tool,
  previousTool: 'paint' as Tool,
  selection: null,
  overlay: null,
  dirty: false,
  saving: false,
  history: { undo: [] as HistoryPatch[], redo: [] as HistoryPatch[] },
  status: { kind: 'idle' } as Status,
  running: false,
  runError: null as RunError | null,
};

const cloneRecipe = (recipe: OpCall[]) => recipe.map((c) => ({ op: c.op, params: { ...c.params } }));

/** Params from a JSON Schema's `default`s; null defaults are omitted (the backend fills them). */
export function schemaDefaults(schema: JsonSchema): Record<string, unknown> {
  const props = (schema.properties ?? {}) as Record<string, { default?: unknown }>;
  const params: Record<string, unknown> = {};
  for (const [key, prop] of Object.entries(props)) {
    if (prop.default !== undefined && prop.default !== null) params[key] = prop.default;
  }
  return params;
}

function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    if (typeof e.detail === 'string') return e.detail;
    return e.detail
      .map((d) => {
        const err = d as { loc?: unknown[]; msg?: string };
        const loc = Array.isArray(err.loc) ? err.loc.join('.') : '';
        return loc ? `${loc}: ${err.msg ?? ''}` : String(err.msg ?? JSON.stringify(d));
      })
      .join('; ');
  }
  return e instanceof Error ? e.message : String(e);
}

let opsRequest: Promise<void> | null = null;

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
  opSchemas: [],
  defaults: {},
  panel: 'recipe',

  async load(slug) {
    set({ ...initial, slug, status: { kind: 'loading' } });
    try {
      const design = await getDesign(slug);
      if (get().slug !== slug) return; // superseded by a later load
      set({ design, prompt: design.prompt, historyText: design.history, hasInput: design.has_input, version: design.version ?? null, status: { kind: 'idle' } });
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
      overlay: null,
      previewStep: null,
      selectedColour: 0,
    });
  },

  replacePattern(pattern) {
    set({
      pattern,
      dirty: true,
      selection: null,
      overlay: null,
      selectedColour: Math.min(get().selectedColour, Math.max(0, pattern.legend.length - 1)),
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
    if (patch.replace) {
      get().replacePattern(patch.replace.before);
    } else {
      get().setCells(invertChanges(patch.cells));
      get().setBackstitch(patch.backstitchRemove, patch.backstitchAdd);
    }
    set({ history: { undo: history.undo.slice(0, -1), redo: [...history.redo, patch] }, dirty: true });
  },

  redo() {
    const { history } = get();
    const patch = history.redo[history.redo.length - 1];
    if (!patch) return;
    if (patch.replace) {
      get().replacePattern(patch.replace.after);
    } else {
      get().setCells(patch.cells);
      get().setBackstitch(patch.backstitchAdd, patch.backstitchRemove);
    }
    set({ history: { undo: [...history.undo, patch], redo: history.redo.slice(0, -1) }, dirty: true });
  },

  canUndo: () => get().history.undo.length > 0,
  canRedo: () => get().history.redo.length > 0,

  setSelectedColour: (selectedColour) => set({ selectedColour }),
  setTool(tool) {
    const current = get().tool;
    if (tool !== current) set({ tool, previousTool: current });
  },
  setSelection: (selection) => set({ selection }),
  setOverlay: (overlay) => set({ overlay }),
  setPreviewStep: (previewStep) => set({ previewStep }),

  async applyOp(op, params = {}) {
    const before = get().pattern;
    if (!before) return false;
    try {
      const after = await applyOpApi(before, op, params);
      if (get().pattern !== before) {
        useToast.getState().show('The pattern changed while the operation ran; try again.');
        return false;
      }
      get().replacePattern(after);
      get().pushPatch({ cells: [], backstitchAdd: [], backstitchRemove: [], replace: { before, after } });
      return true;
    } catch (e) {
      useToast.getState().show(errorMessage(e));
      return false;
    }
  },

  async save() {
    const { slug, pattern, saving, version } = get();
    if (!slug || !pattern || saving) return false;
    set({ saving: true });
    try {
      const result = await savePattern(slug, pattern, version);
      const saved = result.pattern;
      if (get().slug !== slug) return false;
      set({ version: result.version });
      if (get().pattern === pattern) {
        // nothing changed meanwhile: adopt the canonical copy (else the newer local edits stay, still dirty)
        const { selectedColour, tool, previousTool } = get();
        get().setPattern(saved);
        set({ selectedColour: Math.min(selectedColour, Math.max(0, saved.legend.length - 1)), tool, previousTool });
      }
      useToast.getState().show('Saved');
      return true;
    } catch (e) {
      useToast.getState().show(errorMessage(e));
      return false;
    } finally {
      set({ saving: false });
    }
  },

  async savePrompt(text) {
    const { slug } = get();
    if (!slug) return false;
    try {
      const saved = await savePromptApi(slug, text);
      if (get().slug !== slug) return false;
      set({ prompt: saved.text });
      useToast.getState().show('Brief saved');
      return true;
    } catch (e) {
      useToast.getState().show(errorMessage(e));
      return false;
    }
  },

  async saveHistory(text) {
    const { slug } = get();
    if (!slug) return false;
    try {
      const saved = await saveHistoryApi(slug, text);
      if (get().slug !== slug) return false;
      set({ historyText: saved.text });
      useToast.getState().show('History saved');
      return true;
    } catch (e) {
      useToast.getState().show(errorMessage(e));
      return false;
    }
  },

  async uploadInput(file) {
    const { slug } = get();
    if (!slug) return false;
    try {
      await uploadInputApi(slug, file);
      if (get().slug !== slug) return false;
      set({ hasInput: true, inputVersion: get().inputVersion + 1 });
      useToast.getState().show('Input saved');
      return true;
    } catch (e) {
      useToast.getState().show(errorMessage(e));
      return false;
    }
  },

  setPanel: (panel) => set({ panel }),

  async loadOps() {
    if (get().opSchemas.length > 0) return;
    if (!opsRequest) {
      opsRequest = Promise.all([listOps(), defaultRecipes()])
        .then(([opSchemas, defaults]) => set({ opSchemas, defaults }))
        .finally(() => {
          opsRequest = null;
        });
    }
    await opsRequest;
  },

  setRecipe: (recipe) => set({ recipe: cloneRecipe(recipe), runError: null }),

  loadDefault(name) {
    const recipe = get().defaults[name];
    if (recipe) get().setRecipe(recipe);
  },

  addOp(name, atIndex) {
    const { opSchemas, recipe } = get();
    const schema = opSchemas.find((s) => s.name === name);
    if (!schema) return false;
    const kinds = recipe.map((c) => kindOf(opSchemas, c.op));
    const pixelateAt = kinds.indexOf('pixelate');
    if (schema.kind === 'pixelate' && pixelateAt >= 0) return false;
    const lastNonPattern = kinds.reduce((last, k, i) => (k !== 'pattern' ? i : last), -1);
    const firstNonImage = kinds.findIndex((k) => k !== 'image');
    let index = Math.min(atIndex ?? recipe.length, recipe.length);
    if (schema.kind === 'pattern') index = Math.max(index, lastNonPattern + 1);
    else if (firstNonImage >= 0) index = Math.min(index, schema.kind === 'image' ? firstNonImage : lastNonPattern + 1);
    const next = [...recipe];
    next.splice(index, 0, { op: name, params: schemaDefaults(schema.schema) });
    set({ recipe: next });
    return true;
  },

  removeOp(index) {
    const { recipe } = get();
    if (index < 0 || index >= recipe.length) return;
    set({ recipe: recipe.filter((_, i) => i !== index) });
  },

  moveOp(from, to) {
    const { recipe } = get();
    const n = recipe.length;
    if (from === to || from < 0 || to < 0 || from >= n || to >= n) return;
    const next = [...recipe];
    const [call] = next.splice(from, 1);
    next.splice(to, 0, call);
    set({ recipe: next });
  },

  setParam(index, key, value) {
    const { recipe } = get();
    const call = recipe[index];
    if (!call) return;
    const params = { ...call.params };
    if (value === null || value === undefined) delete params[key];
    else params[key] = value;
    set({ recipe: recipe.map((c, i) => (i === index ? { op: c.op, params } : c)) });
  },

  async runRecipe() {
    const { slug, recipe, running } = get();
    if (!slug || running) return;
    set({ running: true, runError: null });
    try {
      const res = await runRecipeApi(slug, recipe);
      if (get().slug !== slug) return;
      get().setPattern(res.pattern);
      set({ steps: res.steps, running: false });
    } catch (e) {
      const runError: RunError = { message: errorMessage(e) };
      if (e instanceof ApiError) {
        if (e.step_index !== undefined) runError.step_index = e.step_index;
        if (e.op !== undefined) runError.op = e.op;
      }
      set({ running: false, runError });
    }
  },
}));

/** Stage kind of an op by name; unknown names count as pattern ops (the common case). */
export function kindOf(opSchemas: OpSchema[], name: string): OpKind {
  return opSchemas.find((s) => s.name === name)?.kind ?? (name === 'pixelate' ? 'pixelate' : 'pattern');
}
