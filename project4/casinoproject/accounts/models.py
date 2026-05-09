from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    money = models.IntegerField(default=1000)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']