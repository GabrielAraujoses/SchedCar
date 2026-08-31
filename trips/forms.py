from django import forms

from .models import Trip

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
        minimum_departure = Trip.minimum_departure_datetime()
        self.fields['date'].widget.attrs['min'] = minimum_departure.date().isoformat()
        self.fields['date'].help_text = (
            'Solicite com pelo menos 3 dias úteis de antecedência. '
            f'O primeiro horário possível é {minimum_departure.strftime("%d/%m/%Y às %H:%M")}.'
        )
        self.fields['passenger_count'].min_value = 1
        self.fields['passenger_count'].widget.attrs['min'] = 1
