import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { cn } from '@/utils/formatters';
import {
  Shield,
  Loader2,
  Clock,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Hash,
  Lock,
} from 'lucide-react';

import type { SharedArtifactData } from '@/api/packExport';

/* ------------------------------------------------------------------ */
/*  Public API client (no auth)                                        */
/* ------------------------------------------------------------------ */

const publicClient = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

async function fetchSharedArtifact(accessToken: string): Promise<SharedArtifactData> {
  const resp = await publicClient.get(`/shared/${accessToken}/artifact`);
  return resp.data;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const GRADE_COLORS: Record<string, { bg: string; text: string; ring: string }> = {
  A: {
    bg: 'bg-emerald-100 dark:bg-emerald-900/40',
    text: 'text-emerald-700 dark:text-emerald-300',
    ring: 'ring-emerald-500',
  },
  B: { bg: 'bg-green-100 dark:bg-green-900/40', text: 'text-green-700 dark:text-green-300', ring: 'ring-green-500' },
  C: {
    bg: 'bg-yellow-100 dark:bg-yellow-900/40',
    text: 'text-yellow-700 dark:text-yellow-300',
    ring: 'ring-yellow-500',
  },
  D: {
    bg: 'bg-orange-100 dark:bg-orange-900/40',
    text: 'text-orange-700 dark:text-orange-300',
    ring: 'ring-orange-500',
  },
  E: { bg: 'bg-red-100 dark:bg-red-900/40', text: 'text-red-700 dark:text-red-300', ring: 'ring-red-500' },
  F: { bg: 'bg-red-200 dark:bg-red-900/50', text: 'text-red-800 dark:text-red-200', ring: 'ring-red-600' },
};

const VERDICT_LABELS: Record<string, { label: string; color: string; icon: typeof CheckCircle2 }> = {
  ready: { label: 'Pret', color: 'text-green-700 dark:text-green-300', icon: CheckCircle2 },
  passed: { label: 'Pret', color: 'text-green-700 dark:text-green-300', icon: CheckCircle2 },
  conditional: { label: 'Sous conditions', color: 'text-amber-700 dark:text-amber-300', icon: AlertTriangle },
  not_ready: { label: 'Non pret', color: 'text-red-700 dark:text-red-300', icon: XCircle },
};

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function GradeBadge({ grade }: { grade: string }) {
  const colors = GRADE_COLORS[grade] ?? GRADE_COLORS['F'];
  return (
    <div
      className={cn(
        'flex items-center justify-center w-20 h-20 rounded-full ring-4 text-4xl font-bold',
        colors.bg,
        colors.text,
        colors.ring,
      )}
    >
      {grade}
    </div>
  );
}

function SectionRow({ section }: { section: { section_name: string; items_count: number; completeness: number } }) {
  const [open, setOpen] = useState(false);
  const pct = Math.round(section.completeness * 100);

  return (
    <div className="border-b border-gray-100 dark:border-slate-700 last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-50 dark:hover:bg-slate-700/30 transition-colors text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span
            className={cn(
              'w-2 h-2 rounded-full flex-shrink-0',
              pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500',
            )}
          />
          <span className="text-sm text-gray-700 dark:text-slate-300 truncate">{section.section_name}</span>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <span className="text-xs text-gray-500 dark:text-slate-400">{section.items_count} elements</span>
          <span className="text-xs font-medium text-gray-600 dark:text-slate-300">{pct}%</span>
          {open ? (
            <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
          )}
        </div>
      </button>
      {open && (
        <div className="px-4 pb-3">
          <div className="h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all',
                pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500',
              )}
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-gray-500 dark:text-slate-400">
            {section.items_count} element{section.items_count > 1 ? 's' : ''} dans cette section
          </p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Artifact Content                                                   */
/* ------------------------------------------------------------------ */

function ArtifactContent({ data }: { data: SharedArtifactData }) {
  const expiresDate = new Date(data.expires_at).toLocaleDateString('fr-CH');
  const generatedDate = new Date(data.generated_at).toLocaleDateString('fr-CH', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
  const completePct = Math.round(data.overall_completeness * 100);
  const verdictCfg = VERDICT_LABELS[data.readiness_verdict ?? ''] ?? VERDICT_LABELS.not_ready;
  const VerdictIcon = verdictCfg.icon;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 transition-colors">
      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Minimal BatiConnect header */}
        <div className="flex items-center gap-2 mb-8">
          <Shield className="w-6 h-6 text-red-600" />
          <span className="text-lg font-bold text-gray-900 dark:text-white">BatiConnect</span>
        </div>

        {/* Pack title + building address */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm mb-6">
          <div className="flex items-center gap-5">
            {data.passport_grade && <GradeBadge grade={data.passport_grade} />}
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-red-600 dark:text-red-400 uppercase tracking-wider mb-1">
                {data.pack_name}
              </p>
              <h1 className="text-xl font-semibold text-gray-900 dark:text-white truncate">{data.building_address}</h1>
              <p className="text-sm text-gray-500 dark:text-slate-400">
                {data.building_postal_code} {data.building_city}, {data.building_canton}
              </p>
              <p className="mt-1.5 text-xs text-gray-400 dark:text-slate-500">Genere le {generatedDate}</p>
            </div>
          </div>
        </div>

        {/* Key metrics */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {data.passport_grade && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm text-center">
              <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                Grade
              </p>
              <span className={cn('text-3xl font-bold', (GRADE_COLORS[data.passport_grade] ?? GRADE_COLORS['F']).text)}>
                {data.passport_grade}
              </span>
            </div>
          )}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm text-center">
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-1">
              Completude
            </p>
            <span className="text-3xl font-bold text-gray-900 dark:text-white tabular-nums">{completePct}%</span>
          </div>
          {data.readiness_verdict && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm text-center">
              <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-1">
                Readiness
              </p>
              <div className="flex items-center justify-center gap-1.5 mt-1">
                <VerdictIcon className={cn('w-5 h-5', verdictCfg.color)} />
                <span className={cn('text-sm font-semibold', verdictCfg.color)}>{verdictCfg.label}</span>
              </div>
            </div>
          )}
        </div>

        {/* Sections list */}
        {data.sections.length > 0 && (
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm mb-6 overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-200 dark:border-slate-700">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Sections ({data.sections.length})</h2>
            </div>
            {data.sections.map((section, idx) => (
              <SectionRow key={idx} section={section} />
            ))}
          </div>
        )}

        {/* Caveats */}
        {data.caveats.length > 0 && (
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-amber-200 dark:border-amber-800 shadow-sm mb-6 overflow-hidden">
            <div className="px-4 py-3 border-b border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-500" />
                <h2 className="text-sm font-semibold text-amber-700 dark:text-amber-300">
                  Reserves ({data.caveats.length})
                </h2>
              </div>
            </div>
            <ul className="divide-y divide-amber-100 dark:divide-amber-900/30">
              {data.caveats.map((caveat, idx) => (
                <li key={idx} className="px-4 py-3 text-sm text-amber-700 dark:text-amber-300 flex items-start gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 flex-shrink-0 mt-1.5" />
                  {caveat}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Footer */}
        <div className="text-center space-y-3 pt-4 border-t border-gray-200 dark:border-slate-700">
          {data.sha256_hash && (
            <div className="flex items-center justify-center gap-2 text-[10px] text-gray-400 dark:text-slate-500 font-mono">
              <Hash className="w-3 h-3" />
              <span className="truncate max-w-xs">{data.sha256_hash}</span>
            </div>
          )}
          <div className="flex items-center justify-center gap-1.5 text-xs text-gray-400 dark:text-slate-500">
            <Lock className="w-3 h-3" />
            <span>Genere par BatiConnect</span>
          </div>
          <div className="flex items-center justify-center gap-1.5 text-xs text-gray-400 dark:text-slate-500">
            <Clock className="w-3 h-3" />
            <span>Ce lien expire le {expiresDate}</span>
          </div>
          {data.shared_by_org && (
            <p className="text-xs text-gray-400 dark:text-slate-500">Partage par {data.shared_by_org}</p>
          )}
          <p className="text-[10px] text-gray-300 dark:text-slate-600 mt-2">Powered by BatiConnect</p>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Expired page                                                       */
/* ------------------------------------------------------------------ */

function ExpiredView() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex items-center justify-center transition-colors">
      <div className="text-center max-w-sm mx-auto px-4">
        <div className="flex items-center justify-center gap-2 mb-6">
          <Shield className="w-6 h-6 text-red-600" />
          <span className="text-lg font-bold text-gray-900 dark:text-white">BatiConnect</span>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-8 shadow-sm">
          <Clock className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-4" />
          <h1 className="text-lg font-semibold text-gray-700 dark:text-slate-300 mb-2">Ce lien a expire</h1>
          <p className="text-sm text-gray-400 dark:text-slate-500">
            Le lien de partage que vous avez utilise n&apos;est plus valide. Veuillez contacter la personne qui vous
            l&apos;a envoye pour obtenir un nouveau lien.
          </p>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function SharedArtifactView() {
  const { accessToken } = useParams<{ accessToken: string }>();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['shared-artifact', accessToken],
    queryFn: () => fetchSharedArtifact(accessToken!),
    enabled: !!accessToken,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-red-600 mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-slate-400">Chargement...</p>
        </div>
      </div>
    );
  }

  // Check for expired / 410 errors
  if (isError) {
    const status = (error as any)?.response?.status;
    if (status === 410 || status === 404 || status === 403) {
      return <ExpiredView />;
    }
    return <ExpiredView />;
  }

  if (!data) {
    return <ExpiredView />;
  }

  // Check if expired based on data
  if (new Date(data.expires_at) < new Date()) {
    return <ExpiredView />;
  }

  return <ArtifactContent data={data} />;
}
