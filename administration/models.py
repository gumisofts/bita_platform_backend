from django.db import models


class PlanFeature(models.Model):
    name = models.CharField(max_length=100)
    plan = models.ForeignKey("Plan", on_delete=models.CASCADE, related_name="features")

    def __str__(self):
        return self.name


class Plan(models.Model):
    name = models.CharField(max_length=100)
    price = models.CharField(max_length=50)
    currency = models.CharField(
        max_length=10,
        choices=[("USD", "USD"), ("EUR", "EUR"), ("GBP", "GBP"), ("ETB", "ETB")],
        default="ETB",
    )
    billing_period = models.CharField(
        max_length=20,
        choices=[("monthly", "Monthly"), ("yearly", "Yearly")],
        default="monthly",
    )

    def __str__(self):
        return self.name


class Download(models.Model):
    platform = models.CharField(max_length=50)
    icon = models.ImageField(upload_to="downloads/icons/", blank=True, null=True)
    file = models.FileField(upload_to="downloads/files/", blank=True, null=True)

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
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0)

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
