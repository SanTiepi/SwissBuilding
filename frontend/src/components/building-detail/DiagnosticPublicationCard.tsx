import { useState } from 'react';
import { useTranslation } from '@/i18n';
import { ChevronDown, ChevronUp, FileText, Lock, Download, Paperclip, History, ClipboardList } from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface DiagnosticPublicationVersion {
  version: number;
  published_at: string;
  payload_hash: string;
}

export type MatchState = 'auto_matched' | 'manual_matched' | 'needs_review' | 'unmatched';

export interface DiagnosticPublicationAnnex {
  path: string;
  type: string;
  name: string;
}

export interface DiagnosticPublication {
  id: string;
  building_id: string | null;
  source_system: string;
  source_mission_id: string;
  current_version: number;
  match_state: MatchState | (string & {});
  match_key: string | null;
  match_key_type: string | null;
  mission_type: string;
  report_pdf_url: string | null;
  structured_summary: Record<string, unknown> | null;
  annexes: DiagnosticPublicationAnnex[] | Record<string, unknown>[];
  payload_hash: string;
  published_at: string;
  is_immutable: boolean;
  created_at: string;
  versions?: DiagnosticPublicationVersion[];
}

interface DiagnosticPublicationCardProps {
  publications: DiagnosticPublication[];
}

/* ------------------------------------------------------------------ */
/*  Style maps                                                         */
/* ------------------------------------------------------------------ */

const MATCH_STATE_STYLES: Record<string, string> = {
  auto_matched: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  manual_matched: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  needs_review: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  unmatched: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
};

const MISSION_TYPE_STYLES: Record<string, string> = {
  asbestos_full: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  pcb: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  lead: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  hap: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  radon: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  multi: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400',
};

const DEFAULT_BADGE = 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300';

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function DiagnosticPublicationCard({ publications }: DiagnosticPublicationCardProps) {
  const { t } = useTranslation();

  /* ---- empty state ---- */
  if (!publications || publications.length === 0) {
    return (
      <div
        className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6"
        data-testid="diagnostic-publication-card"
      >
        <div className="flex items-center gap-2 mb-4">
          <ClipboardList className="w-5 h-5 text-indigo-500" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('diag_pub.title') || 'Diagnostic Reports'}
          </h2>
        </div>
        <p className="text-sm text-gray-500 dark:text-slate-400" data-testid="diag-pub-empty">
          {t('diag_pub.empty') || 'No diagnostic publications available.'}
        </p>
      </div>
    );
  }

  return (
    <div
      className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6 space-y-4"
      data-testid="diagnostic-publication-card"
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <ClipboardList className="w-5 h-5 text-indigo-500" />
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('diag_pub.title') || 'Diagnostic Reports'}
        </h2>
        <span
          className="inline-flex items-center justify-center min-w-[1.5rem] h-6 px-2 text-xs font-medium rounded-full bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400"
          data-testid="diag-pub-count"
        >
          {publications.length}
        </span>
      </div>

      {/* Publication list */}
      <div className="space-y-3">
        {publications.map((pub) => (
          <PublicationRow key={pub.id} publication={pub} t={t} />
        ))}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Single publication row                                             */
/* ------------------------------------------------------------------ */

function PublicationRow({ publication: pub, t }: { publication: DiagnosticPublication; t: (key: string) => string }) {
  const [annexesOpen, setAnnexesOpen] = useState(false);
  const [versionsOpen, setVersionsOpen] = useState(false);

  const formattedDate = new Date(pub.published_at).toLocaleDateString();

  return (
    <div
      className="border border-gray-200 dark:border-slate-700 rounded-lg p-4 space-y-3"
      data-testid={`diag-pub-row-${pub.id}`}
    >
      {/* Top row: badges + date */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          {/* Mission type */}
          <span
            className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${MISSION_TYPE_STYLES[pub.mission_type] || DEFAULT_BADGE}`}
            data-testid="diag-pub-mission-type"
          >
            {t(`diag_pub.mission_${pub.mission_type}`) || pub.mission_type}
          </span>

          {/* Source system */}
          <span
            className="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-700 dark:bg-slate-600 dark:text-slate-200"
            data-testid="diag-pub-source"
          >
            {pub.source_system}
          </span>

          {/* Match state */}
          <span
            className={`inline-block px-2 py-0.5 text-xs font-medium rounded-full ${MATCH_STATE_STYLES[pub.match_state] || DEFAULT_BADGE}`}
            data-testid="diag-pub-match-state"
          >
            {t(`diag_pub.match_${pub.match_state}`) || pub.match_state}
          </span>
        </div>

        <span className="text-xs text-gray-500 dark:text-slate-400">{formattedDate}</span>
      </div>

      {/* Structured summary */}
      {pub.structured_summary && (
        <div className="text-sm text-gray-700 dark:text-slate-300 space-y-1" data-testid="diag-pub-summary">
          {pub.structured_summary.pollutants_found != null && (
            <p>
              <span className="font-medium">{t('diag_pub.pollutants_found') || 'Pollutants found'}:</span>{' '}
              {String(pub.structured_summary.pollutants_found)}
            </p>
          )}
          {pub.structured_summary.fach_urgency != null && (
            <p>
              <span className="font-medium">{t('diag_pub.fach_urgency') || 'FACH urgency'}:</span>{' '}
              {String(pub.structured_summary.fach_urgency)}
            </p>
          )}
          {pub.structured_summary.zones != null && (
            <p>
              <span className="font-medium">{t('diag_pub.zones') || 'Zones'}:</span>{' '}
              {String(pub.structured_summary.zones)}
            </p>
          )}
        </div>
      )}

      {/* PDF download */}
      {pub.report_pdf_url && (
        <a
          href={pub.report_pdf_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
          data-testid="diag-pub-pdf-link"
        >
          <Download className="w-4 h-4" />
          {t('diag_pub.download_pdf') || 'Download PDF'}
        </a>
      )}

      {/* Immutable indicator */}
      {pub.is_immutable && (
        <div
          className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-slate-400"
          data-testid="diag-pub-immutable"
        >
          <Lock className="w-3.5 h-3.5" />
          <span>{t('diag_pub.immutable') || 'Snapshot immuable'}</span>
        </div>
      )}

      {/* Annexes (collapsible) */}
      {pub.annexes.length > 0 && (
        <div>
          <button
            onClick={() => setAnnexesOpen((v) => !v)}
            className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white transition-colors"
            data-testid="diag-pub-annexes-toggle"
          >
            <Paperclip className="w-4 h-4" />
            <span>
              {t('diag_pub.annexes') || 'Annexes'} ({pub.annexes.length})
            </span>
            {annexesOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
          {annexesOpen && (
            <ul className="mt-2 space-y-1 pl-6" data-testid="diag-pub-annexes-list">
              {pub.annexes.map((annex, i) => {
                const a = annex as Record<string, unknown>;
                const name = String(a.name ?? `Annex ${i + 1}`);
                const type = a.type ? String(a.type) : undefined;
                return (
                  <li key={i} className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-400">
                    <FileText className="w-3.5 h-3.5 flex-shrink-0" />
                    <span>{name}</span>
                    {type && <span className="text-xs text-gray-400 dark:text-slate-500">({type})</span>}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      {/* Version history (collapsible) */}
      {pub.versions && pub.versions.length > 0 && (
        <div>
          <button
            onClick={() => setVersionsOpen((v) => !v)}
            className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white transition-colors"
            data-testid="diag-pub-versions-toggle"
          >
            <History className="w-4 h-4" />
            <span>
              {t('diag_pub.versions') || 'Version history'} ({pub.versions.length})
            </span>
            {versionsOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
          {versionsOpen && (
            <ul className="mt-2 space-y-1 pl-6" data-testid="diag-pub-versions-list">
              {pub.versions.map((ver) => (
                <li key={ver.version} className="text-sm text-gray-600 dark:text-slate-400">
                  <span className="font-medium">v{ver.version}</span>
                  {' — '}
                  {new Date(ver.published_at).toLocaleDateString()}
                  <span className="ml-2 font-mono text-xs text-gray-400 dark:text-slate-500">
                    {ver.payload_hash.slice(0, 12)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
