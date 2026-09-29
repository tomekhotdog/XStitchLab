/** Vertical tool rail on the canvas's left edge; the store's `tool` is the single source of truth. */

import { useEditorStore, type Tool } from '@/store/editorStore';

export const TOOLS: { tool: Tool; label: string; key: string; glyph: string }[] = [
  { tool: 'paint', label: 'Paint', key: 'B', glyph: '✎' },
  { tool: 'fill', label: 'Fill', key: 'G', glyph: '▣' },
  { tool: 'select', label: 'Select', key: 'M', glyph: '⬚' },
  { tool: 'eyedropper', label: 'Eyedropper', key: 'I', glyph: '⊙' },
  { tool: 'backstitch', label: 'Backstitch', key: 'L', glyph: '⟋' },
];

export function Toolbar() {
  const active = useEditorStore((s) => s.tool);
  const setTool = useEditorStore((s) => s.setTool);
  return (
    <nav className="toolbar" aria-label="Tools">
      {TOOLS.map((t) => (
        <button
          key={t.tool}
          type="button"
          className={t.tool === active ? 'tool active' : 'tool'}
          aria-pressed={t.tool === active}
          aria-label={t.label}
          title={`${t.label} (${t.key})`}
          onClick={() => setTool(t.tool)}
        >
          <span className="tool-glyph" aria-hidden="true">{t.glyph}</span>
          <kbd className="tool-key">{t.key}</kbd>
        </button>
      ))}
    </nav>
  );
}
