from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = []
    permission_denied_message = 'Você não tem permissão para acessar esta página.'

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return user.role in self.allowed_roles

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, self.permission_denied_message)
            return redirect('core:dashboard')
        return super().handle_no_permission()


class ManagerRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['manager']


class DriverRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['driver']


class EmployeeRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['employee']
