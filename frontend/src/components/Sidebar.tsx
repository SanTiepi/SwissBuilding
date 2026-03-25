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
} from 'lucide-react';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/utils/formatters';
import type { UserRole } from '@/types';

interface NavItem {
  to: string;
  icon: React.ElementType;
  labelKey: string;
  allowedRoles?: UserRole[];
}

const navItems: NavItem[] = [
  { to: '/dashboard', icon: LayoutDashboard, labelKey: 'nav.dashboard' },
  { to: '/control-tower', icon: Radar, labelKey: 'nav.control_tower' },
  { to: '/portfolio', icon: BarChart3, labelKey: 'nav.portfolio' },
  { to: '/buildings', icon: Building2, labelKey: 'nav.buildings' },
  { to: '/comparison', icon: ArrowLeftRight, labelKey: 'nav.comparison' },
  { to: '/map', icon: Map, labelKey: 'nav.map' },
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
  { to: '/documents', icon: FileText, labelKey: 'nav.documents' },
  { to: '/admin/users', icon: Users, labelKey: 'nav.users', allowedRoles: ['admin'] as UserRole[] },
  { to: '/admin/organizations', icon: Building2, labelKey: 'nav.organizations', allowedRoles: ['admin'] as UserRole[] },
  { to: '/admin/invitations', icon: Mail, labelKey: 'nav.invitations', allowedRoles: ['admin'] as UserRole[] },
  { to: '/admin/jurisdictions', icon: Scale, labelKey: 'nav.jurisdictions', allowedRoles: ['admin'] as UserRole[] },
  { to: '/rules-studio', icon: BookOpen, labelKey: 'nav.rules_studio', allowedRoles: ['admin'] as UserRole[] },
  { to: '/admin/procedures', icon: ClipboardCheck, labelKey: 'nav.procedures', allowedRoles: ['admin'] as UserRole[] },
  { to: '/admin/audit-logs', icon: FileSearch, labelKey: 'nav.audit_logs', allowedRoles: ['admin'] as UserRole[] },
  { to: '/admin/diagnostic-review', icon: ClipboardCheck, labelKey: 'nav.diagnostic_review', allowedRoles: ['admin'] as UserRole[] },
  { to: '/settings', icon: Settings, labelKey: 'nav.settings' },
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

  const visibleItems = navItems.filter((item) => !item.allowedRoles || (user && item.allowedRoles.includes(user.role)));

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
        {visibleItems.map((item) => {
          const Icon = item.icon;
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
              title={collapsed && !isMobile ? t(item.labelKey) : undefined}
              end={item.to === '/dashboard'}
              onClick={() => isMobile && onMobileClose?.()}
            >
              {({ isActive }) => (
                <>
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  {(!collapsed || isMobile) && <span className="truncate">{t(item.labelKey)}</span>}
                  {isActive && <span className="sr-only">(page courante)</span>}
                </>
              )}
            </NavLink>
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
