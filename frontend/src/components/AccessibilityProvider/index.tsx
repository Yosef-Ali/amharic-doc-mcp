/**
 * AccessibilityProvider Component
 *
 * WCAG 2.1 Level AA Accessibility Provider
 *
 * Features:
 * - Focus management and visible focus indicators
 * - ARIA labels and semantic HTML
 * - High contrast mode support
 * - Keyboard navigation for all interactive elements
 * - Screen reader announcements
 * - Skip links
 * - Reduced motion support
 * - Text scaling and zoom support
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import {
  trapFocus,
  announceToScreenReader,
  isHighContrastMode,
  onHighContrastModeChange,
  applyHighContrastTheme,
  prefersReducedMotion,
  onReducedMotionChange,
  createSkipLink,
  generateAriaId
} from '../../utils/accessibility';

interface AccessibilityContextValue {
  // High contrast mode
  highContrastEnabled: boolean;
  toggleHighContrast: () => void;

  // Reduced motion
  reducedMotionEnabled: boolean;
  toggleReducedMotion: () => void;

  // Focus management
  focusTrap: {
    enable: (container: HTMLElement) => void;
    disable: () => void;
  };

  // Screen reader announcements
  announce: (message: string, priority?: 'polite' | 'assertive') => void;

  // Keyboard navigation
  keyboardNavigationEnabled: boolean;
  toggleKeyboardNavigation: () => void;

  // Text scaling
  textScale: number;
  increaseTextScale: () => void;
  decreaseTextScale: () => void;
  resetTextScale: () => void;

  // Focus visible (show outline only on keyboard nav)
  focusVisibleEnabled: boolean;
}

const AccessibilityContext = createContext<AccessibilityContextValue | undefined>(undefined);

interface AccessibilityProviderProps {
  children: React.ReactNode;
  /**
   * Enable skip links for main content navigation
   */
  enableSkipLinks?: boolean;
  /**
   * Main content container ID for skip links
   */
  mainContentId?: string;
  /**
   * Enable automatic focus visible detection
   */
  enableFocusVisible?: boolean;
  /**
   * Enable automatic high contrast detection
   */
  detectHighContrast?: boolean;
  /**
   * Enable automatic reduced motion detection
   */
  detectReducedMotion?: boolean;
}

export const AccessibilityProvider: React.FC<AccessibilityProviderProps> = ({
  children,
  enableSkipLinks = true,
  mainContentId = 'main-content',
  enableFocusVisible = true,
  detectHighContrast = true,
  detectReducedMotion = true
}) => {
  // State
  const [highContrastEnabled, setHighContrastEnabled] = useState(false);
  const [reducedMotionEnabled, setReducedMotionEnabled] = useState(false);
  const [keyboardNavigationEnabled, setKeyboardNavigationEnabled] = useState(true);
  const [textScale, setTextScale] = useState(100);
  const [focusVisibleEnabled, setFocusVisibleEnabled] = useState(false);

  // Refs
  const focusTrapCleanupRef = useRef<(() => void) | null>(null);
  const lastInteractionWasKeyboard = useRef(false);

  /**
   * Initialize accessibility features
   */
  useEffect(() => {
    // Detect high contrast mode
    if (detectHighContrast) {
      const isHighContrast = isHighContrastMode();
      setHighContrastEnabled(isHighContrast);
      applyHighContrastTheme(isHighContrast);

      // Listen for changes
      const cleanup = onHighContrastModeChange((enabled) => {
        setHighContrastEnabled(enabled);
        applyHighContrastTheme(enabled);
      });

      return cleanup;
    }
  }, [detectHighContrast]);

  /**
   * Detect reduced motion preference
   */
  useEffect(() => {
    if (detectReducedMotion) {
      const prefersReduced = prefersReducedMotion();
      setReducedMotionEnabled(prefersReduced);

      if (prefersReduced) {
        document.documentElement.classList.add('reduce-motion');
      }

      // Listen for changes
      const cleanup = onReducedMotionChange((prefersReduced) => {
        setReducedMotionEnabled(prefersReduced);
        if (prefersReduced) {
          document.documentElement.classList.add('reduce-motion');
        } else {
          document.documentElement.classList.remove('reduce-motion');
        }
      });

      return cleanup;
    }
  }, [detectReducedMotion]);

  /**
   * Focus visible management (show focus only on keyboard navigation)
   */
  useEffect(() => {
    if (!enableFocusVisible) return;

    const handleMouseDown = () => {
      lastInteractionWasKeyboard.current = false;
      setFocusVisibleEnabled(false);
      document.documentElement.classList.remove('focus-visible');
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Tab' || e.key === 'Enter' || e.key === ' ' || e.key.startsWith('Arrow')) {
        lastInteractionWasKeyboard.current = true;
        setFocusVisibleEnabled(true);
        document.documentElement.classList.add('focus-visible');
      }
    };

    document.addEventListener('mousedown', handleMouseDown);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handleMouseDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [enableFocusVisible]);

  /**
   * Create skip links
   */
  useEffect(() => {
    if (!enableSkipLinks) return;

    const skipLink = createSkipLink(mainContentId, 'Skip to main content');
    document.body.insertBefore(skipLink, document.body.firstChild);

    return () => {
      skipLink.remove();
    };
  }, [enableSkipLinks, mainContentId]);

  /**
   * Apply text scaling
   */
  useEffect(() => {
    document.documentElement.style.fontSize = `${textScale}%`;
  }, [textScale]);

  /**
   * Add global keyboard shortcuts
   */
  useEffect(() => {
    const handleGlobalKeyboard = (e: KeyboardEvent) => {
      // Ctrl/Cmd + Plus: Increase text size
      if ((e.ctrlKey || e.metaKey) && e.key === '+') {
        e.preventDefault();
        increaseTextScale();
      }

      // Ctrl/Cmd + Minus: Decrease text size
      if ((e.ctrlKey || e.metaKey) && e.key === '-') {
        e.preventDefault();
        decreaseTextScale();
      }

      // Ctrl/Cmd + 0: Reset text size
      if ((e.ctrlKey || e.metaKey) && e.key === '0') {
        e.preventDefault();
        resetTextScale();
      }

      // Escape: Clear focus trap
      if (e.key === 'Escape' && focusTrapCleanupRef.current) {
        focusTrapCleanupRef.current();
        focusTrapCleanupRef.current = null;
      }
    };

    document.addEventListener('keydown', handleGlobalKeyboard);

    return () => {
      document.removeEventListener('keydown', handleGlobalKeyboard);
    };
  }, []);

  /**
   * Toggle high contrast mode
   */
  const toggleHighContrast = useCallback(() => {
    setHighContrastEnabled(prev => {
      const newValue = !prev;
      applyHighContrastTheme(newValue);
      announceToScreenReader(
        `High contrast mode ${newValue ? 'enabled' : 'disabled'}`,
        'polite'
      );
      return newValue;
    });
  }, []);

  /**
   * Toggle reduced motion
   */
  const toggleReducedMotion = useCallback(() => {
    setReducedMotionEnabled(prev => {
      const newValue = !prev;
      if (newValue) {
        document.documentElement.classList.add('reduce-motion');
      } else {
        document.documentElement.classList.remove('reduce-motion');
      }
      announceToScreenReader(
        `Reduced motion ${newValue ? 'enabled' : 'disabled'}`,
        'polite'
      );
      return newValue;
    });
  }, []);

  /**
   * Enable focus trap
   */
  const enableFocusTrap = useCallback((container: HTMLElement) => {
    // Disable any existing trap
    if (focusTrapCleanupRef.current) {
      focusTrapCleanupRef.current();
    }

    // Enable new trap
    focusTrapCleanupRef.current = trapFocus(container, true);
  }, []);

  /**
   * Disable focus trap
   */
  const disableFocusTrap = useCallback(() => {
    if (focusTrapCleanupRef.current) {
      focusTrapCleanupRef.current();
      focusTrapCleanupRef.current = null;
    }
  }, []);

  /**
   * Announce to screen readers
   */
  const announce = useCallback((message: string, priority: 'polite' | 'assertive' = 'polite') => {
    announceToScreenReader(message, priority);
  }, []);

  /**
   * Toggle keyboard navigation
   */
  const toggleKeyboardNavigation = useCallback(() => {
    setKeyboardNavigationEnabled(prev => {
      const newValue = !prev;
      announceToScreenReader(
        `Keyboard navigation ${newValue ? 'enabled' : 'disabled'}`,
        'polite'
      );
      return newValue;
    });
  }, []);

  /**
   * Text scaling functions
   */
  const increaseTextScale = useCallback(() => {
    setTextScale(prev => {
      const newScale = Math.min(prev + 10, 200);
      announceToScreenReader(`Text size increased to ${newScale}%`, 'polite');
      return newScale;
    });
  }, []);

  const decreaseTextScale = useCallback(() => {
    setTextScale(prev => {
      const newScale = Math.max(prev - 10, 50);
      announceToScreenReader(`Text size decreased to ${newScale}%`, 'polite');
      return newScale;
    });
  }, []);

  const resetTextScale = useCallback(() => {
    setTextScale(100);
    announceToScreenReader('Text size reset to 100%', 'polite');
  }, []);

  const value: AccessibilityContextValue = {
    highContrastEnabled,
    toggleHighContrast,
    reducedMotionEnabled,
    toggleReducedMotion,
    focusTrap: {
      enable: enableFocusTrap,
      disable: disableFocusTrap
    },
    announce,
    keyboardNavigationEnabled,
    toggleKeyboardNavigation,
    textScale,
    increaseTextScale,
    decreaseTextScale,
    resetTextScale,
    focusVisibleEnabled
  };

  return (
    <AccessibilityContext.Provider value={value}>
      {/* Live region for screen reader announcements */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        id="accessibility-announcer"
      />

      {/* Keyboard shortcuts help (Alt + K) */}
      <div
        id="keyboard-shortcuts"
        role="dialog"
        aria-label="Keyboard shortcuts"
        className="sr-only"
        tabIndex={-1}
      >
        <h2>Keyboard Shortcuts</h2>
        <ul>
          <li>Tab: Navigate forward</li>
          <li>Shift + Tab: Navigate backward</li>
          <li>Enter or Space: Activate element</li>
          <li>Escape: Close dialog or cancel action</li>
          <li>Arrow keys: Navigate within menus and lists</li>
          <li>Ctrl/Cmd + Plus: Increase text size</li>
          <li>Ctrl/Cmd + Minus: Decrease text size</li>
          <li>Ctrl/Cmd + 0: Reset text size</li>
        </ul>
      </div>

      {/* Main content wrapper with accessible attributes */}
      <div
        role="application"
        aria-label="Amharic Document System"
        lang="en"
        data-high-contrast={highContrastEnabled}
        data-reduced-motion={reducedMotionEnabled}
        data-keyboard-nav={keyboardNavigationEnabled}
      >
        {children}
      </div>
    </AccessibilityContext.Provider>
  );
};

/**
 * Hook to use accessibility context
 */
export function useAccessibility(): AccessibilityContextValue {
  const context = useContext(AccessibilityContext);

  if (!context) {
    throw new Error('useAccessibility must be used within AccessibilityProvider');
  }

  return context;
}

/**
 * Accessibility Control Panel Component
 */
interface AccessibilityControlsProps {
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  className?: string;
}

export const AccessibilityControls: React.FC<AccessibilityControlsProps> = ({
  position = 'bottom-right',
  className = ''
}) => {
  const {
    highContrastEnabled,
    toggleHighContrast,
    reducedMotionEnabled,
    toggleReducedMotion,
    textScale,
    increaseTextScale,
    decreaseTextScale,
    resetTextScale
  } = useAccessibility();

  const [isOpen, setIsOpen] = useState(false);

  const positionClasses = {
    'top-right': 'top-4 right-4',
    'top-left': 'top-4 left-4',
    'bottom-right': 'bottom-4 right-4',
    'bottom-left': 'bottom-4 left-4'
  };

  return (
    <div className={`fixed ${positionClasses[position]} z-50 ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-label="Accessibility settings"
        className="bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-full shadow-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
          />
        </svg>
      </button>

      {isOpen && (
        <div
          role="dialog"
          aria-label="Accessibility settings"
          className="absolute bottom-full mb-2 right-0 bg-white rounded-lg shadow-xl p-4 w-72"
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b">
              <h3 className="font-semibold text-gray-900">Accessibility</h3>
              <button
                onClick={() => setIsOpen(false)}
                aria-label="Close accessibility settings"
                className="text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* High Contrast Toggle */}
            <div className="flex items-center justify-between">
              <label htmlFor="high-contrast-toggle" className="text-sm font-medium text-gray-700">
                High Contrast
              </label>
              <button
                id="high-contrast-toggle"
                role="switch"
                aria-checked={highContrastEnabled}
                onClick={toggleHighContrast}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                  highContrastEnabled ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    highContrastEnabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Reduced Motion Toggle */}
            <div className="flex items-center justify-between">
              <label htmlFor="reduced-motion-toggle" className="text-sm font-medium text-gray-700">
                Reduced Motion
              </label>
              <button
                id="reduced-motion-toggle"
                role="switch"
                aria-checked={reducedMotionEnabled}
                onClick={toggleReducedMotion}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                  reducedMotionEnabled ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    reducedMotionEnabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Text Size Controls */}
            <div>
              <label className="text-sm font-medium text-gray-700 block mb-2">
                Text Size: {textScale}%
              </label>
              <div className="flex items-center space-x-2">
                <button
                  onClick={decreaseTextScale}
                  aria-label="Decrease text size"
                  disabled={textScale <= 50}
                  className="px-3 py-2 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  A-
                </button>
                <button
                  onClick={resetTextScale}
                  aria-label="Reset text size"
                  className="px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  Reset
                </button>
                <button
                  onClick={increaseTextScale}
                  aria-label="Increase text size"
                  disabled={textScale >= 200}
                  className="px-3 py-2 bg-gray-100 hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  A+
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AccessibilityProvider;