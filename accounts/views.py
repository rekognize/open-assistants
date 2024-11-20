from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse, HttpResponseNotAllowed
from django.contrib import messages
from django.utils.translation import gettext as _
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django import forms
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox
from sesame.utils import get_query_string, get_user

import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


class EmailLoginForm(forms.Form):
    email = forms.EmailField(
        label=_("Email"),
        help_text=_("Type your email to receive the login link.")
    )
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)


def email_login(request):
    if request.user.is_authenticated:
        messages.warning(request, _(
            "You are already signed in."
        ))
        return redirect('/')

    if request.method == 'POST':
        form = EmailLoginForm(request.POST)
        if form.is_valid() and request.POST.get('g-recaptcha-response'):
            email = form.cleaned_data["email"]
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Create a new user
                user = User.objects.create_user(
                    username=email,
                    email=email
                )
                user.set_unusable_password()
                user.save()

            messages.success(request, _("Login link is sent. Please check your email."))

            link = reverse("accounts:email_auth")
            link = request.build_absolute_uri(link)
            link += get_query_string(user)
            user.email_user(
                subject=_("OpenAssistants login link"),
                message=_(
                    "Hello,\n\n"
                    "You requested that we send you a link to log in to OpenAssistants.io:\n\n"
                    "%(link)s\n\n\n"
                    "Thank you!"
                ) % {'link': link}
            )

            return redirect('/')
        else:
            messages.error(request, _('Invalid CAPTCHA. Please try again.'))
    else:
        form = EmailLoginForm()

    return render(request, 'accounts/email_login.html', {
        'form': form,
        'recaptcha_site_key': settings.RECAPTCHA_PUBLIC_KEY,
    })


def login_view(request):
    # Parse the token from the request to authenticate the user
    user = get_user(request)
    if user is not None:
        # Perform login logic
        login(request, user)
        # Add a success message
        messages.success(request, _("You have been successfully logged in."))
    else:
        # Login failed
        messages.error(request, _("We couldn't validate your token. Please try again."))
    return redirect('/')


class CustomLogoutView(LogoutView):
    http_method_names = ["get", "post", "options"]

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, _('You have been successfully logged out.'))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.post(request, *args, **kwargs)


@login_required
def stripe_payment_view(request):
    return render(request, 'accounts/upgrade.html', {
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    })


@login_required
def stripe_checkout_session(request):
    # Requested by Stripe.js

    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    session = stripe.checkout.Session.create(
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': 'Open Assistants Pro Plan',
                },
                'unit_amount': 30 * 100,  # $30
            },
            'quantity': 1,
        }],
        mode='payment',
        ui_mode='embedded',
        return_url=request.build_absolute_uri(reverse('accounts:payment_result')) + '?session_id={CHECKOUT_SESSION_ID}',
    )

    return JsonResponse({
        'clientSecret': session.client_secret
    })


@login_required
def stripe_payment_result(request):
    session_id = request.GET.get('session_id')
    session = stripe.checkout.Session.retrieve(session_id)

    if session.payment_status == 'paid':
        messages.success(request, _(
            f"Thank you for upgrading to PRO!"
        ))

    else:
        messages.error(request, _("Transaction failed."))

    return redirect('/')
