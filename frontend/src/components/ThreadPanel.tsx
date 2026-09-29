import { useMemo } from 'react';
import { estimate, totals } from '@/model/threads';
import { useEditorStore } from '@/store/editorStore';

export function ThreadPanel() {
  const pattern = useEditorStore((s) => s.pattern);
  const rows = useMemo(() => (pattern ? estimate(pattern) : []), [pattern]);
  const sum = useMemo(() => totals(rows), [rows]);
  if (!pattern) return null;

  return (
    <section className="threads">
      <h2>Threads</h2>
      <table className="thread-table">
        <thead>
          <tr>
            <th>DMC</th>
            <th className="num">Stitches</th>
            <th className="num">m</th>
            <th className="num">Sections</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={`${r.dmc_code}-${r.is_backstitch}`} className={r.is_background ? 'muted' : undefined}>
              <td className="mono">
                {r.dmc_code}
                {r.is_backstitch && <span className="muted"> bs</span>}
                {r.is_background && <span className="muted"> fabric</span>}
              </td>
              <td className="num mono">{r.stitch_count}</td>
              <td className="num mono">{r.meters.toFixed(2)}</td>
              <td className="num mono">{r.sections_60cm}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th>Total</th>
            <th className="num mono">{sum.stitches}</th>
            <th className="num mono">{sum.meters.toFixed(2)}</th>
            <th className="num mono">{sum.sections_60cm}</th>
          </tr>
        </tfoot>
      </table>
      <p className="muted small">{sum.skeins} skeins · {pattern.metadata.fabric_count} ct</p>
    </section>
  );
}
