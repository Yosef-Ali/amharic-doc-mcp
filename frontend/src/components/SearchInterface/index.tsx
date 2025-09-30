/**
 * SearchInterface component with filters, suggestions, and bilingual UI
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  MagnifyingGlassIcon,
  FunnelIcon,
  XMarkIcon,
  ClockIcon,
  DocumentTextIcon,
  AdjustmentsHorizontalIcon,
  SparklesIcon,
  LanguageIcon
} from '@heroicons/react/24/outline';

interface SearchResult {
  document_id: string;
  filename: string;
  content_snippet: string;
  highlighted_snippet: string;
  relevance_score: number;
  document_type: string;
  created_at: string;
  metadata: Record<string, any>;
  quality_score?: number;
  page_number?: number;
}

interface SearchFilters {
  document_types: string[];
  date_range: {
    start?: string;
    end?: string;
  };
  content_types: string[];
  quality_scores: {
    min: number;
    max: number;
  };
  language?: string;
}

interface SearchSuggestion {
  text: string;
  type: 'term' | 'document' | 'recent' | 'popular';
  score: number;
  context?: string;
}

interface SearchInterfaceProps {
  onSearch: (query: string, filters?: SearchFilters) => Promise<SearchResult[]>;
  onExport?: (results: SearchResult[], format: string) => Promise<void>;
  placeholder?: string;
  showFilters?: boolean;
  showSuggestions?: boolean;
  showLanguageToggle?: boolean;
  maxResults?: number;
  enableHighlighting?: boolean;
  className?: string;
}

const SearchInterface: React.FC<SearchInterfaceProps> = ({
  onSearch,
  onExport,
  placeholder,
  showFilters = true,
  showSuggestions = true,
  showLanguageToggle = true,
  maxResults = 50,
  enableHighlighting = true,
  className = ''
}) => {
  const { t, i18n } = useTranslation();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [showSuggestionsPanel, setShowSuggestionsPanel] = useState(false);
  const [totalResults, setTotalResults] = useState(0);
  
  const searchInputRef = useRef<HTMLInputElement>(null);
  const suggestionsTimeoutRef = useRef<NodeJS.Timeout>();

  // Search filters state
  const [filters, setFilters] = useState<SearchFilters>({
    document_types: [],
    date_range: {},
    content_types: [],
    quality_scores: { min: 0, max: 1 },
    language: i18n.language
  });

  // Recent searches
  const [recentSearches, setRecentSearches] = useState<string[]>([]);

  // Load recent searches from localStorage
  useEffect(() => {
    const saved = localStorage.getItem('recentSearches');
    if (saved) {
      try {
        setRecentSearches(JSON.parse(saved));
      } catch (err) {
        console.error('Failed to parse recent searches:', err);
      }
    }
  }, []);

  // Save recent searches to localStorage
  const saveRecentSearch = useCallback((searchQuery: string) => {
    const updated = [
      searchQuery,
      ...recentSearches.filter(s => s !== searchQuery)
    ].slice(0, 10); // Keep only last 10 searches
    
    setRecentSearches(updated);
    localStorage.setItem('recentSearches', JSON.stringify(updated));
  }, [recentSearches]);

  // Fetch search suggestions
  const fetchSuggestions = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim() || !showSuggestions) return;

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(
        `/api/v1/search/suggestions?query=${encodeURIComponent(searchQuery)}&limit=8`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch suggestions');
      }

      const data = await response.json();
      setSuggestions(data.suggestions || []);
    } catch (err) {
      console.error('Failed to fetch suggestions:', err);
      setSuggestions([]);
    }
  }, [showSuggestions]);

  // Handle input change with debounced suggestions
  const handleInputChange = useCallback((value: string) => {
    setQuery(value);
    setShowSuggestionsPanel(value.length > 0);

    // Clear previous timeout
    if (suggestionsTimeoutRef.current) {
      clearTimeout(suggestionsTimeoutRef.current);
    }

    // Debounce suggestions
    if (value.length > 2) {
      suggestionsTimeoutRef.current = setTimeout(() => {
        fetchSuggestions(value);
      }, 300);
    } else {
      setSuggestions([]);
    }
  }, [fetchSuggestions]);

  // Perform search
  const performSearch = useCallback(async (searchQuery: string = query, searchFilters: SearchFilters = filters) => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError(null);
    setShowSuggestionsPanel(false);

    try {
      const results = await onSearch(searchQuery, searchFilters);
      setResults(results);
      setTotalResults(results.length);
      
      // Save to recent searches
      saveRecentSearch(searchQuery);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setResults([]);
      setTotalResults(0);
    } finally {
      setLoading(false);
    }
  }, [query, filters, onSearch, saveRecentSearch]);

  // Handle search submission
  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    performSearch();
  }, [performSearch]);

  // Handle suggestion selection
  const handleSuggestionSelect = useCallback((suggestion: SearchSuggestion) => {
    setQuery(suggestion.text);
    setShowSuggestionsPanel(false);
    performSearch(suggestion.text);
  }, [performSearch]);

  // Handle filter changes
  const handleFilterChange = useCallback((newFilters: Partial<SearchFilters>) => {
    const updatedFilters = { ...filters, ...newFilters };
    setFilters(updatedFilters);
    
    // Re-search if there's a query
    if (query.trim()) {
      performSearch(query, updatedFilters);
    }
  }, [filters, query, performSearch]);

  // Language toggle
  const toggleLanguage = useCallback(() => {
    const newLang = i18n.language === 'en' ? 'am' : 'en';
    i18n.changeLanguage(newLang);
    handleFilterChange({ language: newLang });
  }, [i18n, handleFilterChange]);

  // Clear search
  const clearSearch = useCallback(() => {
    setQuery('');
    setResults([]);
    setSuggestions([]);
    setError(null);
    setTotalResults(0);
    setShowSuggestionsPanel(false);
    searchInputRef.current?.focus();
  }, []);

  // Export results
  const handleExport = useCallback(async (format: string) => {
    if (!onExport || results.length === 0) return;
    
    try {
      await onExport(results, format);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    }
  }, [onExport, results]);

  // Highlight search terms in text
  const highlightText = useCallback((text: string, searchQuery: string) => {
    if (!enableHighlighting || !searchQuery.trim()) return text;
    
    const terms = searchQuery.split(' ').filter(term => term.length > 2);
    let highlightedText = text;
    
    terms.forEach(term => {
      const regex = new RegExp(`(${term})`, 'gi');
      highlightedText = highlightedText.replace(
        regex, 
        '<mark class="bg-yellow-200 px-1 rounded">$1</mark>'
      );
    });
    
    return highlightedText;
  }, [enableHighlighting]);

  // Memoized recent searches display
  const recentSearchesComponent = useMemo(() => {
    if (recentSearches.length === 0) return null;

    return (
      <div className="border-t border-gray-200 pt-2">
        <div className="text-xs text-gray-500 mb-2 px-3">
          {t('search.suggestions.recent')}
        </div>
        {recentSearches.slice(0, 5).map((search, index) => (
          <button
            key={index}
            onClick={() => handleSuggestionSelect({ text: search, type: 'recent', score: 0 })}
            className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center space-x-2"
          >
            <ClockIcon className="h-4 w-4 text-gray-400" />
            <span>{search}</span>
          </button>
        ))}
      </div>
    );
  }, [recentSearches, handleSuggestionSelect, t]);

  return (
    <div className={`search-interface ${className}`}>
      {/* Search Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-900">
            {t('search.title')}
          </h2>
          
          <div className="flex items-center space-x-3">
            {showLanguageToggle && (
              <button
                onClick={toggleLanguage}
                className="flex items-center space-x-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <LanguageIcon className="h-4 w-4" />
                <span>{i18n.language === 'en' ? 'አማርኛ' : 'English'}</span>
              </button>
            )}
            
            {showFilters && (
              <button
                onClick={() => setShowFilterPanel(!showFilterPanel)}
                className={`flex items-center space-x-2 px-3 py-2 text-sm font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  showFilterPanel
                    ? 'text-blue-700 bg-blue-50 border border-blue-300'
                    : 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50'
                }`}
              >
                <FunnelIcon className="h-4 w-4" />
                <span>{t('search.filters.toggle')}</span>
              </button>
            )}
          </div>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="relative">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              ref={searchInputRef}
              type="text"
              value={query}
              onChange={(e) => handleInputChange(e.target.value)}
              onFocus={() => setShowSuggestionsPanel(query.length > 0)}
              placeholder={placeholder || t('search.placeholder')}
              className="w-full pl-10 pr-20 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              dir={i18n.language === 'am' ? 'rtl' : 'ltr'}
            />
            
            {query && (
              <button
                type="button"
                onClick={clearSearch}
                className="absolute right-12 top-1/2 transform -translate-y-1/2 p-1 text-gray-400 hover:text-gray-600"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            )}
            
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="absolute right-2 top-1/2 transform -translate-y-1/2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white text-sm font-medium rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {loading ? t('search.searching') : t('search.search')}
            </button>
          </div>

          {/* Suggestions Dropdown */}
          {showSuggestionsPanel && (suggestions.length > 0 || recentSearches.length > 0) && (
            <div className="absolute z-50 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg">
              {suggestions.length > 0 && (
                <div className="py-2">
                  <div className="text-xs text-gray-500 mb-2 px-3">
                    {t('search.suggestions.suggested')}
                  </div>
                  {suggestions.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestionSelect(suggestion)}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 flex items-center justify-between"
                    >
                      <div className="flex items-center space-x-2">
                        <SparklesIcon className="h-4 w-4 text-blue-400" />
                        <span>{suggestion.text}</span>
                      </div>
                      <span className="text-xs text-gray-400">
                        {t(`search.suggestions.types.${suggestion.type}`)}
                      </span>
                    </button>
                  ))}
                </div>
              )}
              
              {recentSearchesComponent}
            </div>
          )}
        </form>
      </div>

      {/* Filters Panel */}
      {showFilters && showFilterPanel && (
        <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Document Types */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('search.filters.documentTypes')}
              </label>
              <div className="space-y-2">
                {['pdf', 'image', 'word', 'csv', 'text'].map((type) => (
                  <label key={type} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={filters.document_types.includes(type)}
                      onChange={(e) => {
                        const types = e.target.checked
                          ? [...filters.document_types, type]
                          : filters.document_types.filter(t => t !== type);
                        handleFilterChange({ document_types: types });
                      }}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">
                      {t(`search.filters.types.${type}`)}
                    </span>
                  </label>
                ))}
              </div>
            </div>

            {/* Date Range */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('search.filters.dateRange')}
              </label>
              <div className="space-y-2">
                <input
                  type="date"
                  value={filters.date_range.start || ''}
                  onChange={(e) => handleFilterChange({
                    date_range: { ...filters.date_range, start: e.target.value }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={t('search.filters.startDate')}
                />
                <input
                  type="date"
                  value={filters.date_range.end || ''}
                  onChange={(e) => handleFilterChange({
                    date_range: { ...filters.date_range, end: e.target.value }
                  })}
                  className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder={t('search.filters.endDate')}
                />
              </div>
            </div>

            {/* Quality Score */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('search.filters.qualityScore')}
              </label>
              <div className="space-y-2">
                <div>
                  <label className="text-xs text-gray-500">
                    {t('search.filters.minQuality')}: {Math.round(filters.quality_scores.min * 100)}%
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={filters.quality_scores.min}
                    onChange={(e) => handleFilterChange({
                      quality_scores: { ...filters.quality_scores, min: parseFloat(e.target.value) }
                    })}
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500">
                    {t('search.filters.maxQuality')}: {Math.round(filters.quality_scores.max * 100)}%
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={filters.quality_scores.max}
                    onChange={(e) => handleFilterChange({
                      quality_scores: { ...filters.quality_scores, max: parseFloat(e.target.value) }
                    })}
                    className="w-full"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Search Results */}
      <div>
        {/* Results Header */}
        {(results.length > 0 || loading || error) && (
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-4">
              <h3 className="text-lg font-medium text-gray-900">
                {t('search.results.title')}
              </h3>
              {totalResults > 0 && (
                <span className="text-sm text-gray-500">
                  {t('search.results.count', { count: totalResults, query })}
                </span>
              )}
            </div>
            
            {results.length > 0 && onExport && (
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-500">{t('search.export.label')}:</span>
                <button
                  onClick={() => handleExport('json')}
                  className="px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-700"
                >
                  JSON
                </button>
                <button
                  onClick={() => handleExport('csv')}
                  className="px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-700"
                >
                  CSV
                </button>
                <button
                  onClick={() => handleExport('pdf')}
                  className="px-2 py-1 text-xs font-medium text-blue-600 hover:text-blue-700"
                >
                  PDF
                </button>
              </div>
            )}
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="animate-pulse bg-white border border-gray-200 rounded-lg p-4">
                <div className="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
                <div className="h-3 bg-gray-300 rounded w-full mb-1"></div>
                <div className="h-3 bg-gray-300 rounded w-5/6"></div>
              </div>
            ))}
          </div>
        )}

        {/* Results List */}
        {!loading && results.length > 0 && (
          <div className="space-y-4">
            {results.map((result) => (
              <div
                key={result.document_id}
                className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center space-x-3">
                    <DocumentTextIcon className="h-5 w-5 text-gray-400" />
                    <h4 className="font-medium text-gray-900">
                      {result.filename}
                    </h4>
                    <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded">
                      {result.document_type.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex items-center space-x-2 text-sm text-gray-500">
                    {result.quality_score && (
                      <span>
                        {t('search.results.quality')}: {Math.round(result.quality_score * 100)}%
                      </span>
                    )}
                    <span>
                      {Math.round(result.relevance_score * 100)}% {t('search.results.relevance')}
                    </span>
                  </div>
                </div>
                
                <div className="mb-2">
                  <div 
                    className="text-sm text-gray-700 line-clamp-3"
                    dangerouslySetInnerHTML={{
                      __html: result.highlighted_snippet || highlightText(result.content_snippet, query)
                    }}
                    dir={i18n.language === 'am' ? 'rtl' : 'ltr'}
                  />
                </div>
                
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>
                    {t('search.results.created')}: {new Date(result.created_at).toLocaleDateString()}
                  </span>
                  {result.page_number && (
                    <span>
                      {t('search.results.page')}: {result.page_number}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && results.length === 0 && query && (
          <div className="text-center py-8">
            <MagnifyingGlassIcon className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {t('search.results.noResults')}
            </h3>
            <p className="text-gray-500">
              {t('search.results.noResultsDescription', { query })}
            </p>
          </div>
        )}

        {/* Initial State */}
        {!loading && !error && results.length === 0 && !query && (
          <div className="text-center py-8">
            <MagnifyingGlassIcon className="h-12 w-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {t('search.welcome.title')}
            </h3>
            <p className="text-gray-500">
              {t('search.welcome.description')}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchInterface;