import { useState, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuth } from '@/hooks/useAuth';
import { plansApi } from '@/api/plans';
import { toast } from '@/store/toastStore';
import { RoleGate } from '@/components/RoleGate';
import { cn } from '@/utils/formatters';
import { BuildingSubNav } from '@/components/BuildingSubNav';
import type { PlanType, PlanAnnotationType, PlanAnnotationCreate, TechnicalPlan } from '@/types';
import {
  ArrowLeft,
  Upload,
  Loader2,
  FileImage,
  Download,
  Trash2,
  Eye,
  Plus,
  Pencil,
  X,
  MapPin,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';

const PLAN_TYPES: PlanType[] = [
  'floor_plan',
  'cross_section',
  'elevation',
  'technical_schema',
  'site_plan',
  'detail',
  'annotation',
  'other',
];

const ANNOTATION_TYPES: PlanAnnotationType[] = [
  'marker',
  'zone_reference',
  'sample_location',
  'observation',
  'hazard_zone',
  'measurement_point',
];

const annotationTypeColors: Record<PlanAnnotationType, string> = {
  marker: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  zone_reference: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  sample_location: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  observation: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  hazard_zone: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  measurement_point: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
};

interface AnnotationFormData {
  annotation_type: PlanAnnotationType;
  label: string;
  x: string;
  y: string;
  description: string;
  color: string;
}

const emptyForm: AnnotationFormData = {
  annotation_type: 'marker',
  label: '',
  x: '0.5',
  y: '0.5',
  description: '',
  color: '#ef4444',
};

function AnnotationPanel({ plan, buildingId }: { plan: TechnicalPlan; buildingId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [annotationTypeFilter, setAnnotationTypeFilter] = useState<PlanAnnotationType | ''>('');
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [form, setForm] = useState<AnnotationFormData>(emptyForm);

  const queryKey = ['plan-annotations', buildingId, plan.id, annotationTypeFilter];

  const { data: annotations, isLoading } = useQuery({
    queryKey,
    queryFn: () => plansApi.listAnnotations(buildingId, plan.id, annotationTypeFilter || undefined),
  });

  const createAnnotation = useMutation({
    mutationFn: (data: PlanAnnotationCreate) => plansApi.createAnnotation(buildingId, plan.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plan-annotations', buildingId, plan.id] });
      toast(t('plan.annotations.save') || 'Saved', 'success');
      resetForm();
    },
    onError: (err: any) => toast(err?.response?.data?.detail || 'Error', 'error'),
  });

  const updateAnnotation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<PlanAnnotationCreate> }) =>
      plansApi.updateAnnotation(buildingId, plan.id, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plan-annotations', buildingId, plan.id] });
      toast(t('plan.annotations.save') || 'Saved', 'success');
      resetForm();
    },
    onError: (err: any) => toast(err?.response?.data?.detail || 'Error', 'error'),
  });

  const deleteAnnotation = useMutation({
    mutationFn: (id: string) => plansApi.deleteAnnotation(buildingId, plan.id, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plan-annotations', buildingId, plan.id] });
      toast(t('plan.annotations.delete') || 'Deleted', 'success');
      setDeleteConfirmId(null);
    },
    onError: (err: any) => toast(err?.response?.data?.detail || 'Error', 'error'),
  });

  const resetForm = () => {
    setForm(emptyForm);
    setShowForm(false);
    setEditingId(null);
  };

  const handleSubmit = () => {
    const xVal = parseFloat(form.x);
    const yVal = parseFloat(form.y);
    if (!form.label.trim() || isNaN(xVal) || isNaN(yVal) || xVal < 0 || xVal > 1 || yVal < 0 || yVal > 1) return;

    const payload: PlanAnnotationCreate = {
      annotation_type: form.annotation_type,
      label: form.label.trim(),
      x: xVal,
      y: yVal,
      description: form.description.trim() || undefined,
      color: form.color || undefined,
    };

    if (editingId) {
      updateAnnotation.mutate({ id: editingId, data: payload });
    } else {
      createAnnotation.mutate(payload);
    }
  };

  const startEdit = (ann: {
    id: string;
    annotation_type: PlanAnnotationType;
    label: string;
    x: number;
    y: number;
    description?: string;
    color?: string;
  }) => {
    setForm({
      annotation_type: ann.annotation_type,
      label: ann.label,
      x: String(ann.x),
      y: String(ann.y),
      description: ann.description || '',
      color: ann.color || '#ef4444',
    });
    setEditingId(ann.id);
    setShowForm(true);
  };

  const isPending = createAnnotation.isPending || updateAnnotation.isPending;

  return (
    <div className="mt-3 border-t border-gray-100 dark:border-slate-800 pt-3">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-semibold text-gray-700 dark:text-slate-300 flex items-center gap-1">
          <MapPin className="w-3.5 h-3.5" />
          {t('plan.annotations.title') || 'Annotations'}
        </h4>
        <RoleGate allowedRoles={['admin', 'diagnostician']}>
          <button
            onClick={() => {
              if (showForm) resetForm();
              else setShowForm(true);
            }}
            className="text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 flex items-center gap-1"
          >
            {showForm ? <X className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
            {showForm ? t('plan.annotations.cancel') || 'Cancel' : t('plan.annotations.add') || 'Add'}
          </button>
        </RoleGate>
      </div>

      {/* Filter by annotation type */}
      <div className="flex gap-1 flex-wrap mb-2">
        <button
          onClick={() => setAnnotationTypeFilter('')}
          className={cn(
            'px-2 py-0.5 text-[10px] rounded-full border transition-colors',
            !annotationTypeFilter
              ? 'bg-red-600 text-white border-red-600'
              : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-slate-400 border-gray-200 dark:border-slate-700',
          )}
        >
          {t('common.all') || 'All'}
        </button>
        {ANNOTATION_TYPES.map((at) => (
          <button
            key={at}
            onClick={() => setAnnotationTypeFilter(at)}
            className={cn(
              'px-2 py-0.5 text-[10px] rounded-full border transition-colors',
              annotationTypeFilter === at
                ? 'bg-red-600 text-white border-red-600'
                : 'bg-white dark:bg-slate-800 text-gray-500 dark:text-slate-400 border-gray-200 dark:border-slate-700',
            )}
          >
            {t(`plan.annotations.type_${at}`) || at}
          </button>
        ))}
      </div>

      {/* Form */}
      {showForm && (
        <div className="bg-gray-50 dark:bg-slate-800/50 rounded p-3 mb-2 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <select
              value={form.annotation_type}
              onChange={(e) => setForm({ ...form, annotation_type: e.target.value as PlanAnnotationType })}
              className="px-2 py-1.5 text-xs border border-gray-300 dark:border-slate-600 dark:bg-slate-800 dark:text-white rounded"
            >
              {ANNOTATION_TYPES.map((at) => (
                <option key={at} value={at}>
                  {t(`plan.annotations.type_${at}`) || at}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={form.label}
              onChange={(e) => setForm({ ...form, label: e.target.value })}
              placeholder={t('plan.annotations.label') || 'Label'}
              className="px-2 py-1.5 text-xs border border-gray-300 dark:border-slate-600 dark:bg-slate-800 dark:text-white rounded"
            />
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={form.x}
              onChange={(e) => setForm({ ...form, x: e.target.value })}
              placeholder="X (0-1)"
              className="px-2 py-1.5 text-xs border border-gray-300 dark:border-slate-600 dark:bg-slate-800 dark:text-white rounded"
            />
            <input
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={form.y}
              onChange={(e) => setForm({ ...form, y: e.target.value })}
              placeholder="Y (0-1)"
              className="px-2 py-1.5 text-xs border border-gray-300 dark:border-slate-600 dark:bg-slate-800 dark:text-white rounded"
            />
          </div>
          <input
            type="text"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder={t('plan.annotations.description') || 'Description'}
            className="w-full px-2 py-1.5 text-xs border border-gray-300 dark:border-slate-600 dark:bg-slate-800 dark:text-white rounded"
          />
          <div className="flex items-center gap-2">
            <label className="text-[10px] text-gray-500 dark:text-slate-400">
              {t('plan.annotations.color') || 'Color'}
            </label>
            <input
              type="color"
              value={form.color}
              onChange={(e) => setForm({ ...form, color: e.target.value })}
              className="w-6 h-6 rounded border border-gray-300 dark:border-slate-600 cursor-pointer"
            />
          </div>
          <button
            onClick={handleSubmit}
            disabled={!form.label.trim() || isPending}
            className="px-3 py-1.5 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
          >
            {isPending ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : editingId ? (
              t('plan.annotations.save') || 'Save'
            ) : (
              t('plan.annotations.add') || 'Add'
            )}
          </button>
        </div>
      )}

      {/* Annotation list */}
      {isLoading ? (
        <div className="flex justify-center py-3">
          <Loader2 className="w-4 h-4 animate-spin text-gray-400 dark:text-slate-500" />
        </div>
      ) : !annotations || annotations.length === 0 ? (
        <p className="text-[10px] text-gray-400 dark:text-slate-500 text-center py-2">
          {t('plan.annotations.no_annotations') || 'No annotations.'}
        </p>
      ) : (
        <div className="space-y-1.5 max-h-48 overflow-y-auto">
          {annotations.map((ann) => (
            <div key={ann.id} className="flex items-start gap-2 p-2 bg-gray-50 dark:bg-slate-800/50 rounded text-xs">
              {ann.color && (
                <span className="w-2.5 h-2.5 rounded-full mt-0.5 shrink-0" style={{ backgroundColor: ann.color }} />
              )}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span
                    className={cn(
                      'px-1.5 py-0.5 rounded text-[10px] font-medium',
                      annotationTypeColors[ann.annotation_type],
                    )}
                  >
                    {t(`plan.annotations.type_${ann.annotation_type}`) || ann.annotation_type}
                  </span>
                  <span className="font-medium text-gray-900 dark:text-white truncate">{ann.label}</span>
                </div>
                {ann.description && (
                  <p className="text-gray-500 dark:text-slate-400 mt-0.5 truncate">{ann.description}</p>
                )}
                <p className="text-gray-400 dark:text-slate-500 mt-0.5">
                  {t('plan.annotations.position') || 'Position'}: ({ann.x.toFixed(2)}, {ann.y.toFixed(2)})
                </p>
              </div>
              <RoleGate allowedRoles={['admin', 'diagnostician']}>
                <div className="flex gap-1 shrink-0">
                  <button
                    onClick={() => startEdit(ann)}
                    className="p-1 text-gray-400 hover:text-blue-600 dark:text-slate-500 dark:hover:text-blue-400 rounded"
                    title={t('plan.annotations.edit') || 'Edit'}
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => {
                      if (deleteConfirmId === ann.id) deleteAnnotation.mutate(ann.id);
                      else setDeleteConfirmId(ann.id);
                    }}
                    className={cn(
                      'p-1 rounded',
                      deleteConfirmId === ann.id
                        ? 'text-red-600 bg-red-100 dark:bg-red-950/40'
                        : 'text-gray-400 dark:text-slate-500 hover:text-red-500',
                    )}
                    title={
                      deleteConfirmId === ann.id
                        ? t('plan.annotations.confirm_delete') || 'Click again to confirm'
                        : t('plan.annotations.delete') || 'Delete'
                    }
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              </RoleGate>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function BuildingPlans() {
  const { t } = useTranslation();
  const { buildingId } = useParams<{ buildingId: string }>();
  useAuth();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [typeFilter, setTypeFilter] = useState<PlanType | 'all'>('all');
  const [showUploadForm, setShowUploadForm] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [expandedPlanId, setExpandedPlanId] = useState<string | null>(null);

  // Upload form state
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [planTitle, setPlanTitle] = useState('');
  const [planType, setPlanType] = useState<PlanType>('floor_plan');
  const [floorNumber, setFloorNumber] = useState('');

  const {
    data: plans,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['plans', buildingId, typeFilter],
    queryFn: () => plansApi.list(buildingId!, typeFilter === 'all' ? undefined : { plan_type: typeFilter }),
    enabled: !!buildingId,
  });

  const uploadPlan = useMutation({
    mutationFn: (formData: FormData) => plansApi.upload(buildingId!, formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plans', buildingId] });
      toast(t('plan.uploaded') || 'Plan uploaded', 'success');
      setShowUploadForm(false);
      setUploadFile(null);
      setPlanTitle('');
      setFloorNumber('');
    },
    onError: (err: any) =>
      toast(err?.response?.data?.detail || t('plan.upload_error') || 'Error uploading plan', 'error'),
  });

  const deletePlan = useMutation({
    mutationFn: (planId: string) => plansApi.delete(buildingId!, planId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['plans', buildingId] });
      toast(t('plan.deleted') || 'Plan deleted', 'success');
      setDeleteConfirm(null);
    },
    onError: (err: any) =>
      toast(err?.response?.data?.detail || t('plan.delete_error') || 'Error deleting plan', 'error'),
  });

  const handleUpload = () => {
    if (!uploadFile) return;
    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('title', planTitle);
    formData.append('plan_type', planType);
    if (floorNumber) formData.append('floor_number', floorNumber);
    uploadPlan.mutate(formData);
  };

  const formatSize = (bytes: number | null) => {
    if (!bytes) return '\u2014';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

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
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">{t('plan.title') || 'Technical Plans'}</h1>
        </div>
        <div className="mt-3">
          <BuildingSubNav buildingId={buildingId!} />
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-6 py-6 space-y-6">
        {/* Toolbar */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => setTypeFilter('all')}
              className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                typeFilter === 'all'
                  ? 'bg-red-600 text-white border-red-600'
                  : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'
              }`}
            >
              {t('common.all') || 'All'}
            </button>
            {PLAN_TYPES.map((pt) => (
              <button
                key={pt}
                onClick={() => setTypeFilter(pt)}
                className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
                  typeFilter === pt
                    ? 'bg-red-600 text-white border-red-600'
                    : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-slate-300 border-gray-300 dark:border-slate-700 hover:border-gray-400 dark:hover:border-slate-500'
                }`}
              >
                {t(`plan.type.${pt}`) || pt}
              </button>
            ))}
          </div>
          <RoleGate allowedRoles={['admin', 'diagnostician']}>
            <button
              onClick={() => setShowUploadForm(!showUploadForm)}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700"
            >
              <Upload className="w-4 h-4" />
              {t('plan.upload') || 'Upload Plan'}
            </button>
          </RoleGate>
        </div>

        {/* Upload form */}
        {showUploadForm && (
          <div className="bg-white dark:bg-slate-900 p-4 border border-gray-200 dark:border-slate-800 rounded-lg space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <input
                type="text"
                value={planTitle}
                onChange={(e) => setPlanTitle(e.target.value)}
                placeholder={t('plan.field.title') || 'Plan title'}
                className="px-3 py-2 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white rounded focus:ring-1 focus:ring-red-500 focus:border-red-500"
              />
              <select
                value={planType}
                onChange={(e) => setPlanType(e.target.value as PlanType)}
                className="px-3 py-2 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white rounded"
              >
                {PLAN_TYPES.map((pt) => (
                  <option key={pt} value={pt}>
                    {t(`plan.type.${pt}`) || pt}
                  </option>
                ))}
              </select>
              <input
                type="number"
                value={floorNumber}
                onChange={(e) => setFloorNumber(e.target.value)}
                placeholder={t('plan.field.floor') || 'Floor number'}
                className="px-3 py-2 text-sm border border-gray-300 dark:border-slate-700 dark:bg-slate-800 dark:text-white rounded"
              />
              <div className="flex items-center gap-2">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*,.pdf,.dwg,.dxf"
                  onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
                  className="text-sm text-gray-500 dark:text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-sm file:font-medium file:bg-red-50 file:text-red-600 hover:file:bg-red-100"
                />
              </div>
            </div>
            <button
              onClick={handleUpload}
              disabled={!uploadFile || !planTitle.trim() || uploadPlan.isPending}
              className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
            >
              {uploadPlan.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : t('plan.upload') || 'Upload'}
            </button>
          </div>
        )}

        {/* Plans grid */}
        {isLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400 dark:text-slate-500" />
          </div>
        ) : isError ? (
          <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
            <p className="text-red-700 dark:text-red-300">{t('app.error') || 'An error occurred'}</p>
          </div>
        ) : !plans || plans.length === 0 ? (
          <div className="text-center py-16 text-gray-400 dark:text-slate-500">
            <FileImage className="w-10 h-10 mx-auto mb-3" />
            <p className="text-sm">{t('plan.empty') || 'No plans uploaded yet.'}</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className="bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-800 rounded-lg overflow-hidden hover:shadow-sm transition-shadow"
              >
                {/* Thumbnail placeholder */}
                <div className="h-36 bg-gray-100 dark:bg-slate-800 flex items-center justify-center">
                  <FileImage className="w-10 h-10 text-gray-300 dark:text-slate-600" />
                </div>
                <div className="p-4">
                  <h3 className="font-medium text-sm text-gray-900 dark:text-white truncate">{plan.title}</h3>
                  <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-slate-400">
                    <span className="px-2 py-0.5 bg-gray-100 dark:bg-slate-800 rounded-full">
                      {t(`plan.type.${plan.plan_type}`) || plan.plan_type}
                    </span>
                    {plan.floor_number != null && (
                      <span>
                        {t('plan.floor') || 'Floor'} {plan.floor_number}
                      </span>
                    )}
                    <AnnotationCountBadge buildingId={buildingId!} planId={plan.id} />
                  </div>
                  <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
                    {plan.file_name} &middot; {formatSize(plan.file_size_bytes)}
                  </p>
                  <div className="flex items-center gap-2 mt-3">
                    <a
                      href={`/api/buildings/${buildingId}/plans/${plan.id}/download`}
                      className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 rounded"
                      title={t('plan.download') || 'Download'}
                    >
                      <Download className="w-4 h-4" />
                    </a>
                    <a
                      href={`/api/buildings/${buildingId}/plans/${plan.id}/preview`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/40 rounded"
                      title={t('plan.preview') || 'Preview'}
                    >
                      <Eye className="w-4 h-4" />
                    </a>
                    <button
                      onClick={() => setExpandedPlanId(expandedPlanId === plan.id ? null : plan.id)}
                      className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-950/40 rounded"
                      title={t('plan.annotations.title') || 'Annotations'}
                    >
                      {expandedPlanId === plan.id ? (
                        <ChevronUp className="w-4 h-4" />
                      ) : (
                        <ChevronDown className="w-4 h-4" />
                      )}
                    </button>
                    <RoleGate allowedRoles={['admin', 'diagnostician']}>
                      <button
                        onClick={() => {
                          if (deleteConfirm === plan.id) deletePlan.mutate(plan.id);
                          else setDeleteConfirm(plan.id);
                        }}
                        className={`p-1.5 rounded ${
                          deleteConfirm === plan.id
                            ? 'text-red-600 bg-red-100 dark:bg-red-950/40'
                            : 'text-gray-400 dark:text-slate-500 hover:text-red-500'
                        }`}
                        title={
                          deleteConfirm === plan.id
                            ? t('plan.confirm_delete') || 'Click again to confirm'
                            : t('plan.delete') || 'Delete'
                        }
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </RoleGate>
                  </div>

                  {/* Annotation panel (expanded) */}
                  {expandedPlanId === plan.id && buildingId && <AnnotationPanel plan={plan} buildingId={buildingId} />}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

/** Small badge that shows annotation count for a plan */
function AnnotationCountBadge({ buildingId, planId }: { buildingId: string; planId: string }) {
  const { t } = useTranslation();

  const { data: annotations } = useQuery({
    queryKey: ['plan-annotations', buildingId, planId, ''],
    queryFn: () => plansApi.listAnnotations(buildingId, planId),
  });

  const count = annotations?.length ?? 0;
  if (count === 0) return null;

  return (
    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400 rounded-full text-[10px] font-medium">
      <MapPin className="w-2.5 h-2.5" />
      {t('plan.annotations.annotation_count', { count: String(count) }) || `${count} annotation(s)`}
    </span>
  );
}
