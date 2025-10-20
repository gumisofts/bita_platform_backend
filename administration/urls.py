from django.urls import path
from .views import PlanView, DownloadView, WaitlistView, FAQView, ContactView

urlpatterns = [
    path('plans/', PlanView.as_view(), name='get_plans'),
    path('plans/<int:pk>/', PlanView.as_view(), name='get_plan'),

    path('downloads/', DownloadView.as_view(), name='downloads-list-create'),
    path('downloads/<int:pk>/', DownloadView.as_view(), name='download-detail'),

    path('waitlist/create/', WaitlistView.as_view(), name='waitlist-create'),

    path('faqs/', FAQView.as_view(), name='faqs-list-create'),
    path('faqs/<int:pk>/', FAQView.as_view(), name='faq-detail'),

    path('contacts/create/', ContactView.as_view(), name='contact-create'),
]
