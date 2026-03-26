import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { intelligenceApi } from '@/api/intelligence';
import type { ExplainedScore, ScoreLineItem } from '@/api/intelligence';
import {
  Loader2,
  ChevronDown,
  ChevronRight,
  FileText,
  Shield,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Info,
  ExternalLink,
  Beaker,
  Eye,
  Clipboard,
  Building2,
} from 'lucide-react';

interface ScoreExplainabilityViewProps {
  buildingId: string;
}

const ITEM_TYPE_ICONS: Record<string, typeof FileText> = {
  document: FileText,
  diagnostic: Beaker,
  evidence: Shield,
  action: Clipboard,
  observation: Eye,
  building: Building2,
};

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const colorMap: Record<string, string> = {
    exact: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
    estimated: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    heuristic: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  };

  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold',
        colorMap[confidence] || 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400',
      )}
    >
      {confidence}
    </span>
  );
}

function LineItemRow({ item, onNavigate }: { item: ScoreLineItem; onNavigate: (link: string) => void }) {
  const Icon = ITEM_TYPE_ICONS[item.item_type] || FileText;

  return (
    <button
      onClick={() => onNavigate(item.link)}
      className="w-full flex items-start gap-3 px-3 py-2.5 text-left hover:bg-slate-50 dark:hover:bg-slate-800/50 rounded-lg transition-colors group"
    >
      <Icon className="w-4 h-4 text-slate-400 dark:text-slate-500 mt-0.5 shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-slate-800 dark:text-slate-200 truncate">{item.label}</span>
          <ExternalLink className="w-3 h-3 text-slate-300 dark:text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
        </div>
        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{item.detail}</p>
        <div className="flex items-center gap-2 mt-1">
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
            {item.contribution}
          </span>
          {item.source_class && (
            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400">
              {item.source_class}
            </span>
          )}
          {item.timestamp && (
            <span className="inline-flex items-center gap-1 text-[10px] text-slate-400 dark:text-slate-500">
              <Clock className="w-3 h-3" />
              {new Date(item.timestamp).toLocaleDateString()}
            </span>
          )}
        </div>
      </div>
    </button>
  );
}

function ScoreCard({ score }: { score: ExplainedScore }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const [showMethodology, setShowMethodology] = useState(false);

  const handleNavigate = (link: string) => {
    if (link.startsWith('http')) {
      window.open(link, '_blank');
    } else {
      navigate(link);
    }
  };

  return (
    <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 overflow-hidden">
      {/* Card header — click to expand */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">{score.metric_label}</span>
            <ConfidenceBadge confidence={score.confidence} />
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">{score.metric_name}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-2xl font-black text-slate-900 dark:text-white">
            {typeof score.value === 'number' && score.value <= 1 ? `${Math.round(score.value * 100)}%` : score.value}
          </span>
          {score.unit && score.value > 1 && (
            <span className="text-xs text-slate-500 dark:text-slate-400">{score.unit}</span>
          )}
          {expanded ? (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-slate-400" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-slate-100 dark:border-slate-800">
          {/* Methodology toggle */}
          <div className="px-5 py-2 border-b border-slate-100 dark:border-slate-800">
            <button
              onClick={() => setShowMethodology(!showMethodology)}
              className="flex items-center gap-1.5 text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
            >
              <Info className="w-3.5 h-3.5" />
              {t('score_explainability.how_calculated') || 'Comment ce chiffre est calcule'}
              {showMethodology ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </button>
            {showMethodology && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 leading-relaxed bg-slate-50 dark:bg-slate-800/50 rounded-lg p-3">
                {score.methodology}
              </p>
            )}
          </div>

          {/* Line items */}
          <div className="px-2 py-1 max-h-80 overflow-y-auto">
            {score.line_items.length > 0 ? (
              score.line_items.map((item, i) => <LineItemRow key={i} item={item} onNavigate={handleNavigate} />)
            ) : (
              <div className="flex items-center gap-2 px-3 py-4 text-xs text-slate-400 dark:text-slate-500">
                <AlertTriangle className="w-4 h-4" />
                {t('score_explainability.no_line_items') || 'Aucun element de preuve pour ce score'}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function ScoreExplainabilityView({ buildingId }: ScoreExplainabilityViewProps) {
  const { t } = useTranslation();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['score-explainability', buildingId],
    queryFn: () => intelligenceApi.getScoreExplainability(buildingId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 animate-spin text-red-600" />
      </div>
    );
  }

  if (isError || !data) return null;

  return (
    <div className="space-y-4 mt-5" data-testid="score-explainability-view">
      {/* Header */}
      <div className="flex items-center gap-2">
        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
        <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">
          {t('score_explainability.title') || 'Detail des scores'}
        </h3>
      </div>

      {/* Methodology summary */}
      {data.methodology_summary && (
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">{data.methodology_summary}</p>
      )}

      {/* Score cards */}
      <div className="space-y-3">
        {data.scores.map((score, i) => (
          <ScoreCard key={i} score={score} />
        ))}
      </div>

      {/* Footer — total proof count */}
      <div className="text-center pt-2">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          {t('score_explainability.proof_count_prefix') || 'Ce score repose sur'}{' '}
          <span className="font-bold text-slate-700 dark:text-slate-300">{data.total_line_items}</span>{' '}
          {t('score_explainability.proof_count_suffix') || 'preuves verifiables'}
        </p>
      </div>
    </div>
  );
}
