/**
 * Editor keyboard shortcuts, one window listener. Space (pan) stays in PatternCanvas because it
 * needs the matching keyup. Every key is ignored while focus is in a form field.
 */

import { useEffect, type RefObject } from 'react';
import type { PatternCanvasHandle } from '@/canvas/PatternCanvas';
import { deleteSelection, nudgeSelection } from '@/canvas/tools/select';
import type { ToolContext } from '@/canvas/tools/types';
import { useEditorStore, type Tool } from '@/store/editorStore';

export const ZOOM_STEP = 1.25;

export const TOOL_KEYS: Record<string, Tool> = { b: 'paint', g: 'fill', m: 'select', i: 'eyedropper', l: 'backstitch' };

const ARROWS: Record<string, [number, number]> = {
  ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1],
};

/** The shortcut list shown by ShortcutsHelp; order is the display order. */
export const SHORTCUTS: [keys: string, action: string][] = [
  ['B', 'Paint'],
  ['G', 'Fill'],
  ['M', 'Select'],
  ['I', 'Eyedropper (then back to the previous tool)'],
  ['L', 'Backstitch'],
  ['1 – 9', 'Select a legend colour'],
  ['Delete / Backspace', 'Clear the selection to fabric'],
  ['Arrows', 'Nudge the selection by one cell'],
  ['Esc', 'Clear the selection or step preview'],
  ['Ctrl/Cmd + Z', 'Undo'],
  ['Ctrl/Cmd + Shift + Z, Ctrl + Y', 'Redo'],
  ['Ctrl/Cmd + S', 'Save'],
  ['F', 'Zoom to fit'],
  ['+ / −', 'Zoom in / out'],
  ['Wheel', 'Zoom about the cursor'],
  ['Space + drag, middle drag', 'Pan'],
  ['?', 'This help'],
];

export interface ShortcutTargets {
  canvas?: RefObject<PatternCanvasHandle | null>;
  toggleHelp?(): void;
}

export const isTyping = (target: EventTarget | null) =>
  target instanceof HTMLElement &&
  (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT' || target.isContentEditable);

export function handleShortcut(e: KeyboardEvent, targets: ShortcutTargets): void {
  if (isTyping(e.target) || e.altKey) return;
  const s = useEditorStore.getState();
  const key = e.key;
  const lower = key.toLowerCase();

  if (e.metaKey || e.ctrlKey) {
    if (lower === 'z') e.shiftKey ? s.redo() : s.undo();
    else if (lower === 'y') s.redo();
    else if (lower === 's') void s.save();
    else return;
    e.preventDefault();
    return;
  }

  const canvas = targets.canvas?.current;
  const tool = TOOL_KEYS[lower];
  if (tool) {
    s.setTool(tool);
  } else if (/^[1-9]$/.test(key)) {
    const index = Number(key) - 1;
    if (s.pattern && index < s.pattern.legend.length) s.setSelectedColour(index);
  } else if (key === 'Escape') {
    s.setSelection(null);
    s.setOverlay(null);
    s.setPreviewStep(null);
  } else if (key === 'Delete' || key === 'Backspace') {
    if (s.pattern && s.previewStep === null) deleteSelection(s as ToolContext);
  } else if (ARROWS[key]) {
    if (!s.selection) return; // let the browser scroll
    if (s.pattern && s.previewStep === null) nudgeSelection(s as ToolContext, ...ARROWS[key]);
  } else if (lower === 'f') {
    canvas?.fit();
  } else if (key === '+' || key === '=') {
    canvas?.setZoom(canvas.getView().zoom * ZOOM_STEP);
  } else if (key === '-' || key === '_') {
    canvas?.setZoom(canvas.getView().zoom / ZOOM_STEP);
  } else if (key === '?') {
    targets.toggleHelp?.();
  } else {
    return;
  }
  e.preventDefault();
}

export function useShortcuts(targets: ShortcutTargets): void {
  const { canvas, toggleHelp } = targets;
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => handleShortcut(e, { canvas, toggleHelp });
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [canvas, toggleHelp]);
}
