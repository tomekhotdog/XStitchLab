/** Bottom-centre transient message; state lives in `@/store/toast` so the editor store can show one too. */

import { useEffect } from 'react';
import { useToast } from '@/store/toast';

export { useToast };

export const TOAST_MS = 4000;

export function Toast() {
  const message = useToast((s) => s.message);
  const clear = useToast((s) => s.clear);

  useEffect(() => {
    if (message === null) return;
    const t = window.setTimeout(clear, TOAST_MS);
    return () => window.clearTimeout(t);
  }, [message, clear]);

  if (message === null) return null;
  return (
    <div className="toast" role="status" onClick={clear}>
      {message}
    </div>
  );
}
