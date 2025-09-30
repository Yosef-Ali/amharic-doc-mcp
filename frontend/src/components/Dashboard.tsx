export default function Dashboard() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Upload Card */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Upload Documents
          </h3>
          <p className="text-gray-600 mb-4">
            Upload PDF, images, Word documents, CSV files, or web content for processing.
          </p>
          <button className="btn-primary">
            Upload Files
          </button>
        </div>

        {/* Processing Status Card */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Processing Status
          </h3>
          <p className="text-gray-600 mb-4">
            Monitor real-time progress of your document processing jobs.
          </p>
          <button className="btn-secondary">
            View Status
          </button>
        </div>

        {/* Search Card */}
        <div className="card">
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Search Documents
          </h3>
          <p className="text-gray-600 mb-4">
            Search through processed documents with Amharic language support.
          </p>
          <button className="btn-secondary">
            Search
          </button>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="card">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Recent Activity
        </h3>
        <div className="text-gray-600">
          No recent activity. Upload your first document to get started.
        </div>
      </div>
    </div>
  )
}