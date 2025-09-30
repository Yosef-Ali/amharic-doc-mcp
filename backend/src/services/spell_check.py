"""
Amharic Spell Checking Service

Provides spell checking functionality for Amharic text with dictionary validation,
confidence scoring, and correction suggestions.
"""

from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import re
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class CorrectionConfidence(str, Enum):
    """Confidence levels for spell correction suggestions"""
    HIGH = "high"  # >90% confidence
    MEDIUM = "medium"  # 70-90% confidence
    LOW = "low"  # <70% confidence


@dataclass
class SpellCheckResult:
    """Result of spell checking a word or text"""
    original_text: str
    is_correct: bool
    confidence_score: float
    suggestions: List['CorrectionSuggestion']
    errors: List['SpellingError']
    corrected_text: Optional[str] = None


@dataclass
class CorrectionSuggestion:
    """A suggested correction for a misspelled word"""
    word: str
    confidence: CorrectionConfidence
    edit_distance: int
    frequency_score: float
    context_score: float


@dataclass
class SpellingError:
    """Details about a spelling error"""
    word: str
    position: int
    length: int
    error_type: str  # 'unknown', 'typo', 'grammar'
    suggestions: List[CorrectionSuggestion]


class AmharicSpellChecker:
    """
    Amharic spell checking service with dictionary-based validation.

    Features:
    - Dictionary lookup for word validation
    - Edit distance calculation for suggestions
    - Context-aware correction ranking
    - Confidence scoring
    - Support for Amharic-specific character variations
    """

    def __init__(
        self,
        dictionary_path: Optional[str] = None,
        custom_words: Optional[Set[str]] = None,
        max_suggestions: int = 5,
        min_confidence: float = 0.5
    ):
        """
        Initialize the Amharic spell checker.

        Args:
            dictionary_path: Path to Amharic dictionary file (one word per line)
            custom_words: Additional custom words to include in dictionary
            max_suggestions: Maximum number of correction suggestions per error
            min_confidence: Minimum confidence threshold for suggestions
        """
        self.max_suggestions = max_suggestions
        self.min_confidence = min_confidence

        # Load dictionary
        self.dictionary: Set[str] = set()
        self.word_frequencies: Dict[str, float] = {}

        if dictionary_path:
            self._load_dictionary(dictionary_path)
        else:
            self._load_default_dictionary()

        if custom_words:
            self.dictionary.update(custom_words)

        # Amharic-specific character mappings for normalization
        self.char_variations = self._build_character_variations()

        logger.info(
            f"Initialized AmharicSpellChecker with {len(self.dictionary)} words"
        )

    def _load_dictionary(self, path: str) -> None:
        """Load dictionary from file"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip()
                    if word and self._is_amharic(word):
                        self.dictionary.add(word)
                        # Assign frequency based on position (earlier = more common)
                        self.word_frequencies[word] = 1.0 / (len(self.dictionary) + 1)
        except FileNotFoundError:
            logger.warning(f"Dictionary file not found: {path}, using default")
            self._load_default_dictionary()

    def _load_default_dictionary(self) -> None:
        """Load a minimal default Amharic dictionary"""
        # Common Amharic words (this should be expanded significantly)
        default_words = {
            # Common words
            "እና", "ወይም", "ነው", "ናቸው", "ነበር", "ነበረ", "ይሆናል", "ይሆናሉ",
            # Pronouns
            "እኔ", "አንተ", "አንቺ", "እሱ", "እሷ", "እኛ", "እናንተ", "እነሱ",
            # Common verbs
            "መጣ", "ሄደ", "አለ", "ሆነ", "ሰጠ", "ወሰደ", "አየ", "ሰማ",
            # Numbers
            "አንድ", "ሁለት", "ሦስት", "አራት", "አምስት", "ስድስት", "ሰባት", "ስምንት", "ዘጠኝ", "አስር",
            # Time words
            "ዛሬ", "ትናንት", "ነገ", "አሁን", "ጠዋት", "ማታ", "ቀን", "ሌሊት",
            # Places
            "ኢትዮጵያ", "አዲስ", "አበባ", "አማራ", "ትግራይ", "ኦሮሚያ",
            # Religious terms
            "እግዚአብሔር", "ቤተክርስቲያን", "ገዳም", "ቄስ", "ጸሎት", "ጾም",
        }

        for word in default_words:
            self.dictionary.add(word)
            self.word_frequencies[word] = 0.8  # High frequency for common words

        logger.info(f"Loaded default dictionary with {len(default_words)} words")

    def _build_character_variations(self) -> Dict[str, List[str]]:
        """
        Build Amharic character variation mappings.

        Ethiopic script has multiple forms for some sounds (e.g., ሀ/ሐ/ኀ).
        This helps identify possible alternate spellings.
        """
        return {
            # H sounds
            'ሀ': ['ሐ', 'ኀ', 'ሃ', 'ሓ', 'ኃ'],
            'ሐ': ['ሀ', 'ኀ', 'ሓ', 'ሃ', 'ኃ'],
            'ኀ': ['ሀ', 'ሐ', 'ኃ', 'ሃ', 'ሓ'],

            # S sounds
            'ሰ': ['ሠ', 'ሳ', 'ሣ'],
            'ሠ': ['ሰ', 'ሣ', 'ሳ'],

            # A sounds
            'አ': ['ዓ', 'ኣ'],
            'ዓ': ['አ', 'ኣ'],

            # Tsadhe sounds
            'ጸ': ['ፀ', 'ጻ', 'ፃ'],
            'ፀ': ['ጸ', 'ፃ', 'ጻ'],
        }

    def _is_amharic(self, text: str) -> bool:
        """Check if text contains Amharic characters"""
        # Ethiopic Unicode range: U+1200 to U+137F
        amharic_pattern = re.compile(r'[\u1200-\u137F]+')
        return bool(amharic_pattern.search(text))

    def _normalize_amharic(self, word: str) -> str:
        """Normalize Amharic word by handling character variations"""
        # Remove common punctuation
        word = word.strip('።፣፤፥፦፧፨')
        return word

    def _tokenize(self, text: str) -> List[Tuple[str, int]]:
        """
        Tokenize Amharic text into words with positions.

        Returns:
            List of (word, position) tuples
        """
        # Amharic word boundary pattern
        pattern = r'[\u1200-\u137F]+(?:[-\u1200-\u137F]*[\u1200-\u137F]+)*'

        tokens = []
        for match in re.finditer(pattern, text):
            word = match.group(0)
            position = match.start()
            tokens.append((word, position))

        return tokens

    def check_word(self, word: str) -> SpellCheckResult:
        """
        Check if a single word is spelled correctly.

        Args:
            word: The word to check

        Returns:
            SpellCheckResult with validation and suggestions
        """
        normalized = self._normalize_amharic(word)

        # Check if word is in dictionary
        is_correct = normalized in self.dictionary

        if is_correct:
            return SpellCheckResult(
                original_text=word,
                is_correct=True,
                confidence_score=1.0,
                suggestions=[],
                errors=[],
                corrected_text=word
            )

        # Word not found, generate suggestions
        suggestions = self._generate_suggestions(normalized)

        error = SpellingError(
            word=word,
            position=0,
            length=len(word),
            error_type='unknown' if not suggestions else 'typo',
            suggestions=suggestions
        )

        # Calculate confidence score (inverse of edit distance to best suggestion)
        confidence = 0.0
        if suggestions:
            best_distance = suggestions[0].edit_distance
            confidence = max(0.0, 1.0 - (best_distance / len(word)))

        return SpellCheckResult(
            original_text=word,
            is_correct=False,
            confidence_score=confidence,
            suggestions=suggestions,
            errors=[error],
            corrected_text=suggestions[0].word if suggestions else None
        )

    def check_text(self, text: str, auto_correct: bool = False) -> SpellCheckResult:
        """
        Check spelling of entire text.

        Args:
            text: The text to check
            auto_correct: If True, automatically apply highest-confidence corrections

        Returns:
            SpellCheckResult with all errors and suggestions
        """
        tokens = self._tokenize(text)
        errors = []
        corrected_text = text

        # Check each word
        for word, position in tokens:
            word_result = self.check_word(word)

            if not word_result.is_correct and word_result.errors:
                error = word_result.errors[0]
                error.position = position
                errors.append(error)

                # Apply auto-correction if enabled
                if auto_correct and word_result.corrected_text:
                    corrected_text = corrected_text.replace(
                        word,
                        word_result.corrected_text,
                        1
                    )

        # Calculate overall confidence
        if not tokens:
            confidence = 1.0
        else:
            correct_words = len(tokens) - len(errors)
            confidence = correct_words / len(tokens)

        return SpellCheckResult(
            original_text=text,
            is_correct=len(errors) == 0,
            confidence_score=confidence,
            suggestions=[],
            errors=errors,
            corrected_text=corrected_text if auto_correct else None
        )

    def _generate_suggestions(self, word: str) -> List[CorrectionSuggestion]:
        """
        Generate correction suggestions for a misspelled word.

        Uses edit distance and frequency scoring to rank suggestions.
        """
        suggestions = []

        # Calculate edit distance to all dictionary words
        candidates = []
        for dict_word in self.dictionary:
            distance = self._edit_distance(word, dict_word)

            # Only consider words within reasonable edit distance
            max_distance = max(2, len(word) // 3)
            if distance <= max_distance:
                frequency = self.word_frequencies.get(dict_word, 0.1)

                # Score combines edit distance and frequency
                # Lower distance and higher frequency = better score
                score = (1.0 / (distance + 1)) * (frequency + 0.1)

                candidates.append((dict_word, distance, frequency, score))

        # Sort by score (descending)
        candidates.sort(key=lambda x: x[3], reverse=True)

        # Convert top candidates to CorrectionSuggestion objects
        for dict_word, distance, frequency, score in candidates[:self.max_suggestions]:
            # Determine confidence level
            if score > 0.9:
                confidence = CorrectionConfidence.HIGH
            elif score > 0.7:
                confidence = CorrectionConfidence.MEDIUM
            else:
                confidence = CorrectionConfidence.LOW

            suggestion = CorrectionSuggestion(
                word=dict_word,
                confidence=confidence,
                edit_distance=distance,
                frequency_score=frequency,
                context_score=score
            )

            # Filter by minimum confidence
            if score >= self.min_confidence:
                suggestions.append(suggestion)

        return suggestions

    def _edit_distance(self, word1: str, word2: str) -> int:
        """
        Calculate Levenshtein edit distance between two words.

        Considers character variations specific to Amharic.
        """
        m, n = len(word1), len(word2)

        # Create DP table
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        # Initialize base cases
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        # Fill DP table
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if word1[i-1] == word2[j-1]:
                    cost = 0
                else:
                    # Check if characters are variations of each other
                    cost = 0.5 if self._are_variations(word1[i-1], word2[j-1]) else 1

                dp[i][j] = min(
                    dp[i-1][j] + 1,      # deletion
                    dp[i][j-1] + 1,      # insertion
                    dp[i-1][j-1] + cost  # substitution
                )

        return int(dp[m][n])

    def _are_variations(self, char1: str, char2: str) -> bool:
        """Check if two characters are Amharic variations of each other"""
        if char1 in self.char_variations:
            return char2 in self.char_variations[char1]
        if char2 in self.char_variations:
            return char1 in self.char_variations[char2]
        return False

    def add_to_dictionary(self, word: str, frequency: float = 0.5) -> None:
        """
        Add a word to the custom dictionary.

        Args:
            word: Word to add
            frequency: Frequency score (0.0 to 1.0)
        """
        normalized = self._normalize_amharic(word)
        self.dictionary.add(normalized)
        self.word_frequencies[normalized] = frequency
        logger.debug(f"Added word to dictionary: {normalized}")

    def remove_from_dictionary(self, word: str) -> None:
        """Remove a word from the custom dictionary"""
        normalized = self._normalize_amharic(word)
        self.dictionary.discard(normalized)
        self.word_frequencies.pop(normalized, None)
        logger.debug(f"Removed word from dictionary: {normalized}")

    def get_statistics(self) -> Dict[str, any]:
        """Get spell checker statistics"""
        return {
            "dictionary_size": len(self.dictionary),
            "max_suggestions": self.max_suggestions,
            "min_confidence": self.min_confidence,
            "character_variations": len(self.char_variations)
        }


# Module-level instance for easy import
_default_checker: Optional[AmharicSpellChecker] = None


def get_spell_checker() -> AmharicSpellChecker:
    """Get or create the default spell checker instance"""
    global _default_checker
    if _default_checker is None:
        _default_checker = AmharicSpellChecker()
    return _default_checker


# Convenience functions
def check_word(word: str) -> SpellCheckResult:
    """Check spelling of a single word"""
    return get_spell_checker().check_word(word)


def check_text(text: str, auto_correct: bool = False) -> SpellCheckResult:
    """Check spelling of entire text"""
    return get_spell_checker().check_text(text, auto_correct=auto_correct)