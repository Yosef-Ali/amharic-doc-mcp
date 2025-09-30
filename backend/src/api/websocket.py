"""WebSocket broadcaster for real-time updates in the Amharic Document Processing system."""

from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional, Set
from uuid import UUID
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from ..services.audit import get_audit_service
from ..config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class WebSocketBroadcaster:
    """WebSocket connection manager for real-time updates."""
    
    def __init__(self):
        # Active connections by user_id
        self.connections: Dict[str, WebSocket] = {}
        
        # Subscriptions by event type
        self.subscriptions: Dict[str, Set[str]] = {
            "processing_updates": set(),
            "document_notifications": set(),
            "search_updates": set(),
            "export_notifications": set(),
            "quality_alerts": set(),
            "system_notifications": set()
        }
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, session: AsyncSession):
        """Accept WebSocket connection and register user."""
        await websocket.accept()
        self.connections[user_id] = websocket
        self.connection_metadata[user_id] = {
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "subscriptions": []
        }
        
        # Log connection event
        audit_service = get_audit_service(settings)
        await audit_service.log_websocket_event(
            session=session,
            action="CONNECTION_ESTABLISHED",
            user_id=user_id,
            details={"connection_type": "websocket", "protocol": "ws"}
        )
        
        logger.info(f"WebSocket connected: {user_id}")
        
        # Send welcome message
        await self.send_personal_message(user_id, {
            "type": "connection_established",
            "message": "WebSocket connection established",
            "timestamp": datetime.utcnow().isoformat(),
            "available_subscriptions": list(self.subscriptions.keys())
        })

    def disconnect(self, user_id: str):
        """Disconnect user and clean up subscriptions."""
        if user_id in self.connections:
            del self.connections[user_id]
            
        # Remove from all subscriptions
        for subscription_type in self.subscriptions:
            self.subscriptions[subscription_type].discard(user_id)
            
        # Clean up metadata
        if user_id in self.connection_metadata:
            del self.connection_metadata[user_id]
            
        logger.info(f"WebSocket disconnected: {user_id}")

    async def send_personal_message(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user."""
        if user_id not in self.connections:
            return False
            
        try:
            await self.connections[user_id].send_text(json.dumps(message))
            
            # Update last activity
            if user_id in self.connection_metadata:
                self.connection_metadata[user_id]["last_activity"] = datetime.utcnow()
                
            return True
        except Exception as e:
            logger.error(f"Failed to send message to {user_id}: {e}")
            self.disconnect(user_id)
            return False

    async def broadcast_to_subscribers(self, subscription_type: str, message: Dict[str, Any]):
        """Broadcast message to all subscribers of a specific type."""
        if subscription_type not in self.subscriptions:
            logger.warning(f"Unknown subscription type: {subscription_type}")
            return
            
        subscribers = self.subscriptions[subscription_type].copy()
        disconnected_users = []
        
        for user_id in subscribers:
            success = await self.send_personal_message(user_id, message)
            if not success:
                disconnected_users.append(user_id)
        
        # Clean up failed connections
        for user_id in disconnected_users:
            self.subscriptions[subscription_type].discard(user_id)

    async def subscribe_user(self, user_id: str, subscription_type: str, session: AsyncSession):
        """Subscribe user to specific event type."""
        if subscription_type not in self.subscriptions:
            return False
            
        self.subscriptions[subscription_type].add(user_id)
        
        # Update metadata
        if user_id in self.connection_metadata:
            if subscription_type not in self.connection_metadata[user_id]["subscriptions"]:
                self.connection_metadata[user_id]["subscriptions"].append(subscription_type)
        
        # Log subscription event
        audit_service = get_audit_service(settings)
        await audit_service.log_websocket_event(
            session=session,
            action="SUBSCRIPTION_ADDED",
            user_id=user_id,
            details={"subscription_type": subscription_type}
        )
        
        # Send confirmation
        await self.send_personal_message(user_id, {
            "type": "subscription_confirmed",
            "subscription_type": subscription_type,
            "message": f"Subscribed to {subscription_type}"
        })
        
        return True

    async def unsubscribe_user(self, user_id: str, subscription_type: str, session: AsyncSession):
        """Unsubscribe user from specific event type."""
        if subscription_type in self.subscriptions:
            self.subscriptions[subscription_type].discard(user_id)
            
        # Update metadata
        if user_id in self.connection_metadata:
            subscriptions = self.connection_metadata[user_id]["subscriptions"]
            if subscription_type in subscriptions:
                subscriptions.remove(subscription_type)
        
        # Log unsubscription event
        audit_service = get_audit_service(settings)
        await audit_service.log_websocket_event(
            session=session,
            action="SUBSCRIPTION_REMOVED",
            user_id=user_id,
            details={"subscription_type": subscription_type}
        )
        
        # Send confirmation
        await self.send_personal_message(user_id, {
            "type": "unsubscription_confirmed",
            "subscription_type": subscription_type,
            "message": f"Unsubscribed from {subscription_type}"
        })

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.connections),
            "subscriptions": {
                sub_type: len(users) for sub_type, users in self.subscriptions.items()
            },
            "connected_users": list(self.connections.keys())
        }

    # Event-specific broadcast methods
    async def broadcast_processing_update(self, job_id: UUID, status: str, progress: float, user_id: str = None):
        """Broadcast processing job update."""
        message = {
            "type": "processing_update",
            "job_id": str(job_id),
            "status": status,
            "progress": progress,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_id:
            await self.send_personal_message(user_id, message)
        else:
            await self.broadcast_to_subscribers("processing_updates", message)

    async def broadcast_document_notification(self, document_id: UUID, event_type: str, details: Dict[str, Any], user_id: str = None):
        """Broadcast document-related notification."""
        message = {
            "type": "document_notification",
            "document_id": str(document_id),
            "event_type": event_type,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_id:
            await self.send_personal_message(user_id, message)
        else:
            await self.broadcast_to_subscribers("document_notifications", message)

    async def broadcast_search_update(self, query: str, results_count: int, user_id: str = None):
        """Broadcast search-related update."""
        message = {
            "type": "search_update",
            "query": query,
            "results_count": results_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_id:
            await self.send_personal_message(user_id, message)
        else:
            await self.broadcast_to_subscribers("search_updates", message)

    async def broadcast_export_notification(self, export_id: UUID, status: str, user_id: str = None):
        """Broadcast export job notification."""
        message = {
            "type": "export_notification",
            "export_id": str(export_id),
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_id:
            await self.send_personal_message(user_id, message)
        else:
            await self.broadcast_to_subscribers("export_notifications", message)

    async def broadcast_quality_alert(self, document_id: UUID, alert_type: str, details: Dict[str, Any], user_id: str = None):
        """Broadcast quality-related alert."""
        message = {
            "type": "quality_alert",
            "document_id": str(document_id),
            "alert_type": alert_type,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if user_id:
            await self.send_personal_message(user_id, message)
        else:
            await self.broadcast_to_subscribers("quality_alerts", message)

    async def broadcast_system_notification(self, notification_type: str, message: str, severity: str = "info"):
        """Broadcast system-wide notification."""
        notification_message = {
            "type": "system_notification",
            "notification_type": notification_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast_to_subscribers("system_notifications", notification_message)


# Global broadcaster instance
ws_broadcaster = WebSocketBroadcaster()


async def websocket_handler(websocket: WebSocket, user_id: str, session: AsyncSession):
    """Main WebSocket handler for processing connections."""
    await ws_broadcaster.connect(websocket, user_id, session)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            message_type = message.get("type")
            
            if message_type == "ping":
                await ws_broadcaster.send_personal_message(user_id, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
            elif message_type == "subscribe":
                subscription_type = message.get("subscription_type")
                if subscription_type:
                    await ws_broadcaster.subscribe_user(user_id, subscription_type, session)
                    
            elif message_type == "unsubscribe":
                subscription_type = message.get("subscription_type")
                if subscription_type:
                    await ws_broadcaster.unsubscribe_user(user_id, subscription_type, session)
                    
            elif message_type == "get_status":
                stats = ws_broadcaster.get_connection_stats()
                await ws_broadcaster.send_personal_message(user_id, {
                    "type": "status_response",
                    "stats": stats,
                    "user_subscriptions": ws_broadcaster.connection_metadata.get(user_id, {}).get("subscriptions", [])
                })
                
            else:
                await ws_broadcaster.send_personal_message(user_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
                
    except WebSocketDisconnect:
        ws_broadcaster.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        ws_broadcaster.disconnect(user_id)


def get_websocket_broadcaster() -> WebSocketBroadcaster:
    """Get the global WebSocket broadcaster instance."""
    return ws_broadcaster