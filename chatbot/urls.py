from django.urls import path
from . import views

urlpatterns = [
    path("", views.chatbot_home, name="chat_home"),
    path("get-response/", views.chatbot_response, name="chat_response"),
    path("whatsapp-webhook/", views.whatsapp_webhook, name="whatsapp_webhook"),
]
