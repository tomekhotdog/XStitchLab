/** Transient status message. `useToast.getState().show(msg)` from anywhere; one message at a time. */

import { create } from 'zustand';

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
