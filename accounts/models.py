from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYEE = 'employee', 'Colaborador'
        MANAGER = 'manager', 'Gerente'
        DRIVER = 'driver', 'Motorista'

    username = None  # login é pelo employee_id (matrícula)

    employee_id_validator = RegexValidator(
        regex=r'^\d{1,10}$',
        message='A matrícula deve conter apenas números (até 10 dígitos).',
    )

    employee_id = models.CharField(
        'Matrícula', max_length=10, unique=True, validators=[employee_id_validator],
    )
    email = models.EmailField('E-mail', unique=True)
    role = models.CharField('Papel', max_length=20, choices=Role.choices)
    phone_number = models.CharField('Telefone', max_length=20, blank=True)
    created_at = models.DateTimeField('Criado em', auto_now_add=True)

    USERNAME_FIELD = 'employee_id'
    REQUIRED_FIELDS = ['email']

    objects = UserManager()

    def __str__(self):
        name = self.get_full_name() or self.employee_id
        return f'{name} ({self.get_role_display()})'

    @property
    def is_employee(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_driver(self):
        return self.role == self.Role.DRIVER