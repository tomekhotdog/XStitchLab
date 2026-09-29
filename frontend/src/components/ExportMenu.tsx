/**
 * Title-bar "Export" menu: one link per export kind, opened in a new tab. Exports read the saved
 * design, so entries are disabled without a pattern and a note warns while edits are unsaved.
 */

import { useEffect, useRef, useState } from 'react';
import { exportUrl } from '@/api/client';
import type { ExportKind, SheetLayout } from '@/api/types';
import { useEditorStore } from '@/store/editorStore';

export interface ExportEntry {
  label: string;
  kind: ExportKind;
  layout?: SheetLayout;
}

export const EXPORTS: ExportEntry[] = [
  { label: 'Pattern sheet A4', kind: 'sheet', layout: 'a4' },
  { label: 'Pattern sheet A5', kind: 'sheet', layout: 'a5' },
  { label: 'PDF', kind: 'pdf' },
  { label: 'Colour PNG', kind: 'png-color' },
  { label: 'Symbol PNG', kind: 'png-symbol' },
  { label: 'Realistic PNG', kind: 'png-realistic' },
  { label: 'JSON', kind: 'json' },
];

export function ExportMenu() {
  const slug = useEditorStore((s) => s.slug);
  const pattern = useEditorStore((s) => s.pattern);
  const dirty = useEditorStore((s) => s.dirty);
  const [open, setOpen] = useState(false);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    const onPointer = (e: PointerEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('pointerdown', onPointer);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('pointerdown', onPointer);
    };
  }, [open]);

  const enabled = Boolean(slug && pattern);

  return (
    <div className="export-menu-root" ref={root}>
      <button
        type="button"
        data-testid="export"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        Export
      </button>
      {open && (
        <div className="export-menu" role="menu" aria-label="Export">
          {EXPORTS.map((e) =>
            enabled ? (
              <a
                key={e.label}
                role="menuitem"
                className="export-item"
                href={exportUrl(slug as string, e.kind, e.layout)}
                target="_blank"
                rel="noopener"
                onClick={() => setOpen(false)}
              >
                {e.label}
              </a>
            ) : (
              <a key={e.label} role="menuitem" className="export-item" aria-disabled="true" tabIndex={-1}>
                {e.label}
              </a>
            ),
          )}
          <p className="muted small export-note">
            {!enabled && <>No pattern to export yet. </>}
            {enabled && dirty && <>Unsaved edits are not included; save first. </>}
            Files are also written into the design folder
          </p>
        </div>
      )}
    </div>
  );
}
