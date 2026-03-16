import { create } from 'zustand';

export type ToastType = 'error' | 'success' | 'info';

export interface ToastOptions {
  onUndo?: () => void;
  duration?: number;
}

export interface Toast {
  id: number;
  message: string;
  type: ToastType;
  onUndo?: () => void;
}

interface ToastStore {
  toasts: Toast[];
  addToast: (message: string, type?: ToastType, options?: ToastOptions) => void;
  removeToast: (id: number) => void;
}

let nextId = 0;
const timers = new Map<number, ReturnType<typeof setTimeout>>();

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (message, type = 'error', options?: ToastOptions) => {
    const id = ++nextId;
    const duration = options?.duration ?? 5000;
    set((s) => ({ toasts: [...s.toasts, { id, message, type, onUndo: options?.onUndo }] }));
    const timer = setTimeout(() => {
      timers.delete(id);
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
    }, duration);
    timers.set(id, timer);
  },
  removeToast: (id) => {
    const timer = timers.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.delete(id);
    }
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }));
  },
}));

export function toast(message: string, type: ToastType = 'error', options?: ToastOptions) {
  useToastStore.getState().addToast(message, type, options);
}
