from django.contrib.auth.models import User
from django.db import models
from fernet_fields import EncryptedCharField


class ExternalAccountCredentials(models.Model):
    user = models.OneToOneField(User, primary_key=True, on_delete=models.CASCADE)
    aws_access_key = EncryptedCharField(default=None, max_length=255, blank=True)
    aws_secret_access_key = EncryptedCharField(default=None, max_length=255, blank=True)
    drbx_refresh_token = EncryptedCharField(default=None, max_length=255, blank=True)

    class Meta:
        verbose_name_plural = "External account credentials"


class MachinePool(models.Model):
    user = models.OneToOneField(User, primary_key=True, on_delete=models.CASCADE)


class Machine(models.Model):
    pool = models.ForeignKey(
        MachinePool, related_name="machines", on_delete=models.CASCADE
    )
    status = models.CharField(default="Available", max_length=255, blank=True)
    ip = models.CharField(default=None, max_length=255, blank=True)
    pem = EncryptedCharField(default=None, max_length=4096, blank=True)
    id = models.CharField(primary_key=True, default=None, max_length=255, blank=True)
