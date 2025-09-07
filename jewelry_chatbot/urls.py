# from django.contrib import admin
# from django.urls import path
# from chatbot import views

# urlpatterns = [
#     path("admin/", admin.site.urls),
#     path("", views.chat_view, name="chat"),
#     path("save_request/", views.save_request, name="save_request"),
# ]

# from django.contrib import admin
# from django.urls import path, include

# urlpatterns = [
#     path("admin/", admin.site.urls),
#     path("", include("chatbot.urls")),  
# ]

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("chatbot.urls")),  
]

#  Serve media files (only in DEBUG mode)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
