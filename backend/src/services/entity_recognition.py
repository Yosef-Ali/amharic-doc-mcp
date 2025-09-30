"""
Ethiopian Entity Recognition Service

Extracts and classifies named entities from Amharic text including:
- Ethiopian names (personal, family, traditional)
- Ethiopian places (regions, cities, landmarks)
- Ethiopian organizations (government, religious, business)
- Dates and times (Gregorian and Ethiopian calendar)
- Ethiopian-specific entities (titles, honorifics, ethnic groups)

Targets >90% precision threshold for entity recognition.
"""

from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """Types of named entities recognized"""
    PERSON = "PERSON"  # Personal names
    LOCATION = "LOCATION"  # Places, cities, regions
    ORGANIZATION = "ORGANIZATION"  # Companies, institutions
    DATE = "DATE"  # Dates and times
    TITLE = "TITLE"  # Honorifics and titles
    ETHNIC_GROUP = "ETHNIC_GROUP"  # Ethiopian ethnic groups
    RELIGIOUS_TERM = "RELIGIOUS_TERM"  # Religious references
    EVENT = "EVENT"  # Historical events, festivals
    MONETARY = "MONETARY"  # Currency amounts
    NUMBER = "NUMBER"  # Numerical values


@dataclass
class Entity:
    """A recognized named entity"""
    text: str
    entity_type: EntityType
    start_position: int
    end_position: int
    confidence: float
    metadata: Dict[str, any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class EntityRecognitionResult:
    """Result of entity recognition on text"""
    text: str
    entities: List[Entity]
    precision: float
    entity_counts: Dict[EntityType, int]


class EthiopianEntityRecognizer:
    """
    Named Entity Recognition service for Ethiopian/Amharic text.

    Features:
    - Pattern-based recognition for Ethiopian names, places, organizations
    - Rule-based classification with confidence scoring
    - Context-aware entity disambiguation
    - Support for Ethiopian-specific entity types
    - >90% precision target through conservative classification
    """

    def __init__(
        self,
        min_confidence: float = 0.9,
        enable_disambiguation: bool = True
    ):
        """
        Initialize the Ethiopian entity recognizer.

        Args:
            min_confidence: Minimum confidence threshold (default 0.9 for >90% precision)
            enable_disambiguation: Enable context-based entity disambiguation
        """
        self.min_confidence = min_confidence
        self.enable_disambiguation = enable_disambiguation

        # Load entity databases
        self.person_names = self._load_person_names()
        self.place_names = self._load_place_names()
        self.organization_names = self._load_organization_names()
        self.titles = self._load_titles()
        self.ethnic_groups = self._load_ethnic_groups()
        self.religious_terms = self._load_religious_terms()

        # Compile recognition patterns
        self.patterns = self._compile_patterns()

        logger.info(
            f"Initialized EthiopianEntityRecognizer with "
            f"min_confidence={min_confidence}"
        )

    def _load_person_names(self) -> Dict[str, Set[str]]:
        """Load Ethiopian personal name database"""
        return {
            'first_names': {
                # Common Ethiopian first names
                'አበበ', 'ተስፋዬ', 'ግርማ', 'ህይወት', 'ብርሃኔ', 'ደሴ', 'መስፍን',
                'ታደሰ', 'ዮሐንስ', 'ገብረ', 'ወልደ', 'ሃይሉ', 'ካሳ', 'ተክለ',
                'እሸቱ', 'አስተር', 'ብሩክ', 'ሳራ', 'ሄለን', 'ረሃና', 'ፀሀይ',
                'ሙሉጌታ', 'አዲስ', 'ክብረት', 'ልደቱ', 'መኮነን', 'ደረጄ',
                # Religious names
                'ገብርኤል', 'ሚካኤል', 'ራፋኤል', 'ዑራኤል', 'ማርያም', 'ዳዊት',
            },
            'prefixes': {
                'ገብረ', 'ወልደ', 'ተስፋ', 'ታደሰ', 'አበበ', 'ታፈሰ', 'ካሳ',
                'ሃይለ', 'በላይ', 'መለስ', 'ፀጋ', 'አለማየሁ', 'ይመር'
            },
            'suffixes': {
                'ሥላሴ', 'ማርያም', 'ሚካኤል', 'ስላሴ', 'ገብረ', 'ወልድ', 'ሥላሴ'
            }
        }

    def _load_place_names(self) -> Set[str]:
        """Load Ethiopian place names"""
        return {
            # Major cities
            'አዲስ', 'አበባ', 'አዲስአበባ', 'ድሬዳዋ', 'ባህርዳር', 'ጎንደር', 'መቀሌ',
            'ሀዋሳ', 'ጅማ', 'አዋሳ', 'አርባምንጭ', 'ዴብረዘይት', 'ደሴ', 'ሼኔ',
            'አሶሳ', 'ሐረር', 'ጋምቤላ', 'ሶማሌ', 'አድዋ', 'አክሱም', 'ላሊበላ',

            # Regions
            'ኦሮሚያ', 'አማራ', 'ትግራይ', 'ደቡብ', 'ብኔሻንጉል', 'አፋር', 'ሶማሊ',
            'ጋምቤላ', 'ሐረሪ', 'ቤንሻንጉል', 'ሲዳማ', 'ደቡብምዕራብ',

            # Historical places
            'አክሱም', 'ጎንዳር', 'ላሊበላ', 'አድዋ', 'መቀለ', 'አንኮበር',

            # Natural features
            'ታናሐይቅ', 'አባይ', 'አዋሽ', 'ኦሞ', 'ባሌ', 'ሰሜን', 'ስሜን',
        }

    def _load_organization_names(self) -> Dict[str, Set[str]]:
        """Load Ethiopian organization names and patterns"""
        return {
            'keywords': {
                'ሚኒስቴር', 'ቤተመንግሥት', 'ባንክ', 'ዩኒቨርሲቲ', 'ኮሌጅ',
                'ሆስፒታል', 'ቤተክርስቲያን', 'መስጊድ', 'ገደለ', 'ድርጅት',
                'ማህበር', 'ኩባንያ', 'ፋብሪካ', 'ትምህርትቤት', 'ድርጅት'
            },
            'prefixes': {
                'የኢትዮጵያ', 'የአዲስ', 'የአፍሪካ', 'የአማራ', 'የትግራይ', 'የኦሮሚያ'
            }
        }

    def _load_titles(self) -> Set[str]:
        """Load Ethiopian titles and honorifics"""
        return {
            # Traditional titles
            'ልጅ', 'ራስ', 'ደጃዝማች', 'ፊታውራሪ', 'ገራዝማች', 'ባላምባራስ',
            'ጽንጸይ', 'ንጉሠ', 'ንግሥት', 'ጃንሆይ', 'መንግስቱ', 'መኮንን',

            # Modern titles
            'ዶክተር', 'ፕሮፌሰር', 'አቶ', 'ወ', 'ወይዘሮ', 'ወ/', 'ዶ/', 'ፕ/',
            'ጄነራል', 'ኮለኔል', 'ሜጀር', 'ካፒቴን', 'ሊቀመንበር',

            # Religious titles
            'አቡነ', 'ወ', 'እመቤታችን', 'ቅዱስ', 'አባ', 'ሊቀ', 'መምህር',
            'ገቢነ', 'ዲያቆን', 'ቀሲስ', 'ሊቀካህናት', 'አርከ', 'ኤጲስ',
        }

    def _load_ethnic_groups(self) -> Set[str]:
        """Load Ethiopian ethnic group names"""
        return {
            'ኦሮሞ', 'አማራ', 'ትግራይ', 'ትግሬ', 'ሶማሌ', 'አፋር', 'ጉራጌ',
            'ሲዳማ', 'ወላይታ', 'ሀዲያ', 'ጋምቤላ', 'በንሻንጉል', 'ሐረሪ',
            'አርጎባ', 'ናሙ', 'ኮንሶ', 'ጌዴኦ', 'ካፊቾ', 'ሸኮ', 'መንነ',
        }

    def _load_religious_terms(self) -> Set[str]:
        """Load Ethiopian religious terminology"""
        return {
            # Orthodox Christian
            'እግዚአብሔር', 'ክርስቶስ', 'ማርያም', 'ቅዱስ', 'ቅድስት', 'ገብርኤል',
            'ሚካኤል', 'ራጉኤል', 'ዑራኤል', 'ሰላሴ', 'ተዋሕዶ', 'መስቀል',
            'ትንሳኤ', 'ፋሲካ', 'በዓል', 'ጾም', 'ሰኔበት', 'ሰንበት',

            # Islamic
            'አላህ', 'መሐመድ', 'መስጊድ', 'ቁርአን', 'ሱንና', 'ሐጅ', 'ረመዳን',

            # General religious
            'አምላክ', 'ዲን', 'እምነት', 'ሀይማኖት', 'ምእማን', 'ጸሎት',
        }

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for entity recognition"""
        return {
            # Ethiopian date pattern (e.g., "ጥር 15 ቀን 2016 ዓ.ም.")
            'ethiopian_date': re.compile(
                r'(መስከረም|ጥቅምት|ኅዳር|ታኅሣሥ|ጥር|የካቲት|መጋቢት|ሚያዝያ|ግንቦት|ሰኔ|ሐምሌ|ነሐሴ|ጳጉሜን)\s+\d{1,2}\s+ቀን\s+\d{4}\s+ዓ\.ም\.'
            ),

            # Gregorian date (numeric)
            'gregorian_date': re.compile(
                r'\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{1,2}-\d{1,2}'
            ),

            # Currency (Ethiopian Birr)
            'currency': re.compile(
                r'(?:\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:ብር|ETB)'
            ),

            # Numbers with Ethiopian separators
            'number': re.compile(
                r'\d+(?:,\d{3})*(?:\.\d+)?'
            ),

            # Full name pattern (Title + First + Last)
            'full_name': re.compile(
                r'(?:ዶክተር|አቶ|ወይዘሮ|አቡነ|ገብረ|ወልደ)?\s*[\u1200-\u137F]+\s+[\u1200-\u137F]+'
            ),
        }

    def recognize_entities(self, text: str) -> EntityRecognitionResult:
        """
        Recognize named entities in Amharic text.

        Args:
            text: Input text to analyze

        Returns:
            EntityRecognitionResult with all recognized entities
        """
        entities = []

        # Apply each recognition method
        entities.extend(self._recognize_persons(text))
        entities.extend(self._recognize_locations(text))
        entities.extend(self._recognize_organizations(text))
        entities.extend(self._recognize_dates(text))
        entities.extend(self._recognize_titles(text))
        entities.extend(self._recognize_ethnic_groups(text))
        entities.extend(self._recognize_religious_terms(text))
        entities.extend(self._recognize_monetary(text))

        # Remove overlapping entities (keep highest confidence)
        entities = self._resolve_overlaps(entities)

        # Apply disambiguation if enabled
        if self.enable_disambiguation:
            entities = self._disambiguate_entities(text, entities)

        # Filter by confidence threshold
        entities = [e for e in entities if e.confidence >= self.min_confidence]

        # Sort by position
        entities.sort(key=lambda e: e.start_position)

        # Calculate precision estimate
        precision = self._estimate_precision(entities)

        # Count entities by type
        entity_counts = defaultdict(int)
        for entity in entities:
            entity_counts[entity.entity_type] += 1

        return EntityRecognitionResult(
            text=text,
            entities=entities,
            precision=precision,
            entity_counts=dict(entity_counts)
        )

    def _recognize_persons(self, text: str) -> List[Entity]:
        """Recognize person names"""
        entities = []

        # Tokenize text
        words = self._tokenize(text)

        i = 0
        while i < len(words):
            word, start, end = words[i]

            # Check for title + name pattern
            if word in self.titles and i + 1 < len(words):
                next_word, next_start, next_end = words[i + 1]

                # Check if next word is a known name
                if next_word in self.person_names['first_names']:
                    # Check for full name (title + first + last)
                    if i + 2 < len(words):
                        last_word, last_start, last_end = words[i + 2]
                        full_name = f"{word} {next_word} {last_word}"

                        entities.append(Entity(
                            text=full_name,
                            entity_type=EntityType.PERSON,
                            start_position=start,
                            end_position=last_end,
                            confidence=0.95,
                            metadata={'has_title': True}
                        ))
                        i += 3
                        continue

            # Check for compound names (prefix + suffix pattern)
            if word in self.person_names['prefixes'] and i + 1 < len(words):
                next_word, next_start, next_end = words[i + 1]
                if next_word in self.person_names['suffixes']:
                    full_name = f"{word}{next_word}"

                    entities.append(Entity(
                        text=full_name,
                        entity_type=EntityType.PERSON,
                        start_position=start,
                        end_position=next_end,
                        confidence=0.92,
                        metadata={'name_type': 'compound'}
                    ))
                    i += 2
                    continue

            # Check single name
            if word in self.person_names['first_names']:
                entities.append(Entity(
                    text=word,
                    entity_type=EntityType.PERSON,
                    start_position=start,
                    end_position=end,
                    confidence=0.85,
                    metadata={'name_type': 'single'}
                ))

            i += 1

        return entities

    def _recognize_locations(self, text: str) -> List[Entity]:
        """Recognize place names"""
        entities = []

        words = self._tokenize(text)
        for word, start, end in words:
            if word in self.place_names:
                # Higher confidence for multi-word places
                confidence = 0.95 if ' ' in word else 0.90

                entities.append(Entity(
                    text=word,
                    entity_type=EntityType.LOCATION,
                    start_position=start,
                    end_position=end,
                    confidence=confidence
                ))

        return entities

    def _recognize_organizations(self, text: str) -> List[Entity]:
        """Recognize organization names"""
        entities = []

        words = self._tokenize(text)

        # Look for keyword-based organizations
        for i, (word, start, end) in enumerate(words):
            if word in self.organization_names['keywords']:
                # Check for prefix (e.g., "የኢትዮጵያ ባንክ")
                if i > 0:
                    prev_word, prev_start, _ = words[i - 1]
                    if prev_word in self.organization_names['prefixes']:
                        org_name = f"{prev_word} {word}"
                        entities.append(Entity(
                            text=org_name,
                            entity_type=EntityType.ORGANIZATION,
                            start_position=prev_start,
                            end_position=end,
                            confidence=0.93
                        ))
                        continue

                entities.append(Entity(
                    text=word,
                    entity_type=EntityType.ORGANIZATION,
                    start_position=start,
                    end_position=end,
                    confidence=0.88
                ))

        return entities

    def _recognize_dates(self, text: str) -> List[Entity]:
        """Recognize date expressions"""
        entities = []

        # Ethiopian calendar dates
        for match in self.patterns['ethiopian_date'].finditer(text):
            entities.append(Entity(
                text=match.group(0),
                entity_type=EntityType.DATE,
                start_position=match.start(),
                end_position=match.end(),
                confidence=0.98,
                metadata={'calendar': 'ethiopian'}
            ))

        # Gregorian dates
        for match in self.patterns['gregorian_date'].finditer(text):
            entities.append(Entity(
                text=match.group(0),
                entity_type=EntityType.DATE,
                start_position=match.start(),
                end_position=match.end(),
                confidence=0.95,
                metadata={'calendar': 'gregorian'}
            ))

        return entities

    def _recognize_titles(self, text: str) -> List[Entity]:
        """Recognize titles and honorifics"""
        entities = []

        words = self._tokenize(text)
        for word, start, end in words:
            if word in self.titles:
                entities.append(Entity(
                    text=word,
                    entity_type=EntityType.TITLE,
                    start_position=start,
                    end_position=end,
                    confidence=0.92
                ))

        return entities

    def _recognize_ethnic_groups(self, text: str) -> List[Entity]:
        """Recognize Ethiopian ethnic group names"""
        entities = []

        words = self._tokenize(text)
        for word, start, end in words:
            if word in self.ethnic_groups:
                entities.append(Entity(
                    text=word,
                    entity_type=EntityType.ETHNIC_GROUP,
                    start_position=start,
                    end_position=end,
                    confidence=0.91
                ))

        return entities

    def _recognize_religious_terms(self, text: str) -> List[Entity]:
        """Recognize religious terminology"""
        entities = []

        words = self._tokenize(text)
        for word, start, end in words:
            if word in self.religious_terms:
                entities.append(Entity(
                    text=word,
                    entity_type=EntityType.RELIGIOUS_TERM,
                    start_position=start,
                    end_position=end,
                    confidence=0.90
                ))

        return entities

    def _recognize_monetary(self, text: str) -> List[Entity]:
        """Recognize monetary amounts"""
        entities = []

        for match in self.patterns['currency'].finditer(text):
            entities.append(Entity(
                text=match.group(0),
                entity_type=EntityType.MONETARY,
                start_position=match.start(),
                end_position=match.end(),
                confidence=0.97
            ))

        return entities

    def _tokenize(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Tokenize text into words with positions.

        Returns:
            List of (word, start_pos, end_pos) tuples
        """
        pattern = r'[\u1200-\u137F]+(?:[-\u1200-\u137F\s]*[\u1200-\u137F]+)*'

        tokens = []
        for match in re.finditer(pattern, text):
            word = match.group(0).strip()
            if word:
                tokens.append((word, match.start(), match.end()))

        return tokens

    def _resolve_overlaps(self, entities: List[Entity]) -> List[Entity]:
        """
        Resolve overlapping entities by keeping highest confidence.
        """
        if not entities:
            return []

        # Sort by start position
        sorted_entities = sorted(entities, key=lambda e: e.start_position)

        result = []
        current = sorted_entities[0]

        for entity in sorted_entities[1:]:
            # Check for overlap
            if entity.start_position < current.end_position:
                # Keep entity with higher confidence
                if entity.confidence > current.confidence:
                    current = entity
            else:
                result.append(current)
                current = entity

        result.append(current)
        return result

    def _disambiguate_entities(
        self,
        text: str,
        entities: List[Entity]
    ) -> List[Entity]:
        """
        Apply context-based disambiguation to improve accuracy.

        For example, distinguishing between person names and place names
        based on surrounding context.
        """
        # Simple context-based boosting
        for entity in entities:
            # Check surrounding words for context clues
            start = max(0, entity.start_position - 50)
            end = min(len(text), entity.end_position + 50)
            context = text[start:end].lower()

            # Boost confidence for persons near title words
            if entity.entity_type == EntityType.PERSON:
                title_words = ['አቶ', 'ዶክተር', 'ወይዘሮ', 'ልጅ']
                if any(title in context for title in title_words):
                    entity.confidence = min(0.98, entity.confidence + 0.05)

            # Boost confidence for locations near direction/place indicators
            elif entity.entity_type == EntityType.LOCATION:
                place_indicators = ['ከተማ', 'ክልል', 'ቦታ', 'ወረዳ']
                if any(indicator in context for indicator in place_indicators):
                    entity.confidence = min(0.98, entity.confidence + 0.05)

        return entities

    def _estimate_precision(self, entities: List[Entity]) -> float:
        """
        Estimate overall precision based on entity confidences.
        """
        if not entities:
            return 1.0

        avg_confidence = sum(e.confidence for e in entities) / len(entities)
        return avg_confidence


# Module-level instance
_default_recognizer: Optional[EthiopianEntityRecognizer] = None


def get_entity_recognizer() -> EthiopianEntityRecognizer:
    """Get or create the default entity recognizer instance"""
    global _default_recognizer
    if _default_recognizer is None:
        _default_recognizer = EthiopianEntityRecognizer()
    return _default_recognizer


# Convenience function
def recognize_entities(text: str) -> EntityRecognitionResult:
    """Recognize named entities in text"""
    return get_entity_recognizer().recognize_entities(text)