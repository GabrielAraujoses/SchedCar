from django.urls import path

from . import views

app_name = 'trips'

urlpatterns = [
    path('', views.TripListView.as_view(), name='list'),
    path('request/', views.TripRequestView.as_view(), name='request'),
    path('<int:pk>/', views.TripDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.TripUpdateView.as_view(), name='edit'),
    path('<int:pk>/approve/', views.TripApproveView.as_view(), name='approve'),
    path('<int:pk>/reject/', views.TripRejectView.as_view(), name='reject'),
    path('<int:pk>/start/', views.TripStartView.as_view(), name='start'),
    path('<int:pk>/complete/', views.TripCompleteView.as_view(), name='complete'),
    path('<int:pk>/cancel/', views.TripCancelView.as_view(), name='cancel'),
]
