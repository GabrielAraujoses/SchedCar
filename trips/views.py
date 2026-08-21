from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from core.mixins import DriverRequiredMixin, EmployeeRequiredMixin, ManagerRequiredMixin
from vehicles.models import Vehicle
from . import notifications
from .forms import TripApprovalForm, TripRejectionForm, TripRequestForm
from .models import Trip


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

		trip.save()
		notifications.notify_reference_number_issued(trip)
		notifications.notify_managers_new_request(trip)
		messages.success(self.request, f'Solicitação registrada! Protocolo: {trip.reference_number}')
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

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['approval_form'] = TripApprovalForm()
		context['rejection_form'] = TripRejectionForm()
		return context


class TripApproveView(ManagerRequiredMixin, View):
	http_method_names = ['post']

	def post(self, request, *args, **kwargs):
		trip = get_object_or_404(Trip, pk=kwargs['pk'])
		form = TripApprovalForm(request.POST)

		if trip.status != Trip.Status.PENDING:
			messages.warning(request, 'Esta viagem já foi processada.')
			return redirect('trips:detail', pk=trip.pk)

		if form.is_valid():
			vehicle, driver = form.cleaned_data['vehicle'], form.cleaned_data['driver']
			try:
				trip.approve(manager=request.user, vehicle=vehicle, driver=driver)
			except ValidationError as error:
				for errors in error.message_dict.values():
					for message in errors:
						messages.error(request, message)
				return redirect('trips:detail', pk=trip.pk)

			vehicle.status = Vehicle.Status.ON_TRIP
			vehicle.save(update_fields=['status'])
			notifications.notify_approval_result(trip)
			messages.success(request, f'Viagem {trip.reference_number} aprovada.')
		else:
			messages.error(request, 'Selecione um veículo e um motorista válidos.')
		return redirect('trips:detail', pk=trip.pk)


class TripRejectView(ManagerRequiredMixin, View):
	http_method_names = ['post']

	def post(self, request, *args, **kwargs):
		trip = get_object_or_404(Trip, pk=kwargs['pk'])
		form = TripRejectionForm(request.POST)
		if trip.status != Trip.Status.PENDING:
			messages.warning(request, 'Esta viagem já foi processada.')
			return redirect('trips:detail', pk=trip.pk)
		if form.is_valid():
			trip.reject(manager=request.user, reason=form.cleaned_data['rejection_reason'])
			notifications.notify_approval_result(trip)
			messages.success(request, f'Viagem {trip.reference_number} rejeitada.')
		else:
			messages.error(request, 'Informe o motivo da rejeição.')
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
