import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Building2,
  Shield,
  X,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Settings,
  CalendarCheck,
  Briefcase,
  Wallet,
  BarChart3,
  Map,
  Calculator,
  Users,
  Mail,
  Scale,
  FileSearch,
  Megaphone,
  Download,
  ArrowLeftRight,
  ShieldCheck,
  BookOpen,
  ClipboardCheck,
  Radar,
  Presentation,
  Gauge,
  Rocket,
  TrendingUp,
  Trophy,
  Landmark,
  Search,
  Play,
  Award,
} from 'lucide-react';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/utils/formatters';
import type { UserRole } from '@/types';

interface NavItem {
  to: string;
  icon: React.ElementType;
  labelKey: string;
  fallbackLabel?: string;
  allowedRoles?: UserRole[];
}

// ─── 5 Primary Hubs ────────────────────────────────────────────────────────
const primaryHubs: NavItem[] = [
  { to: '/today', icon: CalendarCheck, labelKey: 'nav.today', fallbackLabel: "Aujourd'hui" },
  { to: '/buildings', icon: Building2, labelKey: 'nav.buildings' },
  { to: '/cases', icon: Briefcase, labelKey: 'nav.cases', fallbackLabel: 'Dossiers' },
  { to: '/finance', icon: Wallet, labelKey: 'nav.finance', fallbackLabel: 'Finance' },
  { to: '/portfolio-command', icon: BarChart3, labelKey: 'nav.portfolio_command', fallbackLabel: 'Portefeuille' },
];

// ─── Secondary items (collapsible "Plus") ───────────────────────────────────
const secondaryItems: NavItem[] = [
  // ABSORBED: /dashboard, /control-tower, /portfolio, /portfolio-triage, /actions, /documents
  // These routes now redirect to their canonical workspaces (Today or PortfolioCommand).
  { to: '/comparison', icon: ArrowLeftRight, labelKey: 'nav.comparison' },
  { to: '/map', icon: Map, labelKey: 'nav.map' },
  { to: '/address-preview', icon: Search, labelKey: 'nav.address_preview', fallbackLabel: 'Apercu adresse' },
  {
    to: '/risk-simulator',
    icon: Calculator,
    labelKey: 'nav.simulation',
    allowedRoles: ['admin', 'diagnostician', 'architect'],
  },
  { to: '/campaigns', icon: Megaphone, labelKey: 'campaign.title' },
  { to: '/exports', icon: Download, labelKey: 'nav.exports' },
  { to: '/authority-packs', icon: ShieldCheck, labelKey: 'nav.authority_packs' },
  { to: '/marketplace/companies', icon: Briefcase, labelKey: 'nav.marketplace_companies' },
  { to: '/marketplace/rfq', icon: Briefcase, labelKey: 'nav.marketplace_rfq' },
  { to: '/demo-path', icon: Play, labelKey: 'nav.demo_path', fallbackLabel: 'Demo' },
  { to: '/pilot-scorecard', icon: Award, labelKey: 'nav.pilot_scorecard', fallbackLabel: 'Pilote' },
  { to: '/indispensability', icon: Shield, labelKey: 'nav.indispensability', fallbackLabel: 'Indispensabilite' },
];

// ─── Admin items ────────────────────────────────────────────────────────────
const adminItems: NavItem[] = [
  { to: '/admin/users', icon: Users, labelKey: 'nav.users', allowedRoles: ['admin'] as UserRole[] },
  { to: '/admin/organizations', icon: Building2, labelKey: 'nav.organizations', allowedRoles: ['admin'] as UserRole[] },
  { to: '/admin/invitations', icon: Mail, labelKey: 'nav.invitations', allowedRoles: ['admin'] as UserRole[] },
  { to: '/admin/jurisdictions', icon: Scale, labelKey: 'nav.jurisdictions', allowedRoles: ['admin'] as UserRole[] },
  { to: '/rules-studio', icon: BookOpen, labelKey: 'nav.rules_studio', allowedRoles: ['admin'] as UserRole[] },
  { to: '/admin/procedures', icon: ClipboardCheck, labelKey: 'nav.procedures', allowedRoles: ['admin'] as UserRole[] },
  { to: '/admin/audit-logs', icon: FileSearch, labelKey: 'nav.audit_logs', allowedRoles: ['admin'] as UserRole[] },
  {
    to: '/admin/diagnostic-review',
    icon: ClipboardCheck,
    labelKey: 'nav.diagnostic_review',
    allowedRoles: ['admin'] as UserRole[],
  },
  {
    to: '/admin/demo-runbook',
    icon: Presentation,
    labelKey: 'nav.demo_runbook',
    allowedRoles: ['admin'] as UserRole[],
  },
  { to: '/admin/pilot-dashboard', icon: Gauge, labelKey: 'nav.pilot_dashboard', allowedRoles: ['admin'] as UserRole[] },
  { to: '/admin/rollout', icon: Rocket, labelKey: 'nav.rollout', allowedRoles: ['admin'] as UserRole[] },
  { to: '/admin/expansion', icon: TrendingUp, labelKey: 'nav.expansion', allowedRoles: ['admin'] as UserRole[] },
  {
    to: '/admin/customer-success',
    icon: Trophy,
    labelKey: 'nav.customer_success',
    allowedRoles: ['admin'] as UserRole[],
  },
  {
    to: '/admin/governance-signals',
    icon: Landmark,
    labelKey: 'nav.governance_signals',
    allowedRoles: ['admin'] as UserRole[],
  },
  {
    to: '/admin/marketplace-reviews',
    icon: ClipboardCheck,
    labelKey: 'nav.marketplace_reviews',
    allowedRoles: ['admin'] as UserRole[],
  },
  {
    to: '/admin/remediation-intelligence',
    icon: Radar,
    labelKey: 'intelligence.nav_label',
    allowedRoles: ['admin'] as UserRole[],
  },
];

// ─── Footer items ───────────────────────────────────────────────────────────
const footerItems: NavItem[] = [{ to: '/settings', icon: Settings, labelKey: 'nav.settings' }];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  onMobileClose?: () => void;
  isMobile?: boolean;
}

export function Sidebar({ collapsed, onToggle, onMobileClose, isMobile }: SidebarProps) {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const [secondaryOpen, setSecondaryOpen] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);

  const filterItems = (items: NavItem[]) =>
    items.filter((item) => !item.allowedRoles || (user && item.allowedRoles.includes(user.role)));

  const renderItem = (item: NavItem) => {
    const Icon = item.icon;
    const label = item.fallbackLabel ? t(item.labelKey) || item.fallbackLabel : t(item.labelKey);
    return (
      <NavLink
        key={item.to}
        to={item.to}
        className={({ isActive }) =>
          cn(
            'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150',
            'hover:bg-slate-800 hover:text-white',
            isActive ? 'bg-red-600/90 text-white shadow-sm' : 'text-slate-300',
            collapsed && !isMobile && 'justify-center px-0',
          )
        }
        title={collapsed && !isMobile ? label : undefined}
        onClick={() => isMobile && onMobileClose?.()}
      >
        {({ isActive }) => (
          <>
            <Icon className="w-5 h-5 flex-shrink-0" />
            {(!collapsed || isMobile) && <span className="truncate">{label}</span>}
            {isActive && <span className="sr-only">(page courante)</span>}
          </>
        )}
      </NavLink>
    );
  };

  const visibleSecondary = filterItems(secondaryItems);
  const visibleAdmin = filterItems(adminItems);

  return (
    <aside
      className={cn(
        'flex flex-col h-full bg-slate-900 text-white transition-all duration-300 ease-in-out',
        isMobile ? 'w-64' : collapsed ? 'w-16' : 'w-64',
      )}
    >
      {/* Logo / App Name */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-slate-700/50">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-red-600 flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          {(!collapsed || isMobile) && (
            <span className="text-lg font-semibold tracking-tight whitespace-nowrap">BatiConnect</span>
          )}
        </div>
        {isMobile && onMobileClose && (
          <button
            onClick={onMobileClose}
            className="p-1.5 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            aria-label={t('form.close')}
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto" aria-label="Navigation principale">
        {/* 5 Primary Hubs */}
        {primaryHubs.map(renderItem)}

        {/* Separator */}
        {(!collapsed || isMobile) && visibleSecondary.length > 0 && (
          <div className="pt-3">
            <button
              onClick={() => setSecondaryOpen(!secondaryOpen)}
              className="flex items-center justify-between w-full px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-500 hover:text-slate-300 transition-colors"
            >
              <span>{t('nav.more') || 'Plus'}</span>
              {secondaryOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>
        )}
        {collapsed && !isMobile && visibleSecondary.length > 0 && (
          <div className="my-2 mx-3 border-t border-slate-700/50" />
        )}
        {(secondaryOpen || (collapsed && !isMobile)) && visibleSecondary.map(renderItem)}

        {/* Admin section */}
        {visibleAdmin.length > 0 && (
          <>
            {!collapsed || isMobile ? (
              <div className="pt-3">
                <button
                  onClick={() => setAdminOpen(!adminOpen)}
                  className="flex items-center justify-between w-full px-3 py-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-500 hover:text-slate-300 transition-colors"
                >
                  <span>{t('nav.admin') || 'Administration'}</span>
                  {adminOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
              </div>
            ) : (
              <div className="my-2 mx-3 border-t border-slate-700/50" />
            )}
            {(adminOpen || (collapsed && !isMobile)) && visibleAdmin.map(renderItem)}
          </>
        )}

        {/* Separator before footer */}
        <div className="my-2 mx-3 border-t border-slate-700/50" />
        {footerItems.map(renderItem)}
      </nav>

      {/* Collapse toggle - hidden on mobile */}
      {!isMobile && (
        <div className="border-t border-slate-700/50 p-2">
          <button
            onClick={onToggle}
            className="flex items-center justify-center w-full py-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
          </button>
        </div>
      )}
    </aside>
  );
}
