from django.db import models
from django.contrib.postgres.fields import ArrayField

class Plan(models.Model):
    name = models.CharField(max_length=100)
    price = models.CharField(max_length=50)
    currency = models.CharField(max_length=10)
    billing_period = models.CharField(max_length=20)
    features = ArrayField(models.CharField(max_length=200), default=list, blank=True)

    def __str__(self):
        return self.name


class Download(models.Model):
    platform = models.CharField(max_length=50)
    icon_url = models.URLField(max_length=255, blank=True, null=True)
    download_link = models.URLField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.platform


class Waitlist(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class FAQ(models.Model):
    question = models.TextField()
    answer = models.TextField()

    def __str__(self):
        return self.question


class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    company = models.CharField(max_length=100, blank=True, null=True)
    message = models.TextField()
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.email}"