/**
 * ProcessingDashboard component with real-time status, skeletons, and failure handling
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  PlayIcon,
  PauseIcon,
  StopIcon,
  ArrowPathIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';

interface ProcessingJob {
  id: string;
  document_id: string;
  job_type: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED' | 'MANUAL_REVIEW';
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  progress?: number;
  filename?: string;
}

interface ProcessingTask {
  id: string;
  job_id: string;
  task_type: string;
  status: string;
  agent_type: string;
  confidence_score?: number;
  retry_count: number;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

interface ProcessingStats {
  system_status: string;
  total_jobs: number;
  queued_jobs: number;
  running_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  manual_review_queue: number;
  average_processing_time: number;
  queue_health: string;
}

interface ProcessingDashboardProps {
  userId: string;
  refreshInterval?: number;
  showFilters?: boolean;
  showStats?: boolean;
  maxJobs?: number;
  onJobClick?: (job: ProcessingJob) => void;
  onJobAction?: (jobId: string, action: string) => Promise<void>;
  className?: string;
}

const ProcessingDashboard: React.FC<ProcessingDashboardProps> = ({
  userId,
  refreshInterval = 5000,
  showFilters = true,
  showStats = true,
  maxJobs = 50,
  onJobClick,
  onJobAction,
  className = ''
}) => {
  const { t } = useTranslation();
  const [jobs, setJobs] = useState<ProcessingJob[]>([]);
  const [stats, setStats] = useState<ProcessingStats | null>(null);
  const [selectedJob, setSelectedJob] = useState<ProcessingJob | null>(null);
  const [selectedTasks, setSelectedTasks] = useState<ProcessingTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    status: 'all',
    jobType: 'all',
    priority: 'all'
  });
  const [websocket, setWebsocket] = useState<WebSocket | null>(null);

  // WebSocket connection for real-time updates
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const ws = new WebSocket(`${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/mcp/ws/${userId}`);
    
    ws.onopen = () => {
      console.log('Processing Dashboard WebSocket connected');
      // Subscribe to processing updates
      ws.send(JSON.stringify({
        type: 'subscribe',
        subscription_type: 'processing_updates'
      }));
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      
      if (message.type === 'processing_update') {
        // Update job status in real-time
        setJobs(prev => prev.map(job => 
          job.id === message.job_id 
            ? { ...job, status: message.status, progress: message.progress }
            : job
        ));
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('Processing Dashboard WebSocket disconnected');
    };

    setWebsocket(ws);

    return () => {
      ws.close();
    };
  }, [userId]);

  // Fetch processing jobs
  const fetchJobs = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `/api/v1/processing/jobs?limit=${maxJobs}&status_filter=${filters.status === 'all' ? '' : filters.status}&job_type=${filters.jobType === 'all' ? '' : filters.jobType}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch processing jobs');
      }

      const data = await response.json();
      setJobs(data.jobs);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [maxJobs, filters]);

  // Fetch processing statistics
  const fetchStats = useCallback(async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/v1/processing/status', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch processing stats');
      }

      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  }, []);

  // Fetch job tasks when a job is selected
  const fetchJobTasks = useCallback(async (jobId: string) => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/v1/processing/jobs/${jobId}/tasks`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to fetch job tasks');
      }

      const tasks = await response.json();
      setSelectedTasks(tasks);
    } catch (err) {
      console.error('Failed to fetch tasks:', err);
      setSelectedTasks([]);
    }
  }, []);

  // Initial data loading
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchJobs(),
        showStats ? fetchStats() : Promise.resolve()
      ]);
      setLoading(false);
    };

    loadData();
  }, [fetchJobs, fetchStats, showStats]);

  // Periodic refresh
  useEffect(() => {
    if (!refreshInterval) return;

    const interval = setInterval(() => {
      fetchJobs();
      if (showStats) fetchStats();
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [fetchJobs, fetchStats, refreshInterval, showStats]);

  // Handle job selection
  const handleJobClick = useCallback((job: ProcessingJob) => {
    setSelectedJob(job);
    fetchJobTasks(job.id);
    onJobClick?.(job);
  }, [fetchJobTasks, onJobClick]);

  // Handle job actions (cancel, retry, etc.)
  const handleJobAction = useCallback(async (jobId: string, action: string) => {
    try {
      const token = localStorage.getItem('access_token');
      let endpoint = '';
      
      switch (action) {
        case 'cancel':
          endpoint = `/api/v1/processing/jobs/${jobId}/cancel`;
          break;
        case 'promote':
          endpoint = `/api/v1/processing/jobs/${jobId}/promote`;
          break;
        default:
          return;
      }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: action === 'promote' ? JSON.stringify({
          reason: 'Manual review requested',
          reviewer_notes: ''
        }) : undefined
      });

      if (!response.ok) {
        throw new Error(`Failed to ${action} job`);
      }

      // Refresh jobs after action
      await fetchJobs();
      await onJobAction?.(jobId, action);
    } catch (err) {
      console.error(`Failed to ${action} job:`, err);
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  }, [fetchJobs, onJobAction]);

  // Status icon mapping
  const getStatusIcon = (status: string, className: string = 'h-5 w-5') => {
    switch (status) {
      case 'COMPLETED':
        return <CheckCircleIcon className={`${className} text-green-500`} />;
      case 'FAILED':
        return <XCircleIcon className={`${className} text-red-500`} />;
      case 'RUNNING':
        return <PlayIcon className={`${className} text-blue-500`} />;
      case 'PENDING':
        return <ClockIcon className={`${className} text-yellow-500`} />;
      case 'CANCELLED':
        return <StopIcon className={`${className} text-gray-500`} />;
      case 'MANUAL_REVIEW':
        return <ExclamationTriangleIcon className={`${className} text-orange-500`} />;
      default:
        return <ClockIcon className={`${className} text-gray-400`} />;
    }
  };

  // Get priority color
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'URGENT':
        return 'bg-red-100 text-red-800';
      case 'HIGH':
        return 'bg-orange-100 text-orange-800';
      case 'MEDIUM':
        return 'bg-yellow-100 text-yellow-800';
      case 'LOW':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  // Format duration
  const formatDuration = (start: string, end?: string) => {
    const startTime = new Date(start);
    const endTime = end ? new Date(end) : new Date();
    const duration = endTime.getTime() - startTime.getTime();
    
    const minutes = Math.floor(duration / (1000 * 60));
    const seconds = Math.floor((duration % (1000 * 60)) / 1000);
    
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  // Filtered jobs
  const filteredJobs = useMemo(() => {
    return jobs.filter(job => {
      if (filters.status !== 'all' && job.status !== filters.status) return false;
      if (filters.jobType !== 'all' && job.job_type !== filters.jobType) return false;
      if (filters.priority !== 'all' && job.priority !== filters.priority) return false;
      return true;
    });
  }, [jobs, filters]);

  // Loading skeleton
  const LoadingSkeleton = () => (
    <div className="space-y-4">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="animate-pulse">
          <div className="flex items-center space-x-4 p-4 bg-white border border-gray-200 rounded-lg">
            <div className="h-5 w-5 bg-gray-300 rounded-full"></div>
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-gray-300 rounded w-3/4"></div>
              <div className="h-3 bg-gray-300 rounded w-1/2"></div>
            </div>
            <div className="h-6 w-16 bg-gray-300 rounded"></div>
          </div>
        </div>
      ))}
    </div>
  );

  if (loading) {
    return (
      <div className={`processing-dashboard ${className}`}>
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900">
            {t('processing.dashboard.title')}
          </h2>
        </div>
        <LoadingSkeleton />
      </div>
    );
  }

  return (
    <div className={`processing-dashboard ${className}`}>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">
            {t('processing.dashboard.title')}
          </h2>
          <button
            onClick={() => {
              fetchJobs();
              if (showStats) fetchStats();
            }}
            className="flex items-center space-x-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <ArrowPathIcon className="h-4 w-4" />
            <span>{t('processing.dashboard.refresh')}</span>
          </button>
        </div>
        
        {/* System Stats */}
        {showStats && stats && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center">
                <ChartBarIcon className="h-5 w-5 text-blue-500" />
                <span className="ml-2 text-sm font-medium text-gray-700">
                  {t('processing.stats.total')}
                </span>
              </div>
              <p className="text-2xl font-bold text-gray-900">{stats.total_jobs}</p>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center">
                <ClockIcon className="h-5 w-5 text-yellow-500" />
                <span className="ml-2 text-sm font-medium text-gray-700">
                  {t('processing.stats.queued')}
                </span>
              </div>
              <p className="text-2xl font-bold text-yellow-600">{stats.queued_jobs}</p>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center">
                <PlayIcon className="h-5 w-5 text-blue-500" />
                <span className="ml-2 text-sm font-medium text-gray-700">
                  {t('processing.stats.running')}
                </span>
              </div>
              <p className="text-2xl font-bold text-blue-600">{stats.running_jobs}</p>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center">
                <CheckCircleIcon className="h-5 w-5 text-green-500" />
                <span className="ml-2 text-sm font-medium text-gray-700">
                  {t('processing.stats.completed')}
                </span>
              </div>
              <p className="text-2xl font-bold text-green-600">{stats.completed_jobs}</p>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center">
                <XCircleIcon className="h-5 w-5 text-red-500" />
                <span className="ml-2 text-sm font-medium text-gray-700">
                  {t('processing.stats.failed')}
                </span>
              </div>
              <p className="text-2xl font-bold text-red-600">{stats.failed_jobs}</p>
            </div>
          </div>
        )}
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="mb-6 flex flex-wrap gap-4">
          <select
            value={filters.status}
            onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">{t('processing.filters.allStatuses')}</option>
            <option value="PENDING">{t('processing.status.pending')}</option>
            <option value="RUNNING">{t('processing.status.running')}</option>
            <option value="COMPLETED">{t('processing.status.completed')}</option>
            <option value="FAILED">{t('processing.status.failed')}</option>
            <option value="CANCELLED">{t('processing.status.cancelled')}</option>
            <option value="MANUAL_REVIEW">{t('processing.status.manualReview')}</option>
          </select>

          <select
            value={filters.priority}
            onChange={(e) => setFilters(prev => ({ ...prev, priority: e.target.value }))}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">{t('processing.filters.allPriorities')}</option>
            <option value="URGENT">{t('processing.priority.urgent')}</option>
            <option value="HIGH">{t('processing.priority.high')}</option>
            <option value="MEDIUM">{t('processing.priority.medium')}</option>
            <option value="LOW">{t('processing.priority.low')}</option>
          </select>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-center">
            <XCircleIcon className="h-5 w-5 text-red-500" />
            <span className="ml-2 text-sm font-medium text-red-800">{error}</span>
          </div>
        </div>
      )}

      {/* Jobs List */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Jobs Column */}
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            {t('processing.jobs.title')} ({filteredJobs.length})
          </h3>
          
          {filteredJobs.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <ClockIcon className="h-12 w-12 mx-auto mb-3 text-gray-400" />
              <p>{t('processing.jobs.empty')}</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredJobs.map((job) => (
                <div
                  key={job.id}
                  onClick={() => handleJobClick(job)}
                  className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                    selectedJob?.id === job.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 bg-white hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {getStatusIcon(job.status)}
                      <div>
                        <div className="font-medium text-gray-900">
                          {job.filename || `${job.job_type} Job`}
                        </div>
                        <div className="text-sm text-gray-500">
                          {t('processing.jobs.createdAt')}: {new Date(job.created_at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${getPriorityColor(job.priority)}`}>
                        {t(`processing.priority.${job.priority.toLowerCase()}`)}
                      </span>
                      {(job.status === 'PENDING' || job.status === 'RUNNING') && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleJobAction(job.id, 'cancel');
                          }}
                          className="p-1 text-red-600 hover:bg-red-100 rounded"
                        >
                          <StopIcon className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                  </div>
                  
                  {job.progress !== undefined && job.status === 'RUNNING' && (
                    <div className="mt-3">
                      <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>{t('processing.jobs.progress')}</span>
                        <span>{Math.round(job.progress)}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${job.progress}%` }}
                        />
                      </div>
                    </div>
                  )}
                  
                  {job.error_message && (
                    <div className="mt-2 text-sm text-red-600">
                      {job.error_message}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Job Details Column */}
        <div>
          {selectedJob ? (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                {t('processing.jobDetails.title')}
              </h3>
              
              <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(selectedJob.status)}
                    <span className="font-medium">
                      {selectedJob.filename || `${selectedJob.job_type} Job`}
                    </span>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded ${getPriorityColor(selectedJob.priority)}`}>
                    {t(`processing.priority.${selectedJob.priority.toLowerCase()}`)}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">{t('processing.jobDetails.jobType')}:</span>
                    <span className="ml-2 font-medium">{selectedJob.job_type}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">{t('processing.jobDetails.status')}:</span>
                    <span className="ml-2 font-medium">
                      {t(`processing.status.${selectedJob.status.toLowerCase()}`)}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">{t('processing.jobDetails.created')}:</span>
                    <span className="ml-2 font-medium">
                      {new Date(selectedJob.created_at).toLocaleString()}
                    </span>
                  </div>
                  {selectedJob.started_at && (
                    <div>
                      <span className="text-gray-500">{t('processing.jobDetails.duration')}:</span>
                      <span className="ml-2 font-medium">
                        {formatDuration(selectedJob.started_at, selectedJob.completed_at)}
                      </span>
                    </div>
                  )}
                </div>

                {/* Job Tasks */}
                {selectedTasks.length > 0 && (
                  <div>
                    <h4 className="font-medium text-gray-900 mb-2">
                      {t('processing.jobDetails.tasks')}
                    </h4>
                    <div className="space-y-2">
                      {selectedTasks.map((task) => (
                        <div key={task.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                          <div className="flex items-center space-x-2">
                            {getStatusIcon(task.status, 'h-4 w-4')}
                            <span className="text-sm font-medium">{task.task_type}</span>
                            <span className="text-xs text-gray-500">({task.agent_type})</span>
                          </div>
                          {task.confidence_score && (
                            <span className="text-xs text-gray-600">
                              {Math.round(task.confidence_score * 100)}%
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              <p>{t('processing.jobDetails.selectJob')}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ProcessingDashboard;