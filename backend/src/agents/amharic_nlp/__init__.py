"""Amharic NLP agent for processing Ethiopian text."""

from __future__ import annotations

import logging
import re
from typing import Dict, Any, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ...config.settings import Settings

logger = logging.getLogger(__name__)


class AmharicNLPAgent:
    """Agent specialized in Amharic natural language processing."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        
        # Amharic-specific patterns and vocabularies
        self.amharic_range = (0x1200, 0x137F)
        self.common_stop_words = {
            "እና", "ወይም", "ለ", "በ", "ከ", "ወደ", "አለ", "ነው", "ነበር", 
            "ይህ", "ያ", "እዚህ", "እዚያ", "ይህን", "ያን", "መሆን", "ሆነ"
        }
        
        # Ethiopian entity patterns (simplified)
        self.name_patterns = [
            r'[ሀ-ሆ][ሀ-ሆ][ሀ-ሆ]+',  # Simple name pattern
            r'አቶ\s+[ሀ-ሆ]+',  # Mr. + name
            r'ወ/ሮ\s+[ሀ-ሆ]+',  # Mrs. + name
        ]
        
        self.place_indicators = {
            "አዲስ", "ከተማ", "ዞን", "ወረዳ", "ቀበሌ", "ክፍለ", "ግንድ", "ባህር"
        }
        
    async def process_amharic_text(
        self,
        session: AsyncSession,
        text: str,
        document_id: UUID,
        analysis_type: str = "full"
    ) -> Dict[str, Any]:
        """Process Amharic text for various NLP tasks."""
        try:
            logger.info(f"Starting Amharic NLP processing for document {document_id}")
            
            result = {
                "success": True,
                "document_id": str(document_id),
                "text_length": len(text),
                "analysis_type": analysis_type,
                "language_detection": self._detect_language(text),
                "text_statistics": self._calculate_text_statistics(text)
            }
            
            if analysis_type in ["full", "entities"]:
                result["named_entities"] = await self._extract_named_entities(text)
                
            if analysis_type in ["full", "summary"]:
                result["text_summary"] = await self._generate_summary(text)
                
            if analysis_type in ["full", "morphology"]:
                result["morphological_analysis"] = await self._analyze_morphology(text)
                
            if analysis_type in ["full", "spell_check"]:
                result["spell_check"] = await self._spell_check(text)
                
            logger.info(f"Amharic NLP processing completed for document {document_id}")
            return result
            
        except Exception as e:
            logger.error(f"Amharic NLP processing failed for document {document_id}: {e}")
            return {"success": False, "error": str(e)}
            
    def _detect_language(self, text: str) -> Dict[str, Any]:
        """Detect if text contains Amharic and estimate language distribution."""
        total_chars = len(text)
        if total_chars == 0:
            return {"primary_language": "unknown", "confidence": 0.0}
            
        amharic_chars = sum(
            1 for char in text 
            if self.amharic_range[0] <= ord(char) <= self.amharic_range[1]
        )
        
        ascii_chars = sum(1 for char in text if char.isascii() and char.isalpha())
        
        amharic_ratio = amharic_chars / total_chars
        ascii_ratio = ascii_chars / total_chars
        
        if amharic_ratio > 0.3:
            primary_language = "amharic"
            confidence = min(amharic_ratio * 2, 1.0)
        elif ascii_ratio > 0.5:
            primary_language = "english"
            confidence = min(ascii_ratio * 1.5, 1.0)
        else:
            primary_language = "mixed"
            confidence = 0.6
            
        return {
            "primary_language": primary_language,
            "confidence": round(confidence, 2),
            "amharic_ratio": round(amharic_ratio, 2),
            "ascii_ratio": round(ascii_ratio, 2),
            "character_distribution": {
                "amharic": amharic_chars,
                "ascii": ascii_chars,
                "other": total_chars - amharic_chars - ascii_chars
            }
        }
        
    def _calculate_text_statistics(self, text: str) -> Dict[str, Any]:
        """Calculate basic text statistics."""
        words = text.split()
        sentences = re.split(r'[።!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Count Amharic words
        amharic_words = [
            word for word in words 
            if any(self.amharic_range[0] <= ord(char) <= self.amharic_range[1] for char in word)
        ]
        
        return {
            "total_characters": len(text),
            "total_words": len(words),
            "total_sentences": len(sentences),
            "amharic_words": len(amharic_words),
            "average_word_length": round(sum(len(word) for word in words) / len(words), 2) if words else 0,
            "average_sentence_length": round(sum(len(sent.split()) for sent in sentences) / len(sentences), 2) if sentences else 0
        }
        
    async def _extract_named_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from Amharic text."""
        entities = []
        
        # Person names (simplified pattern matching)
        for pattern in self.name_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                entities.append({
                    "text": match.group(),
                    "label": "PERSON",
                    "start": match.start(),
                    "end": match.end(),
                    "confidence": 0.7
                })
                
        # Places (based on indicators)
        words = text.split()
        for i, word in enumerate(words):
            if any(indicator in word for indicator in self.place_indicators):
                # Look for potential place names around indicators
                start_idx = max(0, i - 1)
                end_idx = min(len(words), i + 2)
                place_candidate = " ".join(words[start_idx:end_idx])
                
                entities.append({
                    "text": place_candidate,
                    "label": "LOCATION",
                    "start": text.find(place_candidate),
                    "end": text.find(place_candidate) + len(place_candidate),
                    "confidence": 0.6
                })
                
        # Organizations (simplified - look for common org indicators)
        org_indicators = ["ኩባንያ", "ድርጅት", "መንግስት", "ሚኒስቴር", "ቢሮ"]
        for indicator in org_indicators:
            if indicator in text:
                # Find context around organization indicator
                words = text.split()
                for i, word in enumerate(words):
                    if indicator in word:
                        start_idx = max(0, i - 2)
                        end_idx = min(len(words), i + 1)
                        org_candidate = " ".join(words[start_idx:end_idx])
                        
                        entities.append({
                            "text": org_candidate,
                            "label": "ORGANIZATION",
                            "start": text.find(org_candidate),
                            "end": text.find(org_candidate) + len(org_candidate),
                            "confidence": 0.5
                        })
                        
        # Remove duplicates and sort by position
        unique_entities = []
        seen_texts = set()
        for entity in entities:
            if entity["text"] not in seen_texts:
                seen_texts.add(entity["text"])
                unique_entities.append(entity)
                
        return sorted(unique_entities, key=lambda x: x["start"])
        
    async def _generate_summary(self, text: str) -> Dict[str, Any]:
        """Generate a summary of the Amharic text."""
        sentences = re.split(r'[።!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 2:
            return {
                "summary": text[:200] + "..." if len(text) > 200 else text,
                "method": "truncation",
                "sentence_count": len(sentences),
                "compression_ratio": 1.0
            }
            
        # Simple extractive summarization
        # Score sentences based on word frequency
        words = text.lower().split()
        word_freq = {}
        for word in words:
            if word not in self.common_stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
                
        # Score sentences
        sentence_scores = []
        for sentence in sentences:
            score = 0
            sentence_words = sentence.lower().split()
            for word in sentence_words:
                score += word_freq.get(word, 0)
            if sentence_words:
                score = score / len(sentence_words)
            sentence_scores.append((score, sentence))
            
        # Select top sentences
        sentence_scores.sort(reverse=True)
        top_sentences = [sent for _, sent in sentence_scores[:min(3, len(sentences) // 2)]]
        
        summary = " ".join(top_sentences)
        compression_ratio = len(summary) / len(text)
        
        return {
            "summary": summary,
            "method": "extractive",
            "sentence_count": len(top_sentences),
            "compression_ratio": round(compression_ratio, 2)
        }
        
    async def _analyze_morphology(self, text: str) -> Dict[str, Any]:
        """Basic morphological analysis for Amharic text."""
        words = text.split()
        amharic_words = [
            word for word in words 
            if any(self.amharic_range[0] <= ord(char) <= self.amharic_range[1] for char in word)
        ]
        
        # Simple morphological patterns
        prefixes = {"የ", "ለ", "በ", "ከ", "እ", "ስ", "ም", "ት"}
        suffixes = {"ን", "ም", "ው", "ዋ", "ች", "ዎች", "ና", "ኝ"}
        
        morphology_stats = {
            "total_amharic_words": len(amharic_words),
            "words_with_prefixes": 0,
            "words_with_suffixes": 0,
            "common_patterns": {}
        }
        
        for word in amharic_words[:100]:  # Analyze first 100 words
            # Check prefixes
            if any(word.startswith(prefix) for prefix in prefixes):
                morphology_stats["words_with_prefixes"] += 1
                
            # Check suffixes
            if any(word.endswith(suffix) for suffix in suffixes):
                morphology_stats["words_with_suffixes"] += 1
                
        return morphology_stats
        
    async def _spell_check(self, text: str) -> Dict[str, Any]:
        """Basic spell checking for Amharic text."""
        words = text.split()
        amharic_words = [
            word for word in words 
            if any(self.amharic_range[0] <= ord(char) <= self.amharic_range[1] for char in word)
        ]
        
        # Simplified spell checking based on character patterns
        suspicious_words = []
        
        for word in amharic_words:
            # Check for unusual character combinations
            if len(word) > 15:  # Very long words might be OCR errors
                suspicious_words.append({
                    "word": word,
                    "issue": "unusually_long",
                    "suggestion": word[:10] + "..."
                })
            elif len(word) == 1 and word in "ሀሁሂሃሄህሆ":
                # Single characters that might be OCR artifacts
                suspicious_words.append({
                    "word": word,
                    "issue": "isolated_character",
                    "suggestion": None
                })
                
        return {
            "total_words_checked": len(amharic_words),
            "suspicious_words": suspicious_words,
            "confidence": 0.7,  # Basic spell checker confidence
            "suggestions_available": len([w for w in suspicious_words if w.get("suggestion")])
        }


_amharic_nlp_agent: Optional[AmharicNLPAgent] = None

def get_amharic_nlp_agent(settings: Settings) -> AmharicNLPAgent:
    global _amharic_nlp_agent
    if _amharic_nlp_agent is None:
        _amharic_nlp_agent = AmharicNLPAgent(settings)
    return _amharic_nlp_agent