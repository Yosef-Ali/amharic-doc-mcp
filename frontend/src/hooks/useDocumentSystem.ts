import { useCallback, useMemo, useState } from 'react'

type DocumentStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED'

type ProcessingStatus = 'pending' | 'running' | 'completed'

type ExportStatus = 'processing' | 'completed' | 'failed'

export interface Document {
  id: string
  filename: string
  contentType: string
  fileSize: number
  status: DocumentStatus
  createdAt: string
  updatedAt: string
  progress?: number
}

export interface ProcessingJob {
  id: string
  documentId: string
  jobType: string
  status: ProcessingStatus
  progress: number
  createdAt: string
  errorMessage?: string
}

export interface SearchResult {
  documentId: string
  filename: string
  contentSnippet: string
  relevanceScore: number
  createdAt: string
}

export interface ExportJob {
  id: string
  documentId: string
  format: string
  status: ExportStatus
  downloadUrl?: string
}

export interface DocumentSystemState {
  documents: Document[]
  jobs: ProcessingJob[]
  searchResults: SearchResult[]
  exportJobs: ExportJob[]
  loading: boolean
  error: string | null
  connected: boolean
}

export interface UseDocumentSystemReturn {
  state: DocumentSystemState
  uploadDocument: (filename: string) => Promise<Document>
  deleteDocument: (documentId: string) => Promise<void>
  getDocuments: () => Promise<Document[]>
  createProcessingJob: (documentId: string, jobType: string) => Promise<ProcessingJob>
  getProcessingJobs: () => Promise<ProcessingJob[]>
  searchDocuments: (query: string) => Promise<SearchResult[]>
  exportDocument: (documentId: string, format: string) => Promise<ExportJob>
  downloadExport: (exportId: string) => Promise<Blob>
  getSystemStatus: () => Promise<Record<string, string | number>>
  refreshData: () => Promise<void>
  clearError: () => void
  connect: () => void
  disconnect: () => void
}

const initialDocuments: Document[] = [
  {
    id: 'doc-1',
    filename: 'ትምህርት መዝገብ.pdf',
    contentType: 'application/pdf',
    fileSize: 2100,
    status: 'COMPLETED',
    createdAt: '2024-02-01',
    updatedAt: '2024-02-03',
  },
  {
    id: 'doc-2',
    filename: 'Meeting Minutes.docx',
    contentType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    fileSize: 1500,
    status: 'PROCESSING',
    createdAt: '2024-03-09',
    updatedAt: '2024-03-10',
    progress: 45,
  },
]

const initialJobs: ProcessingJob[] = [
  {
    id: 'job-1',
    documentId: 'doc-2',
    jobType: 'ocr',
    status: 'running',
    progress: 45,
    createdAt: '2024-03-10',
  },
]

const shortDelay = (ms = 200) => new Promise<void>((resolve) => setTimeout(resolve, ms))

const now = () => new Date().toISOString()

export const useDocumentSystem = (): UseDocumentSystemReturn => {
  const [state, setState] = useState<DocumentSystemState>({
    documents: initialDocuments,
    jobs: initialJobs,
    searchResults: [],
    exportJobs: [],
    loading: false,
    error: null,
    connected: false,
  })

  const safeSetState = useCallback(
    (updater: (previous: DocumentSystemState) => DocumentSystemState) => {
      setState((previous) => updater({ ...previous }))
    },
    [],
  )

  const refreshData = useCallback(async () => {
    safeSetState((prev) => ({ ...prev, loading: true }))
    await shortDelay()
    safeSetState((prev) => ({ ...prev, loading: false }))
  }, [safeSetState])

  const uploadDocument = useCallback(async (filename: string) => {
    await shortDelay()
    const newDocument: Document = {
      id: Math.random().toString(36).slice(2, 10),
      filename,
      contentType: 'application/octet-stream',
      fileSize: 0,
      status: 'PENDING',
      createdAt: now(),
      updatedAt: now(),
    }
    safeSetState((prev) => ({
      ...prev,
      documents: [newDocument, ...prev.documents],
    }))
    return newDocument
  }, [safeSetState])

  const deleteDocument = useCallback(async (documentId: string) => {
    await shortDelay()
    safeSetState((prev) => ({
      ...prev,
      documents: prev.documents.filter((doc) => doc.id !== documentId),
      jobs: prev.jobs.filter((job) => job.documentId !== documentId),
    }))
  }, [safeSetState])

  const getDocuments = useCallback(async () => {
    await shortDelay()
    return state.documents
  }, [state.documents])

  const createProcessingJob = useCallback(async (documentId: string, jobType: string) => {
    await shortDelay()
    const job: ProcessingJob = {
      id: Math.random().toString(36).slice(2, 10),
      documentId,
      jobType,
      status: 'pending',
      progress: 0,
      createdAt: now(),
    }
    safeSetState((prev) => ({
      ...prev,
      jobs: [job, ...prev.jobs],
    }))
    return job
  }, [safeSetState])

  const getProcessingJobs = useCallback(async () => {
    await shortDelay()
    return state.jobs
  }, [state.jobs])

  const searchDocuments = useCallback(async (query: string) => {
    await shortDelay()
    const cleaned = query.trim().toLowerCase()
    const results: SearchResult[] = state.documents
      .filter((doc) => doc.filename.toLowerCase().includes(cleaned))
      .map((doc) => ({
        documentId: doc.id,
        filename: doc.filename,
        contentSnippet: 'Sample extract showing highlighted search terms.',
        relevanceScore: 0.75,
        createdAt: doc.createdAt,
      }))
    safeSetState((prev) => ({ ...prev, searchResults: results }))
    return results
  }, [safeSetState, state.documents])

  const exportDocument = useCallback(async (documentId: string, format: string) => {
    await shortDelay()
    const exportJob: ExportJob = {
      id: Math.random().toString(36).slice(2, 10),
      documentId,
      format,
      status: 'processing',
    }
    safeSetState((prev) => ({
      ...prev,
      exportJobs: [exportJob, ...prev.exportJobs],
    }))
    return exportJob
  }, [safeSetState])

  const downloadExport = useCallback(async (_exportId: string) => {
    await shortDelay()
    return new Blob(['Sample export content'], { type: 'text/plain' })
  }, [])

  const getSystemStatus = useCallback(async () => {
    await shortDelay()
    return {
      documents: state.documents.length,
      processingJobs: state.jobs.length,
      lastUpdated: now(),
    }
  }, [state.documents.length, state.jobs.length])

  const clearError = useCallback(() => {
    safeSetState((prev) => ({ ...prev, error: null }))
  }, [safeSetState])

  const connect = useCallback(() => {
    safeSetState((prev) => ({ ...prev, connected: true }))
  }, [safeSetState])

  const disconnect = useCallback(() => {
    safeSetState((prev) => ({ ...prev, connected: false }))
  }, [safeSetState])

  const publicState = useMemo<DocumentSystemState>(() => ({ ...state }), [state])

  return {
    state: publicState,
    uploadDocument,
    deleteDocument,
    getDocuments,
    createProcessingJob,
    getProcessingJobs,
    searchDocuments,
    exportDocument,
    downloadExport,
    getSystemStatus,
    refreshData,
    clearError,
    connect,
    disconnect,
  }
}
