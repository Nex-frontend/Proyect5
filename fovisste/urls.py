from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='logout.html'), name='logout'),
    path('signup/', views.signup_view, name='signup'),

    # Password reset
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    # URLs de la aplicación
    path('', views.dashboard_view, name='dashboard'),
    path('foviste/carga/', views.carga_view, name='carga'),
    path('foviste/consulta/', views.consulta_view, name='consulta'),
    path('foviste/qnaproceso/', views.qnaproceso_view, name='qnaproceso'),
    path('foviste/resultados/', views.resultados_view, name='resultados'),

    # API
    path('api/upload/', views.api_upload_view, name='api_upload'),
]
