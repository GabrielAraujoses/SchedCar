from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from vehicles.models import Vehicle
from trips.models import Trip


@login_required
def dashboard(request):
	Trip.sync_automatic_statuses()
	user = request.user
	context = {}

	if user.is_employee:
		my_trips = Trip.objects.filter(employee=user).order_by('-requested_at')
		context['trips'] = my_trips[:10]
		context['pending_count'] = my_trips.filter(status=Trip.Status.PENDING).count()

	elif user.is_manager:
		pending = Trip.objects.filter(status=Trip.Status.PENDING).order_by('date')
		context['pending_trips'] = pending
		context['pending_count'] = pending.count()
		context['available_vehicles_count'] = Vehicle.objects.filter(
			status=Vehicle.Status.AVAILABLE, is_active=True
		).count()
		context['active_trips_today'] = Trip.objects.filter(
			date=timezone.localdate(), status__in=Trip.ACTIVE_STATUSES
		).count()
		from django.contrib.auth import get_user_model

		User = get_user_model()
		context['total_users'] = User.objects.count()
		context['total_vehicles'] = Vehicle.objects.count()

	elif user.is_driver:
		context['my_trips'] = Trip.objects.filter(
			driver=user, status__in=[Trip.Status.APPROVED, Trip.Status.IN_PROGRESS]
		).order_by('date')

	return render(request, 'core/dashboard.html', context)


def home(request):
	return redirect('accounts:login')
