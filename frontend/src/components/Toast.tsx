/** Bottom-centre transient message. `useToast.getState().show(msg)` from anywhere; one message at a time. */

import { useEffect } from 'react';
import { create } from 'zustand';

export const TOAST_MS = 4000;

interface ToastState {
  message: string | null;
  show(message: string): void;
  clear(): void;
}

export const useToast = create<ToastState>()((set) => ({
  message: null,
  show: (message) => set({ message }),
  clear: () => set({ message: null }),
}));

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
