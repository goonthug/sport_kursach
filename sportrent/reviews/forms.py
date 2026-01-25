"""
Формы для системы отзывов.
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Review


class ReviewForm(forms.ModelForm):
    """Форма создания отзыва."""

    rating = forms.IntegerField(
        label='Общая оценка',
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '5'
        }),
        help_text='От 1 до 5 звезд'
    )

    comment = forms.CharField(
        label='Ваш отзыв',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Расскажите о своем опыте аренды...'
        }),
        help_text='Минимум 20 символов'
    )

    punctuality_rating = forms.IntegerField(
        label='Пунктуальность',
        min_value=1,
        max_value=5,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '5'
        })
    )

    condition_rating = forms.IntegerField(
        label='Состояние инвентаря',
        min_value=1,
        max_value=5,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '5'
        })
    )

    communication_rating = forms.IntegerField(
        label='Качество общения',
        min_value=1,
        max_value=5,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '5'
        })
    )

    class Meta:
        model = Review
        fields = [
            'rating', 'comment',
            'punctuality_rating', 'condition_rating', 'communication_rating'
        ]

    def clean_comment(self):
        """Валидация комментария."""
        comment = self.cleaned_data.get('comment', '').strip()

        if len(comment) < 20:
            raise ValidationError('Отзыв должен содержать минимум 20 символов')

        if len(comment) > 1000:
            raise ValidationError('Отзыв не должен превышать 1000 символов')

        return comment