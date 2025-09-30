"""Webhook notification service managing subscriptions, signed deliveries, and retry policies."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from enum import Enum

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from sqlalchemy.orm import selectinload

from ..config.settings import Settings

logger = logging.getLogger(__name__)


class WebhookEventType(str, Enum):
    """Supported webhook event types."""
    DOCUMENT_UPLOADED = "document.uploaded"
    DOCUMENT_PROCESSED = "document.processed" 
    PROCESSING_STARTED = "processing.started"
    PROCESSING_COMPLETED = "processing.completed"
    PROCESSING_FAILED = "processing.failed"
    QUALITY_THRESHOLD_EXCEEDED = "quality.threshold_exceeded"
    QUALITY_ANOMALY_DETECTED = "quality.anomaly_detected"
    EXPORT_COMPLETED = "export.completed"
    SYSTEM_ERROR = "system.error"


class WebhookStatus(str, Enum):
    """Webhook delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    EXPIRED = "expired"


# Simple in-memory models for demonstration
# In production, these would be proper SQLAlchemy models

class WebhookSubscription:
    """Webhook subscription model."""
    
    def __init__(
        self,
        id: UUID,
        url: str,
        events: List[str],
        secret: str,
        active: bool = True,
        created_at: datetime = None,
        user_id: UUID = None,
        headers: Dict[str, str] = None,
        retry_config: Dict[str, Any] = None
    ):
        self.id = id
        self.url = url
        self.events = events
        self.secret = secret
        self.active = active
        self.created_at = created_at or datetime.utcnow()
        self.user_id = user_id
        self.headers = headers or {}
        self.retry_config = retry_config or {
            "max_attempts": 3,
            "initial_delay": 5,
            "backoff_multiplier": 2,
            "max_delay": 300
        }


class WebhookDelivery:
    """Webhook delivery attempt model."""
    
    def __init__(
        self,
        id: UUID,
        subscription_id: UUID,
        event_type: str,
        payload: Dict[str, Any],
        status: WebhookStatus = WebhookStatus.PENDING,
        attempt_count: int = 0,
        created_at: datetime = None,
        last_attempt_at: datetime = None,
        next_retry_at: datetime = None,
        response_status: int = None,
        response_body: str = None,
        error_message: str = None
    ):
        self.id = id
        self.subscription_id = subscription_id
        self.event_type = event_type
        self.payload = payload
        self.status = status
        self.attempt_count = attempt_count
        self.created_at = created_at or datetime.utcnow()
        self.last_attempt_at = last_attempt_at
        self.next_retry_at = next_retry_at
        self.response_status = response_status
        self.response_body = response_body
        self.error_message = error_message


class WebhookService:
    """Service for managing webhook subscriptions and deliveries."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # In-memory storage for demonstration
        # In production, these would be database operations
        self.subscriptions: Dict[UUID, WebhookSubscription] = {}
        self.deliveries: Dict[UUID, WebhookDelivery] = {}
        
        # Configuration
        self.max_payload_size = 1024 * 1024  # 1MB
        self.signature_header = "X-Webhook-Signature"
        self.timestamp_header = "X-Webhook-Timestamp"
        self.event_header = "X-Webhook-Event"
        self.delivery_timeout = 30  # seconds
        self.max_retry_attempts = 5
        self.retry_delays = [5, 15, 45, 120, 300]  # seconds
        
        # Start background task for retry processing
        self.retry_task = None
        
    async def initialize(self) -> None:
        """Initialize the webhook service."""
        # Start retry processor
        self.retry_task = asyncio.create_task(self._retry_processor())
        logger.info("Webhook service initialized")
        
    async def create_subscription(
        self,
        session: AsyncSession,
        url: str,
        events: List[WebhookEventType],
        user_id: UUID,
        secret: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_config: Optional[Dict[str, Any]] = None
    ) -> WebhookSubscription:
        """Create a new webhook subscription."""
        # Validate URL
        if not self._is_valid_webhook_url(url):
            raise ValueError("Invalid webhook URL")
            
        # Validate events
        if not events:
            raise ValueError("At least one event type must be specified")
            
        # Generate secret if not provided
        if not secret:
            secret = self._generate_webhook_secret()
            
        subscription = WebhookSubscription(
            id=uuid4(),
            url=url,
            events=[event.value for event in events],
            secret=secret,
            user_id=user_id,
            headers=headers or {},
            retry_config=retry_config
        )
        
        # Store subscription (in production, save to database)
        self.subscriptions[subscription.id] = subscription
        
        logger.info(f"Created webhook subscription {subscription.id} for user {user_id}")
        
        # Test webhook endpoint
        await self._test_webhook_endpoint(subscription)
        
        return subscription
        
    async def update_subscription(
        self,
        session: AsyncSession,
        subscription_id: UUID,
        url: Optional[str] = None,
        events: Optional[List[WebhookEventType]] = None,
        active: Optional[bool] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Optional[WebhookSubscription]:
        """Update an existing webhook subscription."""
        subscription = self.subscriptions.get(subscription_id)
        if not subscription:
            return None
            
        # Update fields
        if url is not None:
            if not self._is_valid_webhook_url(url):
                raise ValueError("Invalid webhook URL")
            subscription.url = url
            
        if events is not None:
            if not events:
                raise ValueError("At least one event type must be specified")
            subscription.events = [event.value for event in events]
            
        if active is not None:
            subscription.active = active
            
        if headers is not None:
            subscription.headers = headers
            
        logger.info(f"Updated webhook subscription {subscription_id}")
        
        # Test updated endpoint if URL changed
        if url is not None and subscription.active:
            await self._test_webhook_endpoint(subscription)
            
        return subscription
        
    async def delete_subscription(
        self,
        session: AsyncSession,
        subscription_id: UUID
    ) -> bool:
        """Delete a webhook subscription."""
        subscription = self.subscriptions.pop(subscription_id, None)
        if subscription:
            logger.info(f"Deleted webhook subscription {subscription_id}")
            return True
        return False
        
    async def get_subscriptions(
        self,
        session: AsyncSession,
        user_id: Optional[UUID] = None,
        active_only: bool = True
    ) -> List[WebhookSubscription]:
        """Get webhook subscriptions."""
        subscriptions = list(self.subscriptions.values())
        
        if user_id:
            subscriptions = [s for s in subscriptions if s.user_id == user_id]
            
        if active_only:
            subscriptions = [s for s in subscriptions if s.active]
            
        return subscriptions
        
    async def trigger_webhook(
        self,
        session: AsyncSession,
        event_type: WebhookEventType,
        payload: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> List[UUID]:
        """Trigger webhooks for a specific event."""
        # Find matching subscriptions
        matching_subscriptions = []
        for subscription in self.subscriptions.values():
            if not subscription.active:
                continue
                
            # Check event type match
            if event_type.value not in subscription.events:
                continue
                
            # Check user filter if provided
            if user_id and subscription.user_id != user_id:
                continue
                
            matching_subscriptions.append(subscription)
            
        if not matching_subscriptions:
            logger.debug(f"No matching subscriptions for event {event_type.value}")
            return []
            
        # Create delivery records
        delivery_ids = []
        for subscription in matching_subscriptions:
            delivery = WebhookDelivery(
                id=uuid4(),
                subscription_id=subscription.id,
                event_type=event_type.value,
                payload=payload
            )
            
            self.deliveries[delivery.id] = delivery
            delivery_ids.append(delivery.id)
            
        logger.info(f"Created {len(delivery_ids)} webhook deliveries for event {event_type.value}")
        
        # Trigger immediate delivery attempts
        for delivery_id in delivery_ids:
            asyncio.create_task(self._attempt_delivery(delivery_id))
            
        return delivery_ids
        
    async def get_delivery_status(
        self,
        session: AsyncSession,
        delivery_id: UUID
    ) -> Optional[WebhookDelivery]:
        """Get webhook delivery status."""
        return self.deliveries.get(delivery_id)
        
    async def get_delivery_history(
        self,
        session: AsyncSession,
        subscription_id: Optional[UUID] = None,
        event_type: Optional[str] = None,
        status: Optional[WebhookStatus] = None,
        limit: int = 100
    ) -> List[WebhookDelivery]:
        """Get webhook delivery history."""
        deliveries = list(self.deliveries.values())
        
        # Apply filters
        if subscription_id:
            deliveries = [d for d in deliveries if d.subscription_id == subscription_id]
            
        if event_type:
            deliveries = [d for d in deliveries if d.event_type == event_type]
            
        if status:
            deliveries = [d for d in deliveries if d.status == status]
            
        # Sort by creation time (newest first) and limit
        deliveries.sort(key=lambda x: x.created_at, reverse=True)
        return deliveries[:limit]
        
    async def retry_failed_delivery(
        self,
        session: AsyncSession,
        delivery_id: UUID
    ) -> bool:
        """Manually retry a failed webhook delivery."""
        delivery = self.deliveries.get(delivery_id)
        if not delivery or delivery.status not in [WebhookStatus.FAILED, WebhookStatus.EXPIRED]:
            return False
            
        # Reset for retry
        delivery.status = WebhookStatus.PENDING
        delivery.next_retry_at = datetime.utcnow()
        delivery.error_message = None
        
        # Attempt delivery
        await self._attempt_delivery(delivery_id)
        
        logger.info(f"Manual retry initiated for delivery {delivery_id}")
        return True
        
    async def _attempt_delivery(self, delivery_id: UUID) -> None:
        """Attempt to deliver a webhook."""
        delivery = self.deliveries.get(delivery_id)
        if not delivery:
            return
            
        subscription = self.subscriptions.get(delivery.subscription_id)
        if not subscription or not subscription.active:
            delivery.status = WebhookStatus.FAILED
            delivery.error_message = "Subscription not found or inactive"
            return
            
        delivery.attempt_count += 1
        delivery.last_attempt_at = datetime.utcnow()
        delivery.status = WebhookStatus.RETRYING
        
        try:
            # Prepare webhook payload
            webhook_payload = {
                "event": delivery.event_type,
                "timestamp": delivery.created_at.isoformat(),
                "delivery_id": str(delivery.id),
                "data": delivery.payload
            }
            
            # Generate signature
            timestamp = str(int(datetime.utcnow().timestamp()))
            payload_json = json.dumps(webhook_payload, separators=(',', ':'))
            signature = self._generate_signature(payload_json, subscription.secret, timestamp)
            
            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                self.signature_header: signature,
                self.timestamp_header: timestamp,
                self.event_header: delivery.event_type,
                "User-Agent": "Amharic-Document-System-Webhooks/1.0"
            }
            headers.update(subscription.headers)
            
            # Check payload size
            if len(payload_json) > self.max_payload_size:
                raise ValueError("Payload too large")
                
            # Make HTTP request
            response = await self.http_client.post(
                subscription.url,
                content=payload_json,
                headers=headers,
                timeout=self.delivery_timeout
            )
            
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:1000]  # Limit stored response
            
            # Check for success
            if 200 <= response.status_code < 300:
                delivery.status = WebhookStatus.DELIVERED
                logger.info(f"Webhook delivery {delivery_id} succeeded")
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            delivery.error_message = str(e)[:500]  # Limit error message
            logger.warning(f"Webhook delivery {delivery_id} failed: {e}")
            
            # Schedule retry if attempts remaining
            if delivery.attempt_count < subscription.retry_config.get("max_attempts", self.max_retry_attempts):
                delay = self._calculate_retry_delay(delivery.attempt_count, subscription.retry_config)
                delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
                delivery.status = WebhookStatus.PENDING
                logger.info(f"Scheduled retry for delivery {delivery_id} in {delay}s")
            else:
                delivery.status = WebhookStatus.EXPIRED
                logger.error(f"Webhook delivery {delivery_id} exhausted all retry attempts")
                
    async def _retry_processor(self) -> None:
        """Background task to process webhook retries."""
        while True:
            try:
                current_time = datetime.utcnow()
                
                # Find deliveries ready for retry
                retry_deliveries = [
                    delivery for delivery in self.deliveries.values()
                    if (delivery.status == WebhookStatus.PENDING and
                        delivery.next_retry_at and
                        delivery.next_retry_at <= current_time)
                ]
                
                # Process retries
                for delivery in retry_deliveries:
                    asyncio.create_task(self._attempt_delivery(delivery.id))
                    
                # Clean up old deliveries (older than 30 days)
                cutoff_date = current_time - timedelta(days=30)
                old_delivery_ids = [
                    delivery_id for delivery_id, delivery in self.deliveries.items()
                    if delivery.created_at < cutoff_date
                ]
                
                for delivery_id in old_delivery_ids:
                    del self.deliveries[delivery_id]
                    
                if old_delivery_ids:
                    logger.info(f"Cleaned up {len(old_delivery_ids)} old webhook deliveries")
                    
            except Exception as e:
                logger.error(f"Retry processor error: {e}")
                
            # Wait before next iteration
            await asyncio.sleep(60)  # Check every minute
            
    def _is_valid_webhook_url(self, url: str) -> bool:
        """Validate webhook URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            
            # Must be HTTP/HTTPS
            if parsed.scheme not in ["http", "https"]:
                return False
                
            # Must have hostname
            if not parsed.netloc:
                return False
                
            # Reject localhost in production
            if self.settings.ENVIRONMENT == "production" and "localhost" in parsed.netloc.lower():
                return False
                
            return True
            
        except Exception:
            return False
            
    def _generate_webhook_secret(self) -> str:
        """Generate a secure webhook secret."""
        import secrets
        return secrets.token_urlsafe(32)
        
    def _generate_signature(self, payload: str, secret: str, timestamp: str) -> str:
        """Generate HMAC signature for webhook payload."""
        message = f"{timestamp}.{payload}"
        signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
        
    def _calculate_retry_delay(
        self,
        attempt_count: int,
        retry_config: Dict[str, Any]
    ) -> int:
        """Calculate delay for next retry attempt."""
        initial_delay = retry_config.get("initial_delay", 5)
        backoff_multiplier = retry_config.get("backoff_multiplier", 2)
        max_delay = retry_config.get("max_delay", 300)
        
        delay = initial_delay * (backoff_multiplier ** (attempt_count - 1))
        return min(delay, max_delay)
        
    async def _test_webhook_endpoint(self, subscription: WebhookSubscription) -> None:
        """Test webhook endpoint with a ping event."""
        test_payload = {
            "event": "webhook.test",
            "timestamp": datetime.utcnow().isoformat(),
            "subscription_id": str(subscription.id),
            "data": {
                "message": "This is a test webhook to verify your endpoint"
            }
        }
        
        try:
            timestamp = str(int(datetime.utcnow().timestamp()))
            payload_json = json.dumps(test_payload, separators=(',', ':'))
            signature = self._generate_signature(payload_json, subscription.secret, timestamp)
            
            headers = {
                "Content-Type": "application/json",
                self.signature_header: signature,
                self.timestamp_header: timestamp,
                self.event_header: "webhook.test",
                "User-Agent": "Amharic-Document-System-Webhooks/1.0"
            }
            headers.update(subscription.headers)
            
            response = await self.http_client.post(
                subscription.url,
                content=payload_json,
                headers=headers,
                timeout=10
            )
            
            if 200 <= response.status_code < 300:
                logger.info(f"Webhook test successful for subscription {subscription.id}")
            else:
                logger.warning(f"Webhook test failed for subscription {subscription.id}: HTTP {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Webhook test failed for subscription {subscription.id}: {e}")
            
    async def close(self) -> None:
        """Close the webhook service."""
        if self.retry_task:
            self.retry_task.cancel()
            try:
                await self.retry_task
            except asyncio.CancelledError:
                pass
                
        await self.http_client.aclose()
        logger.info("Webhook service closed")


# Global webhook service instance
_webhook_service: Optional[WebhookService] = None


def get_webhook_service(settings: Settings) -> WebhookService:
    """Get the global webhook service instance."""
    global _webhook_service
    if _webhook_service is None:
        _webhook_service = WebhookService(settings)
    return _webhook_service