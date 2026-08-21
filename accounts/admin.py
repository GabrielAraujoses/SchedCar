from django.contrib import admin

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ['employee_id']
    list_display = ['employee_id', 'get_full_name', 'email', 'role', 'is_active', 'is_staff']
    list_filter = ['role', 'is_active']
    search_fields = ['employee_id', 'first_name', 'last_name', 'email']
    fieldsets = (
        (None, {'fields': ('employee_id', 'password')}),
        ('Dados pessoais', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Perfil', {'fields': ('role',)}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('employee_id', 'email', 'role', 'password1', 'password2')}),
    )
