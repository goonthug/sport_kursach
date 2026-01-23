"""
Модели для системы внутренних сообщений (чата).
"""

import uuid
from django.db import models
from django.utils import timezone
from users.models import User
from rentals.models import Rental


class ChatMessage(models.Model):
    """Сообщения в чате между клиентом и менеджером."""

    MESSAGE_TYPE_CHOICES = [
        ('text', 'Текст'),
        ('file', 'Файл'),
        ('system', 'Системное'),
    ]

    message_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rental = models.ForeignKey(Rental, on_delete=models.CASCADE, related_name='chat_messages', verbose_name='Аренда')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='Отправитель')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages',
                                 verbose_name='Получатель')

    message_text = models.TextField(verbose_name='Текст сообщения')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text',
                                    verbose_name='Тип сообщения')
    file_url = models.FileField(upload_to='chat_files/', blank=True, null=True, verbose_name='Файл')

    sent_date = models.DateTimeField(default=timezone.now, verbose_name='Дата отправки')
    read_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата прочтения')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')

    class Meta:
        db_table = 'chat_messages'
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['sent_date']
        indexes = [
            models.Index(fields=['rental', 'sent_date']),
            models.Index(fields=['sender', 'receiver']),
        ]

    def __str__(self):
        return f"Сообщение от {self.sender.email} к {self.receiver.email}"

    def mark_as_read(self):
        """Отметить сообщение как прочитанное."""
        if not self.is_read:
            self.is_read = True
            self.read_date = timezone.now()
            self.save(update_fields=['is_read', 'read_date'])