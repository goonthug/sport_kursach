"""
Сериализаторы для REST API пользователей.
"""

from rest_framework import serializers
from .models import User, Client, Owner


class UserSerializer(serializers.ModelSerializer):
    """Публичный профиль пользователя."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'user_id', 'email', 'phone', 'role', 'status',
            'avg_rating', 'loyalty_points', 'full_name', 'avatar_url',
            'registration_date',
        ]
        read_only_fields = ['user_id', 'role', 'status', 'avg_rating', 'registration_date']

    def get_full_name(self, obj):
        return obj.get_full_name()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=['client', 'owner'])
    full_name = serializers.CharField(max_length=200)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)

    # Поля клиента (обязательны для role='client')
    passport_series = serializers.CharField(max_length=4, required=False, allow_blank=True)
    passport_number = serializers.CharField(max_length=6, required=False, allow_blank=True)
    passport_issue_date = serializers.DateField(required=False, allow_null=True)
    passport_department_code = serializers.CharField(max_length=7, required=False, allow_blank=True)
    passport_nda_accepted = serializers.BooleanField(required=False, default=False)

    # Поля владельца
    tax_number = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Пользователь с таким email уже существует')
        return value

    def validate(self, data):
        if data['role'] == 'client' and not data.get('passport_nda_accepted'):
            raise serializers.ValidationError({
                'passport_nda_accepted': 'Необходимо принять соглашение на обработку паспортных данных (152-ФЗ)'
            })
        return data
