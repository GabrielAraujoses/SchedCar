from datetime import datetime, time, timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import User
from vehicles.models import Brand, Vehicle

from .models import Trip
from .services import allocate_trip


class TripTestCase(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user(
            employee_id='1001',
            email='colaborador@example.com',
            password='SenhaTeste@2026',
            role=User.Role.EMPLOYEE,
        )
        self.driver = User.objects.create_user(
            employee_id='2001',
            email='motorista@example.com',
            password='SenhaTeste@2026',
            role=User.Role.DRIVER,
        )
        self.brand = Brand.objects.create(name='Marca de teste')
        self.small_vehicle = Vehicle.objects.create(
            name='Carro pequeno',
            brand=self.brand,
            license_plate='TES1A01',
            capacity=4,
        )
        self.large_vehicle = Vehicle.objects.create(
            name='Van',
            brand=self.brand,
            license_plate='TES1A18',
            capacity=18,
        )

    def make_trip(self, **overrides):
        date = overrides.pop('date', timezone.localdate() + timedelta(days=10))
        departure_time = overrides.pop('departure_time', time(9, 0))
        expected_return = overrides.pop(
            'expected_return',
            timezone.make_aware(datetime.combine(date, time(11, 0))),
        )
        values = {
            'employee': self.employee,
            'department': 'Operações',
            'purpose': 'Visita técnica',
            'origin': 'Portaria',
            'destination': 'Terminal',
            'date': date,
            'departure_time': departure_time,
            'expected_return': expected_return,
            'passenger_count': 1,
        }
        values.update(overrides)
        return Trip(**values)


class TripValidationTests(TripTestCase):
    def test_rejects_past_date(self):
        trip = self.make_trip(date=timezone.localdate() - timedelta(days=1))

        with self.assertRaises(ValidationError) as error:
            trip.full_clean()

        self.assertIn('date', error.exception.message_dict)

    def test_rejects_zero_passengers(self):
        trip = self.make_trip(passenger_count=0)

        with self.assertRaises(ValidationError) as error:
            trip.full_clean()

        self.assertIn('passenger_count', error.exception.message_dict)

    @patch('trips.models.timezone.now')
    def test_requires_three_business_days_with_the_same_time(self, mocked_now):
        mocked_now.return_value = timezone.make_aware(datetime(2026, 9, 4, 10, 0))
        date = datetime(2026, 9, 8).date()
        trip = self.make_trip(
            date=date,
            departure_time=time(9, 59),
            expected_return=timezone.make_aware(datetime.combine(date, time(12, 0))),
        )

        with self.assertRaises(ValidationError) as error:
            trip.full_clean()

        self.assertIn('date', error.exception.message_dict)

    def test_requires_two_hours_between_vehicle_trips(self):
        date = timezone.localdate() + timedelta(days=10)
        first_trip = self.make_trip(
            vehicle=self.small_vehicle,
            driver=self.driver,
            date=date,
            departure_time=time(8, 0),
            expected_return=timezone.make_aware(datetime.combine(date, time(10, 0))),
            status=Trip.Status.APPROVED,
        )
        first_trip.full_clean()
        first_trip.save()
        next_trip = self.make_trip(
            vehicle=self.small_vehicle,
            driver=self.driver,
            date=date,
            departure_time=time(11, 0),
            expected_return=timezone.make_aware(datetime.combine(date, time(13, 0))),
        )

        with self.assertRaises(ValidationError) as error:
            next_trip.full_clean()

        self.assertIn('vehicle', error.exception.message_dict)
        self.assertIn('driver', error.exception.message_dict)


class AutomaticAllocationTests(TripTestCase):
    def test_allocates_smallest_vehicle_that_supports_passenger_count(self):
        trip = self.make_trip(passenger_count=5)

        vehicle, driver, reason = allocate_trip(trip)

        self.assertEqual(vehicle, self.large_vehicle)
        self.assertEqual(driver, self.driver)
        self.assertEqual(reason, '')

    def test_explains_when_no_driver_is_available(self):
        self.driver.is_active = False
        self.driver.save(update_fields=['is_active'])
        trip = self.make_trip()

        vehicle, driver, reason = allocate_trip(trip)

        self.assertIsNone(vehicle)
        self.assertIsNone(driver)
        self.assertIn('motorista', reason.lower())

    def test_explains_when_no_vehicle_has_enough_capacity(self):
        trip = self.make_trip(passenger_count=19)

        vehicle, driver, reason = allocate_trip(trip)

        self.assertIsNone(vehicle)
        self.assertIsNone(driver)
        self.assertIn('19 passageiros', reason)

    def test_explains_when_compatible_vehicle_has_schedule_conflict(self):
        date = timezone.localdate() + timedelta(days=10)
        reserved_trip = self.make_trip(
            vehicle=self.large_vehicle,
            driver=self.driver,
            date=date,
            departure_time=time(9, 0),
            expected_return=timezone.make_aware(datetime.combine(date, time(11, 0))),
            passenger_count=5,
            status=Trip.Status.APPROVED,
        )
        reserved_trip.full_clean()
        reserved_trip.save()
        trip = self.make_trip(
            date=date,
            departure_time=time(10, 0),
            expected_return=timezone.make_aware(datetime.combine(date, time(12, 0))),
            passenger_count=5,
        )

        vehicle, driver, reason = allocate_trip(trip)

        self.assertIsNone(vehicle)
        self.assertIsNone(driver)
        self.assertIn('veículo', reason.lower())


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class TripRequestFlowTests(TripTestCase):
    def login_as_employee(self):
        self.client.force_login(self.employee)

    def request_payload(self, **overrides):
        date = timezone.localdate() + timedelta(days=10)
        payload = {
            'department': 'Operações',
            'purpose': 'Visita técnica',
            'origin': 'Portaria',
            'destination': 'Terminal',
            'date': date.isoformat(),
            'departure_time': '09:00',
            'expected_return': datetime.combine(date, time(11, 0)).strftime('%Y-%m-%dT%H:%M'),
            'passenger_count': 5,
        }
        payload.update(overrides)
        return payload

    def test_request_is_approved_automatically_when_resources_exist(self):
        self.login_as_employee()

        response = self.client.post('/trips/request/', self.request_payload())
        trip = Trip.objects.get()

        self.assertRedirects(response, f'/trips/{trip.pk}/')
        self.assertEqual(trip.status, Trip.Status.APPROVED)
        self.assertEqual(trip.vehicle, self.large_vehicle)
        self.assertEqual(trip.driver, self.driver)
        self.large_vehicle.refresh_from_db()
        self.assertEqual(self.large_vehicle.status, Vehicle.Status.AVAILABLE)

    def test_request_form_explains_minimum_lead_time(self):
        self.login_as_employee()

        response = self.client.get('/trips/request/')

        self.assertContains(response, '3 dias úteis de antecedência')

    def test_request_is_rejected_with_reason_when_vehicle_is_in_maintenance(self):
        self.small_vehicle.status = Vehicle.Status.MAINTENANCE
        self.small_vehicle.save(update_fields=['status'])
        self.large_vehicle.status = Vehicle.Status.MAINTENANCE
        self.large_vehicle.save(update_fields=['status'])
        self.login_as_employee()

        response = self.client.post('/trips/request/', self.request_payload(passenger_count=1))
        trip = Trip.objects.get()

        self.assertRedirects(response, f'/trips/{trip.pk}/')
        self.assertEqual(trip.status, Trip.Status.REJECTED)
        self.assertIn('manutenção', trip.rejection_reason.lower())

    def test_future_trip_does_not_block_vehicle_for_a_later_period(self):
        self.login_as_employee()
        date = timezone.localdate() + timedelta(days=10)
        first_response = self.client.post('/trips/request/', self.request_payload(
            date=date.isoformat(),
            departure_time='09:00',
            expected_return=datetime.combine(date, time(11, 0)).strftime('%Y-%m-%dT%H:%M'),
        ))
        second_response = self.client.post('/trips/request/', self.request_payload(
            purpose='Visita técnica posterior',
            date=date.isoformat(),
            departure_time='14:00',
            expected_return=datetime.combine(date, time(16, 0)).strftime('%Y-%m-%dT%H:%M'),
        ))
        first_trip, second_trip = Trip.objects.order_by('pk')

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(first_trip.status, Trip.Status.APPROVED)
        self.assertEqual(second_trip.status, Trip.Status.APPROVED)
        self.assertEqual(first_trip.vehicle, self.large_vehicle)
        self.assertEqual(second_trip.vehicle, self.large_vehicle)

    def test_driver_sees_start_action_for_assigned_trip(self):
        trip = self.make_trip(vehicle=self.small_vehicle, driver=self.driver, status=Trip.Status.APPROVED)
        trip.full_clean()
        trip.save()
        self.client.force_login(self.driver)

        response = self.client.get(f'/trips/{trip.pk}/')

        self.assertContains(response, 'Iniciar viagem')
