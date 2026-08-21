from django import forms
from django.contrib.auth import get_user_model

from vehicles.models import Vehicle
from .models import Trip

User = get_user_model()
FIELD_CLASS = 'form-control'


class TripRequestForm(forms.ModelForm):
    class Meta:
        model = Trip
        fields = [
            'department', 'purpose', 'origin', 'destination',
            'date', 'departure_time', 'expected_return', 'passenger_count',
        ]
        widgets = {
            'department': forms.TextInput(attrs={'class': FIELD_CLASS}),
            'purpose': forms.TextInput(attrs={'class': FIELD_CLASS}),
            'origin': forms.TextInput(attrs={'class': FIELD_CLASS}),
            'destination': forms.TextInput(attrs={'class': FIELD_CLASS}),
            'date': forms.DateInput(attrs={'class': FIELD_CLASS, 'type': 'date'}),
            'departure_time': forms.TimeInput(attrs={'class': FIELD_CLASS, 'type': 'time'}),
            'expected_return': forms.DateTimeInput(attrs={'class': FIELD_CLASS, 'type': 'datetime-local'}),
            'passenger_count': forms.NumberInput(attrs={'class': FIELD_CLASS, 'min': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = True


class TripApprovalForm(forms.Form):
    vehicle = forms.ModelChoiceField(
        queryset=Vehicle.objects.filter(is_active=True, status=Vehicle.Status.AVAILABLE),
        label='Veículo', widget=forms.Select(attrs={'class': 'form-select'}),
    )
    driver = forms.ModelChoiceField(
        queryset=User.objects.filter(role='driver', is_active=True),
        label='Motorista', widget=forms.Select(attrs={'class': 'form-select'}),
    )


class TripRejectionForm(forms.Form):
    rejection_reason = forms.CharField(
        label='Motivo da rejeição', max_length=255,
        widget=forms.Textarea(attrs={'class': FIELD_CLASS, 'rows': 3}),
    )
