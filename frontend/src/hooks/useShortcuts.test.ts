import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { PatternCanvasHandle } from '@/canvas/PatternCanvas';
import { useEditorStore } from '@/store/editorStore';
import { grid, loadPattern, makePattern } from '@/test/tools';
import { useShortcuts } from './useShortcuts';

const store = () => useEditorStore.getState();
const realSave = store().save;

const canvas = {
  fit: vi.fn(),
  setZoom: vi.fn(),
  getView: () => ({ zoom: 2, panX: 0, panY: 0, cellPx: 16 }),
} as unknown as PatternCanvasHandle;
const toggleHelp = vi.fn();

function press(key: string, init: KeyboardEventInit = {}, target: EventTarget = window): KeyboardEvent {
  const e = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init });
  target.dispatchEvent(e);
  return e;
}

beforeEach(() => {
  vi.clearAllMocks();
  loadPattern(makePattern(4, 4, 3));
  useEditorStore.setState({ save: vi.fn().mockResolvedValue(true) });
  renderHook(() => useShortcuts({ canvas: { current: canvas }, toggleHelp }));
});

afterEach(() => {
  useEditorStore.setState({ save: realSave });
});

describe('tools and colours', () => {
  it.each([['b', 'paint'], ['g', 'fill'], ['m', 'select'], ['i', 'eyedropper'], ['l', 'backstitch'], ['G', 'fill']])(
    "'%s' selects the %s tool",
    (key, tool) => {
      store().setTool(tool === 'paint' ? 'fill' : 'paint');
      press(key);
      expect(store().tool).toBe(tool);
    },
  );

  it('digits select legend entries 1-9 when they exist', () => {
    press('3');
    expect(store().selectedColour).toBe(2);
    press('9');
    expect(store().selectedColour).toBe(2);
  });
});

describe('history and save', () => {
  const cells = [{ x: 0, y: 0, from: 0, to: 1 }];
  beforeEach(() => {
    store().setCells(cells);
    store().pushPatch({ cells, backstitchAdd: [], backstitchRemove: [] });
  });

  it('Ctrl/Cmd+Z undoes, Ctrl/Cmd+Shift+Z and Ctrl+Y redo', () => {
    expect(press('z', { ctrlKey: true }).defaultPrevented).toBe(true);
    expect(grid()[0][0]).toBe(0);
    press('z', { metaKey: true, shiftKey: true });
    expect(grid()[0][0]).toBe(1);
    press('z', { metaKey: true });
    expect(grid()[0][0]).toBe(0);
    press('y', { ctrlKey: true });
    expect(grid()[0][0]).toBe(1);
  });

  it('Ctrl/Cmd+S saves and prevents the browser dialog', () => {
    expect(press('s', { metaKey: true }).defaultPrevented).toBe(true);
    expect(store().save).toHaveBeenCalledTimes(1);
    press('s', { ctrlKey: true });
    expect(store().save).toHaveBeenCalledTimes(2);
  });

  it("plain 's' does not save", () => {
    press('s');
    expect(store().save).not.toHaveBeenCalled();
  });
});

describe('selection keys', () => {
  beforeEach(() => {
    const p = makePattern(4, 4, 3);
    p.grid[1][1] = 1;
    loadPattern(p);
    store().setSelection({ x: 1, y: 1, w: 1, h: 1 });
  });

  it('Delete and Backspace clear the selection to the Background', () => {
    expect(press('Backspace').defaultPrevented).toBe(true);
    expect(grid()[1][1]).toBe(0);
    store().undo();
    press('Delete');
    expect(grid()[1][1]).toBe(0);
  });

  it('arrows nudge the selection', () => {
    expect(press('ArrowRight').defaultPrevented).toBe(true);
    expect(grid()[1]).toEqual([0, 0, 1, 0]);
    press('ArrowDown');
    expect(grid()[2]).toEqual([0, 0, 1, 0]);
    expect(store().selection).toEqual({ x: 2, y: 2, w: 1, h: 1 });
  });

  it('Escape clears the selection, overlay and step preview', () => {
    store().setOverlay({ marquee: { x: 0, y: 0, w: 1, h: 1 } });
    store().setPreviewStep(0);
    press('Escape');
    expect(store().selection).toBeNull();
    expect(store().overlay).toBeNull();
    expect(store().previewStep).toBeNull();
  });

  it('edits are inert while a step preview is shown', () => {
    store().setPreviewStep(0);
    press('Delete');
    expect(grid()[1][1]).toBe(1);
  });
});

describe('view and help', () => {
  it("'f' fits, '+' and '-' zoom about the centre, '?' toggles help", () => {
    press('f');
    expect(canvas.fit).toHaveBeenCalled();
    press('+');
    expect(canvas.setZoom).toHaveBeenLastCalledWith(2.5);
    press('-');
    expect(canvas.setZoom).toHaveBeenLastCalledWith(1.6);
    press('?', { shiftKey: true });
    expect(toggleHelp).toHaveBeenCalledTimes(1);
  });
});

describe('focus in a field', () => {
  it.each(['input', 'textarea', 'select'])('ignores keys typed into a %s', (tag) => {
    const el = document.createElement(tag);
    document.body.appendChild(el);
    press('g', {}, el);
    press('z', { ctrlKey: true }, el);
    expect(store().tool).toBe('paint');
    el.remove();
  });

  it('ignores keys in a contentEditable element', () => {
    const el = document.createElement('div');
    Object.defineProperty(el, 'isContentEditable', { value: true });
    document.body.appendChild(el);
    press('g', {}, el);
    expect(store().tool).toBe('paint');
    el.remove();
  });
});
