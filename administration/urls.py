from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ContactViewSet,
    DownloadViewSet,
    FAQViewSet,
    PlanViewSet,
    WaitlistViewSet,
)

router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="plan")
router.register(r"downloads", DownloadViewSet, basename="download")
router.register(r"faqs", FAQViewSet, basename="faq")
router.register(r"waitlist", WaitlistViewSet, basename="waitlist")
router.register(r"contacts", ContactViewSet, basename="contact")

urlpatterns = [
    path("", include(router.urls)),
]
