import { useState, useEffect, useCallback, useRef } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/Sidebar';
import { Header } from '@/components/Header';
import { OfflineBanner } from '@/components/OfflineBanner';
import { CommandPalette } from '@/components/CommandPalette';
import { cn } from '@/utils/formatters';

export function Layout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const paletteTriggeredByRef = useRef<HTMLElement | null>(null);

  const handleOpenSearch = useCallback(() => {
    paletteTriggeredByRef.current = document.activeElement as HTMLElement | null;
    setCommandPaletteOpen(true);
  }, []);

  const handleClosePalette = useCallback(() => {
    setCommandPaletteOpen(false);
    // Restore focus to the element that triggered the palette
    requestAnimationFrame(() => {
      paletteTriggeredByRef.current?.focus();
      paletteTriggeredByRef.current = null;
    });
  }, []);

  // Global Cmd+K / Ctrl+K shortcut
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (!commandPaletteOpen) {
          paletteTriggeredByRef.current = document.activeElement as HTMLElement | null;
        }
        setCommandPaletteOpen((prev) => !prev);
      }
    }
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [commandPaletteOpen]);

  return (
    <div className="flex h-screen bg-slate-50 dark:bg-slate-900 overflow-hidden">
      {/* Skip to main content link for keyboard users */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-[200] focus:px-4 focus:py-2 focus:bg-white focus:dark:bg-slate-800 focus:text-slate-900 focus:dark:text-white focus:rounded-lg focus:shadow-lg focus:border focus:border-slate-300 focus:dark:border-slate-600 focus:text-sm focus:font-medium focus:outline-none focus:ring-2 focus:ring-red-500"
      >
        Skip to main content
      </a>
      <OfflineBanner />
      <CommandPalette open={commandPaletteOpen} onClose={handleClosePalette} />
      {/* Mobile backdrop */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar - hidden on mobile unless menu is open */}
      <div
        className={cn(
          'md:relative md:flex md:flex-shrink-0',
          mobileMenuOpen ? 'fixed inset-y-0 left-0 z-50 flex' : 'hidden',
        )}
      >
        <Sidebar
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
          onMobileClose={() => setMobileMenuOpen(false)}
          isMobile={mobileMenuOpen}
        />
      </div>

      {/* Main content area */}
      <div className="flex flex-col flex-1 min-w-0">
        <Header onMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)} onSearchOpen={handleOpenSearch} />
        <main id="main-content" className="flex-1 overflow-y-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
