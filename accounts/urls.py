from django.urls import path
from .views import email_login, login_view, CustomLogoutView

app_name = "accounts"

urlpatterns = [
    path("login/", email_login, name="login_form"),
    path("login/auth/", login_view, name="email_auth"),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
]
