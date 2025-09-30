import React from 'react'

interface AccessibilityWrapperProps {
  children: React.ReactNode
}

const AccessibilityWrapper: React.FC<AccessibilityWrapperProps> = ({ children }) => {
  return (
    <div role="region" aria-live="polite" aria-atomic="true">
      {children}
    </div>
  )
}

export default AccessibilityWrapper
