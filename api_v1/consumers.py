import json
import asyncio
import threading
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from . import notifications


class NotificationsConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notification events.
    Connect to: ws://127.0.0.1:8000/ws/notifications/
    """
    
    async def connect(self):
        self.user = self.scope.get("user")
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        self.user_id = self.user.id
        self.queue = notifications.subscribe(self.user_id)
        self.is_listening = True
        
        await self.accept()
        
        # Start listening for notifications in a background task
        asyncio.create_task(self._listen_for_notifications())
    
    async def disconnect(self, close_code):
        self.is_listening = False
        notifications.unsubscribe(self.user_id)
    
    async def _listen_for_notifications(self):
        """Background task to listen for notification events"""
        while self.is_listening:
            try:
                try:
                    ev = self.queue.get(timeout=1)
                except Exception:
                    continue
                
                if not ev:
                    continue
                
                # Check for close signal
                if ev.get('type') == 'closed':
                    break
                
                # Send notification to WebSocket
                await self.send(text_data=json.dumps(ev))
                
            except Exception as e:
                # Log error but continue listening
                print(f"WebSocket error: {e}")
                break
    
    async def receive(self, text_data):
        """Handle incoming messages from WebSocket client"""
        try:
            data = json.loads(text_data)
            # Handle any client messages if needed
        except json.JSONDecodeError:
            pass