/** One Recipe step: header (title, badges, move/remove, collapse) and a ParamField per schema property. */

import { useState } from 'react';
import type { OpCall, OpSchema } from '@/api/types';
import { useEditorStore } from '@/store/editorStore';
import { ParamField } from './ParamField';

interface Props {
  index: number;
  call: OpCall;
  schema: OpSchema | undefined;
  count: number;
  error?: string;
}

export function OpCard({ index, call, schema, count, error }: Props) {
  const removeOp = useEditorStore((s) => s.removeOp);
  const moveOp = useEditorStore((s) => s.moveOp);
  const setParam = useEditorStore((s) => s.setParam);
  const [collapsed, setCollapsed] = useState(false);

  const kind = schema?.kind ?? (call.op === 'pixelate' ? 'pixelate' : 'pattern');
  const isImport = kind === 'image' || kind === 'pixelate';
  const properties = (schema?.schema.properties ?? {}) as Record<string, Record<string, unknown>>;
  const keys = Object.keys(properties);

  return (
    <section className={`op-card${isImport ? ' op-card-import' : ''}${error ? ' op-card-error' : ''}`} aria-label={`Step ${index + 1}: ${call.op}`}>
      <header className="op-card-head">
        <button
          type="button"
          className="op-collapse"
          aria-expanded={!collapsed}
          onClick={() => setCollapsed((c) => !c)}
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? '▸' : '▾'}
        </button>
        <div className="op-heading">
          <span className="op-title">
            <span className="mono muted op-index">{index + 1}</span> {schema?.title ?? call.op}
          </span>
          <span className="op-badges">
            {schema && <span className="badge">{schema.group}</span>}
            <span className="badge">{kind}</span>
          </span>
        </div>
        <span className="op-actions">
          <button type="button" disabled={index === 0} onClick={() => moveOp(index, index - 1)} title="Move up" aria-label="Move up">↑</button>
          <button type="button" disabled={index >= count - 1} onClick={() => moveOp(index, index + 1)} title="Move down" aria-label="Move down">↓</button>
          <button type="button" onClick={() => removeOp(index)} title="Remove" aria-label="Remove">✕</button>
        </span>
      </header>
      {error && <div className="op-error" role="alert">{error}</div>}
      {!collapsed && (
        <div className="op-card-body">
          {schema?.description && <p className="muted small op-desc">{schema.description}</p>}
          {keys.map((key) => (
            <ParamField
              key={key}
              name={key}
              schema={properties[key]}
              value={call.params[key]}
              onChange={(k, v) => setParam(index, k, v)}
            />
          ))}
          {!schema && (
            <pre className="mono muted small">{JSON.stringify(call.params, null, 1)}</pre>
          )}
          {schema && keys.length === 0 && <p className="muted small">No parameters.</p>}
        </div>
      )}
    </section>
  );
}
