import React from 'react'

export interface ProcessingJobSummary {
  id: string
  jobName: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  progress?: number
}

export interface ProcessingDashboardProps {
  jobs?: ProcessingJobSummary[]
  title?: string
}

const statusStyles: Record<ProcessingJobSummary['status'], string> = {
  queued: 'bg-slate-100 text-slate-700',
  running: 'bg-amber-100 text-amber-700',
  completed: 'bg-emerald-100 text-emerald-700',
  failed: 'bg-rose-100 text-rose-700',
}

const defaultJobs: ProcessingJobSummary[] = [
  { id: 'job-1', jobName: 'OCR conversion', status: 'completed', progress: 100 },
  { id: 'job-2', jobName: 'Translation', status: 'running', progress: 40 },
  { id: 'job-3', jobName: 'Quality check', status: 'queued', progress: 0 },
]

const ProcessingDashboard: React.FC<ProcessingDashboardProps> = ({ jobs = defaultJobs, title = 'Processing timeline' }) => {
  return (
    <section className="card space-y-4" aria-label="Document processing overview">
      <header className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <p className="text-sm text-gray-500">Track document jobs from upload to completion.</p>
        </div>
      </header>

      <ul className="space-y-3">
        {jobs.map((job) => (
          <li key={job.id} className="flex flex-col gap-2 rounded-lg border border-gray-200 p-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="font-medium text-gray-900">{job.jobName}</p>
                <p className="text-xs text-gray-500">Job ID: {job.id}</p>
              </div>
              <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${statusStyles[job.status]}`}>
                {job.status.toUpperCase()}
              </span>
            </div>
            <progress
              value={job.progress ?? (job.status === 'completed' ? 100 : job.status === 'queued' ? 0 : 50)}
              max={100}
              className="h-2 w-full overflow-hidden rounded-full bg-gray-200"
            />
          </li>
        ))}
      </ul>
    </section>
  )
}

export default ProcessingDashboard
