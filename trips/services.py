from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from vehicles.models import Vehicle


def allocate_trip(trip):
    """Seleciona o menor veículo compatível e um motorista livre para a viagem."""
    all_compatible_vehicles = Vehicle.objects.filter(capacity__gte=trip.passenger_count)
    if not all_compatible_vehicles.exists():
        return None, None, (
            f'Não há veículo cadastrado para {trip.passenger_count} passageiros.'
        )

    eligible_vehicles = all_compatible_vehicles.filter(is_active=True).exclude(
        status__in=[Vehicle.Status.MAINTENANCE, Vehicle.Status.INACTIVE]
    ).order_by('capacity', 'name')
    if not eligible_vehicles.exists():
        return None, None, (
            'Os veículos compatíveis estão em manutenção ou inativos.'
        )

    vehicle = next(
        (
            candidate
            for candidate in eligible_vehicles
            if not trip._has_conflict('vehicle', candidate.pk)
        ),
        None,
    )
    if vehicle is None:
        return None, None, (
            'Não há veículo compatível livre para o período solicitado, '
            'considerando os conflitos de agenda e o intervalo operacional.'
        )

    User = get_user_model()
    active_drivers = User.objects.filter(role='driver', is_active=True).order_by('employee_id')
    if not active_drivers.exists():
        return None, None, 'Não há motorista ativo disponível para a viagem.'

    driver = next(
        (
            candidate
            for candidate in active_drivers
            if not trip._has_conflict('driver', candidate.pk)
        ),
        None,
    )
    if driver is None:
        return None, None, (
            'Não há motorista livre para o período solicitado, '
            'considerando os conflitos de agenda e o intervalo operacional.'
        )

    return vehicle, driver, ''


def _send(subject, message, recipients):
    recipients = list(dict.fromkeys(recipient for recipient in recipients if recipient))
    if recipients:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipients)


def notify_reference_number_issued(trip):
    subject = f'Solicitação registrada - Protocolo {trip.reference_number}'
    message = (
        f'Protocolo: {trip.reference_number}\n'
        f'Setor: {trip.department}\nDestino: {trip.destination}\n'
        f'Data: {trip.date.strftime("%d/%m/%Y")} às {trip.departure_time.strftime("%H:%M")}\n'
        f'Guarde este protocolo para comprovar a sua viagem.'
    )
    _send(subject, message, [trip.employee.email])


def notify_managers_new_request(trip):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    subject = f'Nova solicitação - Protocolo {trip.reference_number}'
    message = f'Colaborador {trip.employee} solicitou uma viagem para {trip.destination}.'
    manager_emails = list(
        User.objects.filter(role='manager', is_active=True).values_list('email', flat=True)
    )
    configured_emails = settings.MANAGER_NOTIFICATION_EMAILS.split(',')
    _send(subject, message, manager_emails + configured_emails)


def notify_approval_result(trip):
    if trip.status == trip.Status.APPROVED:
        subject = f'Viagem aprovada - Protocolo {trip.reference_number}'
        message = f'Veículo: {trip.vehicle}\nMotorista: {trip.driver}'
        recipients = [trip.employee.email]
        if trip.driver_id:
            recipients.append(trip.driver.email)
        _send(subject, message, recipients)
    elif trip.status == trip.Status.REJECTED:
        subject = f'Viagem rejeitada - Protocolo {trip.reference_number}'
        message = f'Motivo: {trip.rejection_reason or "não informado"}'
        _send(subject, message, [trip.employee.email])
