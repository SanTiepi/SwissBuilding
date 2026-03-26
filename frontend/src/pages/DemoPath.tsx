import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/api/client';
import { cn } from '@/utils/formatters';
import {
  Building2,
  Shield,
  ShieldCheck,
  Microscope,
  ChevronRight,
  ChevronLeft,
  ExternalLink,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Lightbulb,
  Play,
} from 'lucide-react';

// ---- Types ----

interface DemoStep {
  order: number;
  title: string;
  description: string;
  api_endpoint: string;
  expected_insight: string;
  page_path: string;
  cta_label: string;
}

interface DemoScenario {
  scenario_type: string;
  title: string;
  description: string;
  icon: string;
  step_count: number;
  steps: DemoStep[];
}

// ---- API ----

const demoPathApi = {
  listPaths: async (): Promise<DemoScenario[]> => {
    const response = await apiClient.get<DemoScenario[]>('/demo/paths');
    return response.data;
  },
  getPath: async (type: string): Promise<DemoScenario> => {
    const response = await apiClient.get<DemoScenario>(`/demo/paths/${type}`);
    return response.data;
  },
};

// ---- Icon mapper ----

const ICON_MAP: Record<string, React.ElementType> = {
  building: Building2,
  shield: Shield,
  'shield-check': ShieldCheck,
  microscope: Microscope,
};

const SCENARIO_COLORS: Record<string, { bg: string; border: string; text: string; accent: string }> = {
  property_manager: {
    bg: 'bg-blue-50 dark:bg-blue-900/20',
    border: 'border-blue-200 dark:border-blue-800',
    text: 'text-blue-700 dark:text-blue-300',
    accent: 'bg-blue-600',
  },
  authority: {
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    border: 'border-emerald-200 dark:border-emerald-800',
    text: 'text-emerald-700 dark:text-emerald-300',
    accent: 'bg-emerald-600',
  },
  insurer: {
    bg: 'bg-purple-50 dark:bg-purple-900/20',
    border: 'border-purple-200 dark:border-purple-800',
    text: 'text-purple-700 dark:text-purple-300',
    accent: 'bg-purple-600',
  },
  diagnostician: {
    bg: 'bg-orange-50 dark:bg-orange-900/20',
    border: 'border-orange-200 dark:border-orange-800',
    text: 'text-orange-700 dark:text-orange-300',
    accent: 'bg-orange-600',
  },
};

// ---- Scenario Card ----

function ScenarioCard({
  scenario,
  isSelected,
  onClick,
}: {
  scenario: DemoScenario;
  isSelected: boolean;
  onClick: () => void;
}) {
  const Icon = ICON_MAP[scenario.icon] || Building2;
  const colors = SCENARIO_COLORS[scenario.scenario_type] || SCENARIO_COLORS.property_manager;
  const { t } = useTranslation();

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'relative flex flex-col items-center gap-3 p-6 rounded-2xl border-2 transition-all text-center',
        isSelected
          ? `${colors.bg} ${colors.border} ${colors.text} shadow-lg scale-[1.02]`
          : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-600',
      )}
      data-testid={`scenario-card-${scenario.scenario_type}`}
    >
      <div
        className={cn(
          'w-14 h-14 rounded-xl flex items-center justify-center',
          isSelected ? colors.accent : 'bg-slate-100 dark:bg-slate-700',
        )}
      >
        <Icon className={cn('w-7 h-7', isSelected ? 'text-white' : 'text-slate-500 dark:text-slate-400')} />
      </div>
      <div>
        <h3 className={cn('font-semibold text-sm', isSelected ? colors.text : 'text-slate-900 dark:text-white')}>
          {scenario.title}
        </h3>
        <p className="text-xs mt-1 opacity-75">
          {scenario.step_count} {t('demo_path.steps_label') || 'etapes'}
        </p>
      </div>
      {isSelected && (
        <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 w-3 h-3 rotate-45 bg-white dark:bg-slate-900 border-b-2 border-r-2 border-slate-200 dark:border-slate-700" />
      )}
    </button>
  );
}

// ---- Step Walkthrough ----

function StepWalkthrough({ scenario }: { scenario: DemoScenario }) {
  const [currentStep, setCurrentStep] = useState(0);
  const { t } = useTranslation();
  const colors = SCENARIO_COLORS[scenario.scenario_type] || SCENARIO_COLORS.property_manager;

  const step = scenario.steps[currentStep];
  if (!step) return null;

  const progress = ((currentStep + 1) / scenario.steps.length) * 100;

  return (
    <div className="mt-8 space-y-6" data-testid="step-walkthrough">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <span>
            {t('demo_path.step') || 'Etape'} {currentStep + 1} / {scenario.steps.length}
          </span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
          <div
            className={cn('h-full rounded-full transition-all duration-500', colors.accent)}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Step content */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
        {/* Step header */}
        <div className={cn('px-6 py-4', colors.bg)}>
          <div className="flex items-center gap-3">
            <span
              className={cn(
                'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold text-white',
                colors.accent,
              )}
            >
              {step.order}
            </span>
            <div>
              <h3 className={cn('font-semibold text-lg', colors.text)}>{step.title}</h3>
            </div>
          </div>
        </div>

        {/* Step body */}
        <div className="px-6 py-5 space-y-4">
          <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed">{step.description}</p>

          {/* Expected insight */}
          <div className="flex gap-3 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
            <Lightbulb className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-1">
                {t('demo_path.expected_insight') || 'Insight attendu'}
              </p>
              <p className="text-sm text-amber-900 dark:text-amber-200">{step.expected_insight}</p>
            </div>
          </div>

          {/* API endpoint */}
          <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500 font-mono">
            <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400">
              GET
            </span>
            {step.api_endpoint}
          </div>

          {/* CTA */}
          <Link
            to={step.page_path}
            className={cn(
              'inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-all hover:opacity-90',
              colors.accent,
            )}
            data-testid={`step-cta-${step.order}`}
          >
            <ExternalLink className="w-4 h-4" />
            {step.cta_label}
          </Link>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setCurrentStep((prev) => Math.max(0, prev - 1))}
          disabled={currentStep === 0}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            currentStep === 0
              ? 'text-slate-300 dark:text-slate-600 cursor-not-allowed'
              : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800',
          )}
          data-testid="step-prev"
        >
          <ChevronLeft className="w-4 h-4" />
          {t('demo_path.previous') || 'Precedent'}
        </button>

        {/* Step dots */}
        <div className="flex items-center gap-1.5">
          {scenario.steps.map((_, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setCurrentStep(idx)}
              className={cn(
                'w-2.5 h-2.5 rounded-full transition-all',
                idx === currentStep
                  ? cn(colors.accent, 'w-6')
                  : idx < currentStep
                    ? 'bg-emerald-400'
                    : 'bg-slate-300 dark:bg-slate-600',
              )}
              data-testid={`step-dot-${idx}`}
            />
          ))}
        </div>

        <button
          type="button"
          onClick={() => setCurrentStep((prev) => Math.min(scenario.steps.length - 1, prev + 1))}
          disabled={currentStep === scenario.steps.length - 1}
          className={cn(
            'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
            currentStep === scenario.steps.length - 1
              ? 'text-slate-300 dark:text-slate-600 cursor-not-allowed'
              : 'text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800',
          )}
          data-testid="step-next"
        >
          {t('demo_path.next') || 'Suivant'}
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Completed state */}
      {currentStep === scenario.steps.length - 1 && (
        <div className="text-center py-6 bg-emerald-50 dark:bg-emerald-900/20 rounded-2xl border border-emerald-200 dark:border-emerald-800">
          <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3" />
          <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">
            {t('demo_path.completed') || 'Parcours termine !'}
          </p>
          <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-1">
            {t('demo_path.completed_hint') || 'Vous avez explore toutes les etapes de ce scenario.'}
          </p>
        </div>
      )}
    </div>
  );
}

// ---- Main page ----

export default function DemoPath() {
  const { t } = useTranslation();
  useAuth();

  const [selectedType, setSelectedType] = useState<string | null>(null);

  const {
    data: scenarios = [],
    isLoading: listLoading,
    isError: listError,
  } = useQuery({
    queryKey: ['demo-paths'],
    queryFn: demoPathApi.listPaths,
  });

  const {
    data: selectedScenario,
    isLoading: scenarioLoading,
    isError: scenarioError,
  } = useQuery({
    queryKey: ['demo-path', selectedType],
    queryFn: () => demoPathApi.getPath(selectedType!),
    enabled: !!selectedType,
  });

  if (listLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  if (listError) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-red-600 text-white mb-4 shadow-lg">
          <Play className="w-7 h-7" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
          {t('demo_path.title') || 'Experience guidee BatiConnect'}
        </h1>
        <p className="mt-2 text-base text-slate-500 dark:text-slate-400 max-w-xl mx-auto">
          {t('demo_path.description') || 'Choisissez votre role et decouvrez BatiConnect en quelques etapes cles.'}
        </p>
      </div>

      {/* Scenario selector */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4" data-testid="scenario-selector">
        {scenarios.map((scenario) => (
          <ScenarioCard
            key={scenario.scenario_type}
            scenario={scenario}
            isSelected={selectedType === scenario.scenario_type}
            onClick={() => setSelectedType(scenario.scenario_type)}
          />
        ))}
      </div>

      {/* Loading scenario */}
      {scenarioLoading && selectedType && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-red-600" />
        </div>
      )}

      {/* Error loading scenario */}
      {scenarioError && selectedType && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
          <p className="text-red-700 dark:text-red-300 text-sm">{t('app.error')}</p>
        </div>
      )}

      {/* Step walkthrough */}
      {selectedScenario && selectedScenario.steps.length > 0 && <StepWalkthrough scenario={selectedScenario} />}
    </div>
  );
}
