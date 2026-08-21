from django.conf import settings
from django.core.mail import send_mail


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
