from django.db import models

from django.core.validators import RegexValidator
from django.db import models


def vehicle_photo_path(instance, filename):
    return f'vehicles/{instance.license_plate}/{filename}'


class Brand(models.Model):
    name = models.CharField('Marca', max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Disponível'
        ON_TRIP = 'on_trip', 'Em viagem'
        MAINTENANCE = 'maintenance', 'Em manutenção'
        INACTIVE = 'inactive', 'Inativo'

    license_plate_validator = RegexValidator(
        regex=r'^[A-Za-z]{3}-?\d[A-Za-z0-9]\d{2}$',
        message='Informe uma placa válida (ex: ABC-1234 ou ABC1D23).',
    )

    name = models.CharField('Nome do carro', max_length=100)
    brand = models.ForeignKey(
        Brand, on_delete=models.PROTECT, related_name='vehicles',
        null=True, blank=True, verbose_name='Marca',
    )
    license_plate = models.CharField(
        'Placa', max_length=8, unique=True, validators=[license_plate_validator],
    )
    capacity = models.PositiveSmallIntegerField('Capacidade de passageiros')
    status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.AVAILABLE)

    # Foto do carro — exige a biblioteca Pillow (pip install pillow).
    # Só o Gerente consegue enviar/alterar (restrição fica na view).
    photo = models.ImageField(
        'Foto do carro', upload_to=vehicle_photo_path, blank=True, null=True,
    )

    is_active = models.BooleanField('Ativo', default=True)
    created_at = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} - {self.license_plate.upper()}'

    def save(self, *args, **kwargs):
        self.license_plate = self.license_plate.upper()
        super().save(*args, **kwargs)
