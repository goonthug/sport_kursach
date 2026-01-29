import json

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

from rentals.models import Rental
from users.models import User
from .models import ChatMessage


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.rental_id = self.scope['url_route']['kwargs']['rental_id']

        if not self.user.is_authenticated:
            await self.close()
            return

        has_access, other_user_id = await self._check_access()
        if not has_access:
            await self.close()
            return

        self.other_user_id = other_user_id
        self.room_group_name = f'chat_{self.rental_id}'

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self._mark_messages_read()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if self.user.role == 'administrator':
            return

        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        message_text = (data.get('message') or '').strip()
        if not message_text:
            return

        if not self.other_user_id:
            return

        message = await self._create_message(message_text)
        payload = await self._serialize_message(message)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                'message': payload,
            }
        )

        await self.channel_layer.group_send(
            self._user_group_name(self.other_user_id),
            {
                'type': 'notify.message',
                'message': {
                    'title': f'Новое сообщение от {payload["sender_name"]}',
                    'body': f'{payload["inventory_name"]}: {payload["text_preview"]}',
                    'url': f'/chat/{self.rental_id}/',
                },
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat.message',
            'message': event['message'],
        }))

    async def notify_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notify.message',
            'message': event['message'],
        }))

    @database_sync_to_async
    def _check_access(self):
        rental = Rental.objects.select_related('client__user', 'manager__user').filter(pk=self.rental_id).first()
        if not rental:
            return False, None

        user = self.user
        other_user_id = None

        if user.role == 'client' and hasattr(user, 'client_profile'):
            if rental.client == user.client_profile:
                other_user_id = rental.manager.user_id if rental.manager else None
                return True, other_user_id
            return False, None

        if user.role == 'manager' and hasattr(user, 'manager_profile'):
            if rental.manager == user.manager_profile:
                other_user_id = rental.client.user_id
                return True, other_user_id
            return False, None

        if user.role == 'administrator':
            return True, None

        return False, None

    @database_sync_to_async
    def _mark_messages_read(self):
        ChatMessage.objects.filter(
            rental_id=self.rental_id,
            receiver=self.user,
            is_read=False
        ).update(is_read=True, read_date=timezone.now())

    @database_sync_to_async
    def _create_message(self, text):
        rental = Rental.objects.select_related('client__user', 'manager__user').get(pk=self.rental_id)
        receiver = User.objects.get(user_id=self.other_user_id)

        return ChatMessage.objects.create(
            rental=rental,
            sender=self.user,
            receiver=receiver,
            message_text=text,
            message_type='text'
        )

    @database_sync_to_async
    def _serialize_message(self, message):
        inventory_name = message.rental.inventory.name
        return {
            'message_id': str(message.message_id),
            'sender_id': str(message.sender.user_id),
            'sender_name': message.sender.get_full_name(),
            'text': message.message_text,
            'text_preview': message.message_text[:120],
            'sent_date': message.sent_date.isoformat(),
            'is_read': message.is_read,
            'inventory_name': inventory_name,
        }

    @staticmethod
    def _user_group_name(user_id):
        return f'user_{user_id}'


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f'user_{self.user.user_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notify_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notify.message',
            'message': event['message'],
        }))
