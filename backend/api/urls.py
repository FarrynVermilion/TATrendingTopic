from django.urls import path
from . import views

urlpatterns = [
    # ─── Pipeline Endpoints ──────────────────────────────────────────────────
    # Step 1: Dataset Overview & Upload
    path('dataset/overview/', views.dataset_overview, name='dataset_overview'),
    path('dataset/upload/', views.dataset_upload, name='dataset_upload'),

    # Pipeline Orchestration
    path('pipeline/start/', views.pipeline_start, name='pipeline_start'),
    path('pipeline/status/', views.pipeline_status, name='pipeline_status'),

    # Step 2: Preprocessing
    path('preprocessing/run/', views.preprocessing_run, name='preprocessing_run'),
    path('preprocessing/ngrams/', views.preprocessing_ngrams, name='preprocessing_ngrams'),
    path('preprocessing/edges/', views.preprocessing_edges, name='preprocessing_edges'),

    # Step 3: Burst Detection
    path('burst/analysis/', views.burst_analysis, name='burst_analysis'),

    # Step 4: Link Anomaly
    path('link-anomaly/network/', views.link_anomaly_network, name='link_anomaly_network'),

    # Step 5: Executive Summary
    path('summary/trends/', views.summary_trends, name='summary_trends'),

    # ─── Legacy Endpoints ────────────────────────────────────────────────────
    path('get-headers/', views.get_csv_headers, name='get_csv_headers'),
    path('process-gsdmm/', views.process_gsdmm, name='process_gsdmm'),
]
