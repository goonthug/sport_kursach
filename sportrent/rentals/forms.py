"""
Формы для управления арендой.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import Rental


class RentalCreateForm(forms.ModelForm):
    """Форма создания заявки на аренду."""

    start_date = forms.DateField(
        label='Дата начала',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'min': timezone.now().date().isoformat()
        })
    )

    end_date = forms.DateField(
        label='Дата окончания',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

    notes = forms.CharField(
        label='Примечания (необязательно)',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Укажите особые пожелания или вопросы'
        })
    )

    class Meta:
        model = Rental
        fields = ['start_date', 'end_date', 'notes']

    def __init__(self, *args, **kwargs):
        self.inventory = kwargs.pop('inventory', None)
        super().__init__(*args, **kwargs)

    def clean_start_date(self):
        """Валидация даты начала."""
        start_date = self.cleaned_data.get('start_date')

        if start_date < timezone.now().date():
            raise ValidationError('Дата начала не может быть в прошлом')

        return start_date

    def clean(self):
        """Комплексная валидация дат."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            # Проверка что end_date после start_date
            if end_date <= start_date:
                raise ValidationError('Дата окончания должна быть после даты начала')

            # Рассчитываем количество дней
            rental_days = (end_date - start_date).days

            # Проверка минимального и максимального срока
            if self.inventory:
                if rental_days < self.inventory.min_rental_days:
                    raise ValidationError(
                        f'Минимальный срок аренды для этого инвентаря: {self.inventory.min_rental_days} дней'
                    )

                if rental_days > self.inventory.max_rental_days:
                    raise ValidationError(
                        f'Максимальный срок аренды для этого инвентаря: {self.inventory.max_rental_days} дней'
                    )

                # Проверка что инвентарь свободен в эти даты
                overlapping = Rental.objects.filter(
                    inventory=self.inventory,
                    status__in=['confirmed', 'active']
                ).filter(
                    start_date__lt=end_date,
                    end_date__gt=start_date
                )

                if overlapping.exists():
                    raise ValidationError('Инвентарь уже забронирован на эти даты')

        return cleaned_data


class RentalUpdateForm(forms.ModelForm):
    """Форма редактирования аренды (для менеджеров)."""

    class Meta:
        model = Rental
        fields = ['status', 'notes', 'rejection_reason']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'rejection_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }