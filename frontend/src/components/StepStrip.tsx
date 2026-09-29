/**
 * Horizontal strip of Step previews under the canvas. Click selects `previewStep` (click again or
 * Esc clears); J/K move between steps. While a step is previewed the canvas shows its PNG and
 * editing is off (tools check `previewStep !== null`).
 */

import { useEffect } from 'react';
import { pngSrc } from '@/api/client';
import type { Step } from '@/api/types';
import { useEditorStore } from '@/store/editorStore';

const isTyping = (target: EventTarget | null) =>
  target instanceof HTMLElement && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.tagName === 'SELECT' || target.isContentEditable);

export function stepSummary(step: Step): string {
  const { width, height, colors, stitches } = step.stats;
  const size = `${width}×${height}`;
  return step.kind === 'pattern' || step.kind === 'pixelate' ? `${size} · ${colors} colours · ${stitches} stitches` : size;
}

export function StepStrip() {
  const steps = useEditorStore((s) => s.steps);
  const previewStep = useEditorStore((s) => s.previewStep);
  const setPreviewStep = useEditorStore((s) => s.setPreviewStep);
  const n = steps.length;

  useEffect(() => {
    if (n === 0) return;
    const onKey = (e: KeyboardEvent) => {
      if (isTyping(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;
      const current = useEditorStore.getState().previewStep;
      if (e.key === 'Escape') {
        if (current !== null) setPreviewStep(null);
      } else if (e.key === 'j' || e.key === 'J') {
        setPreviewStep(current === null ? 0 : (current + 1) % n);
      } else if (e.key === 'k' || e.key === 'K') {
        setPreviewStep(current === null ? n - 1 : current === 0 ? null : current - 1);
      } else {
        return;
      }
      e.preventDefault();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [n, setPreviewStep]);

  if (n === 0) return null;

  return (
    <div className="step-strip" role="region" aria-label="Recipe steps">
      <div className="step-strip-head small">
        {previewStep === null ? (
          <span className="muted">Steps · click to preview · J/K to step through</span>
        ) : (
          <span>Previewing step {previewStep + 1} — press Esc to return</span>
        )}
      </div>
      <ol className="step-list">
        {steps.map((step, i) => (
          <li key={i}>
            <button
              type="button"
              className="step-thumb"
              aria-pressed={previewStep === i}
              onClick={() => setPreviewStep(previewStep === i ? null : i)}
              title={stepSummary(step)}
            >
              <img src={pngSrc(step.preview_png)} alt={`${step.name} preview`} />
              <span className="step-name mono">{i + 1}. {step.name}</span>
              <span className="step-stats muted">{stepSummary(step)}</span>
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
