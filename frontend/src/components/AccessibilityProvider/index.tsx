import React, { createContext, useContext, useMemo, useState } from 'react'

interface AccessibilityContextValue {
  highContrastEnabled: boolean
  toggleHighContrast: () => void
  reducedMotionEnabled: boolean
  toggleReducedMotion: () => void
  focusTrap: {
    enable: (_container: HTMLElement) => void
    disable: () => void
  }
  announce: (_message: string) => void
  keyboardNavigationEnabled: boolean
  toggleKeyboardNavigation: () => void
  textScale: number
  increaseTextScale: () => void
  decreaseTextScale: () => void
  resetTextScale: () => void
  focusVisibleEnabled: boolean
}

const AccessibilityContext = createContext<AccessibilityContextValue | undefined>(undefined)

interface AccessibilityProviderProps {
  children: React.ReactNode
}

export const AccessibilityProvider: React.FC<AccessibilityProviderProps> = ({ children }) => {
  const [highContrastEnabled, setHighContrastEnabled] = useState(false)
  const [reducedMotionEnabled, setReducedMotionEnabled] = useState(false)
  const [keyboardNavigationEnabled, setKeyboardNavigationEnabled] = useState(true)
  const [textScale, setTextScale] = useState(100)
  const [focusTrapEnabled, setFocusTrapEnabled] = useState(false)

  const value = useMemo<AccessibilityContextValue>(() => {
    const updateTextScale = (next: number) => {
      const bounded = Math.min(150, Math.max(75, next))
      setTextScale(bounded)
      if (typeof document !== 'undefined') {
        document.documentElement.style.fontSize = `${bounded}%`
      }
    }

    return {
      highContrastEnabled,
      toggleHighContrast: () => {
        const next = !highContrastEnabled
        setHighContrastEnabled(next)
        if (typeof document !== 'undefined') {
          document.documentElement.classList.toggle('high-contrast', next)
        }
      },
      reducedMotionEnabled,
      toggleReducedMotion: () => {
        const next = !reducedMotionEnabled
        setReducedMotionEnabled(next)
        if (typeof document !== 'undefined') {
          document.documentElement.classList.toggle('reduce-motion', next)
        }
      },
      focusTrap: {
        enable: () => setFocusTrapEnabled(true),
        disable: () => setFocusTrapEnabled(false),
      },
      announce: (message: string) => {
        if (!message || typeof document === 'undefined') return
        const region = document.createElement('div')
        region.setAttribute('role', 'status')
        region.className = 'sr-only'
        region.textContent = message
        document.body.appendChild(region)
        const timeout = typeof window !== 'undefined' ? window.setTimeout : setTimeout
        timeout(() => {
          if (region.parentElement) {
            region.parentElement.removeChild(region)
          }
        }, 1500)
      },
      keyboardNavigationEnabled,
      toggleKeyboardNavigation: () => setKeyboardNavigationEnabled((prev) => !prev),
      textScale,
      increaseTextScale: () => updateTextScale(textScale + 10),
      decreaseTextScale: () => updateTextScale(textScale - 10),
      resetTextScale: () => updateTextScale(100),
      focusVisibleEnabled: focusTrapEnabled,
    }
  }, [focusTrapEnabled, highContrastEnabled, keyboardNavigationEnabled, reducedMotionEnabled, textScale])

  return <AccessibilityContext.Provider value={value}>{children}</AccessibilityContext.Provider>
}

export const useAccessibility = () => {
  const context = useContext(AccessibilityContext)
  if (!context) {
    throw new Error('useAccessibility must be used within an AccessibilityProvider')
  }
  return context
}
