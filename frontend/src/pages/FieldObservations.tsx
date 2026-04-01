/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view under BuildingDetail (Building Home).
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { fieldObservationsApi } from '@/api/fieldObservations';
import type { FieldObservation, FieldObservationCreate, ObservationType, ObservationSeverity } from '@/types';
import {
  Loader2,
  Plus,
  ClipboardCheck,
  Eye,
  ShieldCheck,
  ShieldOff,
  X,
  ArrowLeft,
  AlertTriangle,
  Info,
  CheckCircle2,
} from 'lucide-react';
import { cn } from '@/utils/formatters';
import { BuildingSubNav } from '@/components/BuildingSubNav';

const observationTypes: ObservationType[] = [
  'visual_inspection',
  'safety_hazard',
  'material_condition',
  'general_note',
];

const severityLevels: ObservationSeverity[] = ['info', 'minor', 'moderate', 'major', 'critical'];

const severityColors: Record<string, string> = {
  info: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  minor: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  moderate: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  major: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const typeColors: Record<string, string> = {
  visual_inspection: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  safety_hazard: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  material_condition: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  general_note: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
};

export default function FieldObservations() {
  const { buildingId } = useParams<{ buildingId: string }>();
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [typeFilter, setTypeFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const pageSize = 20;

  const {
    data: observationsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['field-observations', buildingId, typeFilter, severityFilter, page],
    queryFn: () =>
      fieldObservationsApi.list(buildingId!, {
        observation_type: typeFilter || undefined,
        severity: severityFilter || undefined,
        page,
        size: pageSize,
      }),
    enabled: !!buildingId,
  });

  const { data: summary } = useQuery({
    queryKey: ['field-observations-summary', buildingId],
    queryFn: () => fieldObservationsApi.summary(buildingId!),
    enabled: !!buildingId,
  });

  const createMutation = useMutation({
    mutationFn: (data: FieldObservationCreate) => fieldObservationsApi.create(buildingId!, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['field-observations', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['field-observations-summary', buildingId] });
      setShowCreateModal(false);
    },
  });

  const verifyMutation = useMutation({
    mutationFn: ({ id, verified }: { id: string; verified: boolean }) => fieldObservationsApi.verify(id, { verified }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['field-observations', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['field-observations-summary', buildingId] });
    },
  });

  const observations = observationsData?.items ?? [];
  const totalPages = observationsData ? Math.ceil(observationsData.total / pageSize) : 0;

  const formatDate = (dateStr: string | undefined | null) => {
    if (!dateStr) return '\u2014';
    try {
      return new Date(dateStr).toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  if (error) {
    return (
      <div className="flex items-center justify-center p-8">
        <p className="text-red-600 dark:text-red-400">{t('app.error')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            to={`/buildings/${buildingId}`}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <ClipboardCheck className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('field_observations.title')}</h1>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          data-testid="field-observations-create-button"
          className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          <Plus className="h-4 w-4" />
          {t('field_observations.create')}
        </button>
      </div>

      <BuildingSubNav buildingId={buildingId!} />

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('field_observations.total')}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{summary.total_observations}</p>
          </div>
          <div
            className={cn(
              'rounded-xl border p-4',
              summary.unverified_count > 0
                ? 'border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-900/20'
                : 'border-gray-200 bg-white dark:border-slate-700 dark:bg-slate-800',
            )}
          >
            <p className="flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400">
              {summary.unverified_count > 0 && <AlertTriangle className="h-3 w-3 text-amber-500" />}
              {t('field_observations.unverified_count')}
            </p>
            <p
              className={cn(
                'mt-1 text-2xl font-bold',
                summary.unverified_count > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-gray-900 dark:text-white',
              )}
            >
              {summary.unverified_count}
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <p className="text-xs text-gray-500 dark:text-slate-400">
              {t('field_observations.severity_major')} / {t('field_observations.severity_critical')}
            </p>
            <p className="mt-1 text-2xl font-bold text-red-600 dark:text-red-400">
              {(summary.by_severity['major'] ?? 0) + (summary.by_severity['critical'] ?? 0)}
            </p>
          </div>
          <div className="rounded-xl border border-gray-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('field_observations.type_safety_hazard')}</p>
            <p className="mt-1 text-2xl font-bold text-orange-600 dark:text-orange-400">
              {summary.by_type['safety_hazard'] ?? 0}
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        >
          <option value="">
            {t('field_observations.observation_type')}: {t('common.all')}
          </option>
          {observationTypes.map((ot) => (
            <option key={ot} value={ot}>
              {t(`field_observations.type_${ot}`)}
            </option>
          ))}
        </select>
        <select
          value={severityFilter}
          onChange={(e) => {
            setSeverityFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        >
          <option value="">
            {t('field_observations.severity')}: {t('common.all')}
          </option>
          {severityLevels.map((s) => (
            <option key={s} value={s}>
              {t(`field_observations.severity_${s}`)}
            </option>
          ))}
        </select>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center p-12">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
        </div>
      ) : observations.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center dark:border-gray-600">
          <ClipboardCheck className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
            {t('field_observations.no_observations')}
          </h3>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {observations.map((obs) => (
              <ObservationCard
                key={obs.id}
                observation={obs}
                t={t}
                onVerify={(verified) => verifyMutation.mutate({ id: obs.id, verified })}
                isVerifying={verifyMutation.isPending}
                formatDate={formatDate}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                {t('common.previous')}
              </button>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                {t('common.next')}
              </button>
            </div>
          )}
        </>
      )}

      {/* Create Modal */}
      {showCreateModal && buildingId && (
        <CreateObservationModal
          buildingId={buildingId}
          onClose={() => setShowCreateModal(false)}
          onSubmit={(data) => createMutation.mutate(data)}
          isSubmitting={createMutation.isPending}
          t={t}
        />
      )}
    </div>
  );
}

function ObservationCard({
  observation,
  t,
  onVerify,
  isVerifying,
  formatDate,
}: {
  observation: FieldObservation;
  t: (key: string) => string;
  onVerify: (verified: boolean) => void;
  isVerifying: boolean;
  formatDate: (dateStr: string | undefined | null) => string;
}) {
  const [showConfirm, setShowConfirm] = useState(false);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-start justify-between">
        <h3 className="font-semibold text-gray-900 dark:text-white">{observation.title}</h3>
        <div className="flex items-center gap-1">
          <span
            className={cn('rounded-full px-2 py-0.5 text-xs font-medium', typeColors[observation.observation_type])}
          >
            {t(`field_observations.type_${observation.observation_type}`)}
          </span>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-2">
        <span className={cn('rounded-full px-2 py-0.5 text-xs font-medium', severityColors[observation.severity])}>
          {t(`field_observations.severity_${observation.severity}`)}
        </span>
        {observation.verified ? (
          <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
            <CheckCircle2 className="h-3 w-3" />
            {t('field_observations.verified')}
          </span>
        ) : (
          <span className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
            <Info className="h-3 w-3" />
            {t('field_observations.unverified')}
          </span>
        )}
      </div>

      {observation.description && (
        <p className="mt-2 text-sm text-gray-600 line-clamp-2 dark:text-gray-400">{observation.description}</p>
      )}

      {observation.location_description && (
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          {t('field_observations.location')}: {observation.location_description}
        </p>
      )}

      <div className="mt-3 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <div className="flex items-center gap-3">
          {observation.observer_name && (
            <span className="flex items-center gap-1">
              <Eye className="h-3 w-3" />
              {observation.observer_name}
            </span>
          )}
          <span>{formatDate(observation.observed_at)}</span>
        </div>

        {!showConfirm ? (
          <button
            onClick={() => setShowConfirm(true)}
            className={cn(
              'inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium transition',
              observation.verified
                ? 'text-amber-600 hover:bg-amber-50 dark:text-amber-400 dark:hover:bg-amber-900/20'
                : 'text-green-600 hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-900/20',
            )}
          >
            {observation.verified ? (
              <>
                <ShieldOff className="h-3 w-3" />
                {t('field_observations.unverify')}
              </>
            ) : (
              <>
                <ShieldCheck className="h-3 w-3" />
                {t('field_observations.verify')}
              </>
            )}
          </button>
        ) : (
          <div className="flex items-center gap-1">
            <button
              onClick={() => {
                onVerify(!observation.verified);
                setShowConfirm(false);
              }}
              disabled={isVerifying}
              className="rounded bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {t('form.confirm')}
            </button>
            <button
              onClick={() => setShowConfirm(false)}
              className="rounded px-2 py-1 text-xs text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function CreateObservationModal({
  buildingId,
  onClose,
  onSubmit,
  isSubmitting,
  t,
}: {
  buildingId: string;
  onClose: () => void;
  onSubmit: (data: FieldObservationCreate) => void;
  isSubmitting: boolean;
  t: (key: string) => string;
}) {
  const [title, setTitle] = useState('');
  const [observationType, setObservationType] = useState<ObservationType>('visual_inspection');
  const [severity, setSeverity] = useState<ObservationSeverity>('info');
  const [description, setDescription] = useState('');
  const [locationDescription, setLocationDescription] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    onSubmit({
      building_id: buildingId,
      observation_type: observationType,
      severity,
      title: title.trim(),
      description: description.trim() || undefined,
      location_description: locationDescription.trim() || undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        data-testid="field-observations-create-modal"
        className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('field_observations.create')}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('field_observations.title')}
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              data-testid="field-observations-form-title"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('field_observations.observation_type')}
              </label>
              <select
                value={observationType}
                onChange={(e) => setObservationType(e.target.value as ObservationType)}
                data-testid="field-observations-form-type"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                {observationTypes.map((ot) => (
                  <option key={ot} value={ot}>
                    {t(`field_observations.type_${ot}`)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('field_observations.severity')}
              </label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value as ObservationSeverity)}
                data-testid="field-observations-form-severity"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                {severityLevels.map((s) => (
                  <option key={s} value={s}>
                    {t(`field_observations.severity_${s}`)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('field_observations.description')}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              data-testid="field-observations-form-description"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('field_observations.location')}
            </label>
            <input
              type="text"
              value={locationDescription}
              onChange={(e) => setLocationDescription(e.target.value)}
              data-testid="field-observations-form-location"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
            >
              {t('form.cancel')}
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !title.trim()}
              data-testid="field-observations-form-submit"
              className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {isSubmitting && <Loader2 className="mr-1 inline h-4 w-4 animate-spin" />}
              {t('field_observations.create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
