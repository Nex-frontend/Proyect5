from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.conf import settings
from . import views

# En desarrollo puede haber problemas con cookies/CSRF; para facilitar testing local
# si DEBUG=True permitimos temporalmente que el login no exija CSRF. En producción
# NUNCA debe estar csrf_exempt.
if settings.DEBUG:
    login_view = csrf_exempt(auth_views.LoginView.as_view(template_name='registration/login.html'))
else:
    login_view = ensure_csrf_cookie(auth_views.LoginView.as_view(template_name='registration/login.html'))

urlpatterns = [
    path('.well-known/appspecific/com.chrome.devtools.json', views.devtools_probe),
    path('login/', login_view, name='login'),
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
    path('api/preview/', views.preview_upload_view, name='api_preview'),
    path('api/update_lote/', views.update_lote_view, name='api_update_lote'),
    path('api/clear_preview/', views.clear_preview_view, name='api_clear_preview'),
    path('api/upload/', views.api_upload_view, name='api_upload'),
]
