/** "Add operation" button with a grouped list of every op; the store keeps stage order. */

import { useState } from 'react';
import type { OpSchema } from '@/api/types';
import { useEditorStore } from '@/store/editorStore';
import { useToast } from './Toast';

const GROUP_ORDER = ['import', 'cleanup', 'kit', 'outline'];

export function groupOps(ops: OpSchema[]): [string, OpSchema[]][] {
  const groups = new Map<string, OpSchema[]>();
  for (const op of ops) groups.set(op.group, [...(groups.get(op.group) ?? []), op]);
  const names = [...groups.keys()].sort((a, b) => {
    const ia = GROUP_ORDER.indexOf(a);
    const ib = GROUP_ORDER.indexOf(b);
    return (ia < 0 ? GROUP_ORDER.length : ia) - (ib < 0 ? GROUP_ORDER.length : ib) || a.localeCompare(b);
  });
  return names.map((n) => [n, groups.get(n)!]);
}

export function AddOpMenu() {
  const opSchemas = useEditorStore((s) => s.opSchemas);
  const addOp = useEditorStore((s) => s.addOp);
  const show = useToast((s) => s.show);
  const [open, setOpen] = useState(false);

  const pick = (name: string) => {
    if (!addOp(name)) show(name === 'pixelate' ? 'The recipe already has a pixelate op.' : `Cannot add ${name}.`);
    setOpen(false);
  };

  return (
    <div className="add-op">
      <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} disabled={opSchemas.length === 0}>
        + Add operation
      </button>
      {open && (
        <div className="add-op-menu" role="menu">
          {groupOps(opSchemas).map(([group, ops]) => (
            <div key={group} className="add-op-group">
              <div className="add-op-group-name muted small">{group}</div>
              {ops.map((op) => (
                <button key={op.name} type="button" role="menuitem" className="add-op-item" title={op.description} onClick={() => pick(op.name)}>
                  {op.title} <span className="mono muted">{op.name}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
