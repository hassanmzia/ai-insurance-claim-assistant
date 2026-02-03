"""WebSocket consumers for real-time updates."""
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class ClaimConsumer(AsyncWebsocketConsumer):
    """Real-time updates for a specific claim."""

    async def connect(self):
        self.claim_id = self.scope['url_route']['kwargs']['claim_id']
        self.room_group_name = f'claim_{self.claim_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def claim_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'claim_update',
            'data': event['data'],
        }))

    async def agent_progress(self, event):
        await self.send(text_data=json.dumps({
            'type': 'agent_progress',
            'data': event['data'],
        }))


class NotificationConsumer(AsyncWebsocketConsumer):
    """Real-time notifications for the current user."""

    async def connect(self):
        self.user = self.scope.get('user')
        if self.user and self.user.is_authenticated:
            self.room_group_name = f'notifications_{self.user.id}'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def new_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data'],
        }))


class DashboardConsumer(AsyncWebsocketConsumer):
    """Real-time dashboard metric updates."""

    async def connect(self):
        self.room_group_name = 'dashboard_updates'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def dashboard_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'data': event['data'],
        }))
