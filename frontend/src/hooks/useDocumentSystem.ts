/**
 * CopilotKit hooks orchestration coordinating MCP calls, optimistic updates, and error surfacing
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';

// Types for MCP integration
interface MCPToolResult {
  success: boolean;
  result?: any;
  error?: string;
  execution_time_ms?: number;
  metadata?: Record<string, any>;
}

interface Document {
  id: string;
  filename: string;
  content_type: string;
  file_size: number;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  created_at: string;
  updated_at: string;
  progress?: number;
}

interface ProcessingJob {
  id: string;
  document_id: string;
  job_type: string;
  status: string;
  progress?: number;
  created_at: string;
  error_message?: string;
}

interface SearchResult {
  document_id: string;
  filename: string;
  content_snippet: string;
  relevance_score: number;
  created_at: string;
}

interface ExportJob {
  id: string;
  document_id: string;
  format: string;
  status: 'processing' | 'completed' | 'failed';
  download_url?: string;
}

interface DocumentSystemState {
  documents: Document[];
  jobs: ProcessingJob[];
  searchResults: SearchResult[];
  exportJobs: ExportJob[];
  loading: boolean;
  error: string | null;
  connected: boolean;
}

interface UseDocumentSystemOptions {
  enableRealTimeUpdates?: boolean;
  autoRefreshInterval?: number;
  optimisticUpdates?: boolean;
  retryFailedOperations?: boolean;
  maxRetries?: number;
}

interface UseDocumentSystemReturn {
  // State
  state: DocumentSystemState;
  
  // Document operations
  uploadDocument: (file: File, metadata?: Record<string, any>) => Promise<Document>;
  getDocument: (documentId: string) => Promise<Document>;
  deleteDocument: (documentId: string) => Promise<void>;
  getDocuments: (filters?: Record<string, any>) => Promise<Document[]>;
  
  // Processing operations
  createProcessingJob: (documentId: string, jobType: string) => Promise<ProcessingJob>;
  getProcessingJob: (jobId: string) => Promise<ProcessingJob>;
  cancelProcessingJob: (jobId: string) => Promise<void>;
  getProcessingJobs: (filters?: Record<string, any>) => Promise<ProcessingJob[]>;
  
  // Search operations
  searchDocuments: (query: string, filters?: Record<string, any>) => Promise<SearchResult[]>;
  getSuggestions: (query: string) => Promise<string[]>;
  
  // Export operations
  exportDocument: (documentId: string, format: string) => Promise<ExportJob>;
  getExportJob: (exportId: string) => Promise<ExportJob>;
  downloadExport: (exportId: string) => Promise<Blob>;
  
  // System operations
  getSystemStatus: () => Promise<Record<string, any>>;
  refreshData: () => Promise<void>;
  clearError: () => void;
  
  // Real-time connection
  connect: () => void;
  disconnect: () => void;
}

export const useDocumentSystem = (
  options: UseDocumentSystemOptions = {}
): UseDocumentSystemReturn => {
  const {
    enableRealTimeUpdates = true,
    autoRefreshInterval = 30000, // 30 seconds
    optimisticUpdates = true,
    retryFailedOperations = true,
    maxRetries = 3
  } = options;

  const { t } = useTranslation();
  
  // State management
  const [state, setState] = useState<DocumentSystemState>({
    documents: [],
    jobs: [],
    searchResults: [],
    exportJobs: [],
    loading: false,
    error: null,
    connected: false
  });

  // Refs for cleanup and persistence
  const websocketRef = useRef<WebSocket | null>(null);
  const retryTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // MCP tool execution helper
  const executeMCPTool = useCallback(async (
    toolName: string, 
    arguments_: Record<string, any>
  ): Promise<MCPToolResult> => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/mcp/tools/${toolName}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ arguments: arguments_ })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }, []);

  // Retry mechanism for failed operations
  const withRetry = useCallback(async <T>(
    operation: () => Promise<T>,
    operationId: string,
    retryCount = 0
  ): Promise<T> => {
    try {
      return await operation();
    } catch (error) {
      if (retryFailedOperations && retryCount < maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, retryCount), 10000); // Exponential backoff, max 10s
        
        return new Promise((resolve, reject) => {
          const timeoutId = setTimeout(async () => {
            retryTimeoutsRef.current.delete(operationId);
            try {
              const result = await withRetry(operation, operationId, retryCount + 1);
              resolve(result);
            } catch (retryError) {
              reject(retryError);
            }
          }, delay);
          
          retryTimeoutsRef.current.set(operationId, timeoutId);
        });
      }
      throw error;
    }
  }, [retryFailedOperations, maxRetries]);

  // Optimistic update helper
  const optimisticUpdate = useCallback(<T>(
    updateFn: (prevState: DocumentSystemState) => DocumentSystemState,
    operation: () => Promise<T>,
    rollbackFn?: (prevState: DocumentSystemState, error: Error) => DocumentSystemState
  ): Promise<T> => {
    if (!optimisticUpdates) {
      return operation();
    }

    // Apply optimistic update
    const prevState = state;
    setState(updateFn);

    return operation().catch(error => {
      // Rollback on error
      if (rollbackFn) {
        setState(rollbackFn(prevState, error));
      } else {
        setState(prevState);
      }
      throw error;
    });
  }, [optimisticUpdates, state]);

  // WebSocket connection management
  const connect = useCallback(() => {
    if (!enableRealTimeUpdates || websocketRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const token = localStorage.getItem('access_token');
      const userId = localStorage.getItem('user_id');
      
      if (!token || !userId) {
        throw new Error('Authentication required for real-time updates');
      }

      const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/mcp/ws/${userId}`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setState(prev => ({ ...prev, connected: true }));
        
        // Subscribe to all relevant events
        ws.send(JSON.stringify({
          type: 'subscribe',
          subscription_type: 'processing_updates'
        }));
        ws.send(JSON.stringify({
          type: 'subscribe',
          subscription_type: 'document_notifications'
        }));
        ws.send(JSON.stringify({
          type: 'subscribe',
          subscription_type: 'export_notifications'
        }));
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          switch (message.type) {
            case 'processing_update':
              setState(prev => ({
                ...prev,
                jobs: prev.jobs.map(job =>
                  job.id === message.job_id
                    ? { ...job, status: message.status, progress: message.progress }
                    : job
                )
              }));
              break;
              
            case 'document_notification':
              if (message.event_type === 'status_change') {
                setState(prev => ({
                  ...prev,
                  documents: prev.documents.map(doc =>
                    doc.id === message.document_id
                      ? { ...doc, status: message.details.new_status }
                      : doc
                  )
                }));
              }
              break;
              
            case 'export_notification':
              setState(prev => ({
                ...prev,
                exportJobs: prev.exportJobs.map(job =>
                  job.id === message.export_id
                    ? { ...job, status: message.status }
                    : job
                )
              }));
              break;
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        setState(prev => ({ ...prev, connected: false }));
        // Attempt to reconnect after a delay
        setTimeout(connect, 5000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setState(prev => ({ ...prev, connected: false, error: 'Real-time connection failed' }));
      };

      websocketRef.current = ws;
    } catch (error) {
      setState(prev => ({ 
        ...prev, 
        connected: false, 
        error: error instanceof Error ? error.message : 'Connection failed' 
      }));
    }
  }, [enableRealTimeUpdates]);

  const disconnect = useCallback(() => {
    if (websocketRef.current) {
      websocketRef.current.close();
      websocketRef.current = null;
    }
    setState(prev => ({ ...prev, connected: false }));
  }, []);

  // Document operations
  const uploadDocument = useCallback(async (
    file: File, 
    metadata: Record<string, any> = {}
  ): Promise<Document> => {
    const operationId = `upload-${Date.now()}`;
    
    return withRetry(async () => {
      const result = await executeMCPTool('upload_document', {
        file_data: file,
        filename: file.name,
        metadata,
        start_processing: true
      });

      if (!result.success) {
        throw new Error(result.error || 'Upload failed');
      }

      const document: Document = {
        id: result.result.document_id,
        filename: file.name,
        content_type: file.type,
        file_size: file.size,
        status: 'PENDING',
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      };

      // Optimistic update
      setState(prev => ({
        ...prev,
        documents: [document, ...prev.documents]
      }));

      return document;
    }, operationId);
  }, [executeMCPTool, withRetry]);

  const getDocument = useCallback(async (documentId: string): Promise<Document> => {
    const operationId = `get-doc-${documentId}`;
    
    return withRetry(async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/documents/${documentId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch document: ${response.statusText}`);
      }

      return await response.json();
    }, operationId);
  }, [withRetry]);

  const deleteDocument = useCallback(async (documentId: string): Promise<void> => {
    const operationId = `delete-${documentId}`;
    
    return optimisticUpdate(
      // Optimistic update: remove document
      prev => ({
        ...prev,
        documents: prev.documents.filter(doc => doc.id !== documentId)
      }),
      // Actual operation
      withRetry(async () => {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/v1/documents/${documentId}`, {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
          throw new Error(`Failed to delete document: ${response.statusText}`);
        }
      }, operationId),
      // Rollback: restore document
      (prevState) => prevState
    );
  }, [optimisticUpdate, withRetry]);

  const getDocuments = useCallback(async (
    filters: Record<string, any> = {}
  ): Promise<Document[]> => {
    const operationId = `get-docs-${Date.now()}`;
    
    return withRetry(async () => {
      const token = localStorage.getItem('access_token');
      const queryParams = new URLSearchParams(filters).toString();
      const response = await fetch(`/api/v1/documents?${queryParams}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch documents: ${response.statusText}`);
      }

      const data = await response.json();
      
      setState(prev => ({
        ...prev,
        documents: data.documents
      }));

      return data.documents;
    }, operationId);
  }, [withRetry]);

  // Processing operations
  const createProcessingJob = useCallback(async (
    documentId: string, 
    jobType: string
  ): Promise<ProcessingJob> => {
    const operationId = `create-job-${documentId}`;
    
    return withRetry(async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/processing/jobs', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          document_id: documentId,
          job_type: jobType
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to create processing job: ${response.statusText}`);
      }

      const job = await response.json();
      
      setState(prev => ({
        ...prev,
        jobs: [job, ...prev.jobs]
      }));

      return job;
    }, operationId);
  }, [withRetry]);

  const getProcessingJob = useCallback(async (jobId: string): Promise<ProcessingJob> => {
    const operationId = `get-job-${jobId}`;
    
    return withRetry(async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/processing/jobs/${jobId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch processing job: ${response.statusText}`);
      }

      return await response.json();
    }, operationId);
  }, [withRetry]);

  const cancelProcessingJob = useCallback(async (jobId: string): Promise<void> => {
    const operationId = `cancel-job-${jobId}`;
    
    return optimisticUpdate(
      // Optimistic update: mark as cancelled
      prev => ({
        ...prev,
        jobs: prev.jobs.map(job =>
          job.id === jobId ? { ...job, status: 'CANCELLED' } : job
        )
      }),
      // Actual operation
      withRetry(async () => {
        const token = localStorage.getItem('access_token');
        const response = await fetch(`/api/v1/processing/jobs/${jobId}/cancel`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
          throw new Error(`Failed to cancel job: ${response.statusText}`);
        }
      }, operationId),
      // Rollback: restore previous status
      (prevState) => prevState
    );
  }, [optimisticUpdate, withRetry]);

  const getProcessingJobs = useCallback(async (
    filters: Record<string, any> = {}
  ): Promise<ProcessingJob[]> => {
    const operationId = `get-jobs-${Date.now()}`;
    
    return withRetry(async () => {
      const token = localStorage.getItem('access_token');
      const queryParams = new URLSearchParams(filters).toString();
      const response = await fetch(`/api/v1/processing/jobs?${queryParams}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch processing jobs: ${response.statusText}`);
      }

      const data = await response.json();
      
      setState(prev => ({
        ...prev,
        jobs: data.jobs
      }));

      return data.jobs;
    }, operationId);
  }, [withRetry]);

  // Search operations
  const searchDocuments = useCallback(async (
    query: string, 
    filters: Record<string, any> = {}
  ): Promise<SearchResult[]> => {
    const operationId = `search-${Date.now()}`;
    
    return withRetry(async () => {
      const result = await executeMCPTool('search_documents', {
        query,
        filters,
        page: 1,
        page_size: 50
      });

      if (!result.success) {
        throw new Error(result.error || 'Search failed');
      }

      setState(prev => ({
        ...prev,
        searchResults: result.result.results || []
      }));

      return result.result.results || [];
    }, operationId);
  }, [executeMCPTool, withRetry]);

  const getSuggestions = useCallback(async (query: string): Promise<string[]> => {
    const operationId = `suggestions-${Date.now()}`;
    
    return withRetry(async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/search/suggestions?query=${encodeURIComponent(query)}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error(`Failed to get suggestions: ${response.statusText}`);
      }

      const data = await response.json();
      return data.suggestions.map((s: any) => s.text);
    }, operationId);
  }, [withRetry]);

  // Export operations
  const exportDocument = useCallback(async (
    documentId: string, 
    format: string
  ): Promise<ExportJob> => {
    const operationId = `export-${documentId}-${format}`;
    
    return withRetry(async () => {
      const result = await executeMCPTool('export_document', {
        document_id: documentId,
        format,
        include_metadata: true
      });

      if (!result.success) {
        throw new Error(result.error || 'Export failed');
      }

      const exportJob: ExportJob = {
        id: result.result.export_id,
        document_id: documentId,
        format,
        status: 'processing'
      };

      setState(prev => ({
        ...prev,
        exportJobs: [exportJob, ...prev.exportJobs]
      }));

      return exportJob;
    }, operationId);
  }, [executeMCPTool, withRetry]);

  const getExportJob = useCallback(async (exportId: string): Promise<ExportJob> => {
    const operationId = `get-export-${exportId}`;
    
    return withRetry(async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/export/status/${exportId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch export status: ${response.statusText}`);
      }

      return await response.json();
    }, operationId);
  }, [withRetry]);

  const downloadExport = useCallback(async (exportId: string): Promise<Blob> => {
    const operationId = `download-${exportId}`;
    
    return withRetry(async () => {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/export/download/${exportId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        throw new Error(`Failed to download export: ${response.statusText}`);
      }

      return await response.blob();
    }, operationId);
  }, [withRetry]);

  // System operations
  const getSystemStatus = useCallback(async (): Promise<Record<string, any>> => {
    const operationId = `system-status-${Date.now()}`;
    
    return withRetry(async () => {
      const result = await executeMCPTool('get_system_status', {});

      if (!result.success) {
        throw new Error(result.error || 'Failed to get system status');
      }

      return result.result;
    }, operationId);
  }, [executeMCPTool, withRetry]);

  const refreshData = useCallback(async (): Promise<void> => {
    setState(prev => ({ ...prev, loading: true }));
    
    try {
      await Promise.all([
        getDocuments(),
        getProcessingJobs()
      ]);
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to refresh data'
      }));
    } finally {
      setState(prev => ({ ...prev, loading: false }));
    }
  }, [getDocuments, getProcessingJobs]);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  // Setup auto-refresh
  useEffect(() => {
    if (autoRefreshInterval > 0) {
      refreshIntervalRef.current = setInterval(refreshData, autoRefreshInterval);
      return () => {
        if (refreshIntervalRef.current) {
          clearInterval(refreshIntervalRef.current);
        }
      };
    }
  }, [autoRefreshInterval, refreshData]);

  // Initial connection and data loading
  useEffect(() => {
    connect();
    refreshData();
    
    return () => {
      disconnect();
      // Clear all retry timeouts
      retryTimeoutsRef.current.forEach(timeout => clearTimeout(timeout));
      retryTimeoutsRef.current.clear();
    };
  }, [connect, disconnect, refreshData]);

  return {
    state,
    
    // Document operations
    uploadDocument,
    getDocument,
    deleteDocument,
    getDocuments,
    
    // Processing operations
    createProcessingJob,
    getProcessingJob,
    cancelProcessingJob,
    getProcessingJobs,
    
    // Search operations
    searchDocuments,
    getSuggestions,
    
    // Export operations
    exportDocument,
    getExportJob,
    downloadExport,
    
    // System operations
    getSystemStatus,
    refreshData,
    clearError,
    
    // Connection management
    connect,
    disconnect
  };
};