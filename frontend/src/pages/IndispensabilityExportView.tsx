import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuth } from '@/hooks/useAuth';
import { intelligenceApi } from '@/api/intelligence';
import { Loader2, Printer, ArrowLeft } from 'lucide-react';

export default function IndispensabilityExportView() {
  const { t } = useTranslation();
  useAuth();
  const { buildingId } = useParams<{ buildingId: string }>();
  const navigate = useNavigate();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['indispensability-export', buildingId],
    queryFn: () => intelligenceApi.getIndispensabilityExport(buildingId!),
    enabled: !!buildingId,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-white">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-white">
        <p className="text-red-600 text-sm">{t('indispensability.error') || 'Error loading report'}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white print:bg-white">
      {/* Toolbar (hidden in print) */}
      <div className="print:hidden sticky top-0 z-10 bg-white border-b border-slate-200 px-6 py-3 flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          {t('indispensability.back') || 'Retour'}
        </button>
        <div className="flex-1" />
        <button
          onClick={() => window.print()}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
        >
          <Printer className="w-4 h-4" />
          {t('indispensability.print') || 'Imprimer'}
        </button>
      </div>

      {/* Print content */}
      <div className="max-w-3xl mx-auto px-8 py-12 print:px-0 print:py-0">
        {/* Header */}
        <div className="mb-8 border-b-2 border-red-600 pb-6">
          <h1 className="text-3xl font-bold text-slate-900 mb-2">{data.title}</h1>
          <p className="text-sm text-slate-500">
            {t('indispensability.generated_at') || 'Genere le'} {new Date(data.generated_at).toLocaleDateString()}
          </p>
        </div>

        {/* Executive summary */}
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">
            {t('indispensability.executive_summary') || 'Resume executif'}
          </h2>
          <p className="text-sm text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-lg print:bg-transparent print:p-0">
            {data.executive_summary}
          </p>
        </section>

        {/* Fragmentation section */}
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">
            {t('indispensability.fragmentation_score') || 'Fragmentation'}
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <tbody>
                {Object.entries(data.fragmentation_section).map(([key, val]) => (
                  <tr key={key} className="border-b border-slate-100">
                    <td className="py-2 pr-4 font-medium text-slate-600 whitespace-nowrap">{key.replace(/_/g, ' ')}</td>
                    <td className="py-2 text-slate-800">{String(val)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Defensibility section */}
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">
            {t('indispensability.defensibility_score') || 'Defensibilite'}
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <tbody>
                {Object.entries(data.defensibility_section).map(([key, val]) => (
                  <tr key={key} className="border-b border-slate-100">
                    <td className="py-2 pr-4 font-medium text-slate-600 whitespace-nowrap">{key.replace(/_/g, ' ')}</td>
                    <td className="py-2 text-slate-800">{String(val)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Counterfactual section */}
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">
            {t('indispensability.delta_highlights') || 'Counterfactual'}
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <tbody>
                {Object.entries(data.counterfactual_section).map(([key, val]) => (
                  <tr key={key} className="border-b border-slate-100">
                    <td className="py-2 pr-4 font-medium text-slate-600 whitespace-nowrap">{key.replace(/_/g, ' ')}</td>
                    <td className="py-2 text-slate-800">{String(val)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Value Ledger section */}
        {data.value_ledger_section && Object.keys(data.value_ledger_section).length > 0 && (
          <section className="mb-8">
            <h2 className="text-xl font-semibold text-slate-800 mb-3">
              {t('value.ledger_title') || 'Grand livre de valeur'}
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse">
                <tbody>
                  {Object.entries(data.value_ledger_section).map(([key, val]) => (
                    <tr key={key} className="border-b border-slate-100">
                      <td className="py-2 pr-4 font-medium text-slate-600 whitespace-nowrap">
                        {key.replace(/_/g, ' ')}
                      </td>
                      <td className="py-2 text-slate-800">{String(val)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Recommendation */}
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-slate-800 mb-3">
            {t('indispensability.recommendation') || 'Recommandation'}
          </h2>
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg print:bg-transparent print:border-red-300">
            <p className="text-sm text-slate-800 leading-relaxed">{data.recommendation}</p>
          </div>
        </section>
      </div>
    </div>
  );
}
