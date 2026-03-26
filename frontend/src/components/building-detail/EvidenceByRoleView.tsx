import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { intelligenceApi } from '@/api/intelligence';
import { decisionViewApi } from '@/api/decisionView';
import type { InstantCardResult } from '@/api/intelligence';
import type { DecisionView, AudienceReadiness } from '@/api/decisionView';
import {
  ClipboardList,
  AlertTriangle,
  Ban,
  ArrowRight,
  Recycle,
  ChevronDown,
  ChevronRight,
  Users,
  ShieldAlert,
  Eye,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type AudienceRole = 'property_manager' | 'authority' | 'insurer' | 'diagnostician' | 'contractor';

interface RoleConfig {
  key: AudienceRole;
  icon: React.ReactNode;
  color: string;
  activeColor: string;
}

interface EvidenceByRoleViewProps {
  buildingId: string;
  /** Pre-fetched instant card data (optional — will fetch if not provided) */
  instantCard?: InstantCardResult;
}

// ---------------------------------------------------------------------------
// Role definitions
// ---------------------------------------------------------------------------

const ROLES: RoleConfig[] = [
  {
    key: 'property_manager',
    icon: <Users className="w-4 h-4" />,
    color: 'text-slate-600 dark:text-slate-400 border-slate-300 dark:border-slate-600',
    activeColor: 'bg-blue-600 text-white border-blue-600 dark:bg-blue-500 dark:border-blue-500',
  },
  {
    key: 'authority',
    icon: <ShieldAlert className="w-4 h-4" />,
    color: 'text-slate-600 dark:text-slate-400 border-slate-300 dark:border-slate-600',
    activeColor: 'bg-red-600 text-white border-red-600 dark:bg-red-500 dark:border-red-500',
  },
  {
    key: 'insurer',
    icon: <Eye className="w-4 h-4" />,
    color: 'text-slate-600 dark:text-slate-400 border-slate-300 dark:border-slate-600',
    activeColor: 'bg-amber-600 text-white border-amber-600 dark:bg-amber-500 dark:border-amber-500',
  },
  {
    key: 'diagnostician',
    icon: <ClipboardList className="w-4 h-4" />,
    color: 'text-slate-600 dark:text-slate-400 border-slate-300 dark:border-slate-600',
    activeColor: 'bg-emerald-600 text-white border-emerald-600 dark:bg-emerald-500 dark:border-emerald-500',
  },
  {
    key: 'contractor',
    icon: <ArrowRight className="w-4 h-4" />,
    color: 'text-slate-600 dark:text-slate-400 border-slate-300 dark:border-slate-600',
    activeColor: 'bg-purple-600 text-white border-purple-600 dark:bg-purple-500 dark:border-purple-500',
  },
];

// ---------------------------------------------------------------------------
// Role-specific filtering logic
// ---------------------------------------------------------------------------

function filterForRole(role: AudienceRole, card: InstantCardResult, decisionView: DecisionView | undefined) {
  // Find matching audience readiness from decision view
  const audienceMap: Record<AudienceRole, string> = {
    property_manager: 'transaction',
    authority: 'authority',
    insurer: 'insurer',
    diagnostician: 'authority', // diagnosticians care about authority-facing data
    contractor: 'transaction',
  };
  const audienceKey = audienceMap[role];
  const audienceReadiness = decisionView?.audience_readiness?.find(
    (ar: AudienceReadiness) => ar.audience === audienceKey,
  );

  return {
    whatWeKnow: filterKnowledge(role, card),
    whatIsRisky: filterRisks(role, card, decisionView),
    whatBlocks: filterBlockers(role, card, decisionView),
    whatToDoNext: filterActions(role, card),
    whatIsReusable: filterReusable(role, card),
    audienceReadiness,
    caveats: audienceReadiness?.caveats || [],
  };
}

function filterKnowledge(role: AudienceRole, card: InstantCardResult): string[] {
  const items: string[] = [];
  const wk = card.what_we_know || ({} as any);
  const { identity, physical, diagnostics } = wk;
  const residual_materials = wk.residual_materials || [];

  switch (role) {
    case 'property_manager':
      if (identity?.address) items.push(`Adresse: ${identity.address}`);
      if (identity?.egrid) items.push(`EGRID: ${identity.egrid}`);
      if (physical?.surface_m2) items.push(`Surface: ${physical.surface_m2} m2`);
      if (physical?.dwellings) items.push(`Logements: ${physical.dwellings}`);
      if (diagnostics?.summary) items.push(`Diagnostics: ${diagnostics.summary}`);
      break;
    case 'authority':
      if (identity?.egid) items.push(`EGID: ${identity.egid}`);
      if (identity?.parcel) items.push(`Parcelle: ${identity.parcel}`);
      if (physical?.construction_year) items.push(`Annee: ${physical.construction_year}`);
      if (diagnostics?.summary) items.push(`Diagnostics: ${diagnostics.summary}`);
      if (residual_materials.length > 0) items.push(`Materiaux residuels: ${residual_materials.length} identifies`);
      break;
    case 'insurer':
      if (identity?.address) items.push(`Adresse: ${identity.address}`);
      if (physical?.construction_year) items.push(`Annee: ${physical.construction_year}`);
      if (physical?.surface_m2) items.push(`Surface: ${physical.surface_m2} m2`);
      if (residual_materials.filter((m) => m.status !== 'removed').length > 0)
        items.push(`Materiaux actifs: ${residual_materials.filter((m) => m.status !== 'removed').length}`);
      break;
    case 'diagnostician':
      if (identity?.egid) items.push(`EGID: ${identity.egid}`);
      if (physical?.floors) items.push(`Etages: ${physical.floors}`);
      if (physical?.construction_year) items.push(`Annee: ${physical.construction_year}`);
      if (physical?.heating_type) items.push(`Chauffage: ${physical.heating_type}`);
      if (diagnostics?.summary) items.push(`Diagnostics: ${diagnostics.summary}`);
      residual_materials.forEach((m) => {
        items.push(`${m.material_type}: ${m.status}${m.location ? ` (${m.location})` : ''}`);
      });
      break;
    case 'contractor':
      if (identity?.address) items.push(`Adresse: ${identity.address}`);
      if (physical?.floors) items.push(`Etages: ${physical.floors}`);
      if (physical?.surface_m2) items.push(`Surface: ${physical.surface_m2} m2`);
      residual_materials
        .filter((m) => m.status !== 'removed')
        .forEach((m) => {
          items.push(`${m.material_type}: ${m.status}${m.location ? ` (${m.location})` : ''}`);
        });
      break;
  }
  if (items.length === 0) items.push('Aucune donnee pertinente identifiee');
  return items;
}

function filterRisks(role: AudienceRole, card: InstantCardResult, decisionView: DecisionView | undefined): string[] {
  const items: string[] = [];
  const risky = card.what_is_risky || ({} as any);
  const pollutants = Object.entries(risky.pollutant_risk || {}).filter(
    ([, v]) => typeof v === 'number',
  ) as [string, number][];

  // All roles care about high pollutant risks, but threshold differs
  const threshold = role === 'diagnostician' ? 0.2 : role === 'authority' ? 0.4 : 0.5;
  pollutants
    .filter(([, v]) => v >= threshold)
    .forEach(([k, v]) => {
      items.push(`${k.replace(/_/g, ' ')}: ${Math.round(v * 100)}%`);
    });

  // Compliance gaps — relevant for authority, property_manager, insurer
  if (['authority', 'property_manager', 'insurer'].includes(role)) {
    (risky.compliance_gaps || []).forEach((g) => {
      items.push(String(g.description || g.label || JSON.stringify(g)));
    });
  }

  // Add blocker count from decision view for context
  if (decisionView && decisionView.blockers.length > 0 && ['authority', 'property_manager'].includes(role)) {
    items.push(`${decisionView.blockers.length} blocage(s) actif(s)`);
  }

  if (items.length === 0) items.push('Aucun risque significatif identifie');
  return items;
}

function filterBlockers(role: AudienceRole, card: InstantCardResult, decisionView: DecisionView | undefined): string[] {
  const items: string[] = [];
  const wb = card.what_blocks || ({} as any);
  const procedural = wb.procedural_blockers || [];
  const overdue = wb.overdue_obligations || [];
  const missing = wb.missing_proof || [];

  switch (role) {
    case 'property_manager':
      procedural.forEach((b: any) => items.push(String(b.description || b.label || JSON.stringify(b))));
      overdue.forEach((b: any) => items.push(String(b.description || b.label || JSON.stringify(b))));
      break;
    case 'authority':
      procedural.forEach((b: any) => items.push(String(b.description || b.label || JSON.stringify(b))));
      missing.forEach((b: any) => items.push(String(b.description || b.label || JSON.stringify(b))));
      break;
    case 'insurer':
      missing.forEach((b: any) => items.push(String(b.description || b.label || JSON.stringify(b))));
      break;
    case 'diagnostician':
      missing.forEach((b: any) => items.push(String(b.description || b.label || JSON.stringify(b))));
      break;
    case 'contractor':
      procedural.forEach((b: any) => items.push(String(b.description || b.label || JSON.stringify(b))));
      break;
  }

  // Add relevant decision view blockers
  if (decisionView) {
    decisionView.blockers
      .filter((bl) => {
        if (role === 'authority') return true;
        if (role === 'property_manager') return true;
        if (role === 'contractor') return bl.category === 'procedure_blocked';
        return false;
      })
      .forEach((bl) => {
        if (!items.includes(bl.title)) items.push(bl.title);
      });
  }

  if (items.length === 0) items.push('Aucun blocage identifie');
  return items;
}

function filterActions(role: AudienceRole, card: InstantCardResult): string[] {
  const items: string[] = [];
  const actions = (card.what_to_do_next || ({} as any)).top_3_actions || [];

  switch (role) {
    case 'property_manager':
      // All actions are relevant
      actions.forEach((a) => items.push(`${a.action} (${a.priority})`));
      break;
    case 'authority':
      // Focus on compliance/procedural actions
      actions
        .filter((a) => a.priority === 'high' || a.priority === 'critical')
        .forEach((a) => items.push(`${a.action} (${a.priority})`));
      break;
    case 'insurer':
      // Focus on risk mitigation
      actions
        .filter((a) => a.estimated_cost !== null || a.priority === 'high')
        .forEach((a) =>
          items.push(
            `${a.action}${a.estimated_cost !== null ? ` — CHF ${a.estimated_cost.toLocaleString('fr-CH')}` : ''}`,
          ),
        );
      break;
    case 'diagnostician':
      // Focus on evidence-gathering actions
      actions.filter((a) => a.evidence_needed).forEach((a) => items.push(`${a.action} → ${a.evidence_needed}`));
      if (items.length === 0) actions.forEach((a) => items.push(`${a.action} (${a.priority})`));
      break;
    case 'contractor':
      // Focus on intervention actions with cost
      actions.forEach((a) =>
        items.push(
          `${a.action}${a.estimated_cost !== null ? ` — CHF ${a.estimated_cost.toLocaleString('fr-CH')}` : ''}`,
        ),
      );
      break;
  }

  if (items.length === 0) items.push('Aucune action prioritaire');
  return items;
}

function filterReusable(role: AudienceRole, card: InstantCardResult): string[] {
  const items: string[] = [];
  const reusable = card.what_is_reusable || ({} as any);
  const diagnostic_publications = reusable.diagnostic_publications || [];
  const packs_generated = reusable.packs_generated || [];
  const proof_deliveries = reusable.proof_deliveries || [];

  if (['authority', 'diagnostician', 'property_manager'].includes(role) && diagnostic_publications.length > 0) {
    items.push(`${diagnostic_publications.length} publication(s) diagnostique(s)`);
  }
  if (['property_manager', 'insurer', 'authority'].includes(role) && packs_generated.length > 0) {
    items.push(`${packs_generated.length} pack(s) genere(s)`);
  }
  if (['authority', 'insurer'].includes(role) && proof_deliveries.length > 0) {
    items.push(`${proof_deliveries.length} livraison(s) de preuve`);
  }
  if (['contractor'].includes(role) && packs_generated.length > 0) {
    items.push(`${packs_generated.length} pack(s) disponible(s)`);
  }

  if (items.length === 0) items.push('Aucun element reutilisable');
  return items;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface QuestionSectionProps {
  title: string;
  icon: React.ReactNode;
  headerColor: string;
  items: string[];
  emptyLabel: string;
  testId: string;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
}

function QuestionSection({
  title,
  icon,
  headerColor,
  items,
  emptyLabel,
  testId,
  defaultOpen = true,
  badge,
}: QuestionSectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const isEmpty = items.length === 1 && items[0].startsWith('Aucun');

  return (
    <div data-testid={testId} className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          'w-full flex items-center gap-3 px-4 py-3 text-left font-semibold text-sm transition-colors',
          headerColor,
        )}
        data-testid={`${testId}-toggle`}
      >
        {icon}
        <span className="flex-1">{title}</span>
        {badge}
        {open ? <ChevronDown className="w-4 h-4 opacity-60" /> : <ChevronRight className="w-4 h-4 opacity-60" />}
      </button>
      {open && (
        <div className="px-4 py-3 bg-white dark:bg-slate-900">
          {isEmpty ? (
            <p className="text-xs text-green-600 dark:text-green-400">{emptyLabel}</p>
          ) : (
            <ul className="space-y-1.5">
              {items.map((item, i) => (
                <li key={i} className="text-xs text-slate-700 dark:text-slate-300 flex items-start gap-2">
                  <span className="w-1 h-1 rounded-full bg-slate-400 dark:bg-slate-500 mt-1.5 shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function EvidenceByRoleView({ buildingId, instantCard: externalCard }: EvidenceByRoleViewProps) {
  const { t } = useTranslation();
  const [selectedRole, setSelectedRole] = useState<AudienceRole>('property_manager');

  // Fetch instant card if not provided
  const { data: fetchedCard } = useQuery({
    queryKey: ['instant-card', buildingId],
    queryFn: () => intelligenceApi.getInstantCard(buildingId),
    enabled: !externalCard,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  // Fetch decision view for audience readiness
  const { data: decisionView } = useQuery({
    queryKey: ['decision-view', buildingId],
    queryFn: () => decisionViewApi.get(buildingId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const card = externalCard || fetchedCard;

  if (!card) {
    return (
      <div
        className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-6"
        data-testid="evidence-by-role-loading"
      >
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <Users className="w-4 h-4 animate-pulse" />
          {t('evidence_by_role.loading') || 'Chargement de la vue par role...'}
        </div>
      </div>
    );
  }

  const filtered = filterForRole(selectedRole, card, decisionView);

  return (
    <div className="space-y-4" data-testid="evidence-by-role-view">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Users className="w-5 h-5 text-slate-600 dark:text-slate-400" />
        <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
          {t('evidence_by_role.title') || 'Evidence par role'}
        </h3>
      </div>

      {/* Role selector — horizontal pills */}
      <div className="flex flex-wrap gap-2" data-testid="role-selector">
        {ROLES.map((role) => (
          <button
            key={role.key}
            type="button"
            onClick={() => setSelectedRole(role.key)}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-all',
              selectedRole === role.key ? role.activeColor : role.color,
              selectedRole !== role.key && 'hover:bg-slate-100 dark:hover:bg-slate-700',
            )}
            data-testid={`role-pill-${role.key}`}
          >
            {role.icon}
            {t(`evidence_by_role.role_${role.key}`) || role.key.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* Caveats banner */}
      {filtered.caveats.length > 0 && (
        <div
          className="rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 p-3"
          data-testid="role-caveats"
        >
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            <span className="text-xs font-semibold text-amber-700 dark:text-amber-300">
              {t('evidence_by_role.caveats') || 'Reserves'}
            </span>
          </div>
          <ul className="space-y-1">
            {filtered.caveats.map((c, i) => (
              <li key={i} className="text-xs text-amber-600 dark:text-amber-400">
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Audience readiness summary */}
      {filtered.audienceReadiness?.has_pack && (
        <div
          className="flex flex-wrap gap-3 text-xs text-slate-500 dark:text-slate-400 px-1"
          data-testid="audience-readiness-summary"
        >
          <span>
            Pack v{filtered.audienceReadiness.latest_pack_version} ({filtered.audienceReadiness.latest_pack_status})
          </span>
          {filtered.audienceReadiness.unknowns_count > 0 && (
            <span className="text-amber-600 dark:text-amber-400">
              {filtered.audienceReadiness.unknowns_count} inconnu(s)
            </span>
          )}
          {filtered.audienceReadiness.contradictions_count > 0 && (
            <span className="text-red-600 dark:text-red-400">
              {filtered.audienceReadiness.contradictions_count} contradiction(s)
            </span>
          )}
          {filtered.audienceReadiness.residual_risks_count > 0 && (
            <span className="text-orange-600 dark:text-orange-400">
              {filtered.audienceReadiness.residual_risks_count} risque(s) residuel(s)
            </span>
          )}
        </div>
      )}

      {/* 5 question sections */}
      <QuestionSection
        testId="role-what-we-know"
        title={t('evidence_by_role.what_we_know') || "Ce qu'on sait"}
        icon={<ClipboardList className="w-4 h-4" />}
        headerColor="bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300"
        items={filtered.whatWeKnow}
        emptyLabel={t('evidence_by_role.no_knowledge') || 'Aucune donnee pertinente'}
      />

      <QuestionSection
        testId="role-what-is-risky"
        title={t('evidence_by_role.what_is_risky') || 'Les risques'}
        icon={<AlertTriangle className="w-4 h-4" />}
        headerColor="bg-orange-50 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300"
        items={filtered.whatIsRisky}
        emptyLabel={t('evidence_by_role.no_risks') || 'Aucun risque significatif'}
        badge={
          filtered.whatIsRisky.length > 1 || !filtered.whatIsRisky[0]?.startsWith('Aucun') ? (
            <span className="text-[10px] bg-white/60 dark:bg-slate-800/60 px-2 py-0.5 rounded-full font-medium">
              {filtered.whatIsRisky.filter((r) => !r.startsWith('Aucun')).length}
            </span>
          ) : undefined
        }
      />

      <QuestionSection
        testId="role-what-blocks"
        title={t('evidence_by_role.what_blocks') || 'Ce qui bloque'}
        icon={<Ban className="w-4 h-4" />}
        headerColor={
          filtered.whatBlocks.length > 1 || !filtered.whatBlocks[0]?.startsWith('Aucun')
            ? 'bg-red-50 text-red-800 dark:bg-red-900/30 dark:text-red-300'
            : 'bg-slate-50 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
        }
        items={filtered.whatBlocks}
        emptyLabel={t('evidence_by_role.no_blockers') || 'Aucun blocage identifie'}
        defaultOpen={filtered.whatBlocks.length > 1 || !filtered.whatBlocks[0]?.startsWith('Aucun')}
        badge={
          filtered.whatBlocks.length > 1 || !filtered.whatBlocks[0]?.startsWith('Aucun') ? (
            <span className="bg-red-500 text-white text-[10px] px-2 py-0.5 rounded-full font-bold">
              {filtered.whatBlocks.filter((b) => !b.startsWith('Aucun')).length}
            </span>
          ) : (
            <span className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 text-[10px] px-2 py-0.5 rounded-full font-medium">
              OK
            </span>
          )
        }
      />

      <QuestionSection
        testId="role-what-to-do"
        title={t('evidence_by_role.what_to_do_next') || 'Quoi faire maintenant'}
        icon={<ArrowRight className="w-4 h-4" />}
        headerColor="bg-blue-50 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
        items={filtered.whatToDoNext}
        emptyLabel={t('evidence_by_role.no_actions') || 'Aucune action prioritaire'}
      />

      <QuestionSection
        testId="role-what-is-reusable"
        title={t('evidence_by_role.what_is_reusable') || 'Ce qui sera reutilisable'}
        icon={<Recycle className="w-4 h-4" />}
        headerColor="bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300"
        items={filtered.whatIsReusable}
        emptyLabel={t('evidence_by_role.no_reusable') || 'Aucun element reutilisable'}
        defaultOpen={false}
      />
    </div>
  );
}
