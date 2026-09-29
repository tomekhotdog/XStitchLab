/** Inline modal confirmation (the viewer has no `confirm()`). Esc or the backdrop cancels. */

import { useEffect } from 'react';

interface Props {
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm(): void;
  onCancel(): void;
}

export function ConfirmDialog({ title, message, confirmLabel = 'Continue', cancelLabel = 'Cancel', onConfirm, onCancel }: Props) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.stopPropagation();
        onCancel();
      }
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [onCancel]);

  return (
    <div className="dialog-backdrop" onClick={onCancel}>
      <div className="dialog" role="dialog" aria-modal="true" aria-label={title ?? message} onClick={(e) => e.stopPropagation()}>
        {title && <h3>{title}</h3>}
        <p>{message}</p>
        <div className="dialog-actions">
          <button type="button" onClick={onCancel}>{cancelLabel}</button>
          <button type="button" className="primary" autoFocus onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  );
}
