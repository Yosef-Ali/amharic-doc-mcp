"""Quality assurance agent for validating processing results."""

from __future__ import annotations
import logging
from typing import Dict, Any, List
from ...config.settings import Settings

class QualityAssuranceAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.min_confidence_threshold = 0.95
        
    async def validate_processing_results(
        self, 
        original_content: str, 
        processed_content: str,
        confidence_scores: List[float]
    ) -> Dict[str, Any]:
        """Validate processing results against quality thresholds."""
        try:
            # Calculate accuracy metrics
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            
            # Basic quality checks
            quality_checks = {
                "confidence_above_threshold": avg_confidence >= self.min_confidence_threshold,
                "content_not_empty": len(processed_content.strip()) > 0,
                "reasonable_length": len(processed_content) > len(original_content) * 0.1,
                "amharic_content_detected": any('\u1200' <= char <= '\u137F' for char in processed_content)
            }
            
            overall_quality = sum(quality_checks.values()) / len(quality_checks)
            
            return {
                "success": True,
                "quality_score": overall_quality,
                "average_confidence": avg_confidence,
                "quality_checks": quality_checks,
                "recommendations": self._generate_recommendations(quality_checks, avg_confidence)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def _generate_recommendations(self, checks: Dict[str, bool], confidence: float) -> List[str]:
        """Generate quality improvement recommendations."""
        recommendations = []
        
        if not checks.get("confidence_above_threshold"):
            recommendations.append("Consider re-processing with different OCR settings")
        if not checks.get("amharic_content_detected"):
            recommendations.append("Verify document contains Amharic text")
        if confidence < 0.8:
            recommendations.append("Manual review recommended due to low confidence")
            
        return recommendations

def get_quality_assurance_agent(settings: Settings) -> QualityAssuranceAgent:
    return QualityAssuranceAgent(settings)