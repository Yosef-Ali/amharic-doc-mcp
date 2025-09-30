import React, { ChangeEvent, useState } from 'react'

export interface FileUploadProps {
  onUpload?: (files: File[]) => void
  multiple?: boolean
  accept?: string
}

const FileUpload: React.FC<FileUploadProps> = ({ onUpload, multiple = true, accept }) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])
  const [message, setMessage] = useState<string>('Drag and drop files or browse to start the upload.')

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? [])
    if (files.length === 0) {
      setSelectedFiles([])
    setMessage('No files selected yet.')
      return
    }

    setSelectedFiles(files)
    setMessage(`${files.length} file${files.length === 1 ? '' : 's'} ready to upload.`)
    onUpload?.(files)
  }

  return (
    <div className="card space-y-4" role="region" aria-label="File upload">
      <header>
        <h2 className="text-lg font-semibold text-gray-900">Upload documents</h2>
        <p className="text-sm text-gray-500">Choose files from your computer to process.</p>
      </header>

      <label className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 p-8 text-center cursor-pointer hover:border-primary-400 hover:bg-white transition-colors">
        <span className="text-sm font-medium text-gray-700">Select files</span>
        <span className="mt-1 text-xs text-gray-500">{message}</span>
        <input
          data-testid="file-input"
          type="file"
          className="sr-only"
          multiple={multiple}
          accept={accept}
          onChange={handleChange}
        />
      </label>

      {selectedFiles.length > 0 && (
        <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200">
          {selectedFiles.map((file) => (
            <li key={file.name} className="px-4 py-2 text-sm text-gray-700">
              {file.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default FileUpload
