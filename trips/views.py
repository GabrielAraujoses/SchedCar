from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import DriverRequiredMixin, EmployeeRequiredMixin, ManagerRequiredMixin
from vehicles.models import Vehicle
from . import notifications
from .forms import TripRequestForm
from .models import Trip
from .services import allocate_trip


class TripRequestView(EmployeeRequiredMixin, CreateView):
	model = Trip
	form_class = TripRequestForm
	template_name = 'trips/trip_form.html'

	def form_valid(self, form):
		trip = form.save(commit=False)
		trip.employee = self.request.user
		try:
			trip.full_clean()
		except ValidationError as error:
			for field, errors in error.message_dict.items():
				for message in errors:
					form.add_error(field if field in form.fields else None, message)
			return self.form_invalid(form)

		vehicle, driver, rejection_reason = allocate_trip(trip)
		if vehicle and driver:
			trip.vehicle = vehicle
			trip.driver = driver
			trip.status = Trip.Status.APPROVED
			try:
				trip.full_clean()
			except ValidationError as error:
				for field, errors in error.message_dict.items():
					for message in errors:
						form.add_error(field if field in form.fields else None, message)
				return self.form_invalid(form)
		else:
			trip.status = Trip.Status.REJECTED
			trip.rejection_reason = rejection_reason

		trip.save()
		notifications.notify_reference_number_issued(trip)
		notifications.notify_approval_result(trip)
		if trip.status == Trip.Status.APPROVED:
			messages.success(
				self.request,
				f'Solicitação aprovada automaticamente. Protocolo: {trip.reference_number}. '
				f'Veículo: {trip.vehicle}. Motorista: {trip.driver}.',
			)
		else:
			messages.error(
				self.request,
				f'Solicitação não aprovada. Motivo: {trip.rejection_reason}',
			)
		return redirect('trips:detail', pk=trip.pk)


class TripListView(LoginRequiredMixin, ListView):
	model = Trip
	template_name = 'trips/trip_list.html'
	context_object_name = 'trips'
	paginate_by = 20

	def get_queryset(self):
		Trip.sync_automatic_statuses()
		user = self.request.user
		queryset = Trip.objects.select_related('employee', 'driver', 'vehicle')
		if user.is_employee:
			queryset = queryset.filter(employee=user)
		elif user.is_driver:
			queryset = queryset.filter(driver=user)
		status = self.request.GET.get('status')
		if status:
			queryset = queryset.filter(status=status)
		return queryset

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['status_choices'] = Trip.Status.choices
		return context


class TripDetailView(LoginRequiredMixin, DetailView):
	model = Trip
	template_name = 'trips/trip_detail.html'
	context_object_name = 'trip'

	def get_queryset(self):
		Trip.sync_automatic_statuses()
		user = self.request.user
		queryset = Trip.objects.select_related('employee', 'driver', 'vehicle')
		if user.is_employee:
			return queryset.filter(employee=user)
		if user.is_driver:
			return queryset.filter(driver=user)
		return queryset


class TripUpdateView(ManagerRequiredMixin, UpdateView):
	model = Trip
	form_class = TripRequestForm
	template_name = 'trips/trip_form.html'

	def get_queryset(self):
		return Trip.objects.filter(status__in=[Trip.Status.PENDING, Trip.Status.APPROVED])

	def form_valid(self, form):
		trip = form.save(commit=False)
		try:
			trip.full_clean()
		except ValidationError as error:
			for field, errors in error.message_dict.items():
				for message in errors:
					form.add_error(field if field in form.fields else None, message)
			return self.form_invalid(form)
		trip.save()
		messages.success(self.request, 'Pedido atualizado com sucesso.')
		return redirect('trips:detail', pk=trip.pk)

class TripStartView(DriverRequiredMixin, View):
	http_method_names = ['post']

	def post(self, request, *args, **kwargs):
		trip = get_object_or_404(
			Trip, pk=kwargs['pk'], driver=request.user, status=Trip.Status.APPROVED,
		)
		trip.start()
		messages.success(request, f'Viagem {trip.reference_number} iniciada.')
		return redirect('trips:detail', pk=trip.pk)


class TripCompleteView(DriverRequiredMixin, View):
	http_method_names = ['post']

	def post(self, request, *args, **kwargs):
		trip = get_object_or_404(
			Trip, pk=kwargs['pk'], driver=request.user, status=Trip.Status.IN_PROGRESS,
		)
		trip.complete()
		messages.success(request, f'Viagem {trip.reference_number} concluída.')
		return redirect('trips:detail', pk=trip.pk)


class TripCancelView(EmployeeRequiredMixin, View):
	http_method_names = ['post']

	def post(self, request, *args, **kwargs):
		trip = get_object_or_404(
			Trip, pk=kwargs['pk'], employee=request.user,
			status__in=[Trip.Status.PENDING, Trip.Status.APPROVED],
		)
		trip.cancel()
		if trip.vehicle_id and trip.vehicle.status == Vehicle.Status.ON_TRIP:
			trip.vehicle.status = Vehicle.Status.AVAILABLE
			trip.vehicle.save(update_fields=['status'])
		messages.success(request, f'Viagem {trip.reference_number} cancelada.')
		return redirect('trips:detail', pk=trip.pk)
