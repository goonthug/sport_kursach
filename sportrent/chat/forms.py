"""
Формы для системы чата.
"""

from django import forms
from .models import ChatMessage


class ChatMessageForm(forms.ModelForm):
    """Форма отправки сообщения."""

    message_text = forms.CharField(
        label='Сообщение',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Напишите сообщение...'
        }),
        required=True
    )

    file_url = forms.FileField(
        label='Прикрепить файл (необязательно)',
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = ChatMessage
        fields = ['message_text', 'file_url']

    def clean_message_text(self):
        """Валидация сообщения."""
        text = self.cleaned_data.get('message_text', '').strip()

        if len(text) < 1:
            raise forms.ValidationError('Сообщение не может быть пустым')

        if len(text) > 1000:
            raise forms.ValidationError('Сообщение не должно превышать 1000 символов')

        return text