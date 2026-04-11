/**
 * Mobile-first field observation form (Q3.03).
 * Big buttons, vertical layout, touch-friendly for on-site inspectors.
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { fieldObservationsApi } from '@/api/fieldObservations';
import { toast } from '@/store/toastStore';
import {
  BuildingElementSelector,
  ConditionPicker,
  PhotoCaptureWidget,
  RiskFlagCheckboxes,
  VoiceInput,
} from '@/components/observation';
import type { CapturedPhoto } from '@/components/observation';
import type { ConditionAssessment, FieldObservationCreate, RiskFlag } from '@/types';
import { ArrowLeft, CheckCircle2, Loader2, MapPin, Send } from 'lucide-react';

type Step = 'element' | 'condition' | 'photos' | 'details' | 'preview' | 'done';

const STEPS: Step[] = ['element', 'condition', 'photos', 'details', 'preview'];

export default function ObservationForm() {
  const { buildingId } = useParams<{ buildingId: string }>();
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [step, setStep] = useState<Step>('element');
  const [element, setElement] = useState('');
  const [condition, setCondition] = useState<ConditionAssessment | ''>('');
  const [riskFlags, setRiskFlags] = useState<RiskFlag[]>([]);
  const [photos, setPhotos] = useState<CapturedPhoto[]>([]);
  const [notes, setNotes] = useState('');
  const [observerName, setObserverName] = useState('');
  const [gps, setGps] = useState<{ lat: number; lon: number } | null>(null);
  const [startTime] = useState(() => Date.now());

  // Capture GPS on mount
  useEffect(() => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => setGps({ lat: pos.coords.latitude, lon: pos.coords.longitude }),
        () => {},
        { enableHighAccuracy: true, timeout: 10000 },
      );
    }
  }, []);

  const createMutation = useMutation({
    mutationFn: (data: FieldObservationCreate) => fieldObservationsApi.create(buildingId!, data),
    onSuccess: () => {
      toast(t('observation.submitted') || 'Observation submitted', 'success');
      setStep('done');
    },
    onError: () => {
      toast(t('app.error') || 'Error', 'error');
    },
  });

  const handleSubmit = useCallback(() => {
    if (!buildingId || !condition) return;
    const durationMinutes = Math.round((Date.now() - startTime) / 60000);

    const payload: FieldObservationCreate = {
      building_id: buildingId,
      observation_type: 'visual_inspection',
      severity: condition === 'critical' ? 'critical' : condition === 'poor' ? 'major' : 'info',
      title: `${element || 'general'} — ${condition}`,
      description: notes || undefined,
      condition_assessment: condition,
      risk_flags: riskFlags.length > 0 ? riskFlags : undefined,
      photos: photos.map((p) => ({ uri: p.uri, element_part: p.element_part, timestamp: p.timestamp })),
      gps_lat: gps?.lat,
      gps_lon: gps?.lon,
      inspection_duration_minutes: durationMinutes,
      observer_name: observerName || undefined,
    };

    createMutation.mutate(payload);
  }, [buildingId, element, condition, riskFlags, photos, notes, observerName, gps, startTime, createMutation]);

  const stepIndex = STEPS.indexOf(step);
  const canGoNext =
    (step === 'element' && element !== '') ||
    (step === 'condition' && condition !== '') ||
    step === 'photos' ||
    step === 'details' ||
    step === 'preview';

  const goNext = () => {
    const idx = STEPS.indexOf(step);
    if (idx < STEPS.length - 1) setStep(STEPS[idx + 1]);
  };
  const goBack = () => {
    const idx = STEPS.indexOf(step);
    if (idx > 0) setStep(STEPS[idx - 1]);
  };

  // Done screen
  if (step === 'done') {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center" data-testid="done-screen">
        <CheckCircle2 className="h-16 w-16 text-green-500" />
        <h2 className="mt-4 text-xl font-bold text-gray-900 dark:text-white">
          {t('observation.submitted') || 'Observation submitted'}
        </h2>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          {t('observation.submitted_desc') || 'Your observation has been recorded and risk-scored.'}
        </p>
        <div className="mt-6 flex gap-3">
          <button
            onClick={() => {
              setStep('element');
              setElement('');
              setCondition('');
              setRiskFlags([]);
              setPhotos([]);
              setNotes('');
            }}
            className="rounded-xl bg-indigo-600 px-6 py-3 text-sm font-medium text-white hover:bg-indigo-700"
            data-testid="new-observation-button"
          >
            {t('observation.new_observation') || 'New observation'}
          </button>
          <button
            onClick={() => navigate(`/buildings/${buildingId}`)}
            className="rounded-xl border border-gray-300 px-6 py-3 text-sm text-gray-700 dark:border-gray-600 dark:text-gray-300"
          >
            {t('observation.back_to_building') || 'Back to building'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg px-4 pb-24">
      {/* Header */}
      <div className="flex items-center gap-3 py-4">
        <button
          onClick={() => (stepIndex > 0 ? goBack() : navigate(-1))}
          className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
          data-testid="back-button"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div className="flex-1">
          <h1 className="text-lg font-bold text-gray-900 dark:text-white">
            {t('observation.new_observation') || 'New observation'}
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {t('observation.step') || 'Step'} {stepIndex + 1}/{STEPS.length}
          </p>
        </div>
        {gps && (
          <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400" data-testid="gps-indicator">
            <MapPin className="h-3 w-3" />
            GPS
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div className="mb-6 flex gap-1">
        {STEPS.map((s, i) => (
          <div
            key={s}
            className={`h-1 flex-1 rounded-full transition-all ${
              i <= stepIndex ? 'bg-indigo-500' : 'bg-gray-200 dark:bg-gray-700'
            }`}
          />
        ))}
      </div>

      {/* Step content */}
      <div className="space-y-6">
        {step === 'element' && <BuildingElementSelector value={element} onChange={setElement} />}

        {step === 'condition' && (
          <>
            <ConditionPicker value={condition} onChange={setCondition} />
            <RiskFlagCheckboxes value={riskFlags} onChange={setRiskFlags} />
          </>
        )}

        {step === 'photos' && (
          <PhotoCaptureWidget
            photos={photos}
            onAdd={(p) => setPhotos((prev) => [...prev, p])}
            onRemove={(i) => setPhotos((prev) => prev.filter((_, idx) => idx !== i))}
          />
        )}

        {step === 'details' && (
          <>
            <VoiceInput value={notes} onChange={setNotes} />
            <div>
              <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('observation.observer_name') || 'Your name (sign-off)'}
              </label>
              <input
                type="text"
                value={observerName}
                onChange={(e) => setObserverName(e.target.value)}
                data-testid="observer-name-input"
                className="w-full rounded-xl border border-gray-300 px-4 py-3 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
                placeholder={t('observation.observer_name_placeholder') || 'Inspector name'}
              />
            </div>
          </>
        )}

        {step === 'preview' && (
          <div className="space-y-4 rounded-xl border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800" data-testid="preview-screen">
            <h3 className="font-bold text-gray-900 dark:text-white">{t('observation.review') || 'Review'}</h3>

            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('observation.building_element') || 'Element'}</span>
                <p className="font-medium text-gray-900 dark:text-white">{element || '—'}</p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('observation.condition_assessment') || 'Condition'}</span>
                <p className="font-medium text-gray-900 dark:text-white">{condition || '—'}</p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('observation.risk_flags') || 'Flags'}</span>
                <p className="font-medium text-gray-900 dark:text-white">{riskFlags.join(', ') || '—'}</p>
              </div>
              <div>
                <span className="text-gray-500 dark:text-gray-400">{t('observation.photos') || 'Photos'}</span>
                <p className="font-medium text-gray-900 dark:text-white">{photos.length}</p>
              </div>
            </div>

            {notes && (
              <div className="text-sm">
                <span className="text-gray-500 dark:text-gray-400">{t('observation.notes') || 'Notes'}</span>
                <p className="mt-1 text-gray-900 dark:text-white">{notes}</p>
              </div>
            )}

            {observerName && (
              <div className="text-sm">
                <span className="text-gray-500 dark:text-gray-400">{t('observation.observer_name') || 'Inspector'}</span>
                <p className="font-medium text-gray-900 dark:text-white">{observerName}</p>
              </div>
            )}

            {gps && (
              <div className="text-xs text-gray-500 dark:text-gray-400">
                GPS: {gps.lat.toFixed(5)}, {gps.lon.toFixed(5)}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Bottom navigation */}
      <div className="fixed bottom-0 left-0 right-0 border-t border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-900">
        <div className="mx-auto flex max-w-lg gap-3">
          {stepIndex > 0 && (
            <button
              type="button"
              onClick={goBack}
              className="flex-1 rounded-xl border border-gray-300 px-4 py-3.5 text-sm font-medium text-gray-700 dark:border-gray-600 dark:text-gray-300"
            >
              {t('common.back') || 'Back'}
            </button>
          )}
          {step === 'preview' ? (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={createMutation.isPending}
              data-testid="submit-observation"
              className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {createMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              {t('observation.submit') || 'Submit'}
            </button>
          ) : (
            <button
              type="button"
              onClick={goNext}
              disabled={!canGoNext}
              data-testid="next-step"
              className="flex-1 rounded-xl bg-indigo-600 px-4 py-3.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {t('common.next') || 'Next'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
