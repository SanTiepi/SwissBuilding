import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { remediationIntelligenceApi } from '@/api/remediationIntelligence';
import type { NarrativeSection } from '@/api/remediationIntelligence';
import { BookOpen, AlertCircle, Users } from 'lucide-react';

const AUDIENCES = ['owner', 'authority', 'contractor'] as const;

const AUDIENCE_LABELS: Record<string, { label: string; icon: typeof Users }> = {
  owner: { label: 'Owner', icon: Users },
  authority: { label: 'Authority', icon: Users },
  contractor: { label: 'Contractor', icon: Users },
};

function SectionCard({ section }: { section: NarrativeSection }) {
  return (
    <div className="border-l-2 border-blue-400 pl-4 py-2 space-y-1">
      <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100">{section.title}</h4>
      <p className="text-sm text-gray-600 dark:text-gray-400">{section.body}</p>
      {section.caveats.length > 0 && (
        <div className="flex items-start gap-1 text-xs text-amber-600 dark:text-amber-400">
          <AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
          <span>{section.caveats.join(' ')}</span>
        </div>
      )}
      {section.evidence_refs.length > 0 && (
        <div className="text-xs text-gray-400">Refs: {section.evidence_refs.join(', ')}</div>
      )}
      {section.audience_specific && (
        <span className="text-xs bg-blue-50 dark:bg-blue-900 text-blue-600 dark:text-blue-300 px-1.5 py-0.5 rounded">
          audience-specific
        </span>
      )}
    </div>
  );
}

interface PassportNarrativePanelProps {
  buildingId: string;
}

export function PassportNarrativePanel({ buildingId }: PassportNarrativePanelProps) {
  const { t } = useTranslation();
  const [audience, setAudience] = useState<string>('owner');

  const { data, isLoading, error } = useQuery({
    queryKey: ['passport-narrative', buildingId, audience],
    queryFn: () => remediationIntelligenceApi.getPassportNarrative(buildingId, audience),
    enabled: !!buildingId,
  });

  if (isLoading) {
    return <div className="animate-pulse h-32 bg-gray-100 dark:bg-gray-800 rounded-lg" />;
  }

  if (error) {
    return (
      <div className="text-sm text-red-500">
        {t('intelligence.narrative_error') || 'Failed to load narrative.'}
      </div>
    );
  }

  const sections: NarrativeSection[] = data?.sections || [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            {t('intelligence.passport_narrative') || 'Passport Narrative'}
          </h3>
        </div>
        <div className="flex gap-1">
          {AUDIENCES.map((a) => (
            <button
              key={a}
              onClick={() => setAudience(a)}
              className={`px-3 py-1 text-xs rounded-full transition-colors ${
                audience === a
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200'
              }`}
            >
              {AUDIENCE_LABELS[a]?.label || a}
            </button>
          ))}
        </div>
      </div>
      {sections.length > 0 ? (
        <div className="space-y-3">
          {sections.map((s, i) => (
            <SectionCard key={i} section={s} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500">{t('intelligence.no_narrative') || 'No narrative available.'}</p>
      )}
    </div>
  );
}

export default PassportNarrativePanel;
