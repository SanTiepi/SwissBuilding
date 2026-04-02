import { Loader2, FileDown } from 'lucide-react';
import { cn } from '@/utils/formatters';

interface ReportDownloadButtonProps {
  onClick: () => void;
  loading?: boolean;
  disabled?: boolean;
  label?: string;
  className?: string;
}

export default function ReportDownloadButton({
  onClick,
  loading = false,
  disabled = false,
  label = 'Generer le rapport PDF',
  className,
}: ReportDownloadButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium text-sm transition-all',
        'bg-red-600 text-white hover:bg-red-700 active:bg-red-800',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'dark:bg-red-700 dark:hover:bg-red-600',
        className,
      )}
    >
      {loading ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          Generation en cours...
        </>
      ) : (
        <>
          <FileDown className="h-4 w-4" />
          {label}
        </>
      )}
    </button>
  );
}
