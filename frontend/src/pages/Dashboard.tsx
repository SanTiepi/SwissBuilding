/**
 * MIGRATION: ABSORB INTO Today
 * This page will be absorbed into the Today master workspace.
 * Per ADR-005 and V3 migration plan.
 * New features should target the master workspace directly.
 */
import { lazy, Suspense, useMemo } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useBuildings } from '@/hooks/useBuildings';
import { useQuery } from '@tanstack/react-query';
import { diagnosticsApi } from '@/api/diagnostics';
import { actionsApi } from '@/api/actions';
import { useTranslation } from '@/i18n';
import { formatDate, cn } from '@/utils/formatters';
import { RISK_COLORS, POLLUTANT_COLORS } from '@/utils/constants';
import type { ActionItem, Building, Diagnostic, RiskLevel, PollutantType } from '@/types';
import {
  Building2,
  Activity,
  AlertTriangle,
  ClipboardCheck,
  Plus,
  ArrowRight,
  TrendingUp,
  CheckCircle2,
  Calendar,
  Layers,
  Wrench,
  FileImage,
  FileText,
  Shield,
  Download,
  Briefcase,
  Eye,
} from 'lucide-react';
import { DashboardSkeleton } from '@/components/Skeleton';
import { PredictiveAlertsPortfolio } from '@/components/PredictiveAlerts';

const DashboardCharts = lazy(() =>
  import('@/components/DashboardCharts').then((m) => ({ default: m.DashboardCharts })),
);

const PASSPORT_GRADE_COLORS: Record<string, string> = {
  A: 'bg-emerald-500',
  B: 'bg-green-500',
  C: 'bg-yellow-500',
  D: 'bg-orange-500',
  E: 'bg-red-500',
  F: 'bg-red-700',
};

export default function Dashboard() {
  const { t, locale } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { data: buildingsData, isLoading: buildingsLoading, isError: buildingsError } = useBuildings();
  const {
    data: diagnosticsData,
    isLoading: diagnosticsLoading,
    isError: diagnosticsError,
  } = useQuery({
    queryKey: ['diagnostics', 'all'],
    queryFn: async () => {
      // Fetch diagnostics for all buildings from the buildings data
      const buildingsList = buildingsData?.items ?? [];
      if (!Array.isArray(buildingsList) || buildingsList.length === 0) return [];
      const results = await Promise.all(
        buildingsList.slice(0, 20).map((b) => diagnosticsApi.listByBuilding(b.id).catch(() => [])),
      );
      return results.flat();
    },
    enabled: !buildingsLoading && !!buildingsData,
  });

  const { data: myActions = [], isError: actionsError } = useQuery({
    queryKey: ['my-actions', user?.id],
    queryFn: () =>
      actionsApi.list({
        assigned_to: user?.id,
        status: 'open',
        limit: 5,
      }),
    enabled: !!user?.id,
  });

  const buildings = useMemo(() => buildingsData?.items ?? [], [buildingsData]);
  const diagnostics = diagnosticsData ?? [];

  const isLoading = buildingsLoading || diagnosticsLoading;

  const clientFitCopy = useMemo(() => {
    if (locale === 'fr') {
      return {
        badge: 'Positionnement client',
        title: 'Safe-to-start dossier pour gerances multi-batiments',
        description:
          'Pertinent quand des travaux approchent et que le dossier pre-travaux reste disperse entre rapports, annexes, plans et ERP.',
        tags: ['VD/GE first', 'amiante first', 'overlay ERP'],
        cards: [
          {
            label: 'Acheteur prioritaire',
            value: 'Gerances immobilieres multi-batiments en VD/GE',
          },
          {
            label: 'Douleur critique',
            value: 'Arrets, rework documentaire et pieces manquantes avant chantier',
          },
          {
            label: 'Posture produit',
            value: 'Couche de preuve et de readiness, sans remplacement ERP',
          },
        ],
        metrics: [
          { value: '>=95%', label: 'completude dossier cible' },
          { value: '<=2h', label: 'latence pack pret a partager' },
          { value: '100%', label: 'preuves critiques tracables' },
        ],
        primaryCta: 'Voir la readiness',
        secondaryCta: 'Voir le portefeuille',
        tertiaryCta: 'Explorer les immeubles',
        boundary:
          'Pas de garantie juridique: SwissBuilding rend la preuve, les manques et la preparation visibles avant travaux.',
      };
    }

    if (locale === 'de') {
      return {
        badge: 'Kundennutzen',
        title: 'Safe-to-start dossier fuer Multi-Building Property Manager',
        description:
          'Relevant wenn Arbeiten anstehen und der Pre-Work-Ordner zwischen Berichten, Laboranhaengen, Plaenen und ERP zerstreut bleibt.',
        tags: ['VD/GE first', 'asbestos first', 'ERP overlay'],
        cards: [
          {
            label: 'Prioritaerer Kaeufer',
            value: 'Multi-Building Property Manager in VD/GE',
          },
          {
            label: 'Kritischer Schmerz',
            value: 'Stop-work, Dokumenten-Rework und fehlende Nachweise vor Baubeginn',
          },
          {
            label: 'Produktrolle',
            value: 'Evidence- und Readiness-Layer, kein ERP-Ersatz',
          },
        ],
        metrics: [
          { value: '>=95%', label: 'Ziel fuer Dossier-Vollstaendigkeit' },
          { value: '<=2h', label: 'Zeit bis zum teilbaren Pack' },
          { value: '100%', label: 'kritische Nachweise rueckverfolgbar' },
        ],
        primaryCta: 'Readiness ansehen',
        secondaryCta: 'Portfolio ansehen',
        tertiaryCta: 'Gebaeude oeffnen',
        boundary:
          'Keine Rechtsgarantie: SwissBuilding macht Nachweise, Luecken und Bereitschaft vor Arbeitsbeginn sichtbar.',
      };
    }

    if (locale === 'it') {
      return {
        badge: 'Rilevanza cliente',
        title: 'Safe-to-start dossier per gestori immobiliari multi-edificio',
        description:
          'Rilevante quando i lavori si avvicinano e il dossier pre-lavori resta disperso tra report, allegati di laboratorio, planimetrie ed ERP.',
        tags: ['VD/GE first', 'amianto first', 'overlay ERP'],
        cards: [
          {
            label: 'Buyer prioritario',
            value: 'Gestori immobiliari multi-edificio in VD/GE',
          },
          {
            label: 'Dolore critico',
            value: 'Stop-work, rework documentale e prove mancanti prima del cantiere',
          },
          {
            label: 'Ruolo prodotto',
            value: 'Layer di evidenza e readiness, senza sostituire l ERP',
          },
        ],
        metrics: [
          { value: '>=95%', label: 'completezza dossier obiettivo' },
          { value: '<=2h', label: 'tempo per pack condivisibile' },
          { value: '100%', label: 'prove critiche tracciabili' },
        ],
        primaryCta: 'Vedi readiness',
        secondaryCta: 'Vedi portafoglio',
        tertiaryCta: 'Apri edifici',
        boundary:
          'Nessuna garanzia legale: SwissBuilding rende visibili prove, mancanze e preparazione prima dei lavori.',
      };
    }

    return {
      badge: 'Client Fit',
      title: 'Safe-to-start dossier for multi-building property managers',
      description:
        'Most relevant when works are approaching and the pre-work dossier is still scattered across reports, lab annexes, plans, and ERP archives.',
      tags: ['VD/GE first', 'asbestos first', 'ERP overlay'],
      cards: [
        {
          label: 'Priority buyer',
          value: 'Multi-building property managers in VD/GE',
        },
        {
          label: 'Critical pain',
          value: 'Stop-work risk, documentary rework, and missing evidence before works start',
        },
        {
          label: 'Product posture',
          value: 'Evidence and readiness layer, not an ERP replacement',
        },
      ],
      metrics: [
        { value: '>=95%', label: 'target dossier completeness' },
        { value: '<=2h', label: 'shareable pack latency target' },
        { value: '100%', label: 'critical evidence traceability' },
      ],
      primaryCta: 'Open readiness',
      secondaryCta: 'Open portfolio',
      tertiaryCta: 'Browse buildings',
      boundary:
        'No legal guarantee claim: SwissBuilding makes evidence, gaps, and readiness visible before works start.',
    };
  }, [locale]);

  // KPIs — primary row
  const totalBuildings = Array.isArray(buildings) ? buildings.length : 0;
  const activeDiagnostics = Array.isArray(diagnostics)
    ? diagnostics.filter((d: Diagnostic) => d.status === 'in_progress' || d.status === 'draft').length
    : 0;
  const highRiskBuildings = Array.isArray(buildings)
    ? buildings.filter((b: Building) => {
        const level = b.risk_scores?.overall_risk_level || 'unknown';
        return level === 'high' || level === 'critical';
      }).length
    : 0;
  const pendingValidations = Array.isArray(diagnostics)
    ? diagnostics.filter((d: Diagnostic) => d.status === 'completed').length
    : 0;

  // KPIs — secondary row
  const openActionsCount = Array.isArray(myActions) ? myActions.length : 0;
  const totalDocuments = Array.isArray(diagnostics) ? diagnostics.length : 0;
  const complianceAlerts = highRiskBuildings;
  const avgTrustScore = useMemo(() => {
    if (!Array.isArray(buildings) || buildings.length === 0) return null;
    const scores = buildings
      .map((b: Building) => b.risk_scores?.confidence)
      .filter((c): c is number => typeof c === 'number');
    if (scores.length === 0) return null;
    return Math.round((scores.reduce((sum, s) => sum + s, 0) / scores.length) * 100);
  }, [buildings]);

  // Building address lookup for recent activity
  const buildingMap = useMemo(() => {
    if (!Array.isArray(buildings)) return new Map<string, Building>();
    const map = new Map<string, Building>();
    buildings.forEach((b: Building) => map.set(b.id, b));
    return map;
  }, [buildings]);

  // Risk distribution
  const riskDistribution = (() => {
    if (!Array.isArray(buildings)) return [];
    const counts: Record<string, number> = { low: 0, medium: 0, high: 0, critical: 0 };
    buildings.forEach((b: Building) => {
      const level = b.risk_scores?.overall_risk_level || 'low';
      counts[level] = (counts[level] || 0) + 1;
    });
    return Object.entries(counts).map(([level, count]) => ({
      name: t(`risk.${level}`),
      value: count,
      color: RISK_COLORS[level as RiskLevel] || '#94a3b8',
    }));
  })();

  // Pollutant distribution
  const pollutantDistribution = (() => {
    if (!Array.isArray(diagnostics)) return [];
    const counts: Record<string, number> = {};
    diagnostics.forEach((d) => {
      const p = d.diagnostic_type;
      if (p) counts[p] = (counts[p] || 0) + 1;
    });
    return Object.entries(counts).map(([type, count]) => ({
      name: t(`pollutant.${type}`),
      count,
      fill: POLLUTANT_COLORS[type as PollutantType] || '#64748b',
    }));
  })();

  // Portfolio health — passport grade distribution
  const gradeDistribution = useMemo(() => {
    if (!Array.isArray(buildings) || buildings.length === 0) return [];
    const counts: Record<string, number> = { A: 0, B: 0, C: 0, D: 0, E: 0, F: 0 };
    buildings.forEach((b: Building) => {
      const level = b.risk_scores?.overall_risk_level;
      // Map risk levels to approximate grades
      if (level === 'low') counts['A'] += 1;
      else if (level === 'medium') counts['C'] += 1;
      else if (level === 'high') counts['D'] += 1;
      else if (level === 'critical') counts['F'] += 1;
      else counts['B'] += 1;
    });
    return Object.entries(counts).map(([grade, count]) => ({ grade, count }));
  }, [buildings]);

  // Recent activity (last 8 diagnostics as events)
  const recentActivity = Array.isArray(diagnostics)
    ? diagnostics
        .sort(
          (a: Diagnostic, b: Diagnostic) =>
            new Date(b.updated_at || b.created_at).getTime() - new Date(a.updated_at || a.created_at).getTime(),
        )
        .slice(0, 8)
    : [];

  const kpis = [
    { label: t('dashboard.total_buildings'), value: totalBuildings, icon: Building2, color: 'bg-blue-500' },
    { label: t('dashboard.total_diagnostics'), value: activeDiagnostics, icon: Activity, color: 'bg-emerald-500' },
    { label: t('dashboard.high_risk'), value: highRiskBuildings, icon: AlertTriangle, color: 'bg-orange-500' },
    {
      label: t('dashboard.pending_diagnostics'),
      value: pendingValidations,
      icon: ClipboardCheck,
      color: 'bg-purple-500',
    },
  ];

  const secondaryKpis = [
    {
      label: t('action.my_actions') || 'Open Actions',
      value: openActionsCount,
      icon: CheckCircle2,
      color: 'bg-cyan-500',
    },
    {
      label: t('document.title') || 'Documents',
      value: totalDocuments,
      icon: FileText,
      color: 'bg-indigo-500',
    },
    {
      label: t('dashboard.attention_required') || 'Compliance Alerts',
      value: complianceAlerts,
      icon: Shield,
      color: 'bg-rose-500',
    },
    {
      label: t('trust.score') || 'Avg Trust',
      value: avgTrustScore !== null ? `${avgTrustScore}%` : '—',
      icon: Eye,
      color: 'bg-teal-500',
    },
  ];

  const quickActions = [
    {
      label: t('diagnostic.add') || 'New Diagnostic',
      icon: Plus,
      color: 'bg-emerald-50 dark:bg-emerald-900/30',
      iconColor: 'text-emerald-600',
      hoverColor: 'hover:border-emerald-300 dark:hover:border-emerald-700',
      onClick: () => navigate('/buildings'),
    },
    {
      label: t('export.create') || 'Generate Report',
      icon: Download,
      color: 'bg-indigo-50 dark:bg-indigo-900/30',
      iconColor: 'text-indigo-600',
      hoverColor: 'hover:border-indigo-300 dark:hover:border-indigo-700',
      onClick: () => navigate('/exports'),
    },
    {
      label: t('readiness.title') || 'Readiness Wallet',
      icon: Shield,
      color: 'bg-purple-50 dark:bg-purple-900/30',
      iconColor: 'text-purple-600',
      hoverColor: 'hover:border-purple-300 dark:hover:border-purple-700',
      onClick: () => navigate('/readiness-wallet'),
    },
    {
      label: t('portfolio.title') || 'Portfolio',
      icon: Briefcase,
      color: 'bg-amber-50 dark:bg-amber-900/30',
      iconColor: 'text-amber-600',
      hoverColor: 'hover:border-amber-300 dark:hover:border-amber-700',
      onClick: () => navigate('/portfolio'),
    },
  ];

  const attentionBuildings = Array.isArray(buildings)
    ? buildings
        .filter(
          (b: Building) =>
            b.risk_scores?.overall_risk_level === 'high' || b.risk_scores?.overall_risk_level === 'critical',
        )
        .slice(0, 5)
    : [];

  const PRIORITY_DOT_COLORS: Record<string, string> = {
    low: 'bg-green-500',
    medium: 'bg-yellow-500',
    high: 'bg-orange-500',
    critical: 'bg-red-500',
  };

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  if (buildingsError || diagnosticsError || actionsError) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('dashboard.welcome', { name: user?.first_name || '' })}
          </h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('app.subtitle')}</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/buildings?action=create')}
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            {t('building.add')}
          </button>
          <button
            onClick={() => navigate('/buildings')}
            className="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-200 text-sm font-medium rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
          >
            <TrendingUp className="w-4 h-4" />
            {t('diagnostic.add')}
          </button>
        </div>
      </div>

      <section
        data-testid="client-fit-banner"
        className="relative overflow-hidden rounded-2xl border border-red-200/70 dark:border-red-900/50 bg-gradient-to-br from-red-50 via-white to-orange-50 dark:from-red-950/30 dark:via-slate-900 dark:to-orange-950/20 p-6 shadow-sm"
      >
        <div className="pointer-events-none absolute -right-20 -top-20 h-52 w-52 rounded-full bg-red-200/60 blur-3xl dark:bg-red-800/20" />
        <div className="pointer-events-none absolute -left-16 bottom-0 h-36 w-36 rounded-full bg-orange-200/50 blur-3xl dark:bg-orange-700/10" />

        <div className="relative grid grid-cols-1 xl:grid-cols-[1.15fr_0.85fr] gap-6">
          <div className="space-y-4">
            <span className="inline-flex items-center rounded-full border border-red-300/80 dark:border-red-800 bg-white/80 dark:bg-slate-900/80 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-red-700 dark:text-red-300">
              {clientFitCopy.badge}
            </span>
            <div className="space-y-3">
              <h2 className="max-w-2xl text-2xl font-bold tracking-tight text-gray-900 dark:text-white">
                {clientFitCopy.title}
              </h2>
              <p className="max-w-2xl text-sm leading-6 text-gray-600 dark:text-slate-300">
                {clientFitCopy.description}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              {clientFitCopy.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-white/85 dark:bg-slate-900/80 px-3 py-1 text-xs font-medium text-gray-700 dark:text-slate-200 ring-1 ring-gray-200 dark:ring-slate-700"
                >
                  {tag}
                </span>
              ))}
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => navigate('/readiness-wallet')}
                className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
              >
                {clientFitCopy.primaryCta}
                <ArrowRight className="h-4 w-4" />
              </button>
              <button
                onClick={() => navigate('/portfolio')}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 dark:border-slate-600 bg-white/90 dark:bg-slate-900/80 px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-100 transition-colors hover:bg-white dark:hover:bg-slate-800"
              >
                {clientFitCopy.secondaryCta}
              </button>
              <button
                onClick={() => navigate('/buildings')}
                className="inline-flex items-center gap-2 rounded-lg border border-transparent px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 transition-colors hover:bg-white/70 dark:hover:bg-slate-800/70"
              >
                {clientFitCopy.tertiaryCta}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 xl:grid-cols-1">
            {clientFitCopy.cards.map((card) => (
              <div
                key={card.label}
                className="rounded-xl border border-white/80 dark:border-slate-800 bg-white/85 dark:bg-slate-900/85 p-4 shadow-sm backdrop-blur"
              >
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-gray-500 dark:text-slate-400">
                  {card.label}
                </p>
                <p className="mt-2 text-sm font-medium leading-6 text-gray-900 dark:text-white">{card.value}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="relative mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {clientFitCopy.metrics.map((metric) => (
            <div
              key={metric.label}
              className="rounded-xl border border-red-100 dark:border-red-900/40 bg-white/75 dark:bg-slate-900/75 p-4"
            >
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{metric.value}</p>
              <p className="mt-1 text-xs font-medium uppercase tracking-[0.12em] text-gray-500 dark:text-slate-400">
                {metric.label}
              </p>
            </div>
          ))}
        </div>

        <p className="relative mt-4 text-xs leading-5 text-gray-500 dark:text-slate-400">{clientFitCopy.boundary}</p>
      </section>

      {/* Primary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi) => (
          <div
            key={kpi.label}
            className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500 dark:text-slate-400">{kpi.label}</p>
                <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{kpi.value}</p>
              </div>
              <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center', kpi.color)}>
                <kpi.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Secondary KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {secondaryKpis.map((kpi) => (
          <div
            key={kpi.label}
            data-testid="secondary-kpi"
            className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm"
          >
            <div className="flex items-center gap-3">
              <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', kpi.color)}>
                <kpi.icon className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-xs text-gray-500 dark:text-slate-400">{kpi.label}</p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">{kpi.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
          {t('dashboard.quick_actions') || 'Quick Actions'}
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((action) => (
            <button
              key={action.label}
              onClick={action.onClick}
              data-testid="quick-action"
              className={cn(
                'bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm transition-colors group flex items-center gap-3 text-left w-full',
                action.hoverColor,
              )}
            >
              <div
                className={cn('w-10 h-10 rounded-lg flex items-center justify-center transition-colors', action.color)}
              >
                <action.icon className={cn('w-5 h-5', action.iconColor)} />
              </div>
              <span className="text-sm font-medium text-gray-900 dark:text-white">{action.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Quick Access — Building Intelligence */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Link
          to="/buildings"
          className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm hover:border-red-300 dark:hover:border-red-700 transition-colors group flex items-center gap-4"
        >
          <div className="w-10 h-10 rounded-lg bg-red-50 dark:bg-red-900/30 flex items-center justify-center group-hover:bg-red-100 dark:group-hover:bg-red-900/50 transition-colors">
            <Layers className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">{t('building.tab.explorer')}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('explorer.title')}</p>
          </div>
        </Link>
        <Link
          to="/buildings"
          className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm hover:border-red-300 dark:hover:border-red-700 transition-colors group flex items-center gap-4"
        >
          <div className="w-10 h-10 rounded-lg bg-orange-50 dark:bg-orange-900/30 flex items-center justify-center group-hover:bg-orange-100 dark:group-hover:bg-orange-900/50 transition-colors">
            <Wrench className="w-5 h-5 text-orange-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">{t('building.tab.interventions')}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('intervention.title')}</p>
          </div>
        </Link>
        <Link
          to="/buildings"
          className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm hover:border-red-300 dark:hover:border-red-700 transition-colors group flex items-center gap-4"
        >
          <div className="w-10 h-10 rounded-lg bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center group-hover:bg-blue-100 dark:group-hover:bg-blue-900/50 transition-colors">
            <FileImage className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">{t('building.tab.plans')}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('plan.title')}</p>
          </div>
        </Link>
      </div>

      {/* My Actions + Buildings Requiring Attention */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* My Actions */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-blue-500" />
              {t('action.my_actions')}
            </h2>
            <Link to="/actions" className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1">
              {t('form.view')}
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          {myActions.length > 0 ? (
            <div className="divide-y divide-gray-100 dark:divide-slate-700">
              {myActions.slice(0, 5).map((action: ActionItem) => (
                <Link
                  key={action.id}
                  to={`/buildings/${action.building_id}`}
                  className="py-3 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-slate-700 -mx-2 px-2 rounded-lg transition-colors first:pt-0"
                >
                  <div
                    className={cn(
                      'w-2.5 h-2.5 rounded-full flex-shrink-0',
                      PRIORITY_DOT_COLORS[action.priority] || 'bg-gray-400',
                    )}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{action.title}</p>
                    <p className="text-xs text-gray-500 dark:text-slate-400">
                      {t(`action_priority.${action.priority}`)}
                    </p>
                  </div>
                  {action.due_date && (
                    <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400 flex-shrink-0">
                      <Calendar className="w-3 h-3" />
                      {formatDate(action.due_date)}
                    </span>
                  )}
                </Link>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-slate-400 py-4">{t('action.no_actions')}</p>
          )}
        </div>

        {/* Buildings Requiring Attention */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-orange-500" />
              {t('action.attention_buildings')}
            </h2>
            <Link to="/buildings" className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1">
              {t('form.view')}
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          {attentionBuildings.length > 0 ? (
            <div className="divide-y divide-gray-100 dark:divide-slate-700">
              {attentionBuildings.map((b: Building) => {
                const level = b.risk_scores?.overall_risk_level;
                return (
                  <Link
                    key={b.id}
                    to={`/buildings/${b.id}`}
                    className="py-3 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-slate-700 -mx-2 px-2 rounded-lg transition-colors first:pt-0"
                  >
                    <div
                      className={cn(
                        'w-2.5 h-2.5 rounded-full flex-shrink-0',
                        level === 'critical' ? 'bg-red-500' : 'bg-orange-500',
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{b.address}</p>
                      <p className="text-xs text-gray-500 dark:text-slate-400">
                        {b.postal_code} {b.city}
                      </p>
                    </div>
                    <span
                      className={cn(
                        'px-2 py-0.5 text-xs font-medium rounded-full flex-shrink-0',
                        level === 'critical'
                          ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                          : 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
                      )}
                    >
                      {t(`risk.${level}`)}
                    </span>
                  </Link>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-gray-500 dark:text-slate-400 py-4">{t('action.no_actions')}</p>
          )}
        </div>
      </div>

      {/* Charts */}
      <Suspense
        fallback={
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-[352px] rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 animate-pulse" />
            <div className="h-[352px] rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 animate-pulse" />
          </div>
        }
      >
        <DashboardCharts riskDistribution={riskDistribution} pollutantDistribution={pollutantDistribution} t={t} />
      </Suspense>

      {/* Portfolio Health Summary */}
      {gradeDistribution.length > 0 && (
        <div
          data-testid="portfolio-health"
          className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Briefcase className="w-5 h-5 text-amber-500" />
              {t('portfolio.title') || 'Portfolio Health'}
            </h2>
            <Link to="/portfolio" className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1">
              {t('form.view')}
              <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-3" data-testid="grade-distribution-grid">
            {gradeDistribution.map(({ grade, count }) => {
              const maxCount = Math.max(...gradeDistribution.map((g) => g.count), 1);
              const heightPercent = Math.max((count / maxCount) * 100, 8);
              return (
                <div key={grade} data-testid={`grade-bar-${grade}`} className="flex flex-col items-center gap-2">
                  <div className="w-full h-16 sm:h-24 flex items-end justify-center">
                    <div
                      className={cn('w-full max-w-[40px] rounded-t-md transition-all', PASSPORT_GRADE_COLORS[grade])}
                      style={{ height: `${heightPercent}%` }}
                    />
                  </div>
                  <div className="text-center">
                    <p className="text-xs sm:text-sm font-bold text-gray-900 dark:text-white">{grade}</p>
                    <p className="text-xs text-gray-500 dark:text-slate-400">{count}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Predictive Readiness Alerts */}
      <PredictiveAlertsPortfolio />

      {/* Recent Activity — Enhanced */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">{t('dashboard.recent_activity')}</h2>
          <Link to="/buildings" className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1">
            {t('form.view')}
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>
        {recentActivity.length > 0 ? (
          <div className="divide-y divide-gray-100 dark:divide-slate-700">
            {recentActivity.map((item: Diagnostic) => {
              const building = buildingMap.get(item.building_id);
              return (
                <Link
                  key={item.id}
                  to={`/diagnostics/${item.id}`}
                  className="py-3 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-slate-700 -mx-2 px-2 rounded-lg transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex-shrink-0">
                      <span
                        className={cn(
                          'inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-medium',
                          'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
                        )}
                      >
                        <Activity className="w-3.5 h-3.5" />
                      </span>
                    </div>
                    <div
                      className={cn(
                        'w-2 h-2 rounded-full flex-shrink-0',
                        item.status === 'validated'
                          ? 'bg-emerald-500'
                          : item.status === 'completed'
                            ? 'bg-green-500'
                            : item.status === 'in_progress'
                              ? 'bg-blue-500'
                              : 'bg-gray-400',
                      )}
                    />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                        {t(`diagnostic_type.${item.diagnostic_type}`)}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-slate-400 truncate">
                        {building
                          ? `${building.address}, ${building.city}`
                          : t(`diagnostic_context.${item.diagnostic_context}`)}
                      </p>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0 ml-3">
                    <span
                      className={cn(
                        'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
                        item.status === 'validated'
                          ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                          : item.status === 'completed'
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                            : item.status === 'in_progress'
                              ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                              : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
                      )}
                    >
                      {t(`diagnostic_status.${item.status}`)}
                    </span>
                    <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                      {formatDate(item.updated_at || item.created_at)}
                    </p>
                  </div>
                </Link>
              );
            })}
          </div>
        ) : (
          <p className="text-center text-sm text-gray-500 dark:text-slate-400 py-8">{t('form.no_results')}</p>
        )}
      </div>
    </div>
  );
}
