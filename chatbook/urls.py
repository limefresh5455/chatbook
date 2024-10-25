
from django.contrib import admin
from django.urls import path ,include
from django.conf import settings
from django.conf.urls.static import static
admin.site.site_header = "Read My Book"
admin.site.site_title = "Read My Book Portal"
admin.site.index_title = "Welcome to Read My Book Portal"
admin.site.site_url="http://localhost:3000/"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('askpdf/', include('chatbookapp.urls')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)