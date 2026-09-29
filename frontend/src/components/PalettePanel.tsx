import { useEditorStore } from '@/store/editorStore';

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
            <li key={i}>
              <button
                type="button"
                className="legend-row"
                aria-pressed={i === selected}
                onClick={() => select(i)}
                title={`${entry.dmc_code} ${entry.dmc_name}`}
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
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
