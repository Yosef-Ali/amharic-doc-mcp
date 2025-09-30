"""Search router exposing search, suggestions, and reindex endpoints with normalization."""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.database import get_async_session
from ...services.search import get_search_service
from ...services.search_suggestions import get_search_suggestions_service
from ...services.audit import get_audit_service
from ...models.schemas.search import (
    SearchRequest,
    SearchResponse,
    SearchSuggestionsRequest,
    SearchSuggestionsResponse,
    ReindexRequest,
    ReindexResponse,
    SearchFilters
)
from ...config.settings import get_settings
from .auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["search"])
settings = get_settings()


@router.post(
    "/documents",
    response_model=SearchResponse,
    dependencies=[Depends(RateLimiter(times=100, seconds=60))],  # 100 searches per minute
    summary="Search documents",
    description="Search through processed documents with full-text and semantic search"
)
async def search_documents(
    request: SearchRequest,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Search through user's documents."""
    search_service = get_search_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Perform the search
        search_results = await search_service.search_documents(
            session=session,
            user_id=current_user.id,
            query=request.query,
            filters=request.filters,
            page=request.page,
            page_size=request.page_size,
            search_type=request.search_type,
            highlight=request.highlight
        )
        
        # Log search event
        await audit_service.log_search_event(
            session=session,
            action="SEARCH_PERFORMED",
            user_id=current_user.id,
            details={
                "query": request.query,
                "search_type": request.search_type,
                "results_count": len(search_results["results"]),
                "filters_applied": bool(request.filters and (
                    request.filters.document_types or 
                    request.filters.date_range or 
                    request.filters.content_types or
                    request.filters.quality_scores
                ))
            }
        )
        
        return SearchResponse(
            query=request.query,
            results=search_results["results"],
            total_count=search_results["total_count"],
            page=request.page,
            page_size=request.page_size,
            search_type=request.search_type,
            took_ms=search_results.get("took_ms", 0),
            aggregations=search_results.get("aggregations", {}),
            suggestions=search_results.get("suggestions", [])
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Document search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Document search failed"
        )


@router.get(
    "/suggestions",
    response_model=SearchSuggestionsResponse,
    dependencies=[Depends(RateLimiter(times=200, seconds=60))],  # 200 suggestion requests per minute
    summary="Get search suggestions",
    description="Get search suggestions and autocomplete for query terms"
)
async def get_search_suggestions(
    query: str = Query(..., min_length=1, description="Partial query to get suggestions for"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suggestions"),
    suggestion_type: Optional[str] = Query("all", description="Type of suggestions: all, terms, documents"),
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get search suggestions for autocomplete."""
    suggestions_service = get_search_suggestions_service(settings)
    
    try:
        suggestions = await suggestions_service.get_suggestions(
            session=session,
            user_id=current_user.id,
            query=query,
            limit=limit,
            suggestion_type=suggestion_type
        )
        
        return SearchSuggestionsResponse(
            query=query,
            suggestions=suggestions["suggestions"],
            suggestion_type=suggestion_type,
            total_suggestions=len(suggestions["suggestions"])
        )
        
    except Exception as e:
        logger.error(f"Search suggestions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get search suggestions"
        )


@router.post(
    "/suggestions",
    response_model=SearchSuggestionsResponse,
    dependencies=[Depends(RateLimiter(times=200, seconds=60))],  # 200 suggestion requests per minute
    summary="Get advanced search suggestions",
    description="Get advanced search suggestions with context and filters"
)
async def get_advanced_search_suggestions(
    request: SearchSuggestionsRequest,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get advanced search suggestions with context."""
    suggestions_service = get_search_suggestions_service(settings)
    
    try:
        suggestions = await suggestions_service.get_contextual_suggestions(
            session=session,
            user_id=current_user.id,
            query=request.query,
            context=request.context,
            filters=request.filters,
            limit=request.limit,
            include_recent=request.include_recent,
            include_popular=request.include_popular
        )
        
        return SearchSuggestionsResponse(
            query=request.query,
            suggestions=suggestions["suggestions"],
            suggestion_type="contextual",
            total_suggestions=len(suggestions["suggestions"]),
            context=request.context,
            recent_queries=suggestions.get("recent_queries", []),
            popular_queries=suggestions.get("popular_queries", [])
        )
        
    except Exception as e:
        logger.error(f"Advanced search suggestions failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get advanced search suggestions"
        )


@router.post(
    "/reindex",
    response_model=ReindexResponse,
    dependencies=[Depends(RateLimiter(times=5, seconds=3600))],  # 5 reindex operations per hour
    summary="Reindex documents",
    description="Trigger reindexing of search indexes for documents"
)
async def reindex_documents(
    request: ReindexRequest,
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Trigger document reindexing."""
    search_service = get_search_service(settings)
    audit_service = get_audit_service(settings)
    
    try:
        # Check user permissions for reindexing
        if current_user.role not in ["admin", "moderator"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for reindexing"
            )
            
        # Start reindexing process
        reindex_result = await search_service.reindex_documents(
            session=session,
            document_ids=request.document_ids,
            full_reindex=request.full_reindex,
            force=request.force
        )
        
        # Log reindex event
        await audit_service.log_search_event(
            session=session,
            action="REINDEX_TRIGGERED",
            user_id=current_user.id,
            details={
                "full_reindex": request.full_reindex,
                "force": request.force,
                "document_count": len(request.document_ids) if request.document_ids else "all",
                "job_id": reindex_result.get("job_id")
            }
        )
        
        return ReindexResponse(
            success=True,
            message="Reindexing started successfully",
            job_id=reindex_result.get("job_id"),
            estimated_documents=reindex_result.get("estimated_documents", 0),
            started_at=reindex_result.get("started_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document reindexing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start document reindexing"
        )


@router.get(
    "/reindex/status",
    summary="Get reindex status",
    description="Get status of ongoing reindexing operations"
)
async def get_reindex_status(
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get status of reindexing operations."""
    search_service = get_search_service(settings)
    
    try:
        # Check user permissions
        if current_user.role not in ["admin", "moderator"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to view reindex status"
            )
            
        status_info = await search_service.get_reindex_status(session)
        
        return {
            "reindexing_active": status_info.get("active", False),
            "progress_percentage": status_info.get("progress", 0.0),
            "documents_processed": status_info.get("processed", 0),
            "total_documents": status_info.get("total", 0),
            "estimated_completion": status_info.get("estimated_completion"),
            "started_at": status_info.get("started_at"),
            "current_operation": status_info.get("current_operation")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get reindex status failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get reindex status"
        )


@router.get(
    "/analytics",
    summary="Get search analytics",
    description="Get search analytics and usage statistics"
)
async def get_search_analytics(
    date_from: Optional[str] = Query(None, description="Start date for analytics (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date for analytics (YYYY-MM-DD)"),
    current_user = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Get search analytics."""
    search_service = get_search_service(settings)
    
    try:
        analytics = await search_service.get_search_analytics(
            session=session,
            user_id=current_user.id,
            date_from=date_from,
            date_to=date_to
        )
        
        return {
            "total_searches": analytics.get("total_searches", 0),
            "unique_queries": analytics.get("unique_queries", 0),
            "avg_results_per_search": analytics.get("avg_results", 0.0),
            "top_queries": analytics.get("top_queries", []),
            "search_trends": analytics.get("trends", {}),
            "performance_metrics": analytics.get("performance", {}),
            "date_range": {
                "from": date_from,
                "to": date_to
            }
        }
        
    except Exception as e:
        logger.error(f"Get search analytics failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get search analytics"
        )