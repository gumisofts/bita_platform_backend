from django.urls import path
from . import views

urlpatterns = [
    path("send-mail/", views.send_single_email, name="send_single_email"),
]
