
from django.urls import path
from .views import index, upload, download, login, logout, process, progress
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', index),
    path('login', login),
    path('upload', upload),
    path('download', download),
    path('process/<uuid:uuid_task>/', process),
    path('progress/<int:download>/<uuid:uuid_task>/', progress),
    path('logout', logout),
]
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
