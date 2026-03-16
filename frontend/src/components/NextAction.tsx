import { Link } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { ArrowRight, Plus, FileText, CheckCircle2, ClipboardCheck } from 'lucide-react';
import type { Diagnostic, Building } from '@/types';

interface NextActionProps {
  building: Building;
  diagnostics: Diagnostic[];
}

type ActionType = 'create_diagnostic' | 'add_samples' | 'validate_diagnostic' | 'upload_report' | 'all_done';

interface Action {
  type: ActionType;
  icon: React.ElementType;
  color: string;
  bg: string;
  link?: string;
  diagnosticId?: string;
}

function computeNextAction(building: Building, diagnostics: Diagnostic[]): Action {
  // No diagnostics yet → suggest creating one
  if (diagnostics.length === 0) {
    return {
      type: 'create_diagnostic',
      icon: Plus,
      color: 'text-red-600',
      bg: 'bg-red-50 border-red-200',
      link: `/buildings/${building.id}`,
    };
  }

  // Check for diagnostics in draft state → need samples
  const drafts = diagnostics.filter((d) => d.status === 'draft');
  if (drafts.length > 0) {
    return {
      type: 'add_samples',
      icon: FileText,
      color: 'text-blue-600',
      bg: 'bg-blue-50 border-blue-200',
      link: `/diagnostics/${drafts[0].id}`,
      diagnosticId: drafts[0].id,
    };
  }

  // Check for completed diagnostics needing validation
  const completed = diagnostics.filter((d) => d.status === 'completed');
  if (completed.length > 0) {
    return {
      type: 'validate_diagnostic',
      icon: ClipboardCheck,
      color: 'text-amber-600',
      bg: 'bg-amber-50 border-amber-200',
      link: `/diagnostics/${completed[0].id}`,
      diagnosticId: completed[0].id,
    };
  }

  // Check for in-progress diagnostics → need report upload
  const inProgress = diagnostics.filter((d) => d.status === 'in_progress');
  if (inProgress.length > 0) {
    return {
      type: 'upload_report',
      icon: FileText,
      color: 'text-purple-600',
      bg: 'bg-purple-50 border-purple-200',
      link: `/diagnostics/${inProgress[0].id}`,
      diagnosticId: inProgress[0].id,
    };
  }

  // All done
  return {
    type: 'all_done',
    icon: CheckCircle2,
    color: 'text-green-600',
    bg: 'bg-green-50 border-green-200',
  };
}

export function NextAction({ building, diagnostics }: NextActionProps) {
  const { t } = useTranslation();
  const action = computeNextAction(building, diagnostics);

  const labels: Record<ActionType, { title: string; description: string }> = {
    create_diagnostic: {
      title: t('next_action.create_diagnostic'),
      description: t('next_action.create_diagnostic_desc'),
    },
    add_samples: {
      title: t('next_action.add_samples'),
      description: t('next_action.add_samples_desc'),
    },
    validate_diagnostic: {
      title: t('next_action.validate_diagnostic'),
      description: t('next_action.validate_diagnostic_desc'),
    },
    upload_report: {
      title: t('next_action.upload_report'),
      description: t('next_action.upload_report_desc'),
    },
    all_done: {
      title: t('next_action.all_done'),
      description: t('next_action.all_done_desc'),
    },
  };

  const Icon = action.icon;
  const label = labels[action.type];

  return (
    <div className={`rounded-xl border p-4 ${action.bg}`}>
      <div className="flex items-start gap-3">
        <div className={`flex-shrink-0 mt-0.5 ${action.color}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-semibold ${action.color}`}>{label.title}</p>
          <p className="text-xs text-gray-600 dark:text-slate-300 mt-0.5">{label.description}</p>
        </div>
        {action.link && (
          <Link
            to={action.link}
            className={`flex-shrink-0 inline-flex items-center gap-1 text-xs font-medium ${action.color} hover:underline`}
          >
            {t('form.view')}
            <ArrowRight className="w-3 h-3" />
          </Link>
        )}
      </div>
    </div>
  );
}

/** Compact version for use in building cards */
export function NextActionBadge({ building, diagnostics }: NextActionProps) {
  const { t } = useTranslation();
  const action = computeNextAction(building, diagnostics);
  if (action.type === 'all_done') return null;

  const Icon = action.icon;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${action.color} ${action.bg}`}
    >
      <Icon className="w-3 h-3" />
      {t(`next_action.${action.type}`)}
    </span>
  );
}
