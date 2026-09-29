import { useCallback, useEffect, useRef, useState, type CSSProperties, type KeyboardEvent, type PointerEvent, type RefObject } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { PatternCanvas, type PatternCanvasHandle } from '@/canvas/PatternCanvas';
import type { View, ViewMode } from '@/canvas/LayeredRenderer';
import { BriefPanel } from '@/components/BriefPanel';
import { EmptyState } from '@/components/EmptyState';
import { ExportMenu } from '@/components/ExportMenu';
import { PalettePanel } from '@/components/PalettePanel';
import { RecipePanel } from '@/components/RecipePanel';
import { SaveButton } from '@/components/SaveButton';
import { ShortcutsHelp } from '@/components/ShortcutsHelp';
import { StepStrip } from '@/components/StepStrip';
import { Tabs } from '@/components/Tabs';
import { ThreadPanel } from '@/components/ThreadPanel';
import { Toast } from '@/components/Toast';
import { Toolbar } from '@/components/Toolbar';
import { useShortcuts } from '@/hooks/useShortcuts';
import { useEditorStore, type Panel } from '@/store/editorStore';

export const PANEL_MIN = 280;
export const PANEL_MAX = 520;
export type Theme = 'system' | 'light' | 'dark';
const THEME_KEY = 'xstitch.theme';

const clampWidth = (w: number) => Math.min(PANEL_MAX, Math.max(PANEL_MIN, Math.round(w)));

function readStored(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStored(key: string, value: string | null): void {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* storage unavailable (private window, blocked site data): the setting just isn't remembered */
  }
}

/** Width of one side panel in px, clamped to PANEL_MIN..PANEL_MAX and remembered in localStorage. */
function usePanelWidth(key: string, initial: number) {
  const [width, setWidth] = useState(() => {
    const stored = Number(readStored(key));
    return stored ? clampWidth(stored) : initial;
  });
  const set = useCallback((w: number) => setWidth(clampWidth(w)), []);
  const persist = useCallback((w: number) => writeStored(key, String(clampWidth(w))), [key]);
  return { width, set, persist };
}

/** Theme choice: 'system' removes `data-theme` so prefers-color-scheme decides; otherwise stamps it. */
function useTheme(onChange: () => void) {
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = readStored(THEME_KEY);
    return stored === 'light' || stored === 'dark' ? stored : 'system';
  });
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'system') root.removeAttribute('data-theme');
    else root.setAttribute('data-theme', theme);
    writeStored(THEME_KEY, theme === 'system' ? null : theme);
    onChange();
    if (theme !== 'system' || typeof window.matchMedia !== 'function') return;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    media.addEventListener?.('change', onChange);
    return () => media.removeEventListener?.('change', onChange);
  }, [theme, onChange]);
  return [theme, setTheme] as const;
}

interface ResizeHandleProps {
  label: string;
  /** +1 when dragging right widens the panel (left panel), -1 for the right panel. */
  direction: 1 | -1;
  panel: ReturnType<typeof usePanelWidth>;
}

function ResizeHandle({ label, direction, panel }: ResizeHandleProps) {
  const drag = useRef<{ x: number; w: number } | null>(null);
  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.currentTarget.setPointerCapture?.(e.pointerId);
    drag.current = { x: e.clientX, w: panel.width };
  };
  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    if (drag.current) panel.set(drag.current.w + (e.clientX - drag.current.x) * direction);
  };
  const onPointerUp = (e: PointerEvent<HTMLDivElement>) => {
    if (!drag.current) return;
    const w = drag.current.w + (e.clientX - drag.current.x) * direction;
    drag.current = null;
    panel.set(w);
    panel.persist(w);
  };
  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    const step = e.key === 'ArrowRight' ? 16 : e.key === 'ArrowLeft' ? -16 : 0;
    if (!step) return;
    e.preventDefault();
    const w = panel.width + step * direction;
    panel.set(w);
    panel.persist(w);
  };
  return (
    <div
      className={`panel-resize ${direction === 1 ? 'panel-resize-end' : 'panel-resize-start'}`}
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      aria-valuemin={PANEL_MIN}
      aria-valuemax={PANEL_MAX}
      aria-valuenow={panel.width}
      tabIndex={0}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onKeyDown={onKeyDown}
    />
  );
}

const PANELS: { id: Panel; label: string }[] = [
  { id: 'brief', label: 'Brief' },
  { id: 'recipe', label: 'Recipe' },
];

export function Editor() {
  const { slug = '' } = useParams();
  const [params] = useSearchParams();
  const load = useEditorStore((s) => s.load);
  const panel = useEditorStore((s) => s.panel);
  const setPanel = useEditorStore((s) => s.setPanel);
  const design = useEditorStore((s) => s.design);
  const pattern = useEditorStore((s) => s.pattern);
  const status = useEditorStore((s) => s.status);
  const dirty = useEditorStore((s) => s.dirty);
  const canvasRef = useRef<PatternCanvasHandle>(null);
  const [help, setHelp] = useState(false);
  const toggleHelp = useCallback(() => setHelp((h) => !h), []);
  const closeHelp = useCallback(() => setHelp(false), []);
  useShortcuts({ canvas: canvasRef, toggleHelp });
  const left = usePanelWidth('xstitch.panel.left', 320);
  const right = usePanelWidth('xstitch.panel.right', 320);
  // The fabric colour is a theme token, so a theme switch repaints the canvas layers.
  const repaint = useCallback(() => {
    const handle = canvasRef.current;
    if (!handle) return;
    handle.renderer.redrawAll();
    handle.setZoom(handle.getView().zoom);
  }, []);
  const [theme, setTheme] = useTheme(repaint);

  useEffect(() => {
    void load(slug);
  }, [slug, load]);

  // `?panel=brief` (from "New design") picks the left tab per design; otherwise start on Recipe.
  useEffect(() => {
    setPanel(params.get('panel') === 'brief' ? 'brief' : 'recipe');
  }, [slug, params, setPanel]);

  const title = design?.title ?? slug;

  return (
    <div className="editor" style={{ '--left-w': `${left.width}px`, '--right-w': `${right.width}px` } as CSSProperties}>
      <header className="editor-titlebar">
        <Link to="/" className="back-link">← Library</Link>
        <h1 className="editor-title">
          {title}
          {dirty && <span className="dirty-dot" title="Unsaved changes" aria-label="Unsaved changes" />}
        </h1>
        <span className="mono muted editor-slug">{slug}</span>
        <span className="titlebar-actions">
          <label className="theme-select">
            <span className="visually-hidden">Theme</span>
            <select aria-label="Theme" value={theme} onChange={(e) => setTheme(e.target.value as Theme)}>
              <option value="system">System</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </label>
          <button type="button" className="ghost icon-button" title="Keyboard shortcuts (?)" aria-label="Keyboard shortcuts" onClick={toggleHelp}>?</button>
          <ExportMenu />
          <SaveButton />
        </span>
      </header>
      <aside className="panel panel-left">
        <div className="panel-scroll">
          <Tabs
            label="Design panels"
            items={PANELS.map((p) => ({ ...p, content: p.id === 'brief' ? <BriefPanel /> : <RecipePanel /> }))}
            active={panel}
            onChange={setPanel}
          />
        </div>
        <ResizeHandle label="Resize left panel" direction={1} panel={left} />
      </aside>
      <main className="editor-centre">
        {status.kind === 'loading' && <p className="muted centre">Loading…</p>}
        {status.kind === 'error' && <p className="error centre">{status.message}</p>}
        {status.kind === 'idle' && design && !pattern && <EmptyState />}
        {status.kind === 'idle' && pattern && <CanvasArea canvasRef={canvasRef} />}
        {status.kind === 'idle' && pattern && <StepStrip />}
      </main>
      <aside className="panel panel-right">
        <div className="panel-scroll">
          <PalettePanel />
          <ThreadPanel />
        </div>
        <ResizeHandle label="Resize right panel" direction={-1} panel={right} />
      </aside>
      <ShortcutsHelp open={help} onClose={closeHelp} />
      <Toast />
    </div>
  );
}

function CanvasArea({ canvasRef }: { canvasRef: RefObject<PatternCanvasHandle> }) {
  const [viewMode, setViewMode] = useState<ViewMode>('colour');
  const [zoom, setZoom] = useState(1);
  const onViewChange = (v: View) => setZoom(v.zoom);

  return (
    <>
      <div className="canvas-toolbar">
        <div className="segmented" role="group" aria-label="View mode">
          <button aria-pressed={viewMode === 'colour'} onClick={() => setViewMode('colour')}>Colour</button>
          <button aria-pressed={viewMode === 'symbol'} onClick={() => setViewMode('symbol')}>Symbol</button>
        </div>
        <button onClick={() => canvasRef.current?.fit()} title="Zoom to fit (F)">Fit</button>
        <span className="mono muted zoom">{Math.round(zoom * 100)}%</span>
        <span className="muted hint">wheel: zoom · space+drag: pan · ? keys</span>
      </div>
      <div className="canvas-area">
        <Toolbar />
        <PatternCanvas ref={canvasRef} viewMode={viewMode} onViewChange={onViewChange} />
      </div>
    </>
  );
}
