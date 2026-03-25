import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { rolloutApi } from '@/api/rollout';
import type { PackagePresetPreviewData } from '@/api/rollout';
import { cn } from '@/utils/formatters';
import { Loader2, CheckCircle2, XCircle, HelpCircle, Package, Share2 } from 'lucide-react';

interface PackagePresetPreviewProps {
  buildingId: string;
}

export function PackagePresetPreview({ buildingId }: PackagePresetPreviewProps) {
  const { t } = useTranslation();
  const [selectedPreset, setSelectedPreset] = useState<string>('');

  const { data: presets = [] } = useQuery({
    queryKey: ['package-presets'],
    queryFn: rolloutApi.listPresets,
  });

  const {
    data: preview,
    isLoading: previewLoading,
    isError: previewError,
  } = useQuery<PackagePresetPreviewData>({
    queryKey: ['package-preview', buildingId, selectedPreset],
    queryFn: () => rolloutApi.previewPreset(buildingId, selectedPreset),
    enabled: !!selectedPreset,
  });

  return (
    <div
      className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5"
      data-testid="package-preset-preview"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Package className="w-5 h-5 text-red-600" />
          {t('package_preset.title')}
        </h3>
      </div>

      {/* Preset selector */}
      <select
        value={selectedPreset}
        onChange={(e) => setSelectedPreset(e.target.value)}
        className="w-full px-3 py-2 mb-4 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white text-sm"
        data-testid="preset-selector"
      >
        <option value="">{t('package_preset.select')}</option>
        {presets.map((p) => (
          <option key={p.code} value={p.code}>
            {p.label}
          </option>
        ))}
      </select>

      {!selectedPreset && (
        <p className="text-xs text-gray-500 dark:text-slate-400 text-center py-4">{t('package_preset.select_hint')}</p>
      )}

      {selectedPreset && previewLoading && (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="w-6 h-6 animate-spin text-red-600" />
        </div>
      )}

      {selectedPreset && previewError && (
        <p className="text-xs text-red-500 text-center py-4">{t('app.error')}</p>
      )}

      {preview && (
        <div className="space-y-3">
          {/* Included */}
          {preview.included.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-green-700 dark:text-green-400 mb-1">
                {t('package_preset.included')}
              </h4>
              <ul className="space-y-1">
                {preview.included.map((item) => (
                  <li
                    key={item}
                    className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300"
                    data-testid="preset-included"
                  >
                    <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Excluded */}
          {preview.excluded.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                {t('package_preset.excluded')}
              </h4>
              <ul className="space-y-1">
                {preview.excluded.map((item) => (
                  <li
                    key={item}
                    className="flex items-center gap-2 text-sm text-gray-400 dark:text-slate-500"
                    data-testid="preset-excluded"
                  >
                    <XCircle className="w-4 h-4 text-gray-400 dark:text-slate-500 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Unknown */}
          {preview.unknown.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-orange-600 dark:text-orange-400 mb-1">
                {t('package_preset.unknown')}
              </h4>
              <ul className="space-y-1">
                {preview.unknown.map((item) => (
                  <li
                    key={item}
                    className={cn('flex items-center gap-2 text-sm text-orange-600 dark:text-orange-400')}
                    data-testid="preset-unknown"
                  >
                    <HelpCircle className="w-4 h-4 text-orange-500 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Generate & Share placeholder */}
          <div className="pt-3 border-t border-gray-200 dark:border-slate-700">
            <button
              className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 w-full justify-center"
              data-testid="preset-generate-share"
              onClick={() => {
                /* placeholder */
              }}
            >
              <Share2 className="w-4 h-4" />
              {t('package_preset.generate_share')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default PackagePresetPreview;
