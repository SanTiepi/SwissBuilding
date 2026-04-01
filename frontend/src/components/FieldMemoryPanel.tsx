import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fieldObservationsApi } from '@/api/fieldObservations';
import { useTranslation } from '@/i18n';
import { toast } from '@/store/toastStore';
import { FieldObservationForm } from './FieldObservationForm';
import type { FieldObservation, PatternInsight } from '@/types';

interface FieldMemoryPanelProps {
  buildingId?: string;
}

export function FieldMemoryPanel({ buildingId }: FieldMemoryPanelProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [searchTags, setSearchTags] = useState('');
  const [searchCanton, setSearchCanton] = useState('');
  const [searchPollutant, setSearchPollutant] = useState('');

  // Observations list
  const observationsQuery = useQuery({
    queryKey: ['field-observations', buildingId, searchTags, searchCanton, searchPollutant],
    queryFn: () => {
      if (buildingId && !searchTags && !searchCanton && !searchPollutant) {
        return fieldObservationsApi.list(buildingId);
      }
      return fieldObservationsApi.search({
        tags: searchTags || undefined,
        canton: searchCanton || undefined,
        pollutant: searchPollutant || undefined,
      });
    },
  });

  // Pattern insights
  const patternsQuery = useQuery({
    queryKey: ['field-memory-patterns', buildingId],
    queryFn: () => fieldObservationsApi.patterns(buildingId),
  });

  const upvoteMutation = useMutation({
    mutationFn: (id: string) => fieldObservationsApi.upvote(id),
    onSuccess: () => {
      toast(t('field_memory.upvote_success') || 'Upvoted', 'success');
      queryClient.invalidateQueries({ queryKey: ['field-observations'] });
    },
  });

  const parseTags = (tagsJson?: string): string[] => {
    if (!tagsJson) return [];
    try {
      const parsed = JSON.parse(tagsJson);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  };

  const observations: FieldObservation[] = observationsQuery.data?.items ?? [];
  const patterns: PatternInsight[] = patternsQuery.data ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('field_memory.title') || 'Collective Field Memory'}
        </h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
        >
          {showForm ? (t('common.cancel') || 'Cancel') : (t('field_memory.add_observation') || 'Add observation')}
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
          <FieldObservationForm buildingId={buildingId} onSuccess={() => setShowForm(false)} onCancel={() => setShowForm(false)} />
        </div>
      )}

      {/* Search/Filter bar */}
      <div className="flex flex-wrap gap-2">
        <input
          type="text"
          value={searchTags}
          onChange={(e) => setSearchTags(e.target.value)}
          placeholder={t('field_memory.search_tags') || 'Search tags...'}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        />
        <input
          type="text"
          value={searchCanton}
          onChange={(e) => setSearchCanton(e.target.value)}
          placeholder={t('field_memory.canton') || 'Canton'}
          className="w-20 rounded border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        />
        <select
          value={searchPollutant}
          onChange={(e) => setSearchPollutant(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        >
          <option value="">{t('field_memory.all_pollutants') || 'All pollutants'}</option>
          <option value="asbestos">Asbestos</option>
          <option value="pcb">PCB</option>
          <option value="lead">Lead</option>
          <option value="hap">HAP</option>
          <option value="radon">Radon</option>
          <option value="pfas">PFAS</option>
        </select>
      </div>

      {/* Pattern insights */}
      {patterns.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800 dark:bg-amber-900/20">
          <h3 className="mb-3 text-sm font-semibold text-amber-800 dark:text-amber-300">
            {t('field_memory.patterns') || 'Pattern Insights'}
          </h3>
          <div className="space-y-3">
            {patterns.map((p, i) => (
              <div key={i} className="rounded bg-white p-3 text-sm dark:bg-gray-800">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">{p.pattern}</p>
                    <p className="mt-1 text-gray-600 dark:text-gray-400">{p.recommendation}</p>
                  </div>
                  <div className="ml-2 flex flex-col items-end gap-1">
                    <span className="text-xs text-gray-500">{p.occurrences} obs.</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        p.confidence === 'high'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                          : p.confidence === 'medium'
                            ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                            : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                      }`}
                    >
                      {p.confidence}
                    </span>
                  </div>
                </div>
                {p.tags.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {p.tags.slice(0, 5).map((tag) => (
                      <span
                        key={tag}
                        className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Observations list */}
      {observations.length === 0 && !observationsQuery.isLoading && (
        <p className="text-center text-sm text-gray-500 dark:text-gray-400">
          {t('field_memory.empty') || 'No observations yet. Be the first to share your field knowledge.'}
        </p>
      )}

      {observationsQuery.isLoading && (
        <p className="text-center text-sm text-gray-500">{t('app.loading') || 'Loading...'}</p>
      )}

      <div className="space-y-3">
        {observations.map((obs) => {
          const obsTags = parseTags(obs.tags);
          return (
            <div
              key={obs.id}
              className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-medium text-gray-900 dark:text-white">{obs.title}</h4>
                    {obs.is_verified && (
                      <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800 dark:bg-green-900 dark:text-green-200">
                        {t('field_memory.verified') || 'Verified'}
                      </span>
                    )}
                    <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                      {obs.observation_type}
                    </span>
                    <span className="text-xs text-gray-500">{obs.confidence}</span>
                  </div>
                  {obs.description && (
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">{obs.description}</p>
                  )}
                  {obsTags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {obsTags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  {obs.observer_name && (
                    <p className="mt-1 text-xs text-gray-400">
                      {obs.observer_name} {obs.observer_role ? `(${obs.observer_role})` : ''}
                    </p>
                  )}
                </div>
                <div className="ml-4 flex flex-col items-center">
                  <button
                    onClick={() => upvoteMutation.mutate(obs.id)}
                    disabled={upvoteMutation.isPending}
                    className="flex flex-col items-center text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400"
                    title={t('field_memory.upvote') || 'Upvote'}
                  >
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                    </svg>
                    <span className="text-xs font-medium">{obs.upvotes}</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
