from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext as _
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django import forms
from sesame.utils import get_query_string, get_user
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox


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

            messages.success(request, _("Login link sent. Please check you email."))

            link = reverse("accounts:email_auth")
            link = request.build_absolute_uri(link)
            link += get_query_string(user)
            user.email_user(
                subject=_("giChat login link"),
                message=_(
                    "Hello,\n\n"
                    "You requested that we send you a link to log in to gi.chat:\n\n"
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
