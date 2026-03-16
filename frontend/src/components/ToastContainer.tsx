import { useToastStore } from '@/store/toastStore';
import { useTranslation } from '@/i18n';
import { X } from 'lucide-react';
import { cn } from '@/utils/formatters';

const styles: Record<string, string> = {
  error: 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800 text-red-800 dark:text-red-200',
  success: 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800 text-green-800 dark:text-green-200',
  info: 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200',
};

export function ToastContainer() {
  const { t } = useTranslation();
  const toasts = useToastStore((s) => s.toasts);
  const removeToast = useToastStore((s) => s.removeToast);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm" data-testid="toast-container">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={cn(
            'flex items-center gap-2 px-4 py-3 border rounded-lg shadow-lg text-sm animate-in fade-in slide-in-from-bottom-2',
            styles[toast.type],
          )}
          role="alert"
        >
          <span className="flex-1">{toast.message}</span>
          {toast.onUndo && (
            <button
              onClick={() => {
                toast.onUndo?.();
                removeToast(toast.id);
              }}
              className="flex-shrink-0 text-xs font-semibold underline underline-offset-2 hover:opacity-80 px-1"
            >
              {t('form.undo')}
            </button>
          )}
          <button onClick={() => removeToast(toast.id)} className="flex-shrink-0 opacity-60 hover:opacity-100">
            <X className="w-4 h-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
