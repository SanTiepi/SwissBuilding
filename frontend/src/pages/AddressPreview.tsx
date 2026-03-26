import { useState, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuth } from '@/hooks/useAuth';
import { cn } from '@/utils/formatters';
import { intelligenceApi, type AddressPreviewResult } from '@/api/intelligence';
import {
  Search,
  MapPin,
  Loader2,
  ClipboardList,
  AlertTriangle,
  Ban,
  ArrowRight,
  Recycle,
  ChevronDown,
  ChevronRight,
  Shield,
  Zap,
  Building2,
} from 'lucide-react';

// --- Reusable sub-components ---

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-emerald-500',
  B: 'bg-green-500',
  C: 'bg-yellow-500',
  D: 'bg-orange-500',
  E: 'bg-red-500',
  F: 'bg-red-700',
};

function GradeBadge({ grade }: { grade: string | null }) {
  const g = (grade || 'F').toUpperCase();
  return (
    <div
      data-testid="grade-badge"
      className={cn(
        'inline-flex items-center justify-center w-16 h-16 rounded-2xl text-3xl font-black text-white shadow-xl',
        GRADE_COLORS[g] || GRADE_COLORS.F,
      )}
    >
      {g}
    </div>
  );
}

function ScoreCard({ label, value }: { label: string; value: number | null }) {
  if (value === null) return null;
  const pct = Math.round(value * 100);
  const color =
    pct >= 80
      ? 'text-emerald-600 dark:text-emerald-400'
      : pct >= 60
        ? 'text-green-600 dark:text-green-400'
        : pct >= 40
          ? 'text-yellow-600 dark:text-yellow-400'
          : 'text-red-600 dark:text-red-400';
  return (
    <div className="text-center p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60" data-testid="score-card">
      <p className="text-[11px] text-slate-500 dark:text-slate-400 mb-1">{label}</p>
      <p className={cn('text-2xl font-bold', color)}>{pct}</p>
      <p className="text-[10px] text-slate-400">/100</p>
    </div>
  );
}

function RiskBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? 'bg-red-500' : pct >= 60 ? 'bg-orange-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-green-500';
  return (
    <div className="space-y-1" data-testid="risk-bar">
      <div className="flex justify-between text-xs text-slate-600 dark:text-slate-400">
        <span className="capitalize font-medium">{label}</span>
        <span className="font-bold">{pct}%</span>
      </div>
      <div className="h-2.5 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
        <div className={cn('h-full rounded-full transition-all duration-1000 ease-out', color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function KVRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800 last:border-0">
      <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
      <span className="text-xs font-medium text-slate-800 dark:text-slate-200">{String(value)}</span>
    </div>
  );
}

interface CollapsibleProps {
  title: string;
  icon: React.ReactNode;
  headerColor: string;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
  children: React.ReactNode;
  testId: string;
}

function Collapsible({ title, icon, headerColor, defaultOpen = true, badge, children, testId }: CollapsibleProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div data-testid={testId} className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn('w-full flex items-center gap-3 px-5 py-4 text-left font-semibold text-sm transition-colors', headerColor)}
        data-testid={`${testId}-toggle`}
      >
        {icon}
        <span className="flex-1">{title}</span>
        {badge}
        {open ? <ChevronDown className="w-4 h-4 opacity-60" /> : <ChevronRight className="w-4 h-4 opacity-60" />}
      </button>
      {open && <div className="px-5 py-4 bg-white dark:bg-slate-900 space-y-3">{children}</div>}
    </div>
  );
}

function formatCHF(v: number | null | undefined): string {
  if (v === null || v === undefined) return '-';
  return `CHF ${v.toLocaleString('fr-CH', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

// --- Loading animation ---

const LOADING_SOURCES = [
  'geo.admin.ch (geocodage)',
  'RegBL (registre)',
  'OFSP (radon)',
  'OFEV (bruit)',
  'OFEN (solaire)',
  'ARE (transports)',
  'Calcul des risques',
  'Score intelligence',
];

function LoadingProgress() {
  const { t } = useTranslation();
  const [step, setStep] = useState(0);

  useState(() => {
    let i = 0;
    const iv = setInterval(() => {
      i += 1;
      if (i >= LOADING_SOURCES.length) {
        clearInterval(iv);
      }
      setStep(i);
    }, 400);
    return () => clearInterval(iv);
  });

  return (
    <div className="py-12" data-testid="loading-progress">
      <div className="max-w-md mx-auto space-y-3">
        <div className="flex items-center justify-center gap-3 mb-6">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
          <p className="text-sm font-medium text-slate-600 dark:text-slate-400">
            {t('intelligence.loading') || 'Analyse en cours...'}
          </p>
        </div>
        {LOADING_SOURCES.map((src, i) => (
          <div
            key={src}
            className={cn(
              'flex items-center gap-3 px-4 py-2 rounded-lg text-sm transition-all duration-500',
              i < step
                ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-400'
                : i === step
                  ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 animate-pulse'
                  : 'bg-slate-50 dark:bg-slate-800/40 text-slate-400',
            )}
          >
            {i < step ? (
              <span className="text-emerald-500 text-xs">&#10003;</span>
            ) : i === step ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <span className="w-3 h-3 rounded-full bg-slate-300 dark:bg-slate-600" />
            )}
            <span>{src}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// --- Result view for address preview (flat sections mapped to 5 questions) ---

function AddressPreviewResultView({ data }: { data: AddressPreviewResult }) {
  const { t } = useTranslation();

  const pollutantEntries = Object.entries(data.risk.pollutant_prediction || {}).filter(
    ([, v]) => typeof v === 'number',
  ) as [string, number][];

  const blockerCount = data.compliance.non_compliant_count;

  return (
    <div className="space-y-4 mt-8" data-testid="preview-result">
      {/* Section 1: Ce qu'on sait */}
      <Collapsible
        testId="preview-what-we-know"
        title={t('intelligence.what_we_know') || "Ce qu'on sait"}
        icon={<ClipboardList className="w-5 h-5" />}
        headerColor="bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
              {t('intelligence.identity') || 'Identite'}
            </h4>
            <KVRow label="Adresse" value={data.identity.address_normalized} />
            <KVRow label="EGID" value={data.identity.egid} />
            <KVRow label="EGRID" value={data.identity.egrid} />
            <KVRow label="Parcelle" value={data.identity.parcel} />
            <KVRow label="Latitude" value={data.identity.lat?.toFixed(5)} />
            <KVRow label="Longitude" value={data.identity.lon?.toFixed(5)} />
          </div>
          <div>
            <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
              {t('intelligence.physical') || 'Physique'}
            </h4>
            <KVRow label={t('intelligence.construction_year') || 'Annee'} value={data.physical.construction_year} />
            <KVRow label={t('intelligence.floors') || 'Etages'} value={data.physical.floors} />
            <KVRow label={t('intelligence.dwellings') || 'Logements'} value={data.physical.dwellings} />
            <KVRow label={t('intelligence.surface') || 'Surface'} value={data.physical.surface_m2 ? `${data.physical.surface_m2} m2` : null} />
            <KVRow label={t('intelligence.heating') || 'Chauffage'} value={data.physical.heating_type} />
          </div>
        </div>
        {/* Energy */}
        <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
          <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
            {t('intelligence.energy') || 'Energie'}
          </h4>
          <KVRow label={t('intelligence.solar') || 'Potentiel solaire'} value={data.energy.solar_potential ? 'Disponible' : null} />
          <KVRow label={t('intelligence.district_heating') || 'CAD'} value={data.energy.district_heating_available ? 'Oui' : null} />
        </div>
        {/* Environment */}
        <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
          <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
            {t('intelligence.environment') || 'Environnement'}
          </h4>
          <KVRow label="Radon" value={data.environment.radon ? 'Donnees disponibles' : null} />
          <KVRow label={t('intelligence.noise') || 'Bruit'} value={data.environment.noise ? 'Donnees disponibles' : null} />
          <KVRow label={t('intelligence.hazards') || 'Dangers'} value={data.environment.hazards ? 'Donnees disponibles' : null} />
          <KVRow label={t('intelligence.seismic') || 'Seisme'} value={data.environment.seismic ? 'Donnees disponibles' : null} />
        </div>
      </Collapsible>

      {/* Section 2: Les risques */}
      <Collapsible
        testId="preview-what-is-risky"
        title={t('intelligence.what_is_risky') || 'Les risques'}
        icon={<AlertTriangle className="w-5 h-5" />}
        headerColor={
          pollutantEntries.some(([, v]) => v >= 0.8)
            ? 'bg-red-50 text-red-800 dark:bg-red-900/30 dark:text-red-300'
            : 'bg-orange-50 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300'
        }
      >
        {pollutantEntries.length > 0 ? (
          <div className="space-y-3">
            {pollutantEntries.map(([k, v]) => (
              <RiskBar key={k} label={k.replace(/_/g, ' ')} value={v} />
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t('intelligence.no_pollutant_data') || 'Aucune prediction de risque polluant'}
          </p>
        )}
        {data.risk.environmental_score !== null && (
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
            <KVRow
              label={t('intelligence.environmental_risk') || 'Score risque environnemental'}
              value={`${data.risk.environmental_score.toFixed(1)}/10`}
            />
          </div>
        )}
        {data.compliance.non_compliant_count > 0 && (
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
            <KVRow
              label={t('intelligence.non_compliant') || 'Non-conformites'}
              value={`${data.compliance.non_compliant_count} / ${data.compliance.checks_count}`}
            />
          </div>
        )}
      </Collapsible>

      {/* Section 3: Ce qui bloque */}
      <Collapsible
        testId="preview-what-blocks"
        title={t('intelligence.what_blocks') || 'Ce qui bloque'}
        icon={<Ban className="w-5 h-5" />}
        headerColor={
          blockerCount > 0
            ? 'bg-red-50 text-red-800 dark:bg-red-900/30 dark:text-red-300'
            : 'bg-slate-50 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
        }
        badge={
          blockerCount > 0 ? (
            <span className="bg-red-500 text-white text-[10px] px-2 py-0.5 rounded-full font-bold">{blockerCount}</span>
          ) : (
            <span className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 text-[10px] px-2 py-0.5 rounded-full font-medium">OK</span>
          )
        }
        defaultOpen={blockerCount > 0}
      >
        {blockerCount === 0 ? (
          <p className="text-xs text-green-600 dark:text-green-400">
            {t('intelligence.no_blockers') || 'Aucun blocage identifie a ce stade'}
          </p>
        ) : (
          <p className="text-xs text-red-600 dark:text-red-400">
            {data.compliance.summary || `${blockerCount} non-conformite(s) detectee(s)`}
          </p>
        )}
      </Collapsible>

      {/* Section 4: Quoi faire maintenant */}
      <Collapsible
        testId="preview-what-to-do"
        title={t('intelligence.what_to_do_next') || 'Quoi faire maintenant'}
        icon={<ArrowRight className="w-5 h-5" />}
        headerColor="bg-blue-50 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
      >
        {data.renovation.plan_summary ? (
          <div className="space-y-2">
            <p className="text-sm text-slate-700 dark:text-slate-300">{data.renovation.plan_summary}</p>
            <div className="grid grid-cols-2 gap-3 mt-2">
              <KVRow label={t('intelligence.total_cost') || 'Cout total'} value={formatCHF(data.renovation.total_cost)} />
              <KVRow label={t('intelligence.subsidies') || 'Subventions'} value={formatCHF(data.renovation.total_subsidy)} />
              <KVRow label={t('intelligence.roi') || 'ROI'} value={data.renovation.roi_years ? `${data.renovation.roi_years} ans` : null} />
            </div>
          </div>
        ) : (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t('intelligence.no_renovation') || 'Plan de renovation non calcule'}
          </p>
        )}
        {data.financial.cost_of_inaction && (
          <div className="mt-2 p-3 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800">
            <p className="text-xs font-medium text-orange-700 dark:text-orange-300">
              {t('intelligence.cost_of_inaction') || "Cout de l'inaction"}: {formatCHF(data.financial.cost_of_inaction)}
            </p>
          </div>
        )}
      </Collapsible>

      {/* Section 5: Ce qui sera reutilisable */}
      <Collapsible
        testId="preview-what-is-reusable"
        title={t('intelligence.what_is_reusable') || 'Ce qui sera reutilisable'}
        icon={<Recycle className="w-5 h-5" />}
        headerColor="bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300"
        defaultOpen={false}
      >
        <div className="space-y-2">
          <p className="text-xs text-slate-600 dark:text-slate-400">
            {t('intelligence.reusable_explanation') ||
              "Toutes les donnees collectees lors de cette analyse enrichissent le batiment de maniere permanente. Diagnostic, enrichissement, preuves — tout est capitalise dans la memoire du batiment."}
          </p>
          <div className="flex items-center gap-2 mt-2">
            <Shield className="w-4 h-4 text-emerald-500" />
            <span className="text-xs font-medium text-emerald-600 dark:text-emerald-400">
              {data.metadata.sources_used.length} {t('intelligence.sources_enriched') || 'sources interrogees'}
            </span>
          </div>
        </div>
      </Collapsible>

      {/* Scores dashboard */}
      <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6" data-testid="scores-dashboard">
        <div className="flex flex-col sm:flex-row items-center gap-6">
          <GradeBadge grade={data.scores.overall_grade} />
          <div className="flex-1 grid grid-cols-3 gap-3">
            <ScoreCard label={t('intelligence.neighborhood') || 'Quartier'} value={data.scores.neighborhood} />
            <ScoreCard label={t('intelligence.livability') || 'Habitabilite'} value={data.scores.livability} />
            <ScoreCard label={t('intelligence.connectivity') || 'Connectivite'} value={data.scores.connectivity} />
          </div>
        </div>
        {/* Metadata */}
        <div className="flex items-center gap-4 mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
          <Zap className="w-4 h-4 text-slate-400" />
          <span className="text-[11px] text-slate-500 dark:text-slate-400">
            {data.metadata.sources_used.length} {t('intelligence.sources') || 'sources'} | {t('intelligence.freshness') || 'Fraicheur'}: {data.metadata.freshness}
          </span>
        </div>
      </div>

      {/* CTA */}
      <div className="text-center pt-4">
        <button
          type="button"
          className="inline-flex items-center gap-2 px-8 py-3.5 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all text-sm"
          data-testid="create-building-cta"
          onClick={() => {
            /* TODO: navigate to building creation with pre-filled data */
          }}
        >
          <Building2 className="w-5 h-5" />
          {t('intelligence.create_building') || 'Creer le dossier batiment'}
        </button>
      </div>

      {/* Narrative */}
      {data.narrative.summary_fr && (
        <div className="rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 p-5 mt-2">
          <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed italic">
            &laquo; {data.narrative.summary_fr} &raquo;
          </p>
        </div>
      )}
    </div>
  );
}

// --- Main page ---

export default function AddressPreview() {
  const { t } = useTranslation();
  useAuth();

  const [address, setAddress] = useState('');
  const [postalCode, setPostalCode] = useState('');
  const [city, setCity] = useState('');

  const mutation = useMutation({
    mutationFn: () =>
      intelligenceApi.postAddressPreview({
        address,
        postal_code: postalCode || undefined,
        city: city || undefined,
      }),
  });

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!address.trim()) return;
      mutation.mutate();
    },
    [address, postalCode, city, mutation],
  );

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-white dark:from-slate-950 dark:to-slate-900">
      <div className="max-w-3xl mx-auto px-4 py-8 sm:py-16">
        {/* Hero */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-red-600 text-white mb-6 shadow-xl">
            <MapPin className="w-8 h-8" />
          </div>
          <h1
            className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight"
            data-testid="hero-title"
          >
            {t('intelligence.hero_title') || 'Entrez une adresse, decouvrez tout en 10 secondes'}
          </h1>
          <p className="mt-3 text-base text-slate-500 dark:text-slate-400 max-w-lg mx-auto">
            {t('intelligence.hero_subtitle') || 'Intelligence batiment instantanee: identite, risques, obligations, actions.'}
          </p>
        </div>

        {/* Search form */}
        <form onSubmit={handleSubmit} className="space-y-4" data-testid="address-form">
          <div>
            <input
              type="text"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder={t('intelligence.address_placeholder') || 'Rue et numero (ex: Rue du Midi 15)'}
              className="w-full px-5 py-4 text-lg rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-red-500 focus:ring-4 focus:ring-red-500/10 transition-all"
              data-testid="address-input"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <input
              type="text"
              value={postalCode}
              onChange={(e) => setPostalCode(e.target.value)}
              placeholder={t('intelligence.postal_code') || 'NPA (ex: 1003)'}
              className="px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-red-500 transition-all text-sm"
              data-testid="postal-code-input"
            />
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder={t('intelligence.city') || 'Ville (ex: Lausanne)'}
              className="px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-red-500 transition-all text-sm"
              data-testid="city-input"
            />
          </div>
          <button
            type="submit"
            disabled={mutation.isPending || !address.trim()}
            className={cn(
              'w-full flex items-center justify-center gap-3 px-6 py-4 rounded-xl font-semibold text-base transition-all shadow-lg',
              mutation.isPending
                ? 'bg-slate-400 cursor-not-allowed text-white'
                : 'bg-red-600 hover:bg-red-700 text-white hover:shadow-xl active:scale-[0.99]',
            )}
            data-testid="discover-button"
          >
            {mutation.isPending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Search className="w-5 h-5" />
            )}
            {mutation.isPending
              ? t('intelligence.analyzing') || 'Analyse en cours...'
              : t('intelligence.discover') || 'Decouvrir'}
          </button>
        </form>

        {/* Loading */}
        {mutation.isPending && <LoadingProgress />}

        {/* Error */}
        {mutation.isError && (
          <div
            className="mt-6 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-sm"
            data-testid="error-message"
          >
            {t('intelligence.error') || "Erreur lors de l'analyse. Verifiez l'adresse et reessayez."}
          </div>
        )}

        {/* Result */}
        {mutation.isSuccess && mutation.data && <AddressPreviewResultView data={mutation.data} />}
      </div>
    </div>
  );
}
