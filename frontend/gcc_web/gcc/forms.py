from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Invisible
from django import forms


class SignInForm(forms.Form):
    """A form used for signing in."""
    user_name = forms.CharField()
    user_name.label = "Username"

    user_password = forms.CharField(widget=forms.PasswordInput())
    user_password.label = "Password"

    captcha = ReCaptchaField(widget=ReCaptchaV2Invisible, label="")


class SignUpForm(forms.Form):
    """A form used for signing up."""
    user_name = forms.CharField()
    user_name.label = "Username"

    user_email = forms.EmailField()
    user_email.label = "Email"

    user_password = forms.CharField(widget=forms.PasswordInput())
    user_password.label = "Password"

    _user_password_ = forms.CharField(widget=forms.PasswordInput())
    _user_password_.label = "Re-enter Password"

    captcha = ReCaptchaField(widget=ReCaptchaV2Invisible, label="")

    def clean(self):
        cleaned_data = super(SignUpForm, self).clean()

        password = cleaned_data.get("user_password")
        password_confirm = cleaned_data.get("_user_password_")

        if password and password_confirm:
            if password != password_confirm:
                raise forms.ValidationError("The two password fields must match!")
        else:
            raise forms.ValidationError("You must fill both password fields!")

        return cleaned_data


class CredentialForm(forms.Form):
    """A form used to accept credentials."""
    aws_access_key = forms.CharField()
    aws_access_key.label = "AWS Access Key"

    aws_secret_access_key = forms.CharField()
    aws_secret_access_key.label = "AWS Secret Key"

    captcha = ReCaptchaField(widget=ReCaptchaV2Invisible, label="")


class MachineForm(forms.Form):
    """A form used to udate a user's machine pool."""
    machine_id = forms.CharField()
    machine_id.label = "Machine ID"

    machine_ip = forms.CharField()
    machine_ip.label = "Machine IP"

    machine_pem = forms.FileField(required=False)
    machine_pem.label = "PEM File"

    captcha = ReCaptchaField(widget=ReCaptchaV2Invisible, label="")
