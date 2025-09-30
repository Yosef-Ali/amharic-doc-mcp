"""Image OCR agent for extracting text from images and scanned documents."""

from __future__ import annotations

import cv2
import logging
import numpy as np
from typing import Dict, Any, Optional
from uuid import UUID

import pytesseract
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from ...config.settings import Settings

logger = logging.getLogger(__name__)


class ImageOCRAgent:
    """Agent specialized in OCR text extraction from images."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.tesseract_cmd = settings.TESSERACT_CMD
        self.default_languages = settings.TESSERACT_LANGUAGES
        
    async def extract_text_from_image(
        self,
        session: AsyncSession,
        image_path: str,
        document_id: UUID,
        preprocessing: bool = True,
        language: str = "amh+eng"
    ) -> Dict[str, Any]:
        """Extract text from image using Tesseract OCR."""
        try:
            logger.info(f"Starting OCR extraction for document {document_id}")
            
            # Load and preprocess image
            image = cv2.imread(image_path)
            if image is None:
                return {"success": False, "error": "Could not load image"}
                
            if preprocessing:
                processed_image = self._preprocess_image(image)
            else:
                processed_image = image
                
            # Configure Tesseract
            config = f'--oem 3 --psm 6 -l {language}'
            
            # Extract text with confidence scores
            pil_image = Image.fromarray(cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB))
            
            # Get text and confidence data
            text = pytesseract.image_to_string(pil_image, config=config)
            data = pytesseract.image_to_data(pil_image, config=config, output_type=pytesseract.Output.DICT)
            
            # Calculate confidence metrics
            confidence_scores = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = np.mean(confidence_scores) if confidence_scores else 0
            
            # Extract word-level details
            words = []
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:
                    words.append({
                        'text': data['text'][i],
                        'confidence': int(data['conf'][i]),
                        'bbox': {
                            'x': data['left'][i],
                            'y': data['top'][i],
                            'width': data['width'][i],
                            'height': data['height'][i]
                        }
                    })
                    
            result = {
                "success": True,
                "extracted_text": text.strip(),
                "average_confidence": round(avg_confidence, 2),
                "word_count": len(text.split()),
                "character_count": len(text),
                "words_with_confidence": words,
                "language": language,
                "processing_time": 0,  # Would be calculated in real implementation
                "image_dimensions": {
                    "width": image.shape[1],
                    "height": image.shape[0]
                }
            }
            
            logger.info(f"OCR extraction completed for document {document_id} with {avg_confidence:.1f}% confidence")
            return result
            
        except Exception as e:
            logger.error(f"OCR extraction failed for document {document_id}: {e}")
            return {"success": False, "error": str(e)}
            
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image to improve OCR accuracy."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Morphological operations to clean up
            kernel = np.ones((2, 2), np.uint8)
            processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # Convert back to 3-channel for consistency
            return cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
            
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}, using original")
            return image


_image_ocr_agent: Optional[ImageOCRAgent] = None

def get_image_ocr_agent(settings: Settings) -> ImageOCRAgent:
    global _image_ocr_agent
    if _image_ocr_agent is None:
        _image_ocr_agent = ImageOCRAgent(settings)
    return _image_ocr_agent