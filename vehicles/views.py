from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.mixins import ManagerRequiredMixin
from .forms import VehicleForm
from .models import Vehicle


class VehicleListView(LoginRequiredMixin, ListView):
	"""Qualquer usuário logado pode consultar a frota."""

	model = Vehicle
	template_name = 'vehicles/vehicle_list.html'
	context_object_name = 'vehicles'
	paginate_by = 20

	def get_queryset(self):
		queryset = Vehicle.objects.all()
		status = self.request.GET.get('status')
		if status:
			queryset = queryset.filter(status=status)
		return queryset

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['status_choices'] = Vehicle.Status.choices
		return context


class VehicleCreateView(ManagerRequiredMixin, CreateView):
	model = Vehicle
	form_class = VehicleForm
	template_name = 'vehicles/vehicle_form.html'
	success_url = reverse_lazy('vehicles:list')

	def form_valid(self, form):
		messages.success(self.request, 'Veículo cadastrado com sucesso.')
		return super().form_valid(form)


class VehicleUpdateView(ManagerRequiredMixin, UpdateView):
	model = Vehicle
	form_class = VehicleForm
	template_name = 'vehicles/vehicle_form.html'
	success_url = reverse_lazy('vehicles:list')

	def form_valid(self, form):
		messages.success(self.request, 'Veículo atualizado com sucesso.')
		return super().form_valid(form)


class VehicleDeleteView(ManagerRequiredMixin, DeleteView):
	model = Vehicle
	template_name = 'vehicles/vehicle_confirm_delete.html'
	success_url = reverse_lazy('vehicles:list')
