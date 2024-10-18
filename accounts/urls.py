from django.urls import path
from .views import (
    email_login, login_view, CustomLogoutView,
    stripe_payment_view, stripe_checkout_session, stripe_payment_result
)

app_name = "accounts"

urlpatterns = [
    path("login/", email_login, name="login_form"),
    path("login/auth/", login_view, name="email_auth"),
    path('logout/', CustomLogoutView.as_view(), name='logout'),

    path("upgrade/", stripe_payment_view, name="upgrade"),
    path("payment/session", stripe_checkout_session, name="payment_session"),
    path("payment/result", stripe_payment_result, name="payment_result"),
]
