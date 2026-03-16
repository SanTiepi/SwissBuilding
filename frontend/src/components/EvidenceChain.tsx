import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { evidenceApi } from '@/api/evidence';
import type { EvidenceLink } from '@/types';
import { Link2, FileCheck, Shield, AlertOctagon, ArrowRight, Loader2 } from 'lucide-react';

interface EvidenceChainProps {
  targetType: string;
  targetId: string;
  compact?: boolean;
}

const REL_COLORS: Record<string, string> = {
  proves: 'bg-green-100 text-green-800',
  supports: 'bg-blue-100 text-blue-800',
  contradicts: 'bg-red-100 text-red-800',
  requires: 'bg-yellow-100 text-yellow-800',
  triggers: 'bg-purple-100 text-purple-800',
  supersedes: 'bg-gray-100 text-gray-800',
};

const REL_ICONS: Record<string, React.ElementType> = {
  proves: FileCheck,
  supports: Shield,
  contradicts: AlertOctagon,
  requires: Link2,
  triggers: ArrowRight,
  supersedes: ArrowRight,
};

export function EvidenceChain({ targetType, targetId, compact = false }: EvidenceChainProps) {
  const { t } = useTranslation();
  const {
    data: links = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['evidence', targetType, targetId],
    queryFn: () => evidenceApi.list({ target_type: targetType, target_id: targetId }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t('app.loading')}
      </div>
    );
  }

  if (isError) {
    return compact ? null : <p className="text-sm text-red-600 dark:text-red-400">{t('evidence.load_error')}</p>;
  }

  if (links.length === 0) {
    return compact ? null : <p className="text-sm italic text-gray-400">{t('evidence.none')}</p>;
  }

  if (compact) {
    return (
      <div className="flex items-center gap-1">
        <Link2 className="h-3.5 w-3.5 text-gray-400" />
        <span className="text-xs text-gray-500">
          {links.length} {t('evidence.links')}
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <h4 className="flex items-center gap-1.5 text-sm font-medium text-gray-700">
        <Link2 className="h-4 w-4" />
        {t('evidence.title')} ({links.length})
      </h4>
      {links.map((link: EvidenceLink) => {
        const Icon = REL_ICONS[link.relationship] || Link2;
        const colorClass = REL_COLORS[link.relationship] || 'bg-gray-100 text-gray-800';
        return (
          <div key={link.id} className="flex items-start gap-2 rounded border border-gray-100 bg-white p-2">
            <Icon className="mt-0.5 h-4 w-4 flex-shrink-0 text-gray-500" />
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${colorClass}`}>
                  {t(`evidence_rel.${link.relationship}`) || link.relationship}
                </span>
                <span className="text-xs text-gray-500">{link.source_type}</span>
                {link.confidence != null && (
                  <span className="ml-auto text-xs text-gray-400">{Math.round(link.confidence * 100)}%</span>
                )}
              </div>
              {link.explanation && <p className="mt-1 line-clamp-2 text-xs text-gray-600">{link.explanation}</p>}
              {link.legal_reference && <p className="mt-0.5 text-xs text-gray-400">{link.legal_reference}</p>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
