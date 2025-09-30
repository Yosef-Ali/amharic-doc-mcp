import React from 'react'

interface LayoutProps {
  children: React.ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="flex min-h-screen bg-gray-50 text-gray-900">
      <div className="flex-1 flex flex-col">
        <header className="bg-white border-b border-gray-200 px-6 py-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <p className="text-sm uppercase tracking-wide text-primary-600">
                Amharic Document Tools
              </p>
              <h1 className="text-2xl font-semibold">Simple Processing Dashboard</h1>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <span className="font-medium text-gray-700">Status:</span>
              <span className="px-2 py-1 rounded-full bg-green-100 text-green-700">
                Ready
              </span>
            </div>
          </div>
        </header>

        <main id="main-content" className="flex-1 overflow-auto p-6">
          <div className="mx-auto w-full max-w-5xl space-y-6">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
