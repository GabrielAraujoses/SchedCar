from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User

FIELD_CLASS = 'form-control'


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Matrícula'
        self.fields['username'].widget.attrs.update({'class': FIELD_CLASS, 'autofocus': True})
        self.fields['password'].widget.attrs.update({'class': FIELD_CLASS})


class EmployeeSignUpForm(UserCreationForm):
    """Autocadastro público — sempre cria um Colaborador."""

    class Meta:
        model = User
        fields = ['employee_id', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': FIELD_CLASS})
        self.fields['first_name'].label = 'Nome'
        self.fields['last_name'].label = 'Sobrenome'

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.EMPLOYEE
        if commit:
            user.save()
        return user


class UserForm(UserCreationForm):
    """Cadastro/edição de qualquer perfil — uso restrito ao Gerente."""

    password1 = forms.CharField(
        label='Senha', widget=forms.PasswordInput(attrs={'class': FIELD_CLASS}), required=False,
        help_text='Deixe em branco para manter a senha atual (na edição).',
    )
    password2 = forms.CharField(
        label='Confirmar senha', widget=forms.PasswordInput(attrs={'class': FIELD_CLASS}), required=False,
    )

    class Meta:
        model = User
        fields = ['employee_id', 'first_name', 'last_name', 'email', 'role', 'phone_number', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != 'is_active':
                field.widget.attrs.update({'class': FIELD_CLASS})

    def clean(self):
        cleaned_data = super().clean()
        password1, password2 = cleaned_data.get('password1'), cleaned_data.get('password2')
        if password1 or password2:
            if password1 != password2:
                raise forms.ValidationError('As senhas não coincidem.')
        elif self.instance.pk is None:
            raise forms.ValidationError('A senha é obrigatória para novos usuários.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user
