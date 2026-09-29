/**
 * "…" menu on a legend entry: Replace with DMC… (searchable palette), Merge into… (another legend
 * entry), Set as fabric. Each runs one Operation through `store.applyOp`, so it is undoable.
 */

import { useEffect, useRef, useState } from 'react';
import { listDmc } from '@/api/client';
import type { DmcColour, LegendEntry, Rgb } from '@/api/types';
import { useEditorStore } from '@/store/editorStore';

const MAX_RESULTS = 60;

let dmcCache: Promise<DmcColour[]> | null = null;
/** The DMC palette, fetched once per session. */
export function loadDmc(): Promise<DmcColour[]> {
  if (!dmcCache) {
    dmcCache = listDmc().catch((e: unknown) => {
      dmcCache = null;
      throw e;
    });
  }
  return dmcCache;
}

/** Palette entries whose code or name contains `query` (case-insensitive); code prefix matches first. */
export function filterDmc(colours: DmcColour[], query: string): DmcColour[] {
  const q = query.trim().toLowerCase();
  if (!q) return colours.slice(0, MAX_RESULTS);
  const prefix: DmcColour[] = [];
  const rest: DmcColour[] = [];
  for (const c of colours) {
    const code = c.code.toLowerCase();
    if (code.startsWith(q)) prefix.push(c);
    else if (code.includes(q) || c.name.toLowerCase().includes(q)) rest.push(c);
  }
  return [...prefix, ...rest].slice(0, MAX_RESULTS);
}

const css = (rgb: Rgb) => `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;

type Mode = 'menu' | 'replace' | 'merge';

interface Props {
  index: number;
  entry: LegendEntry;
}

export function PaletteMenu({ index, entry }: Props) {
  const pattern = useEditorStore((s) => s.pattern);
  const applyOp = useEditorStore((s) => s.applyOp);
  const [mode, setMode] = useState<Mode | null>(null);
  const [query, setQuery] = useState('');
  const [dmc, setDmc] = useState<DmcColour[] | null>(null);
  const [dmcError, setDmcError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const open = mode !== null;
  const close = () => {
    setMode(null);
    setQuery('');
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopImmediatePropagation();
        close();
      }
    };
    const onPointer = (e: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) close();
    };
    window.addEventListener('keydown', onKey, true);
    document.addEventListener('pointerdown', onPointer);
    return () => {
      window.removeEventListener('keydown', onKey, true);
      document.removeEventListener('pointerdown', onPointer);
    };
  }, [open]);

  useEffect(() => {
    if (mode !== 'replace' || dmc) return;
    let alive = true;
    loadDmc()
      .then((list) => alive && setDmc(list))
      .catch((e: unknown) => alive && setDmcError(e instanceof Error ? e.message : String(e)));
    return () => {
      alive = false;
    };
  }, [mode, dmc]);

  if (!pattern) return null;
  const isBackground = index === pattern.background_index;

  const run = async (op: string, params: Record<string, unknown>) => {
    setBusy(true);
    try {
      await applyOp(op, params);
    } finally {
      setBusy(false);
      close();
    }
  };

  return (
    <div className="palette-menu-root" ref={rootRef}>
      <button
        type="button"
        className="palette-menu-button"
        aria-label={`Actions for DMC ${entry.dmc_code}`}
        aria-expanded={open}
        onClick={() => (open ? close() : setMode('menu'))}
      >
        …
      </button>
      {mode === 'menu' && (
        <div className="palette-menu" role="menu">
          <button type="button" role="menuitem" className="palette-menu-item" onClick={() => setMode('replace')}>
            Replace with DMC…
          </button>
          <button
            type="button"
            role="menuitem"
            className="palette-menu-item"
            disabled={pattern.legend.length < 2}
            onClick={() => setMode('merge')}
          >
            Merge into…
          </button>
          <button
            type="button"
            role="menuitem"
            className="palette-menu-item"
            disabled={isBackground || busy}
            onClick={() => void run('background_to_fabric', { dmc_code: entry.dmc_code })}
          >
            {isBackground ? 'Is the fabric' : 'Set as fabric'}
          </button>
        </div>
      )}
      {mode === 'replace' && (
        <div className="palette-menu" role="menu">
          <input
            className="palette-search"
            type="search"
            placeholder="DMC code or name"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {dmcError && <p className="error small">{dmcError}</p>}
          {!dmc && !dmcError && <p className="muted small">Loading palette…</p>}
          {dmc && (
            <div className="palette-menu-list">
              {filterDmc(dmc, query).map((c) => (
                <button
                  key={c.code}
                  type="button"
                  role="menuitem"
                  className="palette-menu-item"
                  disabled={busy || c.code === entry.dmc_code}
                  onClick={() => void run('substitute_colour', { from_dmc: entry.dmc_code, to_dmc: c.code })}
                >
                  <span className="swatch small-swatch" style={{ background: css(c.rgb) }} />
                  <span className="mono">{c.code}</span>
                  <span className="muted">{c.name}</span>
                </button>
              ))}
              {filterDmc(dmc, query).length === 0 && <p className="muted small">No match</p>}
            </div>
          )}
        </div>
      )}
      {mode === 'merge' && (
        <div className="palette-menu" role="menu">
          <p className="muted small">Merge {entry.dmc_code} into:</p>
          <div className="palette-menu-list">
            {pattern.legend.map((other, i) =>
              i === index ? null : (
                <button
                  key={i}
                  type="button"
                  role="menuitem"
                  className="palette-menu-item"
                  disabled={busy}
                  onClick={() => void run('merge_colours', { from_dmc: entry.dmc_code, to_dmc: other.dmc_code })}
                >
                  <span className="swatch small-swatch" style={{ background: css(other.rgb) }} />
                  <span className="mono">{other.dmc_code}</span>
                  <span className="muted">{other.dmc_name}</span>
                </button>
              ),
            )}
          </div>
        </div>
      )}
    </div>
  );
}
