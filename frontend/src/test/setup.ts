import '@testing-library/jest-dom'

declare global {
  interface Window {
    scrollTo: (options?: ScrollToOptions | number, y?: number) => void
  }
}

if (typeof window !== 'undefined' && typeof window.scrollTo !== 'function') {
  window.scrollTo = () => {}
}
