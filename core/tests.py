from pathlib import Path

from django.conf import settings
from django.test import TestCase

from accounts.models import User
from vehicles.models import Vehicle


class DemoFixtureTests(TestCase):
    fixtures = ['dados_demo']

    def test_loads_a_complete_demo_fleet_and_test_accounts(self):
        self.assertEqual(Vehicle.objects.count(), 10)
        self.assertEqual(Vehicle.objects.filter(capacity=4).count(), 8)
        self.assertEqual(Vehicle.objects.filter(capacity=18).count(), 2)
        self.assertTrue(all(
            Path(settings.MEDIA_ROOT, vehicle.photo.name).is_file()
            for vehicle in Vehicle.objects.all()
        ))

        self.assertEqual(User.objects.count(), 11)
        self.assertEqual(User.objects.filter(role=User.Role.DRIVER).count(), 5)
        self.assertEqual(User.objects.filter(role=User.Role.EMPLOYEE).count(), 5)
        self.assertEqual(User.objects.filter(role=User.Role.MANAGER).count(), 1)
        self.assertSetEqual(
            set(User.objects.values_list('employee_id', 'first_name', 'last_name')),
            {
                ('2001', 'Lucas', 'Loops'),
                ('2002', 'Davi', 'Davas'),
                ('2003', 'Gabriel', 'Élio'),
                ('2004', 'Kauã', 'Turing'),
                ('2005', 'Pedro', 'Sharp'),
                ('3001', 'Ana', 'Java'),
                ('3002', 'João', 'Jira'),
                ('3003', 'Carlos', 'Magno'),
                ('3004', 'Gil', 'Gibson'),
                ('3005', 'Junior', 'Senior'),
                ('9001', 'Junior', 'Super'),
            },
        )

        manager = User.objects.get(employee_id='9001')
        self.assertTrue(manager.is_staff)
        self.assertTrue(manager.is_superuser)

        passwords = {
            '2001': 'lucastest12345',
            '2002': 'davitest12345',
            '2003': 'gabrieltest12345',
            '2004': 'kauatest12345',
            '2005': 'pedrotest12345',
            '3001': 'anatest12345',
            '3002': 'joaotest12345',
            '3003': 'carlostest12345',
            '3004': 'giltest12345',
            '3005': 'juniortest12345',
            '9001': 'juniortest12345',
        }
        for employee_id, password in passwords.items():
            self.assertTrue(User.objects.get(employee_id=employee_id).check_password(password))
