import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Building2,
  Map,
  Calculator,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Shield,
  X,
  CheckCircle2,
  Users,
  Mail,
  Scale,
  BarChart3,
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
  Briefcase,
  FileBox,
  Search,
  LayoutGrid,
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

interface NavSection {
  sectionLabel?: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    items: [
      { to: '/dashboard', icon: LayoutDashboard, labelKey: 'nav.dashboard' },
      { to: '/control-tower', icon: Radar, labelKey: 'nav.control_tower' },
      { to: '/portfolio', icon: BarChart3, labelKey: 'nav.portfolio' },
      { to: '/buildings', icon: Building2, labelKey: 'nav.buildings' },
      { to: '/comparison', icon: ArrowLeftRight, labelKey: 'nav.comparison' },
      { to: '/map', icon: Map, labelKey: 'nav.map' },
    ],
  },
  {
    sectionLabel: 'Intelligence',
    items: [
      { to: '/address-preview', icon: Search, labelKey: 'nav.address_preview', fallbackLabel: 'Apercu adresse' },
      {
        to: '/portfolio-triage',
        icon: LayoutGrid,
        labelKey: 'nav.portfolio_triage',
        fallbackLabel: 'Triage portfolio',
      },
      { to: '/demo-path', icon: Play, labelKey: 'nav.demo_path', fallbackLabel: 'Demo' },
      { to: '/pilot-scorecard', icon: Award, labelKey: 'nav.pilot_scorecard', fallbackLabel: 'Pilote' },
      { to: '/indispensability', icon: Shield, labelKey: 'nav.indispensability', fallbackLabel: 'Indispensabilite' },
    ],
  },
  {
    items: [
      {
        to: '/risk-simulator',
        icon: Calculator,
        labelKey: 'nav.simulation',
        allowedRoles: ['admin', 'diagnostician', 'architect'],
      },
      { to: '/actions', icon: CheckCircle2, labelKey: 'nav.actions' },
      { to: '/campaigns', icon: Megaphone, labelKey: 'campaign.title' },
      { to: '/exports', icon: Download, labelKey: 'nav.exports' },
      { to: '/authority-packs', icon: ShieldCheck, labelKey: 'nav.authority_packs' },
      { to: '/marketplace/companies', icon: Briefcase, labelKey: 'nav.marketplace_companies' },
      { to: '/marketplace/rfq', icon: FileBox, labelKey: 'nav.marketplace_rfq' },
      { to: '/documents', icon: FileText, labelKey: 'nav.documents' },
      { to: '/admin/users', icon: Users, labelKey: 'nav.users', allowedRoles: ['admin'] as UserRole[] },
      {
        to: '/admin/organizations',
        icon: Building2,
        labelKey: 'nav.organizations',
        allowedRoles: ['admin'] as UserRole[],
      },
      { to: '/admin/invitations', icon: Mail, labelKey: 'nav.invitations', allowedRoles: ['admin'] as UserRole[] },
      { to: '/admin/jurisdictions', icon: Scale, labelKey: 'nav.jurisdictions', allowedRoles: ['admin'] as UserRole[] },
      { to: '/rules-studio', icon: BookOpen, labelKey: 'nav.rules_studio', allowedRoles: ['admin'] as UserRole[] },
      {
        to: '/admin/procedures',
        icon: ClipboardCheck,
        labelKey: 'nav.procedures',
        allowedRoles: ['admin'] as UserRole[],
      },
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
      {
        to: '/admin/pilot-dashboard',
        icon: Gauge,
        labelKey: 'nav.pilot_dashboard',
        allowedRoles: ['admin'] as UserRole[],
      },
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
      { to: '/settings', icon: Settings, labelKey: 'nav.settings' },
    ],
  },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  onMobileClose?: () => void;
  isMobile?: boolean;
}

export function Sidebar({ collapsed, onToggle, onMobileClose, isMobile }: SidebarProps) {
  const { t } = useTranslation();
  const { user } = useAuthStore();

  const filterItems = (items: NavItem[]) =>
    items.filter((item) => !item.allowedRoles || (user && item.allowedRoles.includes(user.role)));

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
            <span className="text-lg font-semibold tracking-tight whitespace-nowrap">SwissBuildingOS</span>
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
        {navSections.map((section, sIdx) => {
          const visibleItems = filterItems(section.items);
          if (visibleItems.length === 0) return null;
          return (
            <div key={sIdx}>
              {section.sectionLabel && (!collapsed || isMobile) && (
                <div className="px-3 pt-4 pb-1">
                  <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
                    {section.sectionLabel}
                  </p>
                </div>
              )}
              {section.sectionLabel && collapsed && !isMobile && (
                <div className="my-2 mx-3 border-t border-slate-700/50" />
              )}
              {visibleItems.map((item) => {
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
                    end={item.to === '/dashboard'}
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
              })}
            </div>
          );
        })}
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
