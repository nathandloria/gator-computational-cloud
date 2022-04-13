from django import forms
from django.contrib import admin

from .models import ExternalAccountCredentials, Machine, MachinePool


class ExternalAccountCredentialsAdmin(admin.ModelAdmin):
    fields = ("user", "aws_access_key", "aws_secret_access_key", "drbx_refresh_token")
    list_display = ("user",)


admin.site.register(ExternalAccountCredentials, ExternalAccountCredentialsAdmin)


class MachineForm(forms.ModelForm):
    ip = forms.CharField()
    pem = forms.FileField(required=False)
    id = forms.CharField()
    status = forms.CharField()


class MachineInline(admin.TabularInline):
    model = Machine
    extra = 1
    form = MachineForm


class MachinePoolAdmin(admin.ModelAdmin):
    fields = ("user",)
    list_display = ("user",)
    inlines = [
        MachineInline,
    ]


admin.site.register(MachinePool, MachinePoolAdmin)
