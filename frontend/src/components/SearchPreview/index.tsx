import React from 'react'

export interface SearchResultItem {
  id: string
  title: string
  snippet: string
  metadata?: Record<string, string>
}

export interface SearchPreviewProps {
  results?: SearchResultItem[]
  query?: string
}

const SearchPreview: React.FC<SearchPreviewProps> = ({ results = [], query }) => {
  const hasResults = results.length > 0

  return (
    <section className="card space-y-4" aria-live="polite">
      <header>
        <h2 className="text-lg font-semibold text-gray-900">Search results</h2>
        {query && <p className="text-sm text-gray-500">Showing matches for “{query}”.</p>}
      </header>

      {!hasResults && <p className="text-sm text-gray-500">No documents found.</p>}

      {hasResults && (
        <ul className="space-y-3">
          {results.map((result, index) => (
            <li key={result.id} className="rounded-lg border border-gray-200 p-4" aria-label={result.title}>
              <div className="text-xs font-semibold uppercase text-gray-500">Result {index + 1}</div>
              <p className="mt-2 text-sm text-gray-700" dangerouslySetInnerHTML={{ __html: result.snippet }} />
              {result.metadata && (
                <dl className="mt-2 grid grid-cols-2 gap-2 text-xs text-gray-500">
                  {Object.entries(result.metadata).map(([label, value]) => (
                    <div key={label}>
                      <dt className="font-medium text-gray-600">{label}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default SearchPreview
