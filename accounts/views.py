from django.contrib import messages
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.db.models import ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.mixins import ManagerRequiredMixin
from .forms import EmployeeSignUpForm, LoginForm, UserForm
from .models import User


class LoginView(AuthLoginView):
    template_name = 'registration/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class LogoutView(AuthLogoutView):
    next_page = 'accounts:login'


class EmployeeSignUpView(CreateView):
    model = User
    form_class = EmployeeSignUpForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Cadastro realizado! Faça login para continuar.')
        return response


# Gestão de contas — antes era exclusiva da TI, agora é do Gerente.

class UserListView(ManagerRequiredMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        queryset = User.objects.all().order_by('role', 'employee_id')
        role = self.request.GET.get('role')
        search = self.request.GET.get('q')
        if role:
            queryset = queryset.filter(role=role)
        if search:
            queryset = queryset.filter(employee_id__icontains=search)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = User.Role.choices
        return context


class UserCreateView(ManagerRequiredMixin, CreateView):
    model = User
    form_class = UserForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        messages.success(self.request, 'Usuário cadastrado com sucesso.')
        return super().form_valid(form)


class UserUpdateView(ManagerRequiredMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = 'accounts/user_form.html'
    success_url = reverse_lazy('accounts:user_list')

    def form_valid(self, form):
        messages.success(self.request, 'Usuário atualizado com sucesso.')
        return super().form_valid(form)


class UserDeleteView(ManagerRequiredMixin, DeleteView):
    model = User
    template_name = 'accounts/user_confirm_delete.html'
    success_url = reverse_lazy('accounts:user_list')

    def dispatch(self, request, *args, **kwargs):
        if self.get_object() == request.user:
            messages.error(request, 'Você não pode excluir o próprio usuário.')
            return redirect('accounts:user_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            response = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'Este usuário possui viagens vinculadas e não pode ser excluído.')
            return redirect('accounts:user_list')
        messages.success(self.request, 'Usuário excluído com sucesso.')
        return response
