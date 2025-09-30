/**
 * FileUpload component with chunked uploads, validation UX, and localization strings
 */

import React, { useState, useRef, useCallback, useMemo } from 'react';
import { useDropzone } from 'react-dropzone';
import { useTranslation } from 'react-i18next';
import { 
  CloudArrowUpIcon, 
  DocumentIcon, 
  XMarkIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

interface FileUploadProps {
  onFileUpload: (files: File[]) => Promise<void>;
  onUploadProgress?: (progress: number) => void;
  onUploadComplete?: (results: UploadResult[]) => void;
  onUploadError?: (error: string) => void;
  maxFileSize?: number; // in bytes
  maxFiles?: number;
  acceptedFileTypes?: string[];
  chunkSize?: number; // in bytes
  showPreview?: boolean;
  disabled?: boolean;
  className?: string;
}

interface UploadResult {
  file: File;
  success: boolean;
  documentId?: string;
  jobId?: string;
  error?: string;
}

interface FileUploadState {
  files: File[];
  uploading: boolean;
  progress: number;
  results: UploadResult[];
  errors: string[];
}

const FileUpload: React.FC<FileUploadProps> = ({
  onFileUpload,
  onUploadProgress,
  onUploadComplete,
  onUploadError,
  maxFileSize = 50 * 1024 * 1024, // 50MB default
  maxFiles = 10,
  acceptedFileTypes = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/tiff',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/csv',
    'text/plain'
  ],
  chunkSize = 1024 * 1024, // 1MB chunks
  showPreview = true,
  disabled = false,
  className = ''
}) => {
  const { t } = useTranslation();
  const [state, setState] = useState<FileUploadState>({
    files: [],
    uploading: false,
    progress: 0,
    results: [],
    errors: []
  });

  // File validation
  const validateFile = useCallback((file: File): string | null => {
    if (file.size > maxFileSize) {
      return t('fileUpload.errors.fileTooLarge', { 
        maxSize: Math.round(maxFileSize / (1024 * 1024)) 
      });
    }

    if (!acceptedFileTypes.includes(file.type)) {
      return t('fileUpload.errors.invalidFileType', { 
        type: file.type 
      });
    }

    return null;
  }, [maxFileSize, acceptedFileTypes, t]);

  // Dropzone configuration
  const {
    getRootProps,
    getInputProps,
    isDragActive,
    isDragReject,
    fileRejections
  } = useDropzone({
    onDrop: (acceptedFiles, rejectedFiles) => {
      if (disabled || state.uploading) return;

      const newErrors: string[] = [];
      const validFiles: File[] = [];

      // Validate accepted files
      acceptedFiles.forEach(file => {
        const error = validateFile(file);
        if (error) {
          newErrors.push(`${file.name}: ${error}`);
        } else if (state.files.length + validFiles.length < maxFiles) {
          validFiles.push(file);
        } else {
          newErrors.push(t('fileUpload.errors.tooManyFiles', { maxFiles }));
        }
      });

      // Handle rejected files
      rejectedFiles.forEach(({ file, errors }) => {
        const errorMessages = errors.map(error => {
          switch (error.code) {
            case 'file-too-large':
              return t('fileUpload.errors.fileTooLarge', { 
                maxSize: Math.round(maxFileSize / (1024 * 1024)) 
              });
            case 'file-invalid-type':
              return t('fileUpload.errors.invalidFileType', { type: file.type });
            default:
              return error.message;
          }
        });
        newErrors.push(`${file.name}: ${errorMessages.join(', ')}`);
      });

      setState(prev => ({
        ...prev,
        files: [...prev.files, ...validFiles],
        errors: newErrors
      }));
    },
    accept: acceptedFileTypes.reduce((acc, type) => ({ ...acc, [type]: [] }), {}),
    maxSize: maxFileSize,
    disabled: disabled || state.uploading,
    multiple: maxFiles > 1
  });

  // Remove file from list
  const removeFile = useCallback((index: number) => {
    setState(prev => ({
      ...prev,
      files: prev.files.filter((_, i) => i !== index)
    }));
  }, []);

  // Format file size
  const formatFileSize = useCallback((bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }, []);

  // Upload files with chunking
  const uploadFiles = useCallback(async () => {
    if (state.files.length === 0 || state.uploading) return;

    setState(prev => ({ 
      ...prev, 
      uploading: true, 
      progress: 0, 
      results: [],
      errors: []
    }));

    try {
      const results: UploadResult[] = [];
      const totalFiles = state.files.length;

      for (let i = 0; i < totalFiles; i++) {
        const file = state.files[i];
        const baseProgress = (i / totalFiles) * 100;
        const fileProgressRange = 100 / totalFiles;

        try {
          // For large files, implement chunked upload
          if (file.size > chunkSize) {
            const chunks = Math.ceil(file.size / chunkSize);
            const uploadId = `upload_${Date.now()}_${Math.random()}`;
            
            for (let chunkIndex = 0; chunkIndex < chunks; chunkIndex++) {
              const start = chunkIndex * chunkSize;
              const end = Math.min(start + chunkSize, file.size);
              const chunk = file.slice(start, end);
              
              // Create form data for chunk
              const chunkFormData = new FormData();
              chunkFormData.append('chunk', chunk);
              chunkFormData.append('chunkIndex', chunkIndex.toString());
              chunkFormData.append('totalChunks', chunks.toString());
              chunkFormData.append('uploadId', uploadId);
              chunkFormData.append('filename', file.name);
              chunkFormData.append('fileType', file.type);
              
              // Upload chunk (this would integrate with your backend API)
              const response = await fetch('/api/v1/documents/upload-chunk', {
                method: 'POST',
                body: chunkFormData,
                headers: {
                  'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                }
              });

              if (!response.ok) {
                throw new Error(`Chunk upload failed: ${response.statusText}`);
              }

              // Update progress for this file
              const chunkProgress = ((chunkIndex + 1) / chunks) * fileProgressRange;
              const totalProgress = baseProgress + chunkProgress;
              
              setState(prev => ({ ...prev, progress: totalProgress }));
              onUploadProgress?.(totalProgress);
            }

            // Finalize chunked upload
            const finalizeResponse = await fetch('/api/v1/documents/finalize-upload', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
              },
              body: JSON.stringify({
                uploadId,
                filename: file.name,
                fileType: file.type,
                totalSize: file.size,
                startProcessing: true
              })
            });

            if (!finalizeResponse.ok) {
              throw new Error('Failed to finalize upload');
            }

            const finalizeData = await finalizeResponse.json();
            results.push({
              file,
              success: true,
              documentId: finalizeData.document_id,
              jobId: finalizeData.processing_job_id
            });

          } else {
            // Regular upload for small files
            const formData = new FormData();
            formData.append('file', file);
            formData.append('startProcessing', 'true');

            const response = await fetch('/api/v1/documents/upload', {
              method: 'POST',
              body: formData,
              headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
              }
            });

            if (!response.ok) {
              throw new Error(`Upload failed: ${response.statusText}`);
            }

            const data = await response.json();
            results.push({
              file,
              success: true,
              documentId: data.document_id,
              jobId: data.processing_job_id
            });
          }

        } catch (error) {
          results.push({
            file,
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error'
          });
        }

        // Update progress
        const fileProgress = baseProgress + fileProgressRange;
        setState(prev => ({ ...prev, progress: fileProgress }));
        onUploadProgress?.(fileProgress);
      }

      // Complete upload
      setState(prev => ({
        ...prev,
        uploading: false,
        progress: 100,
        results,
        files: [] // Clear files after successful upload
      }));

      onUploadComplete?.(results);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      setState(prev => ({
        ...prev,
        uploading: false,
        errors: [errorMessage]
      }));
      onUploadError?.(errorMessage);
    }
  }, [state.files, state.uploading, chunkSize, onUploadProgress, onUploadComplete, onUploadError]);

  // Memoized dropzone styles
  const dropzoneStyles = useMemo(() => {
    const baseStyles = `
      border-2 border-dashed rounded-lg p-6 text-center cursor-pointer
      transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500
    `;
    
    if (disabled || state.uploading) {
      return `${baseStyles} border-gray-300 bg-gray-50 cursor-not-allowed`;
    }
    
    if (isDragReject) {
      return `${baseStyles} border-red-400 bg-red-50`;
    }
    
    if (isDragActive) {
      return `${baseStyles} border-blue-400 bg-blue-50`;
    }
    
    return `${baseStyles} border-gray-300 hover:border-gray-400`;
  }, [disabled, state.uploading, isDragActive, isDragReject]);

  return (
    <div className={`file-upload ${className}`}>
      {/* Dropzone */}
      <div {...getRootProps()} className={dropzoneStyles}>
        <input {...getInputProps()} />
        <div className="flex flex-col items-center justify-center space-y-3">
          <CloudArrowUpIcon className="h-12 w-12 text-gray-400" />
          <div className="text-lg font-medium text-gray-700">
            {isDragActive
              ? t('fileUpload.dropzone.dragActive')
              : t('fileUpload.dropzone.default', { maxFiles })
            }
          </div>
          <div className="text-sm text-gray-500">
            {t('fileUpload.dropzone.supportedFormats')}
          </div>
          <div className="text-xs text-gray-400">
            {t('fileUpload.dropzone.maxSize', { 
              maxSize: Math.round(maxFileSize / (1024 * 1024)) 
            })}
          </div>
        </div>
      </div>

      {/* File list */}
      {state.files.length > 0 && showPreview && (
        <div className="mt-4 space-y-2">
          <h3 className="font-medium text-gray-700">
            {t('fileUpload.fileList.title', { count: state.files.length })}
          </h3>
          {state.files.map((file, index) => (
            <div key={`${file.name}-${index}`} className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
              <div className="flex items-center space-x-3">
                <DocumentIcon className="h-5 w-5 text-gray-400" />
                <div>
                  <div className="font-medium text-sm text-gray-700">{file.name}</div>
                  <div className="text-xs text-gray-500">{formatFileSize(file.size)}</div>
                </div>
              </div>
              {!state.uploading && (
                <button
                  onClick={() => removeFile(index)}
                  className="p-1 text-gray-400 hover:text-red-500 focus:outline-none focus:text-red-500"
                  aria-label={t('fileUpload.fileList.removeFile')}
                >
                  <XMarkIcon className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Upload button */}
      {state.files.length > 0 && !state.uploading && (
        <div className="mt-4">
          <button
            onClick={uploadFiles}
            disabled={disabled}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-medium py-2 px-4 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {t('fileUpload.actions.upload', { count: state.files.length })}
          </button>
        </div>
      )}

      {/* Upload progress */}
      {state.uploading && (
        <div className="mt-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>{t('fileUpload.progress.uploading')}</span>
            <span>{Math.round(state.progress)}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${state.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Upload results */}
      {state.results.length > 0 && (
        <div className="mt-4 space-y-2">
          <h3 className="font-medium text-gray-700">
            {t('fileUpload.results.title')}
          </h3>
          {state.results.map((result, index) => (
            <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-md">
              {result.success ? (
                <CheckCircleIcon className="h-5 w-5 text-green-500" />
              ) : (
                <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
              )}
              <div className="flex-1">
                <div className="font-medium text-sm text-gray-700">{result.file.name}</div>
                {result.success ? (
                  <div className="text-xs text-green-600">
                    {t('fileUpload.results.success')}
                    {result.jobId && (
                      <span className="ml-1">
                        ({t('fileUpload.results.processingStarted')})
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-red-600">{result.error}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error messages */}
      {state.errors.length > 0 && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <div className="flex items-center space-x-2">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
            <h3 className="font-medium text-red-800">
              {t('fileUpload.errors.title')}
            </h3>
          </div>
          <ul className="mt-2 space-y-1">
            {state.errors.map((error, index) => (
              <li key={index} className="text-sm text-red-700">
                {error}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default FileUpload;