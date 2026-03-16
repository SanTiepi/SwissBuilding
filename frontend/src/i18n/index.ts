import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { fr } from './fr';
import { de } from './de';
import { it } from './it';
import { en } from './en';
import type { Language } from '@/types';

export type TranslationMap = Record<string, string>;

const translations: Record<Language, TranslationMap> = { fr, de, it, en };

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
      let value = translations[locale]?.[key] || translations.fr[key] || key;
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
