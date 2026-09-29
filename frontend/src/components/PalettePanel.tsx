import { useEditorStore } from '@/store/editorStore';
import { PaletteMenu } from './PaletteMenu';

const css = (rgb: [number, number, number]) => `rgb(${rgb[0]},${rgb[1]},${rgb[2]})`;

export function PalettePanel() {
  const pattern = useEditorStore((s) => s.pattern);
  const selected = useEditorStore((s) => s.selectedColour);
  const select = useEditorStore((s) => s.setSelectedColour);
  if (!pattern) return null;

  return (
    <section className="palette">
      <h2>Legend</h2>
      <ul className="legend-list">
        {pattern.legend.map((entry, i) => {
          const isBackground = i === pattern.background_index;
          return (
            <li key={i} className="legend-item">
              <button
                type="button"
                className="legend-row"
                aria-pressed={i === selected}
                onClick={() => select(i)}
                title={`${entry.dmc_code} ${entry.dmc_name}${i < 9 ? ` (${i + 1})` : ''}`}
              >
                <span className="swatch" style={{ background: css(entry.rgb) }}>
                  <span className="swatch-symbol">{entry.symbol}</span>
                </span>
                <span className="legend-text">
                  <span className="mono">{entry.dmc_code}</span>
                  <span className="legend-name">{entry.dmc_name}</span>
                </span>
                <span className="legend-count mono">
                  {isBackground ? <span className="badge">fabric</span> : entry.stitch_count}
                </span>
                {i < 9 && <kbd className="legend-key">{i + 1}</kbd>}
              </button>
              <PaletteMenu index={i} entry={entry} />
            </li>
          );
        })}
      </ul>
    </section>
  );
}
