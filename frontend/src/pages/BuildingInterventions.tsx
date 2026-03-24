import { useState, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/store/authStore';
import { interventionsApi } from '@/api/interventions';
import { materialRecommendationsApi } from '@/api/materialRecommendations';
import { MaterialRecommendationsCard } from '@/components/building-detail/MaterialRecommendationsCard';
import { toast } from '@/store/toastStore';
import { RoleGate } from '@/components/RoleGate';
import type { Intervention, InterventionType, InterventionStatus } from '@/types';
import {
  ArrowLeft,
  Plus,
  Loader2,
  Wrench,
  Calendar,
  DollarSign,
  Pencil,
  Trash2,
  ChevronDown,
  ChevronUp,
  Play,
  CheckCircle2,
  XCircle,
  X,
} from 'lucide-react';
import { BuildingSubNav } from '@/components/BuildingSubNav';

const STATUS_FILTERS: Array<InterventionStatus | 'all'> = ['all', 'planned', 'in_progress', 'completed', 'cancelled'];
const INTERVENTION_TYPES: InterventionType[] = [
  'renovation',
  'maintenance',
  'repair',
  'demolition',
  'installation',
  'inspection',
  'diagnostic',
  'asbestos_removal',
  'decontamination',
  'other',
];

const STATUS_COLORS: Record<InterventionStatus, string> = {
  planned: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  in_progress: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  cancelled: 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
};

interface EditFormState {
  title: string;
  intervention_type: InterventionType;
  description: string;
  status: InterventionStatus;
  date_start: string;
  date_end: string;
  cost_chf: string;
  contractor_name: string;
  notes: string;
}

function initEditForm(iv: Intervention): EditFormState {
  return {
    title: iv.title,
    intervention_type: iv.intervention_type,
    description: iv.description ?? '',
    status: iv.status,
    date_start: iv.date_start?.slice(0, 10) ?? '',
    date_end: iv.date_end?.slice(0, 10) ?? '',
    cost_chf: iv.cost_chf != null ? String(iv.cost_chf) : '',
    contractor_name: iv.contractor_name ?? '',
    notes: iv.notes ?? '',
  };
}

export default function BuildingInterventions() {
  const { t } = useTranslation();
  const { buildingId } = useParams<{ buildingId: string }>();
  useAuth();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState<InterventionStatus | 'all'>('all');
  const [page, setPage] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditFormState | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Create form state
  const [title, setTitle] = useState('');
  const [interventionType, setInterventionType] = useState<InterventionType>('renovation');
  const [dateStart, setDateStart] = useState('');
  const [costChf, setCostChf] = useState('');
  const [description, setDescription] = useState('');

  const canEdit = user?.role === 'admin' || user?.role === 'diagnostician';

  const { data, isLoading, isError } = useQuery({
    queryKey: ['interventions', buildingId, statusFilter, page],
    queryFn: () =>
      interventionsApi.list(buildingId!, {
        status: statusFilter === 'all' ? undefined : statusFilter,
        page,
        size: 20,
      }),
    enabled: !!buildingId,
  });

  const { data: recData } = useQuery({
    queryKey: ['material-recommendations', buildingId],
    queryFn: () => materialRecommendationsApi.get(buildingId!),
    enabled: !!buildingId,
  });

  const interventions = useMemo(() => data?.items ?? [], [data?.items]);
  const totalPages = data?.pages ?? 1;

  // Cost summary
  const costSummary = useMemo(() => {
    const summary = { total: 0, planned: 0, in_progress: 0, completed: 0, cancelled: 0 };
    for (const iv of interventions) {
      const cost = iv.cost_chf ?? 0;
      summary.total += cost;
      summary[iv.status] += cost;
    }
    return summary;
  }, [interventions]);

  const createIntervention = useMutation({
    mutationFn: (payload: Partial<Intervention>) => interventionsApi.create(buildingId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['interventions', buildingId] });
      toast(t('intervention.created') || 'Intervention created', 'success');
      setShowForm(false);
      setTitle('');
      setDescription('');
      setDateStart('');
      setCostChf('');
    },
    onError: (err: any) =>
      toast(err?.response?.data?.detail || t('intervention.create_error') || 'Error creating intervention', 'error'),
  });

  const updateIntervention = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<Intervention> }) =>
      interventionsApi.update(buildingId!, id, payload),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['interventions', buildingId] });
      // If it was a status-only change, show status toast; otherwise show updated toast
      const isStatusOnly = Object.keys(variables.payload).length === 1 && variables.payload.status !== undefined;
      toast(
        isStatusOnly
          ? t('intervention.status_change_success') || 'Status updated'
          : t('intervention.updated') || 'Intervention updated',
        'success',
      );
      setEditingId(null);
      setEditForm(null);
    },
    onError: (err: any) =>
      toast(err?.response?.data?.detail || t('intervention.update_error') || 'Error updating intervention', 'error'),
  });

  const deleteIntervention = useMutation({
    mutationFn: (id: string) => interventionsApi.delete(buildingId!, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['interventions', buildingId] });
      toast(t('intervention.deleted') || 'Intervention deleted', 'success');
      setDeleteConfirmId(null);
    },
    onError: (err: any) =>
      toast(err?.response?.data?.detail || t('intervention.delete_error') || 'Error deleting intervention', 'error'),
  });

  const handleCreate = () => {
    createIntervention.mutate({
      title,
      intervention_type: interventionType,
      status: 'planned',
      date_start: dateStart || null,
      cost_chf: costChf ? Number(costChf) : null,
      description: description || null,
    });
  };

  const handleEditSave = () => {
    if (!editForm || !editingId) return;
    updateIntervention.mutate({
      id: editingId,
      payload: {
        title: editForm.title,
        intervention_type: editForm.intervention_type,
        description: editForm.description || null,
        status: editForm.status,
        date_start: editForm.date_start || null,
        date_end: editForm.date_end || null,
        cost_chf: editForm.cost_chf ? Number(editForm.cost_chf) : null,
        contractor_name: editForm.contractor_name || null,
        notes: editForm.notes || null,
      },
    });
  };

  const handleStatusChange = (id: string, newStatus: InterventionStatus) => {
    updateIntervention.mutate({ id, payload: { status: newStatus } });
  };

  const handleDeleteClick = (id: string) => {
    if (deleteConfirmId === id) {
      deleteIntervention.mutate(id);
    } else {
      setDeleteConfirmId(id);
    }
  };

  const openEdit = (iv: Intervention) => {
    setEditingId(iv.id);
    setEditForm(initEditForm(iv));
    setExpandedId(null);
  };

  const closeEdit = () => {
    setEditingId(null);
    setEditForm(null);
  };

  const formatDate = (d: string | null) => {
    if (!d) return '\u2014';
    return new Date(d).toLocaleDateString('fr-CH');
  };

  const formatCost = (n: number) => n.toLocaleString('fr-CH') + ' CHF';

  const inputClass =
    'px-3 py-2 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white rounded focus:ring-1 focus:ring-red-500 focus:border-red-500';

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-950">
      {/* Header */}
      <div className="bg-white dark:bg-slate-900 border-b border-gray-200 dark:border-slate-800 px-6 py-4">
        <div className="flex items-center gap-4">
          <Link
            to={`/buildings/${buildingId}`}
            className="text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">
            {t('intervention.title') || 'Interventions'}
          </h1>
        </div>
        <div className="mt-3">
          <BuildingSubNav buildingId={buildingId!} />
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-6 space-y-6">
        {/* Cost summary bar */}
        {interventions.length > 0 && costSummary.total > 0 && (
          <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg p-4">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-3">
              {t('intervention.cost_summary') || 'Cost Summary'}
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  {t('intervention.total_cost') || 'Total Cost'}
                </p>
                <p className="text-lg font-bold text-gray-900 dark:text-white">{formatCost(costSummary.total)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  {t('intervention.planned_cost') || 'Planned Cost'}
                </p>
                <p className="text-lg font-semibold text-blue-600 dark:text-blue-400">
                  {formatCost(costSummary.planned)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  {t('intervention.in_progress_cost') || 'In Progress Cost'}
                </p>
                <p className="text-lg font-semibold text-yellow-600 dark:text-yellow-400">
                  {formatCost(costSummary.in_progress)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  {t('intervention.completed_cost') || 'Completed Cost'}
                </p>
                <p className="text-lg font-semibold text-green-600 dark:text-green-400">
                  {formatCost(costSummary.completed)}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Material recommendations */}
        {recData && recData.recommendations.length > 0 && (
          <MaterialRecommendationsCard recommendations={recData.recommendations} />
        )}

        {/* Toolbar */}
        <div className="flex items-center justify-between">
          <div className="flex gap-2">
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setStatusFilter(s);
                  setPage(1);
                }}
                className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                  statusFilter === s
                    ? 'bg-red-600 text-white border-red-600'
                    : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-slate-300 border-gray-300 dark:border-slate-700 hover:border-gray-400 dark:hover:border-slate-500'
                }`}
              >
                {s === 'all' ? t('common.all') || 'All' : t(`intervention.status.${s}`) || s}
              </button>
            ))}
          </div>
          <RoleGate allowedRoles={['admin', 'diagnostician']}>
            <button
              onClick={() => setShowForm(!showForm)}
              data-testid="interventions-create-toggle"
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
            >
              <Plus className="w-4 h-4" />
              {t('intervention.add') || 'New Intervention'}
            </button>
          </RoleGate>
        </div>

        {/* Create form */}
        {showForm && (
          <div
            data-testid="interventions-create-form"
            className="bg-white dark:bg-slate-900 p-4 border border-gray-200 dark:border-slate-800 rounded-lg space-y-3"
          >
            <div className="grid grid-cols-2 gap-3">
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={t('intervention.field.title') || 'Title'}
                data-testid="interventions-form-title"
                className={inputClass}
              />
              <select
                value={interventionType}
                onChange={(e) => setInterventionType(e.target.value as InterventionType)}
                data-testid="interventions-form-type"
                className={inputClass}
              >
                {INTERVENTION_TYPES.map((it) => (
                  <option key={it} value={it}>
                    {t(`intervention.type.${it}`) || it}
                  </option>
                ))}
              </select>
              <input
                type="date"
                value={dateStart}
                onChange={(e) => setDateStart(e.target.value)}
                data-testid="interventions-form-date-start"
                className={inputClass}
              />
              <input
                type="number"
                value={costChf}
                onChange={(e) => setCostChf(e.target.value)}
                placeholder={t('intervention.field.cost') || 'Cost CHF'}
                data-testid="interventions-form-cost"
                className={inputClass}
              />
            </div>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder={t('intervention.field.description') || 'Description'}
              data-testid="interventions-form-description"
              className={`w-full ${inputClass} resize-none`}
              rows={2}
            />
            <button
              onClick={handleCreate}
              disabled={!title.trim() || createIntervention.isPending}
              data-testid="interventions-form-submit"
              className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
            >
              {createIntervention.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                t('intervention.create') || 'Create'
              )}
            </button>
          </div>
        )}

        {/* Edit modal */}
        {editingId && editForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-xl shadow-xl w-full max-w-lg mx-4 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                  {t('intervention.edit') || 'Edit Intervention'}
                </h2>
                <button onClick={closeEdit} className="text-gray-400 hover:text-gray-600 dark:hover:text-slate-200">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <input
                  type="text"
                  value={editForm.title}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  placeholder={t('intervention.field.title') || 'Title'}
                  className={inputClass}
                />
                <select
                  value={editForm.intervention_type}
                  onChange={(e) => setEditForm({ ...editForm, intervention_type: e.target.value as InterventionType })}
                  className={inputClass}
                >
                  {INTERVENTION_TYPES.map((it) => (
                    <option key={it} value={it}>
                      {t(`intervention.type.${it}`) || it}
                    </option>
                  ))}
                </select>
                <select
                  value={editForm.status}
                  onChange={(e) => setEditForm({ ...editForm, status: e.target.value as InterventionStatus })}
                  className={inputClass}
                >
                  {(['planned', 'in_progress', 'completed', 'cancelled'] as InterventionStatus[]).map((s) => (
                    <option key={s} value={s}>
                      {t(`intervention.status.${s}`) || s}
                    </option>
                  ))}
                </select>
                <input
                  type="date"
                  value={editForm.date_start}
                  onChange={(e) => setEditForm({ ...editForm, date_start: e.target.value })}
                  placeholder={t('intervention.field.date_start') || 'Start date'}
                  className={inputClass}
                />
                <input
                  type="date"
                  value={editForm.date_end}
                  onChange={(e) => setEditForm({ ...editForm, date_end: e.target.value })}
                  placeholder={t('intervention.field.date_end') || 'End date'}
                  className={inputClass}
                />
                <input
                  type="number"
                  value={editForm.cost_chf}
                  onChange={(e) => setEditForm({ ...editForm, cost_chf: e.target.value })}
                  placeholder={t('intervention.field.cost') || 'Cost CHF'}
                  className={inputClass}
                />
                <input
                  type="text"
                  value={editForm.contractor_name}
                  onChange={(e) => setEditForm({ ...editForm, contractor_name: e.target.value })}
                  placeholder={t('intervention.field.contractor_name') || 'Contractor name'}
                  className="col-span-2 px-3 py-2 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white rounded focus:ring-1 focus:ring-red-500 focus:border-red-500"
                />
              </div>
              <textarea
                value={editForm.description}
                onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                placeholder={t('intervention.field.description') || 'Description'}
                className={`w-full ${inputClass} resize-none`}
                rows={2}
              />
              <textarea
                value={editForm.notes}
                onChange={(e) => setEditForm({ ...editForm, notes: e.target.value })}
                placeholder={t('intervention.field.notes') || 'Notes'}
                className={`w-full ${inputClass} resize-none`}
                rows={2}
              />

              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={closeEdit}
                  className="px-4 py-2 text-sm border border-gray-300 dark:border-slate-700 text-gray-700 dark:text-slate-300 rounded hover:bg-gray-50 dark:hover:bg-slate-800"
                >
                  {t('intervention.cancel_edit') || 'Cancel'}
                </button>
                <button
                  onClick={handleEditSave}
                  disabled={!editForm.title.trim() || updateIntervention.isPending}
                  className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                >
                  {updateIntervention.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    t('intervention.save') || 'Save'
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* List */}
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400 dark:text-slate-500" />
          </div>
        ) : isError ? (
          <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
            <p className="text-red-700 dark:text-red-300">{t('app.error') || 'An error occurred'}</p>
          </div>
        ) : interventions.length === 0 ? (
          <div className="text-center py-16 text-gray-400 dark:text-slate-500">
            <Wrench className="w-10 h-10 mx-auto mb-3" />
            <p className="text-sm">{t('intervention.empty') || 'No interventions found.'}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {interventions.map((iv) => {
              const isExpanded = expandedId === iv.id;

              return (
                <div
                  key={iv.id}
                  className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg overflow-hidden"
                >
                  <div className="p-4 flex items-start gap-4">
                    <Wrench className="w-5 h-5 text-gray-400 dark:text-slate-500 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <button
                          onClick={() => setExpandedId(isExpanded ? null : iv.id)}
                          className="font-medium text-sm text-gray-900 dark:text-white hover:text-red-600 dark:hover:text-red-400 text-left"
                        >
                          {iv.title}
                        </button>
                        <span
                          className={`px-2 py-0.5 text-[10px] font-semibold rounded-full ${STATUS_COLORS[iv.status]}`}
                        >
                          {t(`intervention.status.${iv.status}`) || iv.status}
                        </span>
                        <span className="px-2 py-0.5 text-[10px] font-medium rounded-full bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-slate-300">
                          {t(`intervention.type.${iv.intervention_type}`) || iv.intervention_type}
                        </span>
                        <button
                          onClick={() => setExpandedId(isExpanded ? null : iv.id)}
                          className="ml-auto text-gray-400 hover:text-gray-600 dark:hover:text-slate-300"
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </button>
                      </div>
                      {iv.description && (
                        <p className="text-xs text-gray-500 dark:text-slate-400 mb-2 line-clamp-2">{iv.description}</p>
                      )}
                      <div className="flex items-center gap-4 text-xs text-gray-400 dark:text-slate-500">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {formatDate(iv.date_start)}
                          {iv.date_end && ` \u2192 ${formatDate(iv.date_end)}`}
                        </span>
                        {iv.cost_chf != null && (
                          <span className="flex items-center gap-1">
                            <DollarSign className="w-3 h-3" />
                            {formatCost(iv.cost_chf)}
                          </span>
                        )}
                        {iv.contractor_name && <span>{iv.contractor_name}</span>}
                      </div>

                      {/* Action buttons row */}
                      <div className="flex items-center gap-2 mt-3">
                        {/* Status transition buttons */}
                        {iv.status === 'planned' && canEdit && (
                          <button
                            onClick={() => handleStatusChange(iv.id, 'in_progress')}
                            disabled={updateIntervention.isPending}
                            className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded hover:bg-blue-100 dark:hover:bg-blue-900/30 disabled:opacity-50"
                          >
                            <Play className="w-3 h-3" />
                            {t('intervention.start') || 'Start'}
                          </button>
                        )}
                        {iv.status === 'in_progress' && canEdit && (
                          <>
                            <button
                              onClick={() => handleStatusChange(iv.id, 'completed')}
                              disabled={updateIntervention.isPending}
                              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded hover:bg-green-100 dark:hover:bg-green-900/30 disabled:opacity-50"
                            >
                              <CheckCircle2 className="w-3 h-3" />
                              {t('intervention.complete') || 'Complete'}
                            </button>
                            <button
                              onClick={() => handleStatusChange(iv.id, 'cancelled')}
                              disabled={updateIntervention.isPending}
                              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-slate-400 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded hover:bg-gray-100 dark:hover:bg-slate-700 disabled:opacity-50"
                            >
                              <XCircle className="w-3 h-3" />
                              {t('intervention.cancel_intervention') || 'Cancel'}
                            </button>
                          </>
                        )}

                        {/* Edit / Delete buttons */}
                        {canEdit && (
                          <>
                            <button
                              onClick={() => openEdit(iv)}
                              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-gray-600 dark:text-slate-400 bg-gray-50 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded hover:bg-gray-100 dark:hover:bg-slate-700"
                            >
                              <Pencil className="w-3 h-3" />
                              {t('intervention.edit') || 'Edit'}
                            </button>
                            <RoleGate allowedRoles={['admin', 'diagnostician']}>
                              <button
                                onClick={() => handleDeleteClick(iv.id)}
                                onBlur={() => {
                                  if (deleteConfirmId === iv.id) setDeleteConfirmId(null);
                                }}
                                disabled={deleteIntervention.isPending}
                                className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border disabled:opacity-50 ${
                                  deleteConfirmId === iv.id
                                    ? 'text-white bg-red-600 border-red-600 hover:bg-red-700'
                                    : 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/30'
                                }`}
                              >
                                <Trash2 className="w-3 h-3" />
                                {deleteConfirmId === iv.id
                                  ? t('intervention.confirm_delete') || 'Click again to confirm'
                                  : t('intervention.delete') || 'Delete'}
                              </button>
                            </RoleGate>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Expanded detail panel */}
                  {isExpanded && (
                    <div className="border-t border-gray-200 dark:border-slate-800 px-4 py-4 bg-gray-50 dark:bg-slate-950/50">
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-sm">
                        <div>
                          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                            {t('intervention.status') || 'Status'}
                          </p>
                          <span
                            className={`inline-block px-2 py-0.5 text-xs font-semibold rounded-full ${STATUS_COLORS[iv.status]}`}
                          >
                            {t(`intervention.status.${iv.status}`) || iv.status}
                          </span>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                            {t('intervention.type') || 'Type'}
                          </p>
                          <p className="text-gray-900 dark:text-white">
                            {t(`intervention.type.${iv.intervention_type}`) || iv.intervention_type}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                            {t('intervention.date_range') || 'Date Range'}
                          </p>
                          <p className="text-gray-900 dark:text-white">
                            {formatDate(iv.date_start)}
                            {iv.date_end ? ` \u2192 ${formatDate(iv.date_end)}` : ''}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                            {t('intervention.cost') || 'Cost (CHF)'}
                          </p>
                          <p className="text-gray-900 dark:text-white">
                            {iv.cost_chf != null ? formatCost(iv.cost_chf) : '\u2014'}
                          </p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                            {t('intervention.contractor') || 'Contractor'}
                          </p>
                          <p className="text-gray-900 dark:text-white">{iv.contractor_name || '\u2014'}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                            {t('intervention.created_at') || 'Created on'}
                          </p>
                          <p className="text-gray-900 dark:text-white">{formatDate(iv.created_at)}</p>
                        </div>
                      </div>
                      {iv.description && (
                        <div className="mt-4">
                          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                            {t('intervention.field.description') || 'Description'}
                          </p>
                          <p className="text-sm text-gray-700 dark:text-slate-300 whitespace-pre-wrap">
                            {iv.description}
                          </p>
                        </div>
                      )}
                      {iv.notes && (
                        <div className="mt-3">
                          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                            {t('intervention.notes') || 'Notes'}
                          </p>
                          <p className="text-sm text-gray-700 dark:text-slate-300 whitespace-pre-wrap">{iv.notes}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="px-3 py-1 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 rounded disabled:opacity-50"
            >
              {t('common.previous') || 'Previous'}
            </button>
            <span className="text-sm text-gray-500 dark:text-slate-400">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="px-3 py-1 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 rounded disabled:opacity-50"
            >
              {t('common.next') || 'Next'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
