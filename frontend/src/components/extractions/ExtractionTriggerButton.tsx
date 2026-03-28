import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { toast } from '@/store/toastStore';
import { triggerExtraction } from '@/api/extractions';
import { Loader2, Wand2 } from 'lucide-react';
import { cn } from '@/utils/formatters';

interface ExtractionTriggerButtonProps {
  documentId: string;
  buildingId: string;
  /** Only show for PDF documents */
  mimeType: string | null;
  className?: string;
}

export function ExtractionTriggerButton({ documentId, buildingId, mimeType, className }: ExtractionTriggerButtonProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  // Only show for PDF documents
  const isPdf = mimeType === 'application/pdf' || mimeType?.includes('pdf') || false;
  if (!isPdf) return null;

  const handleTrigger = async () => {
    setIsLoading(true);
    try {
      const extraction = await triggerExtraction(documentId);
      toast(t('extraction.triggered') || 'Extraction lancee');
      navigate(`/buildings/${buildingId}/extractions/${extraction.id}`);
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.message || 'Erreur';
      toast(detail);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={handleTrigger}
      disabled={isLoading}
      title={t('extraction.trigger') || 'Extraire les donnees'}
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg transition-colors',
        'text-purple-700 dark:text-purple-300 bg-purple-50 dark:bg-purple-900/20',
        'hover:bg-purple-100 dark:hover:bg-purple-900/40',
        'border border-purple-200 dark:border-purple-700',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className,
      )}
    >
      {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wand2 className="w-3.5 h-3.5" />}
      <span className="hidden sm:inline">{t('extraction.trigger') || 'Extraire'}</span>
    </button>
  );
}
