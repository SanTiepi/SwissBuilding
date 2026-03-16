import { useEffect, useRef, useState } from 'react';
import { useTranslation } from '@/i18n';
import { dossierApi } from '@/api/dossier';
import { completenessApi } from '@/api/completeness';
import { toast } from '@/store/toastStore';
import { FileDown, Loader2, Eye, ChevronDown } from 'lucide-react';

interface DossierPackButtonProps {
  buildingId: string;
  stage?: 'avt' | 'apt';
}

export function DossierPackButton({ buildingId, stage = 'avt' }: DossierPackButtonProps) {
  const { t } = useTranslation();
  const [generating, setGenerating] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [completenessScore, setCompletenessScore] = useState<number | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const isDisabled = completenessScore !== null && completenessScore < 0.5;

  useEffect(() => {
    let cancelled = false;
    completenessApi
      .evaluate(buildingId, stage)
      .then((result) => {
        if (!cancelled) setCompletenessScore(result.overall_score);
      })
      .catch(() => {
        /* ignore - completeness optional */
      });
    return () => {
      cancelled = true;
    };
  }, [buildingId, stage]);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleGeneratePdf = async () => {
    setDropdownOpen(false);
    setGenerating(true);
    try {
      const result = await dossierApi.generate(buildingId, stage);
      if (result instanceof Blob) {
        const url = URL.createObjectURL(result);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dossier-${buildingId}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        toast(t('dossier.generated'), 'success');
      } else {
        // Gotenberg unavailable - show HTML fallback
        setPreviewHtml(result.html);
        toast(t('dossier.generated'), 'success');
      }
    } catch {
      toast(t('dossier.error'));
    } finally {
      setGenerating(false);
    }
  };

  const handlePreview = async () => {
    setDropdownOpen(false);
    setPreviewing(true);
    try {
      const html = await dossierApi.preview(buildingId, stage);
      setPreviewHtml(html);
    } catch {
      toast(t('dossier.error'));
    } finally {
      setPreviewing(false);
    }
  };

  const scorePct = completenessScore !== null ? Math.round(completenessScore * 100) : null;
  const scoreColor =
    scorePct !== null ? (scorePct >= 95 ? 'text-green-600' : scorePct >= 70 ? 'text-yellow-600' : 'text-red-600') : '';

  return (
    <>
      <div>
        <div className="flex items-center gap-2">
          {/* Completeness score badge */}
          {scorePct !== null && (
            <span className={`text-sm font-semibold ${scoreColor}`} title={t('dossier.section.completeness')}>
              {scorePct}%
            </span>
          )}

          {/* Dropdown button */}
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              disabled={isDisabled || generating || previewing}
              title={isDisabled ? t('dossier.completeness_low') : undefined}
              className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {generating || previewing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileDown className="h-4 w-4" />
              )}
              {generating ? t('dossier.generating') : t('dossier.generate')}
              <ChevronDown className="h-3 w-3" />
            </button>

            {dropdownOpen && (
              <div className="absolute right-0 z-10 mt-1 w-48 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
                <button
                  onClick={handleGeneratePdf}
                  className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
                >
                  <FileDown className="h-4 w-4" />
                  {t('dossier.download_pdf')}
                </button>
                <button
                  onClick={handlePreview}
                  className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50"
                >
                  <Eye className="h-4 w-4" />
                  {t('dossier.preview')}
                </button>
              </div>
            )}
          </div>
        </div>
        <p className="text-xs text-gray-400 dark:text-slate-500 italic mt-1">
          {t('disclaimer.dossier') || 'This dossier does not constitute a legal compliance guarantee.'}
        </p>
      </div>

      {/* Preview modal */}
      {previewHtml && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setPreviewHtml(null)}
        >
          <div
            className="mx-4 max-h-[90vh] w-full max-w-4xl overflow-auto rounded-lg bg-white shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b p-4">
              <h3 className="font-semibold">{t('dossier.preview')}</h3>
              <button onClick={() => setPreviewHtml(null)} className="text-gray-400 hover:text-gray-600">
                &times;
              </button>
            </div>
            <div className="p-4">
              <iframe
                srcDoc={previewHtml}
                className="h-[70vh] w-full rounded border"
                title="Dossier Preview"
                sandbox="allow-same-origin"
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
