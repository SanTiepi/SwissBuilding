import React, { createContext, useContext, useState, useCallback, useMemo, useEffect } from 'react';
import { fr } from './fr';
import type { Language } from '@/types';

export type TranslationMap = Record<string, string>;

// FR is eagerly loaded (default language). Others are lazy-loaded on demand
// to avoid bundling ~375 kB of unused translations into the index chunk.
const translationCache: Partial<Record<Language, TranslationMap>> = { fr };

const langLoaders: Record<Language, () => Promise<{ de?: TranslationMap; en?: TranslationMap; it?: TranslationMap; fr?: TranslationMap }>> = {
  fr: () => Promise.resolve({ fr }),
  de: () => import('./de'),
  en: () => import('./en'),
  it: () => import('./it'),
};

async function loadLanguage(lang: Language): Promise<TranslationMap> {
  if (translationCache[lang]) return translationCache[lang]!;
  const mod = await langLoaders[lang]();
  const map = (mod as Record<string, TranslationMap>)[lang];
  translationCache[lang] = map;
  return map;
}

interface I18nContextValue {
  locale: Language;
  setLocale: (locale: Language) => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nContextValue>({
  locale: 'fr',
  setLocale: () => {},
  t: (key: string) => key,
});

function getInitialLocale(): Language {
  try {
    const stored = localStorage.getItem('swissbuildingos-locale');
    if (stored && ['fr', 'de', 'it', 'en'].includes(stored)) {
      return stored as Language;
    }
  } catch {
    // localStorage unavailable
  }
  return 'fr';
}

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [locale, setLocaleState] = useState<Language>(getInitialLocale);
  const [, setReady] = useState(0);

  // Eagerly load the selected language on mount / locale change
  useEffect(() => {
    if (!translationCache[locale]) {
      loadLanguage(locale).then(() => setReady((n) => n + 1));
    }
  }, [locale]);

  const setLocale = useCallback((newLocale: Language) => {
    setLocaleState(newLocale);
    try {
      localStorage.setItem('swissbuildingos-locale', newLocale);
    } catch {
      // localStorage unavailable
    }
    document.documentElement.lang = newLocale;
  }, []);

  const t = useCallback(
    (key: string, params?: Record<string, string | number>): string => {
      let value = translationCache[locale]?.[key] || translationCache.fr?.[key] || key;
      if (params) {
        Object.entries(params).forEach(([paramKey, paramValue]) => {
          value = value.replace(new RegExp(`\\{${paramKey}\\}`, 'g'), String(paramValue));
        });
      }
      return value;
    },
    [locale],
  );

  const contextValue = useMemo(() => ({ locale, setLocale, t }), [locale, setLocale, t]);

  return React.createElement(I18nContext.Provider, { value: contextValue }, children);
};

export function useTranslation(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useTranslation must be used within an I18nProvider');
  }
  return context;
}
