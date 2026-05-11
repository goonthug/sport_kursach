"""
Тесты для приложения users.
Проверяет: регистрацию клиента с NDA (152-ФЗ) и декоратор @role_required.
"""

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import AnonymousUser

from users.models import User, Client, PassportNDA
from users.decorators import role_required


class PassportNDATest(TestCase):
    """PassportNDA создаётся при регистрации клиента через view."""

    def test_nda_created_on_client_registration(self):
        """POST на /users/register/ с ролью client → запись PassportNDA."""
        data = {
            'email': 'newclient@test.com',
            'password1': 'TestPass1!',
            'password2': 'TestPass1!',
            'role': 'client',
            'full_name': 'Тест Клиент',
            'phone': '9001234567',
            'passport_series': '1234',
            'passport_number': '567890',
            'passport_issue_date': '2020-01-15',
            'passport_department_code': '123-456',
            'passport_nda_accepted': True,
        }
        response = self.client.post('/users/register/', data)
        # Проверяем редирект после успешной регистрации
        self.assertEqual(response.status_code, 302)

        user = User.objects.filter(email='newclient@test.com').first()
        self.assertIsNotNone(user)
        self.assertTrue(PassportNDA.objects.filter(user=user).exists())

    def test_nda_not_created_for_owner(self):
        """Для владельца NDA не создаётся."""
        data = {
            'email': 'newowner@test.com',
            'password1': 'TestPass1!',
            'password2': 'TestPass1!',
            'role': 'owner',
            'full_name': 'Тест Владелец',
            'phone': '9007654321',
            'tax_number': '123456789012',
        }
        self.client.post('/users/register/', data)
        user = User.objects.filter(email='newowner@test.com').first()
        if user:
            self.assertFalse(PassportNDA.objects.filter(user=user).exists())


class RoleRequiredDecoratorTest(TestCase):
    """Декоратор @role_required блокирует неверные роли."""

    def setUp(self):
        self.factory = RequestFactory()
        self.owner_user = User.objects.create_user(
            email='owner@test.com', password='Pass1234!', role='owner'
        )
        self.client_user = User.objects.create_user(
            email='client@test.com', password='Pass1234!', role='client'
        )

    def test_correct_role_passes(self):
        """Пользователь с правильной ролью получает доступ."""
        @role_required('owner')
        def dummy_view(request):
            from django.http import HttpResponse
            return HttpResponse('OK')

        request = self.factory.get('/')
        request.user = self.owner_user
        response = dummy_view(request)
        self.assertEqual(response.status_code, 200)

    def test_wrong_role_redirects(self):
        """Пользователь с неверной ролью получает редирект."""
        @role_required('owner')
        def dummy_view(request):
            from django.http import HttpResponse
            return HttpResponse('OK')

        request = self.factory.get('/')
        request.user = self.client_user
        # role_required использует messages framework — нужна session middleware
        # Проверяем что вернулся не 200
        from django.contrib.messages.storage.fallback import FallbackStorage
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        response = dummy_view(request)
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_redirects_to_login(self):
        """Анонимный пользователь редиректится на страницу входа."""
        @role_required('owner')
        def dummy_view(request):
            from django.http import HttpResponse
            return HttpResponse('OK')

        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = dummy_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response['Location'])
