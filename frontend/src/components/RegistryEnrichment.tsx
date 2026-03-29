import { useState } from 'react';
import { useTranslation } from '@/i18n';
import {
  registryApi,
  type RegistryLookupResult,
  type AddressSearchResult,
  type NaturalHazardsResult,
  type EnrichmentResult,
} from '@/api/registry';

interface RegistryEnrichmentProps {
  buildingId: string;
}

const HAZARD_COLOR: Record<string, string> = {
  unknown: 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  none: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  low: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  moderate: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  high: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  erheblich: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  gross: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
};

function hazardBadgeClass(level: string | undefined): string {
  if (!level) return HAZARD_COLOR.unknown;
  return HAZARD_COLOR[level.toLowerCase()] || HAZARD_COLOR.unknown;
}

export default function RegistryEnrichment({ buildingId }: RegistryEnrichmentProps) {
  const { t } = useTranslation();

  const [egidInput, setEgidInput] = useState('');
  const [addressInput, setAddressInput] = useState('');
  const [egidResult, setEgidResult] = useState<RegistryLookupResult | null>(null);
  const [addressResults, setAddressResults] = useState<AddressSearchResult[]>([]);
  const [hazards, setHazards] = useState<NaturalHazardsResult | null>(null);
  const [enrichResult, setEnrichResult] = useState<EnrichmentResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleEgidLookup = async () => {
    const egid = parseInt(egidInput, 10);
    if (isNaN(egid)) return;
    setLoading(true);
    setError(null);
    setEgidResult(null);
    try {
      const result = await registryApi.lookupByEgid(egid);
      setEgidResult(result);
      // Also fetch hazards if coordinates are available
      if (result.coordinates) {
        const h = await registryApi.getNaturalHazards(result.coordinates.lat, result.coordinates.lng);
        setHazards(h);
      }
    } catch {
      setError(t('registry.no_results') || 'No results found');
    } finally {
      setLoading(false);
    }
  };

  const handleAddressSearch = async () => {
    if (addressInput.length < 2) return;
    setLoading(true);
    setError(null);
    setAddressResults([]);
    try {
      const results = await registryApi.searchByAddress(addressInput);
      setAddressResults(results);
    } catch {
      setError(t('registry.no_results') || 'No results found');
    } finally {
      setLoading(false);
    }
  };

  const handleEnrich = async () => {
    setEnriching(true);
    setError(null);
    setEnrichResult(null);
    try {
      const result = await registryApi.enrichBuilding(buildingId);
      setEnrichResult(result);
    } catch {
      setError(t('registry.no_results') || 'Enrichment failed');
    } finally {
      setEnriching(false);
    }
  };

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        {t('registry.title') || 'Public Registry Lookup'}
      </h3>

      {/* EGID Lookup */}
      <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
        <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
          {t('registry.lookup_egid') || 'Lookup by EGID'}
        </label>
        <div className="flex gap-2">
          <input
            type="number"
            value={egidInput}
            onChange={(e) => setEgidInput(e.target.value)}
            placeholder="e.g. 1234567"
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          />
          <button
            onClick={handleEgidLookup}
            disabled={loading || !egidInput}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
          >
            {loading ? '...' : t('registry.search_address') || 'Search'}
          </button>
        </div>

        {egidResult && (
          <div className="mt-3 rounded-md bg-gray-50 p-3 text-sm dark:bg-gray-800">
            <p className="mb-1 font-medium text-gray-900 dark:text-white">
              {t('registry.preview') || 'Preview'}
            </p>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-gray-600 dark:text-gray-400">
              {egidResult.address && (
                <>
                  <dt className="font-medium">Address</dt>
                  <dd>{egidResult.address}</dd>
                </>
              )}
              {egidResult.city && (
                <>
                  <dt className="font-medium">City</dt>
                  <dd>
                    {egidResult.postal_code} {egidResult.city}
                  </dd>
                </>
              )}
              {egidResult.canton && (
                <>
                  <dt className="font-medium">Canton</dt>
                  <dd>{egidResult.canton}</dd>
                </>
              )}
              {egidResult.construction_year && (
                <>
                  <dt className="font-medium">Year</dt>
                  <dd>{egidResult.construction_year}</dd>
                </>
              )}
              {egidResult.floors && (
                <>
                  <dt className="font-medium">Floors</dt>
                  <dd>{egidResult.floors}</dd>
                </>
              )}
              {egidResult.heating_type && (
                <>
                  <dt className="font-medium">Heating</dt>
                  <dd>{egidResult.heating_type}</dd>
                </>
              )}
            </dl>
            <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
              {t('registry.source_attribution') || 'Data from RegBL / Swisstopo'}
            </p>
          </div>
        )}
      </div>

      {/* Address Search */}
      <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
        <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
          {t('registry.search_address') || 'Search by Address'}
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={addressInput}
            onChange={(e) => setAddressInput(e.target.value)}
            placeholder="Rue du Midi 15, Lausanne"
            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          />
          <button
            onClick={handleAddressSearch}
            disabled={loading || addressInput.length < 2}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
          >
            {loading ? '...' : t('registry.search_address') || 'Search'}
          </button>
        </div>

        {addressResults.length > 0 && (
          <ul className="mt-3 divide-y divide-gray-200 rounded-md border border-gray-200 dark:divide-gray-700 dark:border-gray-700">
            {addressResults.map((r, i) => (
              <li key={i} className="px-3 py-2 text-sm text-gray-700 dark:text-gray-300">
                <span>{r.address}</span>
                {r.egid && (
                  <span className="ml-2 text-xs text-gray-400 dark:text-gray-500">
                    EGID: {r.egid}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Natural Hazards */}
      {hazards && (
        <div className="rounded-lg border border-gray-200 p-4 dark:border-gray-700">
          <h4 className="mb-2 text-sm font-medium text-gray-700 dark:text-gray-300">
            {t('registry.hazards') || 'Natural Hazards'}
          </h4>
          <div className="grid grid-cols-2 gap-2">
            {[
              { key: 'flood_risk', label: t('registry.flood_risk') || 'Flood', data: hazards.flood_risk },
              {
                key: 'landslide_risk',
                label: t('registry.landslide_risk') || 'Landslide',
                data: hazards.landslide_risk,
              },
              {
                key: 'avalanche_risk',
                label: t('registry.avalanche_risk') || 'Avalanche',
                data: hazards.avalanche_risk,
              },
              {
                key: 'earthquake_zone',
                label: t('registry.earthquake_zone') || 'Earthquake',
                data: hazards.earthquake_risk,
              },
            ].map(({ key, label, data }) => (
              <div key={key} className="flex items-center gap-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">{label}:</span>
                <span
                  className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${hazardBadgeClass(data?.level)}`}
                >
                  {data?.level || 'N/A'}
                </span>
              </div>
            ))}
          </div>
          <p className="mt-2 text-xs text-gray-400 dark:text-gray-500">
            {t('registry.source_attribution') || 'Data from RegBL / Swisstopo'}
          </p>
        </div>
      )}

      {/* Enrich button */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleEnrich}
          disabled={enriching}
          className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50 dark:bg-green-500 dark:hover:bg-green-600"
        >
          {enriching
            ? t('registry.enriching') || 'Enriching...'
            : t('registry.enrich') || 'Auto-fill from public registries'}
        </button>

        {enrichResult && (
          <span className="text-sm text-green-600 dark:text-green-400">
            {t('registry.enriched') || 'Enrichment complete'} —{' '}
            {Object.keys(enrichResult.updated_fields).length} fields updated
          </span>
        )}
      </div>

      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}
