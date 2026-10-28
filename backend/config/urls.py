from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', lambda request: JsonResponse({'status': 'ok'})),
    path('api/auth/', include('accounts.urls')),
    # Everything else is the React app (it does its own routing).
    re_path(r'^(?!api/|admin/|static/).*$', TemplateView.as_view(template_name='index.html')),
]
