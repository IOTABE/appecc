from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

admin.site.login_template = 'admin/login.html'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='admin/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('', include('core.urls')),
]