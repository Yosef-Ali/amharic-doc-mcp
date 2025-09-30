"""
AI Provider Configuration

Primary: Gemini 2.5 (free API, best for Amharic)
Fallback: OpenRouter
MCP Client: Claude (for orchestration)
"""

import os
import logging
from typing import Optional, Dict, Any, List
from enum import Enum

import google.generativeai as genai
from openai import OpenAI

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """AI provider types"""
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    CLAUDE_MCP = "claude_mcp"


class GeminiProvider:
    """
    Gemini 2.5 Provider - Primary for Amharic OCR and Proofreading

    Free tier: 15 requests/minute, 1 million tokens/minute
    Best performance for Amharic language understanding
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini provider"""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')

        logger.info("Gemini 2.5 provider initialized")

    def ocr_image(self, image_path: str, language: str = "amh") -> Dict[str, Any]:
        """
        Perform OCR on image using Gemini Vision

        Args:
            image_path: Path to image file
            language: Language code (amh for Amharic)

        Returns:
            Dict with extracted text and confidence
        """
        try:
            # Upload image
            image_file = genai.upload_file(image_path)

            # Prompt optimized for Amharic OCR
            prompt = """Extract ALL text from this image accurately.

Rules:
- Preserve exact formatting and layout
- Include ALL Amharic (አማርኛ) text
- Maintain line breaks and spacing
- Output ONLY the extracted text, no explanations

Text:"""

            # Generate response
            response = self.model.generate_content([prompt, image_file])

            extracted_text = response.text.strip()

            # Gemini doesn't provide confidence, estimate based on response
            confidence = 0.95 if len(extracted_text) > 10 else 0.80

            return {
                "text": extracted_text,
                "confidence": confidence,
                "language": language,
                "provider": "gemini",
                "model": "gemini-2.0-flash-exp"
            }

        except Exception as e:
            logger.error(f"Gemini OCR failed: {e}")
            raise

    def proofread_amharic(self, text: str) -> Dict[str, Any]:
        """
        Proofread Amharic text using Gemini

        Args:
            text: Amharic text to proofread

        Returns:
            Dict with corrected text and suggestions
        """
        try:
            prompt = f"""Proofread this Amharic text and fix any errors.

Rules:
- Fix spelling mistakes
- Correct grammar errors
- Preserve original meaning
- Keep formatting
- Return ONLY the corrected text

Text to proofread:
{text}

Corrected text:"""

            response = self.model.generate_content(prompt)
            corrected_text = response.text.strip()

            return {
                "original": text,
                "corrected": corrected_text,
                "has_changes": text != corrected_text,
                "provider": "gemini"
            }

        except Exception as e:
            logger.error(f"Gemini proofreading failed: {e}")
            raise

    def extract_entities_amharic(self, text: str) -> List[Dict[str, str]]:
        """
        Extract named entities from Amharic text

        Args:
            text: Amharic text

        Returns:
            List of entities with type and text
        """
        try:
            prompt = f"""Extract named entities from this Amharic text.

Return JSON array with format: [{{"type": "PERSON/LOCATION/ORGANIZATION/DATE", "text": "entity"}}]

Text:
{text}

Entities (JSON only):"""

            response = self.model.generate_content(prompt)

            # Parse JSON response
            import json
            entities = json.loads(response.text.strip())

            return entities

        except Exception as e:
            logger.error(f"Entity extraction failed: {e}")
            return []

    def summarize_amharic(self, text: str, max_length: int = 200) -> str:
        """
        Summarize Amharic text

        Args:
            text: Amharic text to summarize
            max_length: Maximum summary length in characters

        Returns:
            Summarized text in Amharic
        """
        try:
            prompt = f"""Summarize this Amharic text in {max_length} characters or less.
Write the summary in Amharic (አማርኛ).

Text:
{text}

Summary (Amharic only):"""

            response = self.model.generate_content(prompt)
            summary = response.text.strip()

            # Trim to max length
            if len(summary) > max_length:
                summary = summary[:max_length].rsplit(' ', 1)[0] + "..."

            return summary

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return text[:max_length] + "..."


class OpenRouterProvider:
    """
    OpenRouter Fallback Provider

    Used when Gemini fails or rate limited
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenRouter provider"""
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )

        # Use Claude 3.5 Sonnet via OpenRouter (good for Amharic)
        self.model = "anthropic/claude-3.5-sonnet"

        logger.info("OpenRouter provider initialized")

    def ocr_image(self, image_path: str, language: str = "amh") -> Dict[str, Any]:
        """OCR using OpenRouter (Claude Vision)"""
        try:
            import base64

            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract ALL text from this image. Include Amharic text. Output only the text."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_data}"
                                }
                            }
                        ]
                    }
                ]
            )

            extracted_text = response.choices[0].message.content.strip()

            return {
                "text": extracted_text,
                "confidence": 0.90,
                "language": language,
                "provider": "openrouter",
                "model": self.model
            }

        except Exception as e:
            logger.error(f"OpenRouter OCR failed: {e}")
            raise

    def proofread_amharic(self, text: str) -> Dict[str, Any]:
        """Proofread using OpenRouter"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": f"Proofread this Amharic text and fix errors. Return only corrected text:\n\n{text}"
                    }
                ]
            )

            corrected_text = response.choices[0].message.content.strip()

            return {
                "original": text,
                "corrected": corrected_text,
                "has_changes": text != corrected_text,
                "provider": "openrouter"
            }

        except Exception as e:
            logger.error(f"OpenRouter proofreading failed: {e}")
            raise


class AIProviderManager:
    """
    Manages AI providers with automatic fallback

    Priority:
    1. Gemini 2.5 (primary - free, best for Amharic)
    2. OpenRouter (fallback)
    """

    def __init__(self):
        """Initialize provider manager"""
        self.providers = {}

        # Try to initialize Gemini
        try:
            self.providers[AIProvider.GEMINI] = GeminiProvider()
            self.primary_provider = AIProvider.GEMINI
            logger.info("Primary provider: Gemini 2.5")
        except Exception as e:
            logger.warning(f"Gemini initialization failed: {e}")
            self.primary_provider = None

        # Try to initialize OpenRouter
        try:
            self.providers[AIProvider.OPENROUTER] = OpenRouterProvider()
            if not self.primary_provider:
                self.primary_provider = AIProvider.OPENROUTER
                logger.info("Primary provider: OpenRouter")
        except Exception as e:
            logger.warning(f"OpenRouter initialization failed: {e}")

        if not self.providers:
            raise ValueError("No AI providers available. Set GOOGLE_API_KEY or OPENROUTER_API_KEY")

    def ocr_image(self, image_path: str, language: str = "amh") -> Dict[str, Any]:
        """
        Perform OCR with automatic fallback

        Args:
            image_path: Path to image
            language: Language code

        Returns:
            OCR result with text and confidence
        """
        # Try primary provider (Gemini)
        if AIProvider.GEMINI in self.providers:
            try:
                return self.providers[AIProvider.GEMINI].ocr_image(image_path, language)
            except Exception as e:
                logger.warning(f"Gemini OCR failed, trying fallback: {e}")

        # Fallback to OpenRouter
        if AIProvider.OPENROUTER in self.providers:
            try:
                return self.providers[AIProvider.OPENROUTER].ocr_image(image_path, language)
            except Exception as e:
                logger.error(f"OpenRouter OCR failed: {e}")
                raise

        raise RuntimeError("All OCR providers failed")

    def proofread_amharic(self, text: str) -> Dict[str, Any]:
        """
        Proofread with automatic fallback

        Args:
            text: Text to proofread

        Returns:
            Proofread result
        """
        # Try primary provider (Gemini)
        if AIProvider.GEMINI in self.providers:
            try:
                return self.providers[AIProvider.GEMINI].proofread_amharic(text)
            except Exception as e:
                logger.warning(f"Gemini proofreading failed, trying fallback: {e}")

        # Fallback to OpenRouter
        if AIProvider.OPENROUTER in self.providers:
            try:
                return self.providers[AIProvider.OPENROUTER].proofread_amharic(text)
            except Exception as e:
                logger.error(f"OpenRouter proofreading failed: {e}")
                raise

        raise RuntimeError("All proofreading providers failed")

    def get_gemini_provider(self) -> Optional[GeminiProvider]:
        """Get Gemini provider directly for advanced features"""
        return self.providers.get(AIProvider.GEMINI)


# Global instance
_provider_manager: Optional[AIProviderManager] = None


def get_ai_provider() -> AIProviderManager:
    """Get global AI provider manager"""
    global _provider_manager

    if _provider_manager is None:
        _provider_manager = AIProviderManager()

    return _provider_manager


def initialize_ai_providers():
    """Initialize AI providers on app startup"""
    global _provider_manager
    _provider_manager = AIProviderManager()
    logger.info("AI providers initialized")


# Example usage:
"""
from src.config.ai_providers import get_ai_provider

ai = get_ai_provider()

# OCR image (Gemini first, OpenRouter fallback)
result = ai.ocr_image("document.jpg", language="amh")
print(result["text"])
print(f"Confidence: {result['confidence']}")
print(f"Provider: {result['provider']}")

# Proofread Amharic text
result = ai.proofread_amharic("የአማርኛ ጽሁፍ")
if result["has_changes"]:
    print(f"Original: {result['original']}")
    print(f"Corrected: {result['corrected']}")

# Use Gemini-specific features
gemini = ai.get_gemini_provider()
if gemini:
    entities = gemini.extract_entities_amharic(text)
    summary = gemini.summarize_amharic(text, max_length=200)
"""