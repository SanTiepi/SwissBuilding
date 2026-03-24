import { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Globe, LogOut, User, ChevronDown, Menu, Search, Moon, Sun } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { useThemeStore } from '@/store/themeStore';
import { useTranslation } from '@/i18n';
import { SUPPORTED_LANGUAGES } from '@/utils/constants';
import { cn } from '@/utils/formatters';
import { NotificationBell } from '@/components/NotificationBell';
import type { Language } from '@/types';

const routeTitles: Record<string, string> = {
  '/dashboard': 'nav.dashboard',
  '/buildings': 'nav.buildings',
  '/map': 'nav.map',
  '/risk-simulator': 'nav.simulation',
  '/documents': 'nav.documents',
  '/settings': 'nav.settings',
};

interface HeaderProps {
  onMenuToggle?: () => void;
  onSearchOpen?: () => void;
}

export function Header({ onMenuToggle, onSearchOpen }: HeaderProps) {
  const { user, logout } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();
  const { t, locale, setLocale } = useTranslation();
  const location = useLocation();

  const [langOpen, setLangOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const langRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  // Close dropdowns on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (langRef.current && !langRef.current.contains(e.target as Node)) {
        setLangOpen(false);
      }
      if (userRef.current && !userRef.current.contains(e.target as Node)) {
        setUserOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close dropdowns on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        if (langOpen) {
          setLangOpen(false);
          langRef.current?.querySelector('button')?.focus();
        }
        if (userOpen) {
          setUserOpen(false);
          userRef.current?.querySelector('button')?.focus();
        }
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [langOpen, userOpen]);

  // Determine page title
  const basePath = '/' + location.pathname.split('/').filter(Boolean).slice(0, 1).join('/');
  const titleKey = routeTitles[basePath] || 'app.title';
  const pageTitle = t(titleKey);

  // User initials
  const initials = user ? `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`.toUpperCase() : '??';

  // Language display available via SUPPORTED_LANGUAGES if needed

  return (
    <header className="flex items-center justify-between h-16 px-3 sm:px-6 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
      {/* Left side: hamburger + page title */}
      <div className="flex items-center gap-2 sm:gap-3 min-w-0">
        {onMenuToggle && (
          <button
            onClick={onMenuToggle}
            className="md:hidden p-2 -ml-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors flex-shrink-0"
            aria-label="Menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}
        <h1 className="text-base sm:text-xl font-semibold text-slate-900 dark:text-white truncate">{pageTitle}</h1>
      </div>

      {/* Search trigger */}
      {onSearchOpen && (
        <button
          onClick={onSearchOpen}
          className="hidden sm:flex items-center gap-2 px-3 py-1.5 text-sm text-slate-400 dark:text-slate-400 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 rounded-lg transition-colors"
          aria-label={t('nav.search')}
        >
          <Search className="w-4 h-4" />
          <span>{t('nav.search')}</span>
          <kbd className="ml-2 px-1.5 py-0.5 text-[10px] font-mono bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded">
            ⌘K
          </kbd>
        </button>
      )}

      {/* Right side controls */}
      <div className="flex items-center gap-1 sm:gap-3 flex-shrink-0">
        {/* Mobile search button — visible only below sm breakpoint */}
        {onSearchOpen && (
          <button
            onClick={onSearchOpen}
            className="sm:hidden min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            aria-label={t('nav.search')}
          >
            <Search className="w-5 h-5" />
          </button>
        )}

        {/* Dark mode toggle — hidden on very small screens, available in user menu context */}
        <button
          onClick={toggleTheme}
          className="hidden sm:flex min-w-[44px] min-h-[44px] items-center justify-center rounded-lg text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
          aria-label={t('settings.dark_mode')}
          data-testid="theme-toggle-desktop"
        >
          {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        {/* Notification bell */}
        <NotificationBell />

        {/* Language switcher */}
        <div ref={langRef} className="relative">
          <button
            onClick={() => setLangOpen(!langOpen)}
            className="flex items-center gap-1 sm:gap-1.5 min-w-[44px] min-h-[44px] justify-center sm:justify-start sm:px-3 py-2 text-sm text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            aria-label={t('settings.language')}
            aria-expanded={langOpen}
            aria-haspopup="true"
          >
            <Globe className="w-4 h-4" />
            <span className="uppercase font-medium hidden sm:inline">{locale}</span>
            <ChevronDown className="w-3.5 h-3.5 hidden sm:block" />
          </button>
          {langOpen && (
            <div
              className="absolute right-0 top-full mt-1 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1 z-50 min-w-[140px]"
              role="menu"
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <button
                  key={lang.code}
                  role="menuitem"
                  onClick={() => {
                    setLocale(lang.code as Language);
                    setLangOpen(false);
                  }}
                  className={cn(
                    'flex items-center w-full px-4 py-2 text-sm transition-colors',
                    locale === lang.code
                      ? 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-400 font-medium'
                      : 'text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700',
                  )}
                >
                  <span className="uppercase font-mono text-xs mr-3 w-5">{lang.code}</span>
                  {lang.label}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Separator — hidden on very small screens */}
        <div className="hidden sm:block w-px h-8 bg-slate-200 dark:bg-slate-700" />

        {/* User menu */}
        <div ref={userRef} className="relative">
          <button
            onClick={() => setUserOpen(!userOpen)}
            className="flex items-center gap-1 sm:gap-2.5 min-w-[44px] min-h-[44px] px-1 sm:px-2 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            aria-label={t('nav.profile')}
            aria-expanded={userOpen}
            aria-haspopup="true"
          >
            <div className="w-8 h-8 rounded-full bg-slate-700 text-white flex items-center justify-center text-xs font-semibold flex-shrink-0">
              {initials}
            </div>
            {user && (
              <div className="hidden sm:block text-left">
                <p className="text-sm font-medium text-slate-900 dark:text-white leading-tight">
                  {user.first_name} {user.last_name}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 leading-tight">{t(`role.${user.role}`)}</p>
              </div>
            )}
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 hidden sm:block" />
          </button>
          {userOpen && (
            <div
              className="absolute right-0 top-full mt-1 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1 z-50 min-w-[200px]"
              role="menu"
            >
              <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-700">
                <p className="text-sm font-medium text-slate-900 dark:text-white">
                  {user?.first_name} {user?.last_name}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{user?.email}</p>
              </div>
              <button
                role="menuitem"
                onClick={() => {
                  setUserOpen(false);
                  // Navigate to profile/settings could go here
                }}
                className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                <User className="w-4 h-4" />
                {t('nav.profile')}
              </button>
              {/* Dark mode toggle — visible in dropdown on small screens */}
              <button
                role="menuitem"
                onClick={() => {
                  toggleTheme();
                  setUserOpen(false);
                }}
                className="flex sm:hidden items-center gap-2.5 w-full px-4 py-2.5 text-sm text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
                data-testid="theme-toggle-mobile"
              >
                {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                {t('settings.dark_mode')}
              </button>
              <div className="border-t border-slate-100 dark:border-slate-700">
                <button
                  role="menuitem"
                  onClick={() => {
                    setUserOpen(false);
                    logout();
                  }}
                  className="flex items-center gap-2.5 w-full px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  {t('nav.logout')}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
