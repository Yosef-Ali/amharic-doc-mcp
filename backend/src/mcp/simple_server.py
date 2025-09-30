"""
Simple MCP Server for Claude Client

Exposes tools for document processing via MCP protocol.
Claude client handles most orchestration, this just provides tools.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path

from mcp import Server, Tool
from mcp.types import TextContent

from ..config.ai_providers import get_ai_provider
from ..services.documents import DocumentService
from ..services.processing import ProcessingService
from ..services.search import SearchService

logger = logging.getLogger(__name__)

# Create MCP server
mcp_server = Server("amharic-doc-processor")


@mcp_server.tool()
async def process_document_image(
    image_path: str,
    language: str = "amh"
) -> Dict[str, Any]:
    """
    Process document image with Gemini OCR

    Args:
        image_path: Path to image file
        language: Language code (amh for Amharic)

    Returns:
        Extracted text and metadata
    """
    try:
        ai = get_ai_provider()

        # Perform OCR with Gemini (auto-fallback to OpenRouter)
        result = ai.ocr_image(image_path, language)

        # Proofread if Amharic
        if language == "amh" and result["text"]:
            proofread_result = ai.proofread_amharic(result["text"])
            result["proofread"] = proofread_result

        return {
            "success": True,
            "text": result["text"],
            "confidence": result["confidence"],
            "provider": result["provider"],
            "proofread": result.get("proofread"),
            "language": language
        }

    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp_server.tool()
async def proofread_amharic_text(text: str) -> Dict[str, Any]:
    """
    Proofread Amharic text using Gemini

    Args:
        text: Amharic text to proofread

    Returns:
        Corrected text and changes
    """
    try:
        ai = get_ai_provider()
        result = ai.proofread_amharic(text)

        return {
            "success": True,
            "original": result["original"],
            "corrected": result["corrected"],
            "has_changes": result["has_changes"],
            "provider": result["provider"]
        }

    except Exception as e:
        logger.error(f"Proofreading failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp_server.tool()
async def extract_amharic_entities(text: str) -> Dict[str, Any]:
    """
    Extract named entities from Amharic text

    Args:
        text: Amharic text

    Returns:
        List of entities with types
    """
    try:
        ai = get_ai_provider()
        gemini = ai.get_gemini_provider()

        if not gemini:
            return {
                "success": False,
                "error": "Gemini provider not available for entity extraction"
            }

        entities = gemini.extract_entities_amharic(text)

        return {
            "success": True,
            "entities": entities,
            "count": len(entities)
        }

    except Exception as e:
        logger.error(f"Entity extraction failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp_server.tool()
async def summarize_amharic_text(
    text: str,
    max_length: int = 200
) -> Dict[str, Any]:
    """
    Summarize Amharic text using Gemini

    Args:
        text: Amharic text to summarize
        max_length: Maximum summary length

    Returns:
        Summarized text in Amharic
    """
    try:
        ai = get_ai_provider()
        gemini = ai.get_gemini_provider()

        if not gemini:
            return {
                "success": False,
                "error": "Gemini provider not available for summarization"
            }

        summary = gemini.summarize_amharic(text, max_length)

        return {
            "success": True,
            "summary": summary,
            "original_length": len(text),
            "summary_length": len(summary)
        }

    except Exception as e:
        logger.error(f"Summarization failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp_server.tool()
async def search_documents(
    query: str,
    language: str = "amh",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search processed documents

    Args:
        query: Search query (can be Amharic)
        language: Search language
        limit: Maximum results

    Returns:
        Search results with highlights
    """
    try:
        search_service = SearchService()

        results = await search_service.search_documents(
            query=query,
            filters={"language": language},
            limit=limit
        )

        return {
            "success": True,
            "results": results["hits"],
            "total": results["total"],
            "query": query
        }

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@mcp_server.tool()
async def get_processing_status(job_id: str) -> Dict[str, Any]:
    """
    Get document processing status

    Args:
        job_id: Processing job ID

    Returns:
        Job status and progress
    """
    try:
        processing_service = ProcessingService()

        status = await processing_service.get_job_status(job_id)

        return {
            "success": True,
            "job_id": job_id,
            "status": status["status"],
            "progress": status.get("progress", 0),
            "result": status.get("result")
        }

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Tool descriptions for Claude
TOOL_DESCRIPTIONS = {
    "process_document_image": """
        Process document image using Gemini OCR.
        Best for Amharic documents. Includes automatic proofreading.
        Returns extracted text with confidence score.
    """,

    "proofread_amharic_text": """
        Proofread Amharic text using Gemini.
        Fixes spelling and grammar errors while preserving meaning.
    """,

    "extract_amharic_entities": """
        Extract named entities (people, places, organizations, dates) from Amharic text.
        Uses Gemini for accurate Ethiopian entity recognition.
    """,

    "summarize_amharic_text": """
        Generate Amharic summary of longer text.
        Summary is in Amharic, preserves key information.
    """,

    "search_documents": """
        Search processed documents with Amharic query support.
        Returns matching documents with highlighted snippets.
    """,

    "get_processing_status": """
        Check status of document processing job.
        Returns progress percentage and completion status.
    """
}


async def run_mcp_server(host: str = "localhost", port: int = 8001):
    """
    Run MCP server for Claude client

    Args:
        host: Server host
        port: Server port
    """
    logger.info(f"Starting MCP server on {host}:{port}")
    logger.info("Available tools:")

    for tool_name, description in TOOL_DESCRIPTIONS.items():
        logger.info(f"  - {tool_name}: {description.strip()}")

    await mcp_server.run(host=host, port=port)


# For Claude client configuration
MCP_CONFIG = {
    "server_url": "http://localhost:8001",
    "tools": list(TOOL_DESCRIPTIONS.keys()),
    "description": "Amharic document processing with Gemini OCR and proofreading"
}


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_mcp_server())