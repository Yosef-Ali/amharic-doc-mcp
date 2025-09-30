"""Search suggestion pipeline service with autocomplete sources and feedback tuning."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID

import redis.asyncio as redis
from elasticsearch import AsyncElasticsearch
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func

from ..db.models.document import Document
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class SearchSuggestionsService:
    """Service for generating intelligent search suggestions and autocomplete."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.es_client = AsyncElasticsearch([settings.ELASTICSEARCH_URL])
        self.index_name = settings.ELASTICSEARCH_INDEX
        
        # Configuration
        self.min_query_length = 2
        self.max_suggestions = 10
        self.cache_ttl = 3600  # 1 hour
        self.popular_terms_cache_ttl = 3600 * 24  # 24 hours
        
    async def get_search_suggestions(
        self,
        query: str,
        limit: int = 10,
        include_popular: bool = True,
        include_contextual: bool = True,
        user_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get comprehensive search suggestions for a query."""
        if len(query.strip()) < self.min_query_length:
            return []
            
        suggestions = []
        
        # Get suggestions from different sources concurrently
        tasks = []
        
        # Elasticsearch completion suggestions
        tasks.append(self._get_es_completion_suggestions(query, limit))
        
        # Fuzzy/typo suggestions
        tasks.append(self._get_fuzzy_suggestions(query, limit // 2))
        
        # Popular terms
        if include_popular:
            tasks.append(self._get_popular_terms(query, limit // 2))
            
        # Contextual suggestions based on user history
        if include_contextual and user_id:
            tasks.append(self._get_contextual_suggestions(query, user_id, limit // 2))
            
        # Amharic-specific suggestions
        tasks.append(self._get_amharic_suggestions(query, limit // 2))
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and rank suggestions
        all_suggestions = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Suggestion task failed: {result}")
                continue
            if isinstance(result, list):
                all_suggestions.extend(result)
                
        # Remove duplicates and rank
        ranked_suggestions = self._rank_and_deduplicate_suggestions(
            all_suggestions, query, limit
        )
        
        return ranked_suggestions
        
    async def record_search_query(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        results_count: int = 0,
        clicked_result: Optional[str] = None
    ) -> None:
        """Record a search query for analytics and suggestion improvement."""
        timestamp = datetime.utcnow()
        
        # Update query frequency
        await self._update_query_frequency(query)
        
        # Record user search history
        if user_id:
            await self._record_user_search_history(user_id, query, timestamp, results_count)
            
        # Record click-through data
        if clicked_result:
            await self._record_click_through(query, clicked_result, timestamp)
            
        logger.debug(f"Recorded search query: '{query}' (results: {results_count})")
        
    async def get_trending_searches(
        self,
        days: int = 7,
        limit: int = 20,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get trending search queries."""
        cache_key = f"trending_searches:{days}d:{language or 'all'}:{limit}"
        
        # Try cache first
        cached_data = await self._get_cached_data(cache_key)
        if cached_data:
            return cached_data
            
        # Calculate trending searches
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get search frequencies from Redis
        pattern = f"search_freq:*"
        keys = await self.redis_client.keys(pattern)
        
        trending = []
        for key in keys:
            try:
                query = key.decode().split(":", 2)[2]
                
                # Filter by language if specified
                if language and not self._is_query_language(query, language):
                    continue
                    
                freq_data = await self.redis_client.hgetall(key)
                if freq_data:
                    total_count = sum(int(count) for count in freq_data.values())
                    if total_count > 0:
                        trending.append({
                            "query": query,
                            "frequency": total_count,
                            "language": self._detect_query_language(query)
                        })
            except Exception as e:
                logger.warning(f"Error processing trending query {key}: {e}")
                
        # Sort by frequency and limit
        trending.sort(key=lambda x: x["frequency"], reverse=True)
        trending = trending[:limit]
        
        # Cache result
        await self._cache_data(cache_key, trending, self.popular_terms_cache_ttl)
        
        return trending
        
    async def get_query_suggestions_with_context(
        self,
        partial_query: str,
        document_context: Optional[List[str]] = None,
        user_id: Optional[UUID] = None
    ) -> List[Dict[str, Any]]:
        """Get contextually aware query suggestions."""
        base_suggestions = await self.get_search_suggestions(
            partial_query, include_contextual=bool(user_id), user_id=user_id
        )
        
        # Enhance with document context
        if document_context:
            context_suggestions = await self._get_document_context_suggestions(
                partial_query, document_context
            )
            
            # Merge and re-rank
            combined_suggestions = base_suggestions + context_suggestions
            return self._rank_and_deduplicate_suggestions(
                combined_suggestions, partial_query, self.max_suggestions
            )
            
        return base_suggestions
        
    async def _get_es_completion_suggestions(
        self,
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get completion suggestions from Elasticsearch."""
        try:
            response = await self.es_client.search(
                index=self.index_name,
                body={
                    "suggest": {
                        "completion_suggest": {
                            "prefix": query,
                            "completion": {
                                "field": "title.completion",
                                "size": limit,
                                "skip_duplicates": True
                            }
                        },
                        "phrase_suggest": {
                            "text": query,
                            "phrase": {
                                "field": "content",
                                "size": limit // 2,
                                "max_errors": 2
                            }
                        }
                    }
                }
            )
            
            suggestions = []
            
            # Process completion suggestions
            if "completion_suggest" in response.get("suggest", {}):
                for suggest_result in response["suggest"]["completion_suggest"]:
                    for option in suggest_result.get("options", []):
                        suggestions.append({
                            "text": option["text"],
                            "score": option["_score"],
                            "source": "completion",
                            "type": "exact_match"
                        })
                        
            # Process phrase suggestions
            if "phrase_suggest" in response.get("suggest", {}):
                for suggest_result in response["suggest"]["phrase_suggest"]:
                    for option in suggest_result.get("options", []):
                        suggestions.append({
                            "text": option["text"],
                            "score": option["score"],
                            "source": "phrase",
                            "type": "phrase_completion"
                        })
                        
            return suggestions
            
        except Exception as e:
            logger.error(f"Elasticsearch completion suggestion failed: {e}")
            return []
            
    async def _get_fuzzy_suggestions(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get fuzzy/typo-corrected suggestions."""
        try:
            response = await self.es_client.search(
                index=self.index_name,
                body={
                    "query": {
                        "fuzzy": {
                            "content": {
                                "value": query,
                                "fuzziness": "AUTO",
                                "max_expansions": limit
                            }
                        }
                    },
                    "size": 0,
                    "aggs": {
                        "suggestions": {
                            "terms": {
                                "field": "content.keyword",
                                "size": limit,
                                "min_doc_count": 1
                            }
                        }
                    }
                }
            )
            
            suggestions = []
            if "aggregations" in response and "suggestions" in response["aggregations"]:
                for bucket in response["aggregations"]["suggestions"]["buckets"]:
                    suggestions.append({
                        "text": bucket["key"],
                        "score": bucket["doc_count"],
                        "source": "fuzzy",
                        "type": "typo_correction"
                    })
                    
            return suggestions
            
        except Exception as e:
            logger.error(f"Fuzzy suggestion failed: {e}")
            return []
            
    async def _get_popular_terms(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get popular search terms that start with the query."""
        pattern = f"search_freq:*{query.lower()}*"
        keys = await self.redis_client.keys(pattern)
        
        popular_terms = []
        for key in keys[:limit * 2]:  # Get more than needed for filtering
            try:
                query_text = key.decode().split(":", 2)[2]
                if query_text.lower().startswith(query.lower()):
                    freq_data = await self.redis_client.hgetall(key)
                    total_freq = sum(int(count) for count in freq_data.values())
                    
                    popular_terms.append({
                        "text": query_text,
                        "score": total_freq,
                        "source": "popular",
                        "type": "popular_query"
                    })
            except Exception as e:
                logger.warning(f"Error processing popular term {key}: {e}")
                
        # Sort by frequency and limit
        popular_terms.sort(key=lambda x: x["score"], reverse=True)
        return popular_terms[:limit]
        
    async def _get_contextual_suggestions(
        self,
        query: str,
        user_id: UUID,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Get personalized suggestions based on user's search history."""
        user_history_key = f"user_search_history:{user_id}"
        
        try:
            # Get recent user searches
            recent_searches = await self.redis_client.lrange(user_history_key, 0, 50)
            
            suggestions = []
            for search_data in recent_searches:
                try:
                    import json
                    search_info = json.loads(search_data)
                    past_query = search_info.get("query", "")
                    
                    # Find related queries
                    if query.lower() in past_query.lower() or past_query.lower() in query.lower():
                        suggestions.append({
                            "text": past_query,
                            "score": search_info.get("results_count", 0),
                            "source": "personal_history",
                            "type": "contextual"
                        })
                        
                    if len(suggestions) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"Error processing user search history: {e}")
                    
            return suggestions
            
        except Exception as e:
            logger.error(f"Contextual suggestions failed: {e}")
            return []
            
    async def _get_amharic_suggestions(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get Amharic-specific suggestions including transliterations."""
        suggestions = []
        
        # Check if query contains Amharic text
        has_amharic = any('\u1200' <= char <= '\u137F' for char in query)
        
        if has_amharic:
            # Amharic morphological suggestions
            morphological_variants = self._generate_amharic_morphological_variants(query)
            for variant in morphological_variants[:limit // 2]:
                suggestions.append({
                    "text": variant,
                    "score": 0.8,
                    "source": "morphological",
                    "type": "amharic_variant"
                })
                
        else:
            # Try transliteration suggestions (English to Amharic)
            transliterations = self._generate_transliteration_suggestions(query)
            for transliteration in transliterations[:limit // 2]:
                suggestions.append({
                    "text": transliteration,
                    "score": 0.6,
                    "source": "transliteration",
                    "type": "transliteration"
                })
                
        return suggestions
        
    async def _get_document_context_suggestions(
        self,
        query: str,
        document_context: List[str]
    ) -> List[Dict[str, Any]]:
        """Get suggestions based on document context."""
        suggestions = []
        
        # Extract relevant terms from document context
        context_terms = []
        for doc_text in document_context:
            terms = self._extract_relevant_terms(doc_text, query)
            context_terms.extend(terms)
            
        # Score and rank context terms
        term_scores = {}
        for term in context_terms:
            if query.lower() in term.lower():
                term_scores[term] = term_scores.get(term, 0) + 1
                
        # Convert to suggestions
        for term, score in sorted(term_scores.items(), key=lambda x: x[1], reverse=True):
            suggestions.append({
                "text": term,
                "score": score,
                "source": "document_context",
                "type": "contextual_term"
            })
            
            if len(suggestions) >= 5:  # Limit context suggestions
                break
                
        return suggestions
        
    def _rank_and_deduplicate_suggestions(
        self,
        suggestions: List[Dict[str, Any]],
        query: str,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Rank and deduplicate suggestions."""
        # Remove duplicates based on text
        seen = set()
        unique_suggestions = []
        
        for suggestion in suggestions:
            text = suggestion["text"].lower().strip()
            if text not in seen and text != query.lower():
                seen.add(text)
                unique_suggestions.append(suggestion)
                
        # Enhanced ranking considering multiple factors
        def rank_suggestion(suggestion):
            base_score = float(suggestion.get("score", 0))
            
            # Boost exact prefix matches
            if suggestion["text"].lower().startswith(query.lower()):
                base_score *= 1.5
                
            # Boost by suggestion type
            type_boosts = {
                "exact_match": 1.3,
                "popular_query": 1.2,
                "phrase_completion": 1.1,
                "contextual": 1.1,
                "amharic_variant": 1.0,
                "typo_correction": 0.9,
                "transliteration": 0.8
            }
            
            suggestion_type = suggestion.get("type", "unknown")
            base_score *= type_boosts.get(suggestion_type, 1.0)
            
            return base_score
            
        # Sort by enhanced score
        unique_suggestions.sort(key=rank_suggestion, reverse=True)
        
        return unique_suggestions[:limit]
        
    def _generate_amharic_morphological_variants(self, query: str) -> List[str]:
        """Generate morphological variants for Amharic queries."""
        variants = []
        
        # Basic Amharic morphological transformations
        # This is a simplified approach - real implementation would use NLP tools
        transformations = [
            ("ን", ""),      # Remove accusative marker
            ("ም", ""),      # Remove question marker  
            ("ው", ""),      # Remove masculine marker
            ("ዋ", "ው"),     # Feminine to masculine
            ("ሁ", ""),      # Remove possessive
            ("ች", "")       # Remove diminutive
        ]
        
        base_query = query.strip()
        variants.append(base_query)
        
        for suffix, replacement in transformations:
            if base_query.endswith(suffix):
                variant = base_query[:-len(suffix)] + replacement
                if variant and variant != base_query:
                    variants.append(variant)
                    
        return variants[:5]  # Limit variants
        
    def _generate_transliteration_suggestions(self, query: str) -> List[str]:
        """Generate transliteration suggestions from Latin to Amharic."""
        # Basic transliteration mapping
        transliteration_map = {
            "ha": "ሀ", "hu": "ሁ", "hi": "ሂ", "haa": "ሃ", "hee": "ሄ", "he": "ህ", "ho": "ሆ",
            "la": "ላ", "lu": "ሉ", "li": "ሊ", "laa": "ላ", "lee": "ሌ", "le": "ል", "lo": "ሎ",
            "ma": "ማ", "mu": "ሙ", "mi": "ሚ", "maa": "ማ", "mee": "ሜ", "me": "ም", "mo": "ሞ",
            # Add more mappings as needed
        }
        
        suggestions = []
        query_lower = query.lower()
        
        for latin, amharic in transliteration_map.items():
            if latin in query_lower:
                transliterated = query_lower.replace(latin, amharic)
                suggestions.append(transliterated)
                
        return suggestions[:3]  # Limit transliterations
        
    def _extract_relevant_terms(self, text: str, query: str) -> List[str]:
        """Extract relevant terms from text based on query."""
        words = text.split()
        relevant_terms = []
        
        for i, word in enumerate(words):
            # Extract phrases containing query terms
            if query.lower() in word.lower():
                # Get surrounding context
                start = max(0, i - 2)
                end = min(len(words), i + 3)
                phrase = " ".join(words[start:end])
                relevant_terms.append(phrase.strip())
                
        return relevant_terms[:10]  # Limit extracted terms
        
    def _is_query_language(self, query: str, language: str) -> bool:
        """Check if query is in specified language."""
        if language == "amh":
            return any('\u1200' <= char <= '\u137F' for char in query)
        elif language == "en":
            return any(char.isascii() and char.isalpha() for char in query)
        return True  # Default to include all
        
    def _detect_query_language(self, query: str) -> str:
        """Detect the primary language of a query."""
        amharic_chars = sum(1 for char in query if '\u1200' <= char <= '\u137F')
        ascii_chars = sum(1 for char in query if char.isascii() and char.isalpha())
        
        if amharic_chars > ascii_chars:
            return "amh"
        elif ascii_chars > 0:
            return "en"
        else:
            return "unknown"
            
    async def _update_query_frequency(self, query: str) -> None:
        """Update query frequency statistics."""
        key = f"search_freq:query:{query.lower()}"
        date_key = datetime.utcnow().strftime("%Y-%m-%d")
        
        try:
            await self.redis_client.hincrby(key, date_key, 1)
            await self.redis_client.expire(key, self.popular_terms_cache_ttl)
        except Exception as e:
            logger.warning(f"Failed to update query frequency: {e}")
            
    async def _record_user_search_history(
        self,
        user_id: UUID,
        query: str,
        timestamp: datetime,
        results_count: int
    ) -> None:
        """Record user's search history."""
        key = f"user_search_history:{user_id}"
        search_data = {
            "query": query,
            "timestamp": timestamp.isoformat(),
            "results_count": results_count
        }
        
        try:
            import json
            await self.redis_client.lpush(key, json.dumps(search_data))
            await self.redis_client.ltrim(key, 0, 99)  # Keep last 100 searches
            await self.redis_client.expire(key, 3600 * 24 * 30)  # 30 days
        except Exception as e:
            logger.warning(f"Failed to record user search history: {e}")
            
    async def _record_click_through(
        self,
        query: str,
        clicked_result: str,
        timestamp: datetime
    ) -> None:
        """Record click-through data for query optimization."""
        key = f"click_through:{query.lower()}"
        
        try:
            await self.redis_client.hincrby(key, clicked_result, 1)
            await self.redis_client.expire(key, self.popular_terms_cache_ttl)
        except Exception as e:
            logger.warning(f"Failed to record click-through: {e}")
            
    async def _get_cached_data(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Get data from cache."""
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                import json
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache retrieval failed: {e}")
        return None
        
    async def _cache_data(
        self,
        cache_key: str,
        data: List[Dict[str, Any]],
        ttl: int
    ) -> None:
        """Cache data with TTL."""
        try:
            import json
            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(data, ensure_ascii=False)
            )
        except Exception as e:
            logger.warning(f"Caching failed: {e}")
            
    async def close(self) -> None:
        """Close connections."""
        await self.redis_client.close()
        await self.es_client.close()


# Global search suggestions service instance
_suggestions_service: Optional[SearchSuggestionsService] = None


def get_search_suggestions_service(settings: Settings) -> SearchSuggestionsService:
    """Get the global search suggestions service instance."""
    global _suggestions_service
    if _suggestions_service is None:
        _suggestions_service = SearchSuggestionsService(settings)
    return _suggestions_service