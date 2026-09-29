import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { PatternCanvas, type PatternCanvasHandle } from '@/canvas/PatternCanvas';
import type { View, ViewMode } from '@/canvas/LayeredRenderer';
import { PalettePanel } from '@/components/PalettePanel';
import { RecipePanel } from '@/components/RecipePanel';
import { StepStrip } from '@/components/StepStrip';
import { ThreadPanel } from '@/components/ThreadPanel';
import { Toast } from '@/components/Toast';
import { useEditorStore } from '@/store/editorStore';

export function Editor() {
  const { slug = '' } = useParams();
  const load = useEditorStore((s) => s.load);
  const design = useEditorStore((s) => s.design);
  const pattern = useEditorStore((s) => s.pattern);
  const status = useEditorStore((s) => s.status);
  const dirty = useEditorStore((s) => s.dirty);

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
          {dirty && <span className="muted"> (unsaved)</span>}
        </h1>
        <span className="mono muted">{slug}</span>
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
        {status.kind === 'idle' && pattern && <CanvasArea />}
        {status.kind === 'idle' && pattern && <StepStrip />}
      </main>
      <aside className="panel panel-right">
        <PalettePanel />
        <ThreadPanel />
      </aside>
      <Toast />
    </div>
  );
}

function CanvasArea() {
  const canvasRef = useRef<PatternCanvasHandle>(null);
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
        <span className="muted hint">wheel: zoom · space+drag: pan</span>
      </div>
      <PatternCanvas ref={canvasRef} viewMode={viewMode} onViewChange={onViewChange} />
    </>
  );
}
