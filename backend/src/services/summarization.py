"""Summarization service for producing Amharic summaries with caching and evaluation."""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.models.document import Document
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class SummarizationService:
    """Service for generating and managing document summaries."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.redis_client = redis.from_url(settings.REDIS_URL)
        self.cache_ttl = 3600 * 24 * 7  # 7 days
        self.min_content_length = 100  # Minimum characters to summarize
        self.max_summary_length = 500  # Maximum summary length in characters
        
    async def generate_summary(
        self,
        session: AsyncSession,
        document_id: UUID,
        content: str,
        language: str = "amh",
        summary_type: str = "extractive",
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """Generate a summary for the given content."""
        # Check cache first unless force regenerate
        cache_key = self._get_cache_key(document_id, content, summary_type)
        
        if not force_regenerate:
            cached_summary = await self._get_cached_summary(cache_key)
            if cached_summary:
                logger.info(f"Retrieved cached summary for document {document_id}")
                return cached_summary
                
        # Validate content length
        if len(content.strip()) < self.min_content_length:
            return {
                "summary": content[:self.max_summary_length],
                "type": "original",
                "language": language,
                "length": len(content),
                "confidence": 1.0,
                "cached": False,
                "generated_at": datetime.utcnow().isoformat(),
                "reason": "Content too short to summarize"
            }
            
        # Generate summary based on type
        if summary_type == "extractive":
            summary_result = await self._generate_extractive_summary(content, language)
        elif summary_type == "abstractive":
            summary_result = await self._generate_abstractive_summary(content, language)
        elif summary_type == "keyword":
            summary_result = await self._generate_keyword_summary(content, language)
        else:
            raise ValueError(f"Unsupported summary type: {summary_type}")
            
        # Add metadata
        summary_result.update({
            "document_id": str(document_id),
            "original_length": len(content),
            "compression_ratio": len(summary_result["summary"]) / len(content),
            "cached": False,
            "generated_at": datetime.utcnow().isoformat()
        })
        
        # Cache the result
        await self._cache_summary(cache_key, summary_result)
        
        # Evaluate summary quality
        quality_score = await self._evaluate_summary_quality(
            content, summary_result["summary"], language
        )
        summary_result["quality_score"] = quality_score
        
        logger.info(f"Generated {summary_type} summary for document {document_id} (quality: {quality_score:.3f})")
        
        return summary_result
        
    async def generate_multi_type_summary(
        self,
        session: AsyncSession,
        document_id: UUID,
        content: str,
        language: str = "amh"
    ) -> Dict[str, Any]:
        """Generate multiple types of summaries for comprehensive coverage."""
        summaries = {}
        
        # Generate different summary types
        summary_types = ["extractive", "abstractive", "keyword"]
        
        for summary_type in summary_types:
            try:
                summary = await self.generate_summary(
                    session, document_id, content, language, summary_type
                )
                summaries[summary_type] = summary
            except Exception as e:
                logger.error(f"Failed to generate {summary_type} summary: {e}")
                summaries[summary_type] = {"error": str(e)}
                
        # Select best summary based on quality scores
        best_summary = self._select_best_summary(summaries)
        
        return {
            "document_id": str(document_id),
            "all_summaries": summaries,
            "recommended_summary": best_summary,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    async def get_summary_by_document(
        self,
        session: AsyncSession,
        document_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get existing summary for a document."""
        # This would typically fetch from a summaries table
        # For now, check cache with different summary types
        cache_patterns = [
            f"summary:{document_id}:*:extractive",
            f"summary:{document_id}:*:abstractive", 
            f"summary:{document_id}:*:keyword"
        ]
        
        for pattern in cache_patterns:
            keys = await self.redis_client.keys(pattern)
            if keys:
                cached_data = await self.redis_client.get(keys[0])
                if cached_data:
                    import json
                    return json.loads(cached_data)
                    
        return None
        
    async def batch_summarize(
        self,
        session: AsyncSession,
        documents: List[Tuple[UUID, str]],  # (document_id, content)
        language: str = "amh",
        summary_type: str = "extractive"
    ) -> List[Dict[str, Any]]:
        """Batch summarize multiple documents."""
        results = []
        
        for document_id, content in documents:
            try:
                summary = await self.generate_summary(
                    session, document_id, content, language, summary_type
                )
                results.append(summary)
            except Exception as e:
                logger.error(f"Failed to summarize document {document_id}: {e}")
                results.append({
                    "document_id": str(document_id),
                    "error": str(e),
                    "generated_at": datetime.utcnow().isoformat()
                })
                
        return results
        
    async def _generate_extractive_summary(
        self,
        content: str,
        language: str
    ) -> Dict[str, Any]:
        """Generate extractive summary by selecting key sentences."""
        sentences = self._split_sentences(content, language)
        
        if len(sentences) <= 3:
            return {
                "summary": content[:self.max_summary_length],
                "type": "extractive",
                "language": language,
                "sentence_count": len(sentences),
                "confidence": 0.9
            }
            
        # Score sentences based on various factors
        sentence_scores = []
        
        for i, sentence in enumerate(sentences):
            score = self._score_sentence(sentence, content, i, len(sentences))
            sentence_scores.append((score, sentence))
            
        # Sort by score and select top sentences
        sentence_scores.sort(reverse=True)
        num_sentences = min(3, max(1, len(sentences) // 3))
        
        selected_sentences = [sent for _, sent in sentence_scores[:num_sentences]]
        summary = " ".join(selected_sentences)
        
        # Truncate if too long
        if len(summary) > self.max_summary_length:
            summary = summary[:self.max_summary_length - 3] + "..."
            
        return {
            "summary": summary,
            "type": "extractive",
            "language": language,
            "sentence_count": len(selected_sentences),
            "confidence": min(sentence_scores[0][0], 1.0) if sentence_scores else 0.5
        }
        
    async def _generate_abstractive_summary(
        self,
        content: str,
        language: str
    ) -> Dict[str, Any]:
        """Generate abstractive summary using language models."""
        # For Amharic, this is complex without dedicated models
        # Fallback to extractive with paraphrasing
        
        extractive_result = await self._generate_extractive_summary(content, language)
        
        # Simple abstractive approach: combine and rephrase key points
        summary = extractive_result["summary"]
        
        # Basic abstractive techniques for Amharic
        if language == "amh":
            summary = self._apply_amharic_abstraction(summary)
        
        return {
            "summary": summary,
            "type": "abstractive",
            "language": language,
            "confidence": extractive_result["confidence"] * 0.8  # Lower confidence for abstraction
        }
        
    async def _generate_keyword_summary(
        self,
        content: str,
        language: str
    ) -> Dict[str, Any]:
        """Generate keyword-based summary."""
        # Extract key terms and phrases
        keywords = self._extract_keywords(content, language)
        
        # Create summary from keywords
        if language == "amh":
            summary = self._create_amharic_keyword_summary(keywords, content)
        else:
            summary = f"ዋና ቃላት: {', '.join(keywords[:10])}"
            
        return {
            "summary": summary[:self.max_summary_length],
            "type": "keyword", 
            "language": language,
            "keywords": keywords[:20],
            "confidence": 0.7
        }
        
    def _split_sentences(self, content: str, language: str) -> List[str]:
        """Split content into sentences based on language."""
        if language == "amh":
            # Amharic sentence delimiters
            delimiters = ["።", "!", "?", "፡፡"]
        else:
            delimiters = [".", "!", "?"]
            
        sentences = [content]
        for delimiter in delimiters:
            new_sentences = []
            for sentence in sentences:
                new_sentences.extend([s.strip() for s in sentence.split(delimiter) if s.strip()])
            sentences = new_sentences
            
        return [s for s in sentences if len(s.strip()) > 10]
        
    def _score_sentence(self, sentence: str, full_content: str, position: int, total: int) -> float:
        """Score a sentence for extractive summarization."""
        score = 0.0
        
        # Position score (first and last sentences often important)
        if position < 2 or position >= total - 2:
            score += 0.3
            
        # Length score (moderate length preferred)
        length = len(sentence.split())
        if 10 <= length <= 30:
            score += 0.2
            
        # Keyword frequency (words that appear multiple times in document)
        words = sentence.lower().split()
        content_words = full_content.lower().split()
        word_freq = {}
        for word in content_words:
            word_freq[word] = word_freq.get(word, 0) + 1
            
        for word in words:
            if word_freq.get(word, 0) > 2:
                score += 0.1
                
        # Amharic-specific scoring
        if any(char in sentence for char in "ሀሁሂሃሄህሆ"):  # Contains Amharic text
            score += 0.2
            
        return min(score, 1.0)
        
    def _extract_keywords(self, content: str, language: str, max_keywords: int = 20) -> List[str]:
        """Extract keywords from content."""
        words = content.lower().split()
        
        # Remove common stop words
        if language == "amh":
            stop_words = {"እና", "ወይም", "ለ", "በ", "ከ", "ወደ", "አለ", "ነው", "ነበር", "ይህ", "ያ"}
        else:
            stop_words = {"the", "and", "or", "for", "in", "on", "at", "to", "of", "with"}
            
        # Count word frequency
        word_freq = {}
        for word in words:
            if word not in stop_words and len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1
                
        # Sort by frequency and return top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:max_keywords]]
        
    def _apply_amharic_abstraction(self, summary: str) -> str:
        """Apply basic abstractive techniques for Amharic."""
        # Simple transformations for Amharic text
        transformations = {
            "የሚሆነው": "ይሆናል",
            "የሚገኘው": "ይገኛል", 
            "የሚያስችለው": "ያስችላል"
        }
        
        for old, new in transformations.items():
            summary = summary.replace(old, new)
            
        return summary
        
    def _create_amharic_keyword_summary(self, keywords: List[str], content: str) -> str:
        """Create Amharic summary from keywords."""
        if len(keywords) < 3:
            return content[:200] + "..." if len(content) > 200 else content
            
        # Create contextual summary using keywords
        summary_parts = []
        
        # Find sentences containing multiple keywords
        sentences = self._split_sentences(content, "amh")
        for sentence in sentences:
            keyword_count = sum(1 for keyword in keywords[:5] if keyword in sentence.lower())
            if keyword_count >= 2:
                summary_parts.append(sentence)
                if len(" ".join(summary_parts)) > 300:
                    break
                    
        if not summary_parts:
            return f"ዋና ነጥቦች፦ {', '.join(keywords[:5])}"
            
        return " ".join(summary_parts)
        
    def _select_best_summary(self, summaries: Dict[str, Any]) -> Dict[str, Any]:
        """Select the best summary from multiple types."""
        best_summary = None
        best_score = 0.0
        
        for summary_type, summary_data in summaries.items():
            if "error" in summary_data:
                continue
                
            score = summary_data.get("confidence", 0.0)
            
            # Prefer extractive for reliability
            if summary_type == "extractive":
                score += 0.1
                
            if score > best_score:
                best_score = score
                best_summary = summary_data
                
        return best_summary or {"summary": "Summary generation failed", "confidence": 0.0}
        
    async def _evaluate_summary_quality(
        self,
        original: str,
        summary: str,
        language: str
    ) -> float:
        """Evaluate summary quality using various metrics."""
        score = 0.0
        
        # Length ratio check
        ratio = len(summary) / len(original)
        if 0.1 <= ratio <= 0.3:  # Good compression ratio
            score += 0.3
        elif ratio < 0.1:
            score += 0.1  # Too compressed
        else:
            score += 0.0  # Not compressed enough
            
        # Keyword coverage
        original_keywords = set(self._extract_keywords(original, language, 10))
        summary_keywords = set(self._extract_keywords(summary, language, 10))
        
        if original_keywords:
            keyword_coverage = len(summary_keywords.intersection(original_keywords)) / len(original_keywords)
            score += keyword_coverage * 0.4
            
        # Readability (simple heuristic)
        avg_sentence_length = len(summary.split()) / max(len(self._split_sentences(summary, language)), 1)
        if 8 <= avg_sentence_length <= 20:  # Optimal sentence length
            score += 0.3
            
        return min(score, 1.0)
        
    def _get_cache_key(self, document_id: UUID, content: str, summary_type: str) -> str:
        """Generate cache key for summary."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"summary:{document_id}:{content_hash}:{summary_type}"
        
    async def _get_cached_summary(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve summary from cache."""
        try:
            cached_data = await self.redis_client.get(cache_key)
            if cached_data:
                import json
                summary = json.loads(cached_data)
                summary["cached"] = True
                return summary
        except Exception as e:
            logger.warning(f"Failed to retrieve cached summary: {e}")
            
        return None
        
    async def _cache_summary(self, cache_key: str, summary: Dict[str, Any]) -> None:
        """Cache summary result."""
        try:
            import json
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(summary, ensure_ascii=False)
            )
        except Exception as e:
            logger.warning(f"Failed to cache summary: {e}")
            
    async def close(self) -> None:
        """Close Redis connection."""
        await self.redis_client.close()


# Global summarization service instance
_summarization_service: Optional[SummarizationService] = None


def get_summarization_service(settings: Settings) -> SummarizationService:
    """Get the global summarization service instance."""
    global _summarization_service
    if _summarization_service is None:
        _summarization_service = SummarizationService(settings)
    return _summarization_service