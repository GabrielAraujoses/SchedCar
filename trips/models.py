from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from vehicles.models import Vehicle


class ReferenceNumberCounter(models.Model):
	"""Garante um protocolo sequencial sem colisão, reiniciando a cada ano."""

	year = models.PositiveIntegerField('Ano', unique=True)
	last_number = models.PositiveIntegerField('Último número emitido', default=0)

	def __str__(self):
		return f'{self.year} -> {self.last_number:09d}'


class Trip(models.Model):
	MINIMUM_LEAD_BUSINESS_DAYS = 3
	OPERATIONAL_INTERVAL = timedelta(hours=2)

	class Status(models.TextChoices):
		PENDING = 'pending', 'Pendente de aprovação'
		APPROVED = 'approved', 'Aprovada'
		REJECTED = 'rejected', 'Rejeitada'
		IN_PROGRESS = 'in_progress', 'Em andamento'
		COMPLETED = 'completed', 'Concluída'
		CANCELLED = 'cancelled', 'Cancelada'

	ACTIVE_STATUSES = [Status.PENDING, Status.APPROVED, Status.IN_PROGRESS]

	reference_number = models.CharField(
		'Protocolo', max_length=15, unique=True, blank=True, editable=False,
	)

	employee = models.ForeignKey(
		settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
		related_name='requested_trips', limit_choices_to={'role': 'employee'},
		verbose_name='Colaborador',
	)
	driver = models.ForeignKey(
		settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
		related_name='trips_as_driver', limit_choices_to={'role': 'driver'},
		null=True, blank=True, verbose_name='Motorista',
	)
	vehicle = models.ForeignKey(
		Vehicle, on_delete=models.PROTECT, related_name='trips',
		null=True, blank=True, verbose_name='Veículo',
	)

	department = models.CharField('Setor', max_length=100)
	purpose = models.CharField('Atividade', max_length=255)
	origin = models.CharField('Origem', max_length=150)
	destination = models.CharField('Destino', max_length=150)
	date = models.DateField('Data da viagem')
	departure_time = models.TimeField('Horário de saída')
	expected_return = models.DateTimeField('Previsão de retorno')
	passenger_count = models.PositiveSmallIntegerField('Quantidade de passageiros')

	status = models.CharField('Status', max_length=20, choices=Status.choices, default=Status.PENDING)
	approved_by = models.ForeignKey(
		settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
		related_name='approved_trips', limit_choices_to={'role': 'manager'},
		verbose_name='Aprovado por',
	)
	rejection_reason = models.CharField('Motivo da rejeição', max_length=255, blank=True)

	requested_at = models.DateTimeField('Solicitado em', auto_now_add=True)
	updated_at = models.DateTimeField('Atualizado em', auto_now=True)

	class Meta:
		ordering = ['-requested_at']

	def __str__(self):
		return f'{self.reference_number or "(sem protocolo)"} - {self.destination}'

	@property
	def can_be_cancelled(self):
		return self.status in (self.Status.PENDING, self.Status.APPROVED)

	def _time_range(self):
		departure = timezone.datetime.combine(self.date, self.departure_time)
		if timezone.is_naive(departure):
			departure = timezone.make_aware(departure)
		return departure, self.expected_return

	@classmethod
	def minimum_departure_datetime(cls):
		"""Retorna o primeiro horário aceito após três dias úteis, sem feriados."""
		now = timezone.localtime()
		minimum_date = now.date()
		business_days = 0

		while business_days < cls.MINIMUM_LEAD_BUSINESS_DAYS:
			minimum_date += timedelta(days=1)
			if minimum_date.weekday() < 5:
				business_days += 1

		return timezone.make_aware(
			timezone.datetime.combine(minimum_date, now.timetz().replace(tzinfo=None))
		)

	def clean(self):
		errors = {}

		if self.date and self.departure_time and self.expected_return:
			departure, return_time = self._time_range()
			now = timezone.localtime()
			if departure <= now:
				errors['date'] = 'A data e o horário de saída devem estar no futuro.'
			elif departure < self.minimum_departure_datetime():
				minimum = self.minimum_departure_datetime()
				errors['date'] = (
					'Solicitações devem ser feitas com pelo menos 3 dias úteis de antecedência. '
					f'O primeiro horário disponível é {minimum.strftime("%d/%m/%Y às %H:%M")}.'
				)
			if return_time <= departure:
				errors['expected_return'] = 'A previsão de retorno deve ser depois do horário de saída.'

		if self.passenger_count is not None and self.passenger_count < 1:
			errors['passenger_count'] = 'Informe pelo menos 1 passageiro.'

		if self.vehicle_id and self.passenger_count and self.vehicle:
			if self.passenger_count > self.vehicle.capacity:
				errors['passenger_count'] = (
					f'O veículo comporta no máximo {self.vehicle.capacity} passageiros.'
				)

		if self.vehicle_id and self.date and self.departure_time and self.expected_return:
			if self._has_conflict('vehicle', self.vehicle_id):
				errors['vehicle'] = 'Este veículo já está reservado nesse período (conflito de agendamento).'

		if self.driver_id and self.date and self.departure_time and self.expected_return:
			if self._has_conflict('driver', self.driver_id):
				errors['driver'] = 'Este motorista já está escalado nesse período.'

		if errors:
			raise ValidationError(errors)

	def _has_conflict(self, field_name, value):
		"""Compara períodos de viagem incluindo o intervalo operacional de 2 horas."""
		departure, return_time = self._time_range()
		candidates = Trip.objects.filter(
			**{field_name: value}, status__in=self.ACTIVE_STATUSES
		).exclude(pk=self.pk)

		for other in candidates:
			other_departure, other_return = other._time_range()
			if (
				departure < other_return + self.OPERATIONAL_INTERVAL
				and other_departure < return_time + self.OPERATIONAL_INTERVAL
			):
				return True
		return False

	@staticmethod
	def generate_reference_number():
		"""Formato 000000001/2026, reiniciando a cada ano."""
		current_year = timezone.localdate().year
		with transaction.atomic():
			counter, _ = ReferenceNumberCounter.objects.select_for_update().get_or_create(year=current_year)
			counter.last_number += 1
			counter.save(update_fields=['last_number'])
			return f'{counter.last_number:09d}/{current_year}'

	def save(self, *args, **kwargs):
		if not self.reference_number:
			self.reference_number = self.generate_reference_number()
		super().save(*args, **kwargs)

	def approve(self, manager, vehicle=None, driver=None):
		if vehicle is not None:
			self.vehicle = vehicle
		if driver is not None:
			self.driver = driver
		self.status = self.Status.APPROVED
		self.approved_by = manager
		self.full_clean()
		self.save()

	def reject(self, manager, reason=''):
		self.status = self.Status.REJECTED
		self.approved_by = manager
		self.rejection_reason = reason
		self.save(update_fields=['status', 'approved_by', 'rejection_reason', 'updated_at'])

	def start(self):
		self.status = self.Status.IN_PROGRESS
		self.save(update_fields=['status', 'updated_at'])

	def complete(self):
		self.status = self.Status.COMPLETED
		self.save(update_fields=['status', 'updated_at'])
		if self.vehicle_id:
			self.vehicle.status = Vehicle.Status.AVAILABLE
			self.vehicle.save(update_fields=['status'])

	def cancel(self):
		self.status = self.Status.CANCELLED
		self.save(update_fields=['status', 'updated_at'])

	@classmethod
	def sync_automatic_statuses(cls):
		"""Atualiza viagens aprovadas conforme os horários planejados."""
		now = timezone.now()
		for trip in cls.objects.select_related('vehicle').filter(
			status__in=[cls.Status.APPROVED, cls.Status.IN_PROGRESS]
		):
			departure, return_time = trip._time_range()
			if now >= return_time:
				trip.complete()
			elif trip.status == cls.Status.APPROVED and now >= departure:
				trip.start()
				if trip.vehicle_id and trip.vehicle.status != Vehicle.Status.ON_TRIP:
					trip.vehicle.status = Vehicle.Status.ON_TRIP
					trip.vehicle.save(update_fields=['status'])
