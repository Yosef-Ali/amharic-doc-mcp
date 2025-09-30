/**
 * Accessibility Utilities
 *
 * Provides comprehensive accessibility helpers for WCAG 2.1 Level AA compliance
 * including focus management, ARIA helpers, and high-contrast mode support.
 */

/**
 * Focus Management
 */

/**
 * Trap focus within a container element (e.g., modals, dialogs)
 * @param container The container element to trap focus within
 * @param restoreFocusOnUnmount Whether to restore focus when unmounting
 * @returns Cleanup function to remove trap
 */
export function trapFocus(
  container: HTMLElement,
  restoreFocusOnUnmount: boolean = true
): () => void {
  const previouslyFocusedElement = document.activeElement as HTMLElement;

  // Get all focusable elements within container
  const getFocusableElements = (): HTMLElement[] => {
    const focusableSelectors = [
      'a[href]',
      'button:not([disabled])',
      'textarea:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      '[tabindex]:not([tabindex="-1"])',
      '[contenteditable="true"]'
    ].join(', ');

    return Array.from(
      container.querySelectorAll<HTMLElement>(focusableSelectors)
    ).filter(
      el => el.offsetParent !== null && !el.hasAttribute('aria-hidden')
    );
  };

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key !== 'Tab') return;

    const focusableElements = getFocusableElements();
    if (focusableElements.length === 0) {
      event.preventDefault();
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Shift + Tab
    if (event.shiftKey) {
      if (document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      }
    }
    // Tab
    else {
      if (document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    }
  };

  // Focus first element
  const focusableElements = getFocusableElements();
  if (focusableElements.length > 0) {
    focusableElements[0].focus();
  }

  // Add event listener
  container.addEventListener('keydown', handleKeyDown);

  // Return cleanup function
  return () => {
    container.removeEventListener('keydown', handleKeyDown);
    if (restoreFocusOnUnmount && previouslyFocusedElement) {
      previouslyFocusedElement.focus();
    }
  };
}

/**
 * Focus first focusable element in container
 */
export function focusFirstElement(container: HTMLElement): boolean {
  const focusableElements = container.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
  );

  if (focusableElements.length > 0) {
    focusableElements[0].focus();
    return true;
  }

  return false;
}

/**
 * Move focus to specific element with optional scroll
 */
export function moveFocusTo(
  element: HTMLElement | null,
  options: { preventScroll?: boolean; selectText?: boolean } = {}
): void {
  if (!element) return;

  element.focus({ preventScroll: options.preventScroll });

  if (options.selectText && element instanceof HTMLInputElement) {
    element.select();
  }
}

/**
 * Create a focus guard to prevent focus from leaving a region
 */
export function createFocusGuard(region: HTMLElement): {
  before: HTMLElement;
  after: HTMLElement;
} {
  const createGuard = (): HTMLElement => {
    const guard = document.createElement('div');
    guard.setAttribute('tabindex', '0');
    guard.setAttribute('aria-hidden', 'true');
    guard.style.cssText = 'position:fixed;top:0;left:0;width:1px;height:1px;opacity:0;pointer-events:none;';
    return guard;
  };

  const beforeGuard = createGuard();
  const afterGuard = createGuard();

  beforeGuard.addEventListener('focus', () => {
    const focusableElements = region.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
    const lastElement = focusableElements[focusableElements.length - 1];
    if (lastElement) lastElement.focus();
  });

  afterGuard.addEventListener('focus', () => {
    const focusableElements = region.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [tabindex]:not([tabindex="-1"])'
    );
    if (focusableElements[0]) focusableElements[0].focus();
  });

  region.parentElement?.insertBefore(beforeGuard, region);
  region.parentElement?.insertBefore(afterGuard, region.nextSibling);

  return { before: beforeGuard, after: afterGuard };
}

/**
 * ARIA Helpers
 */

/**
 * Announce message to screen readers using live region
 */
export function announceToScreenReader(
  message: string,
  priority: 'polite' | 'assertive' = 'polite',
  timeout: number = 5000
): void {
  const announcement = document.createElement('div');
  announcement.setAttribute('role', 'status');
  announcement.setAttribute('aria-live', priority);
  announcement.setAttribute('aria-atomic', 'true');
  announcement.className = 'sr-only';
  announcement.textContent = message;

  document.body.appendChild(announcement);

  setTimeout(() => {
    document.body.removeChild(announcement);
  }, timeout);
}

/**
 * Generate unique ID for ARIA relationships
 */
let idCounter = 0;
export function generateAriaId(prefix: string = 'aria'): string {
  return `${prefix}-${++idCounter}-${Date.now()}`;
}

/**
 * Set ARIA relationship between elements
 */
export function setAriaRelationship(
  element: HTMLElement,
  relatedElement: HTMLElement,
  relationship: 'labelledby' | 'describedby' | 'controls' | 'owns'
): void {
  if (!relatedElement.id) {
    relatedElement.id = generateAriaId(relationship);
  }

  const attrName = `aria-${relationship}`;
  const existingIds = element.getAttribute(attrName)?.split(' ') || [];

  if (!existingIds.includes(relatedElement.id)) {
    existingIds.push(relatedElement.id);
    element.setAttribute(attrName, existingIds.join(' '));
  }
}

/**
 * Remove ARIA relationship
 */
export function removeAriaRelationship(
  element: HTMLElement,
  relatedElementId: string,
  relationship: 'labelledby' | 'describedby' | 'controls' | 'owns'
): void {
  const attrName = `aria-${relationship}`;
  const existingIds = element.getAttribute(attrName)?.split(' ') || [];
  const updatedIds = existingIds.filter(id => id !== relatedElementId);

  if (updatedIds.length > 0) {
    element.setAttribute(attrName, updatedIds.join(' '));
  } else {
    element.removeAttribute(attrName);
  }
}

/**
 * Set ARIA expanded state for expandable elements
 */
export function setAriaExpanded(element: HTMLElement, expanded: boolean): void {
  element.setAttribute('aria-expanded', expanded.toString());
}

/**
 * Set ARIA pressed state for toggle buttons
 */
export function setAriaPressed(element: HTMLElement, pressed: boolean): void {
  element.setAttribute('aria-pressed', pressed.toString());
}

/**
 * Set ARIA checked state for checkboxes/radio buttons
 */
export function setAriaChecked(
  element: HTMLElement,
  checked: boolean | 'mixed'
): void {
  element.setAttribute('aria-checked', checked.toString());
}

/**
 * Set ARIA selected state
 */
export function setAriaSelected(element: HTMLElement, selected: boolean): void {
  element.setAttribute('aria-selected', selected.toString());
}

/**
 * Set ARIA disabled state
 */
export function setAriaDisabled(element: HTMLElement, disabled: boolean): void {
  element.setAttribute('aria-disabled', disabled.toString());
}

/**
 * Set ARIA busy state (loading indicator)
 */
export function setAriaBusy(element: HTMLElement, busy: boolean): void {
  element.setAttribute('aria-busy', busy.toString());
}

/**
 * Set ARIA invalid state for form validation
 */
export function setAriaInvalid(element: HTMLElement, invalid: boolean): void {
  element.setAttribute('aria-invalid', invalid.toString());
}

/**
 * High Contrast Mode
 */

/**
 * Detect if high contrast mode is enabled
 */
export function isHighContrastMode(): boolean {
  // Check for Windows high contrast mode
  if (window.matchMedia) {
    return window.matchMedia('(prefers-contrast: high)').matches ||
           window.matchMedia('(-ms-high-contrast: active)').matches ||
           window.matchMedia('(-ms-high-contrast: black-on-white)').matches ||
           window.matchMedia('(-ms-high-contrast: white-on-black)').matches;
  }
  return false;
}

/**
 * Listen for high contrast mode changes
 */
export function onHighContrastModeChange(
  callback: (isHighContrast: boolean) => void
): () => void {
  const mediaQuery = window.matchMedia('(prefers-contrast: high)');
  const msMediaQuery = window.matchMedia('(-ms-high-contrast: active)');

  const handleChange = () => {
    callback(isHighContrastMode());
  };

  mediaQuery.addEventListener('change', handleChange);
  msMediaQuery.addEventListener('change', handleChange);

  return () => {
    mediaQuery.removeEventListener('change', handleChange);
    msMediaQuery.removeEventListener('change', handleChange);
  };
}

/**
 * Apply high contrast theme
 */
export function applyHighContrastTheme(enable: boolean): void {
  if (enable) {
    document.documentElement.classList.add('high-contrast');
    document.documentElement.style.setProperty('--contrast-mode', 'high');
  } else {
    document.documentElement.classList.remove('high-contrast');
    document.documentElement.style.removeProperty('--contrast-mode');
  }
}

/**
 * Color Contrast
 */

/**
 * Calculate relative luminance of a color
 */
function getRelativeLuminance(rgb: { r: number; g: number; b: number }): number {
  const rsRGB = rgb.r / 255;
  const gsRGB = rgb.g / 255;
  const bsRGB = rgb.b / 255;

  const r = rsRGB <= 0.03928 ? rsRGB / 12.92 : Math.pow((rsRGB + 0.055) / 1.055, 2.4);
  const g = gsRGB <= 0.03928 ? gsRGB / 12.92 : Math.pow((gsRGB + 0.055) / 1.055, 2.4);
  const b = bsRGB <= 0.03928 ? bsRGB / 12.92 : Math.pow((bsRGB + 0.055) / 1.055, 2.4);

  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/**
 * Calculate contrast ratio between two colors
 */
export function getContrastRatio(
  color1: string,
  color2: string
): number {
  // Parse hex colors
  const parseHex = (hex: string): { r: number; g: number; b: number } => {
    const normalized = hex.replace('#', '');
    return {
      r: parseInt(normalized.substr(0, 2), 16),
      g: parseInt(normalized.substr(2, 2), 16),
      b: parseInt(normalized.substr(4, 2), 16)
    };
  };

  const rgb1 = parseHex(color1);
  const rgb2 = parseHex(color2);

  const l1 = getRelativeLuminance(rgb1);
  const l2 = getRelativeLuminance(rgb2);

  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);

  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Check if color contrast meets WCAG AA standards
 */
export function meetsContrastRequirement(
  foreground: string,
  background: string,
  level: 'AA' | 'AAA' = 'AA',
  fontSize: 'normal' | 'large' = 'normal'
): boolean {
  const ratio = getContrastRatio(foreground, background);

  if (level === 'AAA') {
    return fontSize === 'large' ? ratio >= 4.5 : ratio >= 7;
  }

  return fontSize === 'large' ? ratio >= 3 : ratio >= 4.5;
}

/**
 * Keyboard Navigation
 */

/**
 * Handle arrow key navigation for lists/menus
 */
export function handleArrowKeyNavigation(
  event: KeyboardEvent,
  elements: HTMLElement[],
  currentIndex: number,
  options: {
    loop?: boolean;
    horizontal?: boolean;
    onNavigate?: (newIndex: number) => void;
  } = {}
): number {
  const { loop = true, horizontal = false, onNavigate } = options;

  let newIndex = currentIndex;

  const nextKey = horizontal ? 'ArrowRight' : 'ArrowDown';
  const prevKey = horizontal ? 'ArrowLeft' : 'ArrowUp';

  if (event.key === nextKey) {
    event.preventDefault();
    newIndex = currentIndex + 1;
    if (newIndex >= elements.length) {
      newIndex = loop ? 0 : elements.length - 1;
    }
  } else if (event.key === prevKey) {
    event.preventDefault();
    newIndex = currentIndex - 1;
    if (newIndex < 0) {
      newIndex = loop ? elements.length - 1 : 0;
    }
  } else if (event.key === 'Home') {
    event.preventDefault();
    newIndex = 0;
  } else if (event.key === 'End') {
    event.preventDefault();
    newIndex = elements.length - 1;
  }

  if (newIndex !== currentIndex) {
    elements[newIndex]?.focus();
    onNavigate?.(newIndex);
  }

  return newIndex;
}

/**
 * Screen Reader Utilities
 */

/**
 * Hide element from screen readers
 */
export function hideFromScreenReaders(element: HTMLElement): void {
  element.setAttribute('aria-hidden', 'true');
}

/**
 * Show element to screen readers
 */
export function showToScreenReaders(element: HTMLElement): void {
  element.removeAttribute('aria-hidden');
}

/**
 * Check if element is visible to screen readers
 */
export function isVisibleToScreenReaders(element: HTMLElement): boolean {
  return element.getAttribute('aria-hidden') !== 'true';
}

/**
 * Create visually hidden but screen reader accessible element
 */
export function createScreenReaderOnlyElement(text: string): HTMLElement {
  const element = document.createElement('span');
  element.textContent = text;
  element.className = 'sr-only';
  element.style.cssText = `
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
  `;
  return element;
}

/**
 * Form Accessibility
 */

/**
 * Associate label with form field
 */
export function associateLabelWithField(
  label: HTMLLabelElement,
  field: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
): void {
  if (!field.id) {
    field.id = generateAriaId('field');
  }
  label.setAttribute('for', field.id);
}

/**
 * Add error message to form field
 */
export function addFieldError(
  field: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement,
  errorMessage: string
): HTMLElement {
  const errorId = `${field.id || generateAriaId('field')}-error`;
  let errorElement = document.getElementById(errorId);

  if (!errorElement) {
    errorElement = document.createElement('div');
    errorElement.id = errorId;
    errorElement.className = 'field-error';
    errorElement.setAttribute('role', 'alert');
    field.parentElement?.appendChild(errorElement);
  }

  errorElement.textContent = errorMessage;
  field.setAttribute('aria-invalid', 'true');
  field.setAttribute('aria-describedby', errorId);

  return errorElement;
}

/**
 * Remove error message from form field
 */
export function removeFieldError(
  field: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
): void {
  const errorId = field.getAttribute('aria-describedby');
  if (errorId) {
    const errorElement = document.getElementById(errorId);
    errorElement?.remove();
  }

  field.removeAttribute('aria-invalid');
  field.removeAttribute('aria-describedby');
}

/**
 * Skip Links
 */

/**
 * Create skip to content link
 */
export function createSkipLink(
  targetId: string,
  text: string = 'Skip to main content'
): HTMLAnchorElement {
  const skipLink = document.createElement('a');
  skipLink.href = `#${targetId}`;
  skipLink.textContent = text;
  skipLink.className = 'skip-link';
  skipLink.style.cssText = `
    position: absolute;
    top: -40px;
    left: 0;
    background: #000;
    color: #fff;
    padding: 8px;
    text-decoration: none;
    z-index: 9999;
  `;

  skipLink.addEventListener('focus', () => {
    skipLink.style.top = '0';
  });

  skipLink.addEventListener('blur', () => {
    skipLink.style.top = '-40px';
  });

  return skipLink;
}

/**
 * Reduced Motion
 */

/**
 * Check if user prefers reduced motion
 */
export function prefersReducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Listen for reduced motion preference changes
 */
export function onReducedMotionChange(
  callback: (prefersReduced: boolean) => void
): () => void {
  const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

  const handleChange = () => {
    callback(mediaQuery.matches);
  };

  mediaQuery.addEventListener('change', handleChange);

  return () => {
    mediaQuery.removeEventListener('change', handleChange);
  };
}