import { useCallback, useEffect, useRef, useState, type RefObject } from 'react';
import { Link, useParams } from 'react-router-dom';
import { PatternCanvas, type PatternCanvasHandle } from '@/canvas/PatternCanvas';
import type { View, ViewMode } from '@/canvas/LayeredRenderer';
import { PalettePanel } from '@/components/PalettePanel';
import { RecipePanel } from '@/components/RecipePanel';
import { SaveButton } from '@/components/SaveButton';
import { ShortcutsHelp } from '@/components/ShortcutsHelp';
import { StepStrip } from '@/components/StepStrip';
import { ThreadPanel } from '@/components/ThreadPanel';
import { Toast } from '@/components/Toast';
import { Toolbar } from '@/components/Toolbar';
import { useShortcuts } from '@/hooks/useShortcuts';
import { useEditorStore } from '@/store/editorStore';

export function Editor() {
  const { slug = '' } = useParams();
  const load = useEditorStore((s) => s.load);
  const design = useEditorStore((s) => s.design);
  const pattern = useEditorStore((s) => s.pattern);
  const status = useEditorStore((s) => s.status);
  const dirty = useEditorStore((s) => s.dirty);
  const canvasRef = useRef<PatternCanvasHandle>(null);
  const [help, setHelp] = useState(false);
  const toggleHelp = useCallback(() => setHelp((h) => !h), []);
  const closeHelp = useCallback(() => setHelp(false), []);
  useShortcuts({ canvas: canvasRef, toggleHelp });

  useEffect(() => {
    void load(slug);
  }, [slug, load]);

  const title = design?.title ?? slug;

  return (
    <div className="editor">
      <header className="editor-titlebar">
        <Link to="/">← Library</Link>
        <h1>
          {title}
          {dirty && <span className="dirty-dot" title="Unsaved changes" aria-label="Unsaved changes" />}
        </h1>
        <span className="mono muted">{slug}</span>
        <span className="titlebar-actions">
          <button type="button" title="Keyboard shortcuts (?)" aria-label="Keyboard shortcuts" onClick={toggleHelp}>?</button>
          <SaveButton />
        </span>
      </header>
      <aside className="panel panel-left">
        <RecipePanel />
      </aside>
      <main className="editor-centre">
        {status.kind === 'loading' && <p className="muted centre">Loading…</p>}
        {status.kind === 'error' && <p className="error centre">{status.message}</p>}
        {status.kind === 'idle' && design && !pattern && (
          <div className="empty centre">
            <h2>No pattern yet</h2>
            <p>Add an input image and run a recipe.</p>
          </div>
        )}
        {status.kind === 'idle' && pattern && <CanvasArea canvasRef={canvasRef} />}
        {status.kind === 'idle' && pattern && <StepStrip />}
      </main>
      <aside className="panel panel-right">
        <PalettePanel />
        <ThreadPanel />
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
