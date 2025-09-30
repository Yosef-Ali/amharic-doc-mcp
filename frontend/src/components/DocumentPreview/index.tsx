/**
 * DocumentPreview component with highlighting, metadata, and export triggers
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  DocumentTextIcon,
  ArrowDownTrayIcon,
  MagnifyingGlassIcon,
  ShareIcon,
  PencilIcon,
  EyeIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ZoomInIcon,
  ZoomOutIcon,
  PrinterIcon,
  InformationCircleIcon
} from '@heroicons/react/24/outline';

interface DocumentMetadata {
  id: string;
  filename: string;
  content_type: string;
  file_size: number;
  status: string;
  metadata: Record<string, any>;
  processing_info?: {
    ocr_confidence?: number;
    text_extraction_accuracy?: number;
    language_detected?: string;
    page_count?: number;
    processing_time?: number;
  };
  quality_metrics?: {
    overall_quality_score?: number;
    text_legibility_score?: number;
    content_completeness?: number;
    amharic_content_ratio?: number;
  };
  created_at: string;
  updated_at: string;
}

interface DocumentContent {
  text_content: string;
  structured_content?: {
    pages?: Array<{
      page_number: number;
      text: string;
      confidence: number;
      bounding_boxes?: Array<{
        text: string;
        x: number;
        y: number;
        width: number;
        height: number;
      }>;
    }>;
    tables?: Array<{
      page_number: number;
      data: string[][];
      headers?: string[];
    }>;
    images?: Array<{
      page_number: number;
      description: string;
      extracted_text?: string;
    }>;
  };
}

interface DocumentPreviewProps {
  documentId: string;
  metadata: DocumentMetadata;
  content?: DocumentContent;
  searchQuery?: string;
  showMetadata?: boolean;
  showExportOptions?: boolean;
  showAnnotations?: boolean;
  enableTextSelection?: boolean;
  onExport?: (documentId: string, format: string) => Promise<void>;
  onShare?: (documentId: string) => void;
  onEdit?: (documentId: string) => void;
  className?: string;
}

const DocumentPreview: React.FC<DocumentPreviewProps> = ({
  documentId,
  metadata,
  content,
  searchQuery = '',
  showMetadata = true,
  showExportOptions = true,
  showAnnotations = false,
  enableTextSelection = true,
  onExport,
  onShare,
  onEdit,
  className = ''
}) => {
  const { t, i18n } = useTranslation();
  
  // State management
  const [loading, setLoading] = useState(!content);
  const [error, setError] = useState<string | null>(null);
  const [documentContent, setDocumentContent] = useState<DocumentContent | null>(content || null);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(100);
  const [showMetadataPanel, setShowMetadataPanel] = useState(false);
  const [highlightedText, setHighlightedText] = useState<string>('');
  const [selectedText, setSelectedText] = useState<string>('');
  
  // Refs
  const contentRef = useRef<HTMLDivElement>(null);
  const textSelectionRef = useRef<Selection | null>(null);

  // Fetch document content if not provided
  useEffect(() => {
    if (!documentContent && documentId) {
      fetchDocumentContent();
    }
  }, [documentId, documentContent]);

  const fetchDocumentContent = useCallback(async () => {
    if (!documentId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('access_token');
      
      // Fetch extracted content
      const response = await fetch(`/api/v1/documents/${documentId}/content`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Failed to fetch document content');
      }
      
      const contentData = await response.json();
      setDocumentContent(contentData);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load document');
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  // Text highlighting for search terms
  const highlightSearchTerms = useCallback((text: string, query: string) => {
    if (!query.trim()) return text;
    
    const terms = query.split(' ').filter(term => term.length > 2);
    let highlightedText = text;
    
    terms.forEach(term => {
      const regex = new RegExp(`(${term})`, 'gi');
      highlightedText = highlightedText.replace(
        regex, 
        '<mark class="bg-yellow-200 px-1 rounded font-medium">$1</mark>'
      );
    });
    
    return highlightedText;
  }, []);

  // Handle text selection
  const handleTextSelection = useCallback(() => {
    if (!enableTextSelection) return;
    
    const selection = window.getSelection();
    if (selection && selection.toString().trim()) {
      setSelectedText(selection.toString().trim());
      textSelectionRef.current = selection;
    }
  }, [enableTextSelection]);

  // Export handlers
  const handleExport = useCallback(async (format: string) => {
    if (!onExport) return;
    
    try {
      await onExport(documentId, format);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    }
  }, [documentId, onExport]);

  // Zoom handlers
  const handleZoomIn = useCallback(() => {
    setZoom(prev => Math.min(prev + 25, 200));
  }, []);

  const handleZoomOut = useCallback(() => {
    setZoom(prev => Math.max(prev - 25, 50));
  }, []);

  // Page navigation for multi-page documents
  const totalPages = useMemo(() => {
    return documentContent?.structured_content?.pages?.length || 1;
  }, [documentContent]);

  const currentPageContent = useMemo(() => {
    if (!documentContent?.structured_content?.pages) {
      return documentContent?.text_content || '';
    }
    
    const page = documentContent.structured_content.pages.find(p => p.page_number === currentPage);
    return page?.text || '';
  }, [documentContent, currentPage]);

  // Format file size
  const formatFileSize = useCallback((bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }, []);

  // Get quality color
  const getQualityColor = useCallback((score: number) => {
    if (score >= 0.9) return 'text-green-600';
    if (score >= 0.7) return 'text-yellow-600';
    if (score >= 0.5) return 'text-orange-600';
    return 'text-red-600';
  }, []);

  // Loading state
  if (loading) {
    return (
      <div className={`document-preview ${className}`}>
        <div className="animate-pulse">
          <div className="h-8 bg-gray-300 rounded w-3/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-300 rounded"></div>
            <div className="h-4 bg-gray-300 rounded w-5/6"></div>
            <div className="h-4 bg-gray-300 rounded w-4/6"></div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={`document-preview ${className}`}>
        <div className="text-center py-8">
          <DocumentTextIcon className="h-12 w-12 text-gray-400 mx-auto mb-3" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {t('documentPreview.error.title')}
          </h3>
          <p className="text-gray-500 mb-4">{error}</p>
          <button
            onClick={fetchDocumentContent}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {t('documentPreview.error.retry')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`document-preview ${className}`}>
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <DocumentTextIcon className="h-6 w-6 text-gray-400" />
            <div>
              <h2 className="text-xl font-semibold text-gray-900">
                {metadata.filename}
              </h2>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <span>{metadata.content_type.toUpperCase()}</span>
                <span>{formatFileSize(metadata.file_size)}</span>
                <span>
                  {t('documentPreview.header.updated')}: {new Date(metadata.updated_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            {/* Zoom Controls */}
            <div className="flex items-center space-x-1 border border-gray-300 rounded">
              <button
                onClick={handleZoomOut}
                className="p-1 hover:bg-gray-100"
                aria-label={t('documentPreview.zoom.out')}
              >
                <ZoomOutIcon className="h-4 w-4" />
              </button>
              <span className="px-2 py-1 text-sm font-medium min-w-[3rem] text-center">
                {zoom}%
              </span>
              <button
                onClick={handleZoomIn}
                className="p-1 hover:bg-gray-100"
                aria-label={t('documentPreview.zoom.in')}
              >
                <ZoomInIcon className="h-4 w-4" />
              </button>
            </div>
            
            {/* Page Navigation */}
            {totalPages > 1 && (
              <div className="flex items-center space-x-1 border border-gray-300 rounded">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                  className="p-1 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label={t('documentPreview.navigation.previous')}
                >
                  <ChevronLeftIcon className="h-4 w-4" />
                </button>
                <span className="px-2 py-1 text-sm font-medium min-w-[4rem] text-center">
                  {currentPage} / {totalPages}
                </span>
                <button
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className="p-1 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label={t('documentPreview.navigation.next')}
                >
                  <ChevronRightIcon className="h-4 w-4" />
                </button>
              </div>
            )}
            
            {/* Action Buttons */}
            {showMetadata && (
              <button
                onClick={() => setShowMetadataPanel(!showMetadataPanel)}
                className={`p-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  showMetadataPanel 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-gray-600 hover:bg-gray-100'
                }`}
                aria-label={t('documentPreview.actions.toggleMetadata')}
              >
                <InformationCircleIcon className="h-4 w-4" />
              </button>
            )}
            
            {onShare && (
              <button
                onClick={() => onShare(documentId)}
                className="p-2 text-gray-600 hover:bg-gray-100 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label={t('documentPreview.actions.share')}
              >
                <ShareIcon className="h-4 w-4" />
              </button>
            )}
            
            {onEdit && (
              <button
                onClick={() => onEdit(documentId)}
                className="p-2 text-gray-600 hover:bg-gray-100 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label={t('documentPreview.actions.edit')}
              >
                <PencilIcon className="h-4 w-4" />
              </button>
            )}
            
            {showExportOptions && onExport && (
              <div className="relative inline-block">
                <select
                  onChange={(e) => {
                    if (e.target.value) {
                      handleExport(e.target.value);
                      e.target.value = ''; // Reset selection
                    }
                  }}
                  className="px-3 py-1 pr-8 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  defaultValue=""
                >
                  <option value="" disabled>
                    {t('documentPreview.export.label')}
                  </option>
                  <option value="pdf">PDF</option>
                  <option value="docx">Word</option>
                  <option value="txt">Text</option>
                  <option value="json">JSON</option>
                </select>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex">
        {/* Main Content */}
        <div className="flex-1 bg-white">
          <div className="p-6">
            {/* Search Highlighting Info */}
            {searchQuery && (
              <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-center space-x-2">
                  <MagnifyingGlassIcon className="h-4 w-4 text-yellow-600" />
                  <span className="text-sm text-yellow-800">
                    {t('documentPreview.search.highlighted', { query: searchQuery })}
                  </span>
                </div>
              </div>
            )}
            
            {/* Selected Text Actions */}
            {selectedText && (
              <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-blue-800">
                    {t('documentPreview.selection.selected')}: "{selectedText.substring(0, 50)}{selectedText.length > 50 ? '...' : ''}"
                  </span>
                  <button
                    onClick={() => setSelectedText('')}
                    className="text-blue-600 hover:text-blue-800 text-sm"
                  >
                    {t('documentPreview.selection.clear')}
                  </button>
                </div>
              </div>
            )}
            
            {/* Document Content */}
            <div
              ref={contentRef}
              className={`prose max-w-none ${i18n.language === 'am' ? 'prose-rtl' : ''}`}
              style={{ 
                fontSize: `${zoom}%`,
                userSelect: enableTextSelection ? 'text' : 'none'
              }}
              onMouseUp={handleTextSelection}
              dir={i18n.language === 'am' ? 'rtl' : 'ltr'}
            >
              <div
                dangerouslySetInnerHTML={{
                  __html: highlightSearchTerms(currentPageContent, searchQuery)
                }}
              />
            </div>
          </div>
        </div>

        {/* Metadata Panel */}
        {showMetadata && showMetadataPanel && (
          <div className="w-80 bg-gray-50 border-l border-gray-200 p-4 overflow-y-auto">
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-medium text-gray-900 mb-3">
                  {t('documentPreview.metadata.title')}
                </h3>
                
                {/* Basic Information */}
                <div className="space-y-3">
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      {t('documentPreview.metadata.filename')}
                    </dt>
                    <dd className="text-sm text-gray-900">{metadata.filename}</dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      {t('documentPreview.metadata.fileSize')}
                    </dt>
                    <dd className="text-sm text-gray-900">{formatFileSize(metadata.file_size)}</dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      {t('documentPreview.metadata.contentType')}
                    </dt>
                    <dd className="text-sm text-gray-900">{metadata.content_type}</dd>
                  </div>
                  
                  <div>
                    <dt className="text-sm font-medium text-gray-500">
                      {t('documentPreview.metadata.status')}
                    </dt>
                    <dd className="text-sm text-gray-900 capitalize">{metadata.status}</dd>
                  </div>
                </div>
              </div>

              {/* Processing Information */}
              {metadata.processing_info && (
                <div>
                  <h4 className="text-md font-medium text-gray-900 mb-3">
                    {t('documentPreview.metadata.processingInfo')}
                  </h4>
                  <div className="space-y-3">
                    {metadata.processing_info.ocr_confidence && (
                      <div>
                        <dt className="text-sm font-medium text-gray-500">
                          {t('documentPreview.metadata.ocrConfidence')}
                        </dt>
                        <dd className="text-sm text-gray-900">
                          {Math.round(metadata.processing_info.ocr_confidence * 100)}%
                        </dd>
                      </div>
                    )}
                    
                    {metadata.processing_info.language_detected && (
                      <div>
                        <dt className="text-sm font-medium text-gray-500">
                          {t('documentPreview.metadata.detectedLanguage')}
                        </dt>
                        <dd className="text-sm text-gray-900 capitalize">
                          {metadata.processing_info.language_detected}
                        </dd>
                      </div>
                    )}
                    
                    {metadata.processing_info.page_count && (
                      <div>
                        <dt className="text-sm font-medium text-gray-500">
                          {t('documentPreview.metadata.pageCount')}
                        </dt>
                        <dd className="text-sm text-gray-900">
                          {metadata.processing_info.page_count}
                        </dd>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Quality Metrics */}
              {metadata.quality_metrics && (
                <div>
                  <h4 className="text-md font-medium text-gray-900 mb-3">
                    {t('documentPreview.metadata.qualityMetrics')}
                  </h4>
                  <div className="space-y-3">
                    {metadata.quality_metrics.overall_quality_score && (
                      <div>
                        <dt className="text-sm font-medium text-gray-500">
                          {t('documentPreview.metadata.overallQuality')}
                        </dt>
                        <dd className={`text-sm font-medium ${getQualityColor(metadata.quality_metrics.overall_quality_score)}`}>
                          {Math.round(metadata.quality_metrics.overall_quality_score * 100)}%
                        </dd>
                      </div>
                    )}
                    
                    {metadata.quality_metrics.amharic_content_ratio && (
                      <div>
                        <dt className="text-sm font-medium text-gray-500">
                          {t('documentPreview.metadata.amharicContent')}
                        </dt>
                        <dd className="text-sm text-gray-900">
                          {Math.round(metadata.quality_metrics.amharic_content_ratio * 100)}%
                        </dd>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Custom Metadata */}
              {metadata.metadata && Object.keys(metadata.metadata).length > 0 && (
                <div>
                  <h4 className="text-md font-medium text-gray-900 mb-3">
                    {t('documentPreview.metadata.customMetadata')}
                  </h4>
                  <div className="space-y-3">
                    {Object.entries(metadata.metadata).map(([key, value]) => (
                      <div key={key}>
                        <dt className="text-sm font-medium text-gray-500 capitalize">
                          {key.replace(/_/g, ' ')}
                        </dt>
                        <dd className="text-sm text-gray-900">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </dd>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default DocumentPreview;