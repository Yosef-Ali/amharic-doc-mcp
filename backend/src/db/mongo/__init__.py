"""MongoDB repositories for document processing artifacts."""

from .extracted_content import (
    ExtractedContentDocument,
    AmharicAnalysisDocument,
    NamedEntityDocument,
    StructuredBlock,
    ExtractedContentRepository,
)

__all__ = [
    "ExtractedContentDocument",
    "AmharicAnalysisDocument",
    "NamedEntityDocument",
    "StructuredBlock",
    "ExtractedContentRepository",
]
