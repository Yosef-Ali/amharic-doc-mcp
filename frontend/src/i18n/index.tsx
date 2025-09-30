import React, { createContext, useContext, useMemo } from 'react'

import am from './locales/am.json'
import en from './locales/en.json'

type Locale = 'en' | 'am'

type Messages = Record<string, unknown>

interface I18nContextValue {
  locale: Locale
  t: (key: string) => string
}

const I18N_MESSAGES: Record<Locale, Messages> = {
  en,
  am,
}

const I18nContext = createContext<I18nContextValue>({
  locale: 'en',
  t: (key) => key,
})

const resolveMessage = (messages: Messages, key: string): string => {
  const raw = key
    .split('.')
    .reduce<unknown>((accumulator, part) => {
      if (typeof accumulator !== 'object' || accumulator === null) {
        return undefined
      }
      return (accumulator as Record<string, unknown>)[part]
    }, messages)

  return typeof raw === 'string' ? raw : key
}

interface I18nProviderProps {
  children: React.ReactNode
  locale?: Locale
}

const I18nProvider: React.FC<I18nProviderProps> = ({ children, locale = 'en' }) => {
  const value = useMemo<I18nContextValue>(() => {
    const messages = I18N_MESSAGES[locale] ?? I18N_MESSAGES.en
    return {
      locale,
      t: (key: string) => resolveMessage(messages, key),
    }
  }, [locale])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export const useI18n = () => useContext(I18nContext)

export default I18nProvider
