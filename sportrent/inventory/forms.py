"""
Формы для управления инвентарем.
"""

from django import forms
from django.forms import inlineformset_factory
from .models import Inventory, InventoryPhoto, SportCategory


class InventoryForm(forms.ModelForm):
    """
    Форма создания/редактирования инвентаря владельцем.
    Залог не указывается владельцем, его задает менеджер при одобрении заявки.
    """

    class Meta:
        model = Inventory
        fields = [
            'category', 'name', 'description', 'brand', 'model',
            'price_per_day', 'condition', 'min_rental_days',
            'max_rental_days',
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название инвентаря'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Детальное описание'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Бренд'}),
            'model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Модель'}),
            'price_per_day': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'min_rental_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'max_rental_days': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
        labels = {
            'category': 'Категория',
            'name': 'Название',
            'description': 'Описание',
            'brand': 'Бренд',
            'model': 'Модель',
            'price_per_day': 'Цена за день (руб.)',
            'condition': 'Состояние',
            'min_rental_days': 'Минимум дней аренды',
            'max_rental_days': 'Максимум дней аренды',
        }

    def clean(self):
        """Дополнительная валидация."""
        cleaned_data = super().clean()
        min_days = cleaned_data.get('min_rental_days')
        max_days = cleaned_data.get('max_rental_days')

        if min_days and max_days and min_days > max_days:
            raise forms.ValidationError('Минимальный срок аренды не может быть больше максимального.')

        return cleaned_data


class InventoryPhotoForm(forms.ModelForm):
    """Форма для загрузки фотографий инвентаря."""

    class Meta:
        model = InventoryPhoto
        fields = ['photo_url', 'is_main', 'description']
        widgets = {
            'photo_url': forms.FileInput(attrs={'class': 'form-control'}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Описание фото'}),
        }
        labels = {
            'photo_url': 'Фотография',
            'is_main': 'Основное фото',
            'description': 'Описание',
        }


# Formset для множественной загрузки фотографий
InventoryPhotoFormSet = inlineformset_factory(
    Inventory,
    InventoryPhoto,
    form=InventoryPhotoForm,
    extra=3,
    max_num=10,
    can_delete=True,
    validate_max=True
)


class InventoryFilterForm(forms.Form):
    """Форма для фильтрации инвентаря."""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по названию, бренду...'
        })
    )

    category = forms.ModelChoiceField(
        queryset=SportCategory.objects.all(),
        required=False,
        empty_label='Все категории',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    condition = forms.ChoiceField(
        choices=[('', 'Любое состояние')] + list(Inventory.CONDITION_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'От',
            'step': '0.01'
        })
    )

    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'До',
            'step': '0.01'
        })
    )

    sort = forms.ChoiceField(
        choices=[
            ('newest', 'Новые'),
            ('price_asc', 'Цена: по возрастанию'),
            ('price_desc', 'Цена: по убыванию'),
            ('name', 'По названию'),
            ('rating', 'По рейтингу'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )