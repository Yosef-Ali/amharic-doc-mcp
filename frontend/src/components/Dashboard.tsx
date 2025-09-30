import { FormEvent, useMemo, useState } from 'react'

type DocumentStatus = 'Ready' | 'Processing' | 'Completed'

interface DocumentSummary {
  id: string
  name: string
  uploadedAt: string
  status: DocumentStatus
  notes?: string
}

const starterDocuments: DocumentSummary[] = [
  {
    id: '1',
    name: 'ትምህርት መመሪያ 2024.pdf',
    uploadedAt: '2024-02-04',
    status: 'Completed',
    notes: 'Converted to searchable PDF',
  },
  {
    id: '2',
    name: 'Meeting Minutes.docx',
    uploadedAt: '2024-03-12',
    status: 'Processing',
    notes: 'OCR running (Amharic + English)',
  },
  {
    id: '3',
    name: 'አመታዊ ሪፖርት.xlsx',
    uploadedAt: '2024-01-28',
    status: 'Ready',
    notes: 'Waiting for review',
  },
]

function createDocumentFromName(name: string): DocumentSummary {
  const now = new Date()
  const id = Math.random().toString(36).slice(2, 10)
  return {
    id,
    name,
    uploadedAt: now.toISOString().slice(0, 10),
    status: 'Processing',
    notes: 'Queued for processing',
  }
}

function formatStatus(status: DocumentStatus) {
  switch (status) {
    case 'Completed':
      return 'text-green-700 bg-green-100'
    case 'Processing':
      return 'text-amber-700 bg-amber-100'
    default:
      return 'text-slate-700 bg-slate-100'
  }
}

export default function Dashboard() {
  const [documents, setDocuments] = useState<DocumentSummary[]>(starterDocuments)
  const [searchTerm, setSearchTerm] = useState('')
  const [newDocumentName, setNewDocumentName] = useState('')
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | 'All'>('All')

  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      const matchesTerm = doc.name.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesStatus = statusFilter === 'All' || doc.status === statusFilter
      return matchesTerm && matchesStatus
    })
  }, [documents, searchTerm, statusFilter])

  const totals = useMemo(() => {
    return documents.reduce(
      (acc, doc) => {
        acc[doc.status] += 1
        return acc
      },
      { Ready: 0, Processing: 0, Completed: 0 } as Record<DocumentStatus, number>,
    )
  }, [documents])

  const handleCreateDocument = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!newDocumentName.trim()) {
      return
    }

    setDocuments((current) => [createDocumentFromName(newDocumentName.trim()), ...current])
    setNewDocumentName('')
  }

  return (
    <div className="space-y-8">
      <section className="grid gap-4 md:grid-cols-3">
        <article className="card">
          <h2 className="text-lg font-semibold text-gray-900">Ready</h2>
          <p className="mt-2 text-3xl font-bold text-gray-800">{totals.Ready}</p>
          <p className="mt-1 text-sm text-gray-500">Waiting for manual review</p>
        </article>
        <article className="card">
          <h2 className="text-lg font-semibold text-gray-900">Processing</h2>
          <p className="mt-2 text-3xl font-bold text-gray-800">{totals.Processing}</p>
          <p className="mt-1 text-sm text-gray-500">Documents currently being processed</p>
        </article>
        <article className="card">
          <h2 className="text-lg font-semibold text-gray-900">Completed</h2>
          <p className="mt-2 text-3xl font-bold text-gray-800">{totals.Completed}</p>
          <p className="mt-1 text-sm text-gray-500">Ready to download and share</p>
        </article>
      </section>

      <section className="card">
        <form className="space-y-4" onSubmit={handleCreateDocument}>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Add a document manually</h2>
            <p className="text-sm text-gray-500">
              Enter a document name to simulate an upload. The item will appear in the list below.
            </p>
          </div>
          <div className="flex flex-col gap-3 sm:flex-row">
            <label className="sr-only" htmlFor="document-name">
              Document name
            </label>
            <input
              id="document-name"
              className="input sm:flex-1"
              placeholder="አዲስ ሰነድ ስም"
              value={newDocumentName}
              onChange={(event) => setNewDocumentName(event.target.value)}
            />
            <button type="submit" className="btn-primary sm:w-auto">
              Add document
            </button>
          </div>
        </form>
      </section>

      <section className="card space-y-4">
        <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Document history</h2>
            <p className="text-sm text-gray-500">
              Filter by name or status to quickly find a document.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <label className="sr-only" htmlFor="status-filter">
              Status filter
            </label>
            <select
              id="status-filter"
              className="input w-full sm:w-48"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as DocumentStatus | 'All')}
            >
              <option value="All">All statuses</option>
              <option value="Ready">Ready</option>
              <option value="Processing">Processing</option>
              <option value="Completed">Completed</option>
            </select>
            <label className="sr-only" htmlFor="search-term">
              Search documents
            </label>
            <input
              id="search-term"
              className="input w-full sm:w-64"
              placeholder="Search documents"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </div>
        </header>

        <ul className="divide-y divide-gray-200">
          {filteredDocuments.length === 0 && (
            <li className="py-8 text-center text-sm text-gray-500">
              No documents match the current filters.
            </li>
          )}

          {filteredDocuments.map((doc) => (
            <li key={doc.id} className="py-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium text-gray-900">{doc.name}</p>
                  <p className="text-sm text-gray-500">
                    Uploaded on {doc.uploadedAt}
                    {doc.notes ? ` · ${doc.notes}` : ''}
                  </p>
                </div>
                <span
                  className={`inline-flex items-center justify-center rounded-full px-3 py-1 text-sm font-medium ${formatStatus(doc.status)}`}
                >
                  {doc.status}
                </span>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
