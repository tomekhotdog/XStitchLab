/** The `?` overlay: every keyboard shortcut. Esc, the backdrop or the close button dismiss it. */

import { useEffect } from 'react';
import { SHORTCUTS } from '@/hooks/useShortcuts';

interface Props {
  open: boolean;
  onClose(): void;
}

export function ShortcutsHelp({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopImmediatePropagation();
        onClose();
      }
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="dialog-backdrop" onClick={onClose}>
      <div className="dialog shortcuts" role="dialog" aria-modal="true" aria-label="Keyboard shortcuts" onClick={(e) => e.stopPropagation()}>
        <h3>Keyboard shortcuts</h3>
        <table className="shortcuts-table">
          <tbody>
            {SHORTCUTS.map(([keys, action]) => (
              <tr key={keys}>
                <td><kbd>{keys}</kbd></td>
                <td>{action}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="dialog-actions">
          <button type="button" autoFocus onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
