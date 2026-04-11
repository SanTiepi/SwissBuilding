import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { fieldObservationsApi } from '@/api/fieldObservations';
import { useTranslation } from '@/i18n';
import { toast } from '@/store/toastStore';
import type { FieldObservationCreate, ObservationConfidence, ObservationType } from '@/types';

const OBSERVATION_TYPES: ObservationType[] = [
  'anomaly',
  'pattern',
  'tip',
  'warning',
  'material_note',
  'environmental_note',
  'access_note',
  'safety_note',
];

const CONFIDENCE_LEVELS: ObservationConfidence[] = ['certain', 'likely', 'possible', 'speculation'];

interface FieldObservationFormProps {
  buildingId?: string;
  onSuccess?: () => void;
  onCancel?: () => void;
}

export function FieldObservationForm({ buildingId, onSuccess, onCancel }: FieldObservationFormProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [isDetailed, setIsDetailed] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [observationType, setObservationType] = useState<ObservationType>('tip');
  const [confidence, setConfidence] = useState<ObservationConfidence>('likely');
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [canton, setCanton] = useState('');
  const [pollutant, setPollutant] = useState('');
  const [material, setMaterial] = useState('');
  const [yearMin, setYearMin] = useState('');
  const [yearMax, setYearMax] = useState('');

  const createMutation = useMutation({
    mutationFn: (data: FieldObservationCreate) => {
      if (buildingId) {
        return fieldObservationsApi.create(buildingId, data);
      }
      return fieldObservationsApi.createGeneral(data);
    },
    onSuccess: () => {
      toast(t('field_memory.create_success') || 'Observation recorded', 'success');
      queryClient.invalidateQueries({ queryKey: ['field-observations'] });
      queryClient.invalidateQueries({ queryKey: ['field-memory-patterns'] });
      onSuccess?.();
    },
    onError: () => {
      toast(t('app.error') || 'Error', 'error');
    },
  });

  const handleAddTag = () => {
    const trimmed = tagInput.trim().toLowerCase();
    if (trimmed && !tags.includes(trimmed)) {
      setTags([...tags, trimmed]);
    }
    setTagInput('');
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };

  const handleTagKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    const contextJson: Record<string, unknown> = {};
    if (canton) contextJson.canton = canton;
    if (pollutant) contextJson.pollutant = pollutant;
    if (material) contextJson.material = material;
    if (yearMin) contextJson.construction_year_min = parseInt(yearMin, 10);
    if (yearMax) contextJson.construction_year_max = parseInt(yearMax, 10);

    const payload: FieldObservationCreate = {
      building_id: buildingId,
      observation_type: observationType,
      severity: 'info',
      title: title.trim(),
      description: description.trim() || undefined,
      tags: tags.length > 0 ? tags : undefined,
      context_json: Object.keys(contextJson).length > 0 ? contextJson : undefined,
      confidence,
    };

    createMutation.mutate(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Mode toggle */}
      <div className="flex items-center gap-2 text-sm">
        <button
          type="button"
          onClick={() => setIsDetailed(false)}
          className={`rounded px-3 py-1 ${!isDetailed ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'}`}
        >
          {t('field_memory.quick_note') || 'Quick note'}
        </button>
        <button
          type="button"
          onClick={() => setIsDetailed(true)}
          className={`rounded px-3 py-1 ${isDetailed ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'}`}
        >
          {t('field_memory.detailed') || 'Detailed'}
        </button>
      </div>

      {/* Title */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
          {t('field_memory.title') || 'Title'}
        </label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
          placeholder={t('field_memory.title_placeholder') || 'What did you observe?'}
        />
      </div>

      {/* Description */}
      <div>
        <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
          {t('field_memory.description') || 'Description'}
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
        />
      </div>

      {isDetailed && (
        <>
          {/* Observation type */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('field_memory.observation_type') || 'Type'}
            </label>
            <select
              value={observationType}
              onChange={(e) => setObservationType(e.target.value as ObservationType)}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
            >
              {OBSERVATION_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`field_memory.type_${type}`) || type}
                </option>
              ))}
            </select>
          </div>

          {/* Confidence */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('field_memory.confidence') || 'Confidence'}
            </label>
            <div className="flex gap-2">
              {CONFIDENCE_LEVELS.map((level) => (
                <label
                  key={level}
                  className={`cursor-pointer rounded px-3 py-1 text-sm ${
                    confidence === level
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="confidence"
                    value={level}
                    checked={confidence === level}
                    onChange={() => setConfidence(level)}
                    className="sr-only"
                  />
                  {t(`field_memory.confidence_${level}`) || level}
                </label>
              ))}
            </div>
          </div>

          {/* Tags */}
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
              {t('field_memory.tags') || 'Tags'}
            </label>
            <div className="flex flex-wrap gap-1 mb-2">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                >
                  {tag}
                  <button
                    type="button"
                    onClick={() => handleRemoveTag(tag)}
                    className="text-blue-600 hover:text-blue-800 dark:text-blue-300"
                  >
                    x
                  </button>
                </span>
              ))}
            </div>
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleTagKeyDown}
              onBlur={handleAddTag}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
              placeholder={t('field_memory.tags_placeholder') || 'e.g. pcb, joint_sealant, 1970s'}
            />
          </div>

          {/* Context fields */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                {t('field_memory.canton') || 'Canton'}
              </label>
              <input
                type="text"
                value={canton}
                onChange={(e) => setCanton(e.target.value)}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                placeholder="VD"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                {t('field_memory.pollutant') || 'Pollutant'}
              </label>
              <select
                value={pollutant}
                onChange={(e) => setPollutant(e.target.value)}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
              >
                <option value="">--</option>
                <option value="asbestos">Asbestos</option>
                <option value="pcb">PCB</option>
                <option value="lead">Lead</option>
                <option value="hap">HAP</option>
                <option value="radon">Radon</option>
                <option value="pfas">PFAS</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                {t('field_memory.material') || 'Material'}
              </label>
              <input
                type="text"
                value={material}
                onChange={(e) => setMaterial(e.target.value)}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                placeholder={t('field_memory.material_placeholder') || 'e.g. joint sealant'}
              />
            </div>
            <div className="flex gap-2">
              <div className="flex-1">
                <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                  {t('field_memory.year_min') || 'Year min'}
                </label>
                <input
                  type="number"
                  value={yearMin}
                  onChange={(e) => setYearMin(e.target.value)}
                  className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  placeholder="1960"
                />
              </div>
              <div className="flex-1">
                <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                  {t('field_memory.year_max') || 'Year max'}
                </label>
                <input
                  type="number"
                  value={yearMax}
                  onChange={(e) => setYearMax(e.target.value)}
                  className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                  placeholder="1980"
                />
              </div>
            </div>
          </div>
        </>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            {t('common.cancel') || 'Cancel'}
          </button>
        )}
        <button
          type="submit"
          disabled={createMutation.isPending || !title.trim()}
          className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {createMutation.isPending
            ? (t('app.loading') || 'Loading...')
            : (t('field_memory.add_observation') || 'Add observation')}
        </button>
      </div>
    </form>
  );
}
