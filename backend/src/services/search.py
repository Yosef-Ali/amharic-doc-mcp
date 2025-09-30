"""Search service for document indexing and retrieval."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import NotFoundError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.models.document import Document
from ..db.models.search_index import SearchIndex
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class SearchService:
    """Service for document search and indexing."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.es_client = AsyncElasticsearch(
            [settings.ELASTICSEARCH_URL],
            verify_certs=False
        )
        self.index_name = settings.ELASTICSEARCH_INDEX
        
    async def initialize(self) -> None:
        """Initialize Elasticsearch index with proper mappings."""
        # Create index with Amharic-specific mappings
        mapping = {
            "mappings": {
                "properties": {
                    "document_id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "amharic_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "amharic_analyzer"
                    },
                    "content_type": {"type": "keyword"},
                    "language": {"type": "keyword"},
                    "extracted_text": {
                        "type": "text",
                        "analyzer": "amharic_analyzer"
                    },
                    "metadata": {"type": "object"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "file_size": {"type": "long"},
                    "page_count": {"type": "integer"},
                    "ocr_confidence": {"type": "float"},
                    "processing_status": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "embeddings": {
                        "type": "dense_vector",
                        "dims": 768  # For sentence transformers
                    }
                }
            },
            "settings": {
                "analysis": {
                    "analyzer": {
                        "amharic_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "amharic_stemmer",
                                "stop"
                            ]
                        }
                    },
                    "filter": {
                        "amharic_stemmer": {
                            "type": "stemmer",
                            "language": "minimal_amharic"
                        }
                    }
                }
            }
        }
        
        try:
            await self.es_client.indices.create(
                index=self.index_name,
                body=mapping,
                ignore=400  # Ignore if index already exists
            )
            logger.info(f"Elasticsearch index '{self.index_name}' initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch index: {e}")
            
    async def index_document(
        self,
        session: AsyncSession,
        document: Document,
        extracted_content: Dict[str, Any]
    ) -> bool:
        """Index a document for search."""
        try:
            doc_body = {
                "document_id": str(document.id),
                "title": document.filename,
                "content": extracted_content.get("text", ""),
                "content_type": document.content_type,
                "language": extracted_content.get("language", "amh"),
                "extracted_text": extracted_content.get("text", ""),
                "metadata": document.metadata,
                "created_at": document.created_at.isoformat(),
                "updated_at": document.updated_at.isoformat() if document.updated_at else None,
                "file_size": document.file_size,
                "page_count": extracted_content.get("page_count", 1),
                "ocr_confidence": extracted_content.get("ocr_confidence", 0.0),
                "processing_status": str(document.status),
                "tags": extracted_content.get("tags", [])
            }
            
            # Add embeddings if available
            if "embeddings" in extracted_content:
                doc_body["embeddings"] = extracted_content["embeddings"]
                
            # Index document in Elasticsearch
            response = await self.es_client.index(
                index=self.index_name,
                id=str(document.id),
                body=doc_body
            )
            
            # Create search index record in PostgreSQL
            search_index = SearchIndex(
                document_id=document.id,
                index_name=self.index_name,
                indexed_at=datetime.utcnow(),
                embeddings=extracted_content.get("embeddings"),
                facets=extracted_content.get("facets", {})
            )
            
            session.add(search_index)
            await session.commit()
            
            logger.info(f"Document {document.id} indexed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index document {document.id}: {e}")
            return False
            
    async def search_documents(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        page_size: int = 20,
        highlight: bool = True
    ) -> Dict[str, Any]:
        """Search for documents."""
        try:
            # Build Elasticsearch query
            es_query = self._build_search_query(query, filters)
            
            # Add highlighting
            highlight_config = {}
            if highlight:
                highlight_config = {
                    "fields": {
                        "title": {},
                        "content": {},
                        "extracted_text": {}
                    },
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"]
                }
                
            # Calculate pagination
            from_offset = (page - 1) * page_size
            
            # Execute search
            response = await self.es_client.search(
                index=self.index_name,
                body={
                    "query": es_query,
                    "highlight": highlight_config,
                    "from": from_offset,
                    "size": page_size,
                    "sort": [
                        {"_score": {"order": "desc"}},
                        {"updated_at": {"order": "desc"}}
                    ]
                }
            )
            
            # Process results
            hits = response["hits"]
            documents = []
            
            for hit in hits["hits"]:
                doc_data = hit["_source"]
                doc_result = {
                    "document_id": doc_data["document_id"],
                    "title": doc_data["title"],
                    "content_type": doc_data["content_type"],
                    "file_size": doc_data["file_size"],
                    "created_at": doc_data["created_at"],
                    "score": hit["_score"]
                }
                
                # Add highlights if available
                if "highlight" in hit:
                    doc_result["highlights"] = hit["highlight"]
                    
                documents.append(doc_result)
                
            return {
                "documents": documents,
                "total": hits["total"]["value"],
                "page": page,
                "page_size": page_size,
                "total_pages": (hits["total"]["value"] + page_size - 1) // page_size
            }
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {
                "documents": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "error": str(e)
            }
            
    async def get_search_suggestions(
        self,
        query: str,
        limit: int = 10
    ) -> List[str]:
        """Get search suggestions based on query."""
        try:
            # Use completion suggester for autocomplete
            response = await self.es_client.search(
                index=self.index_name,
                body={
                    "suggest": {
                        "title_suggest": {
                            "prefix": query,
                            "completion": {
                                "field": "title.keyword",
                                "size": limit
                            }
                        },
                        "content_suggest": {
                            "prefix": query,
                            "completion": {
                                "field": "content",
                                "size": limit
                            }
                        }
                    }
                }
            )
            
            suggestions = set()
            
            # Extract suggestions from both title and content
            for suggest_type in ["title_suggest", "content_suggest"]:
                if suggest_type in response["suggest"]:
                    for suggestion in response["suggest"][suggest_type]:
                        for option in suggestion["options"]:
                            suggestions.add(option["text"])
                            
            return list(suggestions)[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get suggestions: {e}")
            return []
            
    async def reindex_all_documents(self, session: AsyncSession) -> Dict[str, Any]:
        """Reindex all documents."""
        try:
            # Get all documents that need reindexing
            result = await session.execute(
                select(Document).where(Document.status == "processed")
            )
            documents = result.scalars().all()
            
            stats = {
                "total_documents": len(documents),
                "indexed": 0,
                "failed": 0,
                "errors": []
            }
            
            # Delete existing index
            try:
                await self.es_client.indices.delete(index=self.index_name)
            except NotFoundError:
                pass
                
            # Recreate index
            await self.initialize()
            
            # Reindex documents
            for document in documents:
                try:
                    # Get extracted content (this would come from MongoDB)
                    extracted_content = {
                        "text": "Sample extracted text",  # Would be loaded from MongoDB
                        "language": "amh",
                        "page_count": 1,
                        "ocr_confidence": 0.95
                    }
                    
                    success = await self.index_document(session, document, extracted_content)
                    if success:
                        stats["indexed"] += 1
                    else:
                        stats["failed"] += 1
                        
                except Exception as e:
                    stats["failed"] += 1
                    stats["errors"].append(f"Document {document.id}: {str(e)}")
                    
            logger.info(f"Reindexing completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Reindexing failed: {e}")
            return {
                "total_documents": 0,
                "indexed": 0,
                "failed": 0,
                "errors": [str(e)]
            }
            
    async def delete_document_from_index(
        self,
        session: AsyncSession,
        document_id: UUID
    ) -> bool:
        """Remove document from search index."""
        try:
            # Delete from Elasticsearch
            await self.es_client.delete(
                index=self.index_name,
                id=str(document_id),
                ignore=404
            )
            
            # Delete search index record
            result = await session.execute(
                select(SearchIndex).where(SearchIndex.document_id == document_id)
            )
            search_index = result.scalar_one_or_none()
            
            if search_index:
                await session.delete(search_index)
                await session.commit()
                
            logger.info(f"Document {document_id} removed from search index")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove document {document_id} from index: {e}")
            return False
            
    def _build_search_query(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build Elasticsearch query."""
        # Main search query
        search_query = {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^2", "content", "extracted_text"],
                            "type": "best_fields",
                            "analyzer": "amharic_analyzer"
                        }
                    },
                    {
                        "match": {
                            "title": {
                                "query": query,
                                "boost": 3
                            }
                        }
                    }
                ]
            }
        }
        
        # Add filters
        if filters:
            filter_clauses = []
            
            if "content_type" in filters:
                filter_clauses.append({
                    "term": {"content_type": filters["content_type"]}
                })
                
            if "language" in filters:
                filter_clauses.append({
                    "term": {"language": filters["language"]}
                })
                
            if "date_from" in filters:
                filter_clauses.append({
                    "range": {
                        "created_at": {
                            "gte": filters["date_from"]
                        }
                    }
                })
                
            if "date_to" in filters:
                filter_clauses.append({
                    "range": {
                        "created_at": {
                            "lte": filters["date_to"]
                        }
                    }
                })
                
            if "min_confidence" in filters:
                filter_clauses.append({
                    "range": {
                        "ocr_confidence": {
                            "gte": filters["min_confidence"]
                        }
                    }
                })
                
            if filter_clauses:
                search_query["bool"]["filter"] = filter_clauses
                
        return search_query
        
    async def close(self) -> None:
        """Close Elasticsearch connection."""
        await self.es_client.close()


# Global search service instance
_search_service: Optional[SearchService] = None


def get_search_service(settings: Settings) -> SearchService:
    """Get the global search service instance."""
    global _search_service
    if _search_service is None:
        _search_service = SearchService(settings)
    return _search_service