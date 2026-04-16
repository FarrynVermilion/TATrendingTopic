from django.urls import path
from . import views

urlpatterns = [
    path('get-headers/', views.get_csv_headers, name='get_csv_headers'),
    path('process-gsdmm/', views.process_gsdmm, name='process_gsdmm'),
]
