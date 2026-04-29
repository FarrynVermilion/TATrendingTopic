"""
Django API views for the Trending Topic Detection Pipeline.

Endpoints:
  GET  /api/dataset/overview/          — Step 1: Dataset metadata & KPIs
  POST /api/pipeline/start/            — Start the full pipeline
  GET  /api/preprocessing/ngrams/      — Step 2a: Paginated N-grams
  GET  /api/preprocessing/edges/       — Step 2b: Paginated edge list
  GET  /api/burst/analysis/            — Step 3: Burst detection results
  GET  /api/link-anomaly/network/      — Step 4: Network graph + anomalies
  GET  /api/summary/trends/            — Step 5: Executive summary

Legacy (preserved):
  POST /api/get-headers/               — CSV header extraction
  POST /api/process-gsdmm/             — GSDMM topic modeling
"""

import os
import json
import threading
import pandas as pd
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .auth import api_key_required
from .utils.gsdmm_utils import process_csv_gsdmm


# ─── Pipeline State (in-memory, per-server instance) ─────────────────────────
# In production you'd use Redis or a database-backed task queue.

_pipeline_state = {
    'status': 'idle',          # idle | running | completed | error
    'error': None,
    'df_raw': None,            # Raw scraped DataFrame
    'df_cleaned': None,        # Cleaned DataFrame
    'ngrams': None,            # N-gram extraction results
    'edge_list': None,         # Edge list DataFrame
    'burst_analysis': None,    # Burst detection results
    'network_data': None,      # Link anomaly + network graph
    'trends': None,            # Final trend classification
    'overview': None,          # Dataset overview stats
}

# ─── Data Paths ──────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(settings.BASE_DIR).parent
RAW_CSV_PATH = PROJECT_ROOT / 'web_scrape' / 'perang_iran.csv'
CLEANED_CSV_PATH = PROJECT_ROOT / 'cleaner_script' / 'cleaned_output.csv'


def _load_datasets():
    """Load raw and cleaned CSV into pipeline state."""
    global _pipeline_state

    if not RAW_CSV_PATH.exists():
        raise FileNotFoundError(f"Raw dataset not found: {RAW_CSV_PATH}")
    if not CLEANED_CSV_PATH.exists():
        raise FileNotFoundError(f"Cleaned dataset not found: {CLEANED_CSV_PATH}")

    _pipeline_state['df_raw'] = pd.read_csv(RAW_CSV_PATH)
    _pipeline_state['df_cleaned'] = pd.read_csv(CLEANED_CSV_PATH)


def _paginate(items: list, page: int = 1, page_size: int = 20) -> dict:
    """Paginate a list of items."""
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        'count': total,
        'results': items[start:end],
    }


# ─── Step 1: Dataset Overview ────────────────────────────────────────────────

@csrf_exempt
@api_key_required
def dataset_overview(request):
    """
    GET /api/dataset/overview/
    Returns corpus-level statistics and metadata.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Lazy-load datasets
        if _pipeline_state['df_raw'] is None:
            _load_datasets()

        if _pipeline_state['overview'] is None:
            from .utils.preprocessing import compute_dataset_overview
            _pipeline_state['overview'] = compute_dataset_overview(
                _pipeline_state['df_raw'],
                _pipeline_state['df_cleaned'],
            )

        return JsonResponse(_pipeline_state['overview'])

    except FileNotFoundError as e:
        return JsonResponse({'error': str(e)}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ─── Pipeline Start ─────────────────────────────────────────────────────────

def _run_pipeline_background():
    """Background worker for the full pipeline."""
    global _pipeline_state

    try:
        from .utils.preprocessing import (
            extract_ngrams, extract_edge_list, build_term_time_series,
        )
        from .utils.kleinberg import run_burst_detection
        from .utils.link_anomaly import run_link_anomaly_analysis
        from .utils.trend_validator import build_trend_summary

        df_raw = _pipeline_state['df_raw']
        df_cleaned = _pipeline_state['df_cleaned']

        # Step 2: Preprocessing
        cleaned_texts = df_cleaned['cleaned_text'].dropna().astype(str).tolist()
        ngrams_df = extract_ngrams(cleaned_texts, n_range=(1, 2), min_df=5)
        edge_df = extract_edge_list(df_raw)

        _pipeline_state['ngrams'] = ngrams_df
        _pipeline_state['edge_list'] = edge_df

        # Step 3: Burst Detection
        time_series = build_term_time_series(
            df_cleaned, text_col='cleaned_text', time_col='datetime',
            top_n_terms=50, bin_hours=1,
        )

        burst_result = run_burst_detection(
            time_series['term_series'],
            time_series['bins'],
            s=2.0, gamma=1.0,
        )

        _pipeline_state['burst_analysis'] = burst_result

        # Step 4: Link Anomaly Detection
        anomaly_result = run_link_anomaly_analysis(
            edge_df,
            burst_result['burst_periods'],
            anomaly_threshold=0.5,
        )

        _pipeline_state['network_data'] = anomaly_result['network']

        # Step 5: Trend Validation
        trends = build_trend_summary(
            burst_result['burst_periods'],
            anomaly_result['burst_anomaly_scores'],
            edge_df,
            anomaly_threshold=0.5,
        )

        _pipeline_state['trends'] = trends
        _pipeline_state['status'] = 'completed'

    except Exception as e:
        _pipeline_state['status'] = 'error'
        _pipeline_state['error'] = str(e)
        import traceback
        traceback.print_exc()


@csrf_exempt
@api_key_required
def pipeline_start(request):
    """
    POST /api/pipeline/start/
    Kicks off the full analysis pipeline in a background thread.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if _pipeline_state['status'] == 'running':
        return JsonResponse({
            'pipeline_id': 'main',
            'status': 'already_running',
        })

    try:
        if _pipeline_state['df_raw'] is None:
            _load_datasets()

        _pipeline_state['status'] = 'running'
        _pipeline_state['error'] = None

        thread = threading.Thread(target=_run_pipeline_background, daemon=True)
        thread.start()

        return JsonResponse({
            'pipeline_id': 'main',
            'status': 'started',
        })

    except FileNotFoundError as e:
        return JsonResponse({'error': str(e)}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@api_key_required
def pipeline_status(request):
    """
    GET /api/pipeline/status/
    Returns the current pipeline execution status.
    """
    return JsonResponse({
        'status': _pipeline_state['status'],
        'error': _pipeline_state['error'],
    })


# ─── Step 2: Preprocessing ──────────────────────────────────────────────────

@csrf_exempt
@api_key_required
def preprocessing_ngrams(request):
    """
    GET /api/preprocessing/ngrams/?page=1
    Returns paginated N-gram terms with TF-IDF scores.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    ngrams_df = _pipeline_state.get('ngrams')
    if ngrams_df is None:
        return JsonResponse({'error': 'Pipeline not started or still running'}, status=400)

    page = int(request.GET.get('page', 1))
    records = ngrams_df.to_dict('records') if not ngrams_df.empty else []

    return JsonResponse(_paginate(records, page, page_size=20))


@csrf_exempt
@api_key_required
def preprocessing_edges(request):
    """
    GET /api/preprocessing/edges/?page=1
    Returns paginated mention edge list.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    edge_df = _pipeline_state.get('edge_list')
    if edge_df is None:
        return JsonResponse({'error': 'Pipeline not started or still running'}, status=400)

    page = int(request.GET.get('page', 1))
    records = edge_df.to_dict('records') if not edge_df.empty else []

    return JsonResponse(_paginate(records, page, page_size=20))


# ─── Step 3: Burst Detection ────────────────────────────────────────────────

@csrf_exempt
@api_key_required
def burst_analysis(request):
    """
    GET /api/burst/analysis/?term=perang
    Returns burst detection results. Optionally filter by a specific term.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    burst_data = _pipeline_state.get('burst_analysis')
    if burst_data is None:
        return JsonResponse({'error': 'Pipeline not started or still running'}, status=400)

    selected_term = request.GET.get('term', None)

    if selected_term and selected_term in burst_data.get('available_terms', []):
        # Re-run burst detection for the selected term only
        from .utils.preprocessing import build_term_time_series
        from .utils.kleinberg import run_burst_detection

        df_cleaned = _pipeline_state['df_cleaned']
        time_series = build_term_time_series(
            df_cleaned, text_col='cleaned_text', time_col='datetime',
            top_n_terms=50, bin_hours=1,
        )

        filtered_result = run_burst_detection(
            time_series['term_series'],
            time_series['bins'],
            s=2.0, gamma=1.0,
            selected_term=selected_term,
        )

        # Keep available_terms from full analysis
        filtered_result['available_terms'] = burst_data['available_terms']
        return JsonResponse(filtered_result)

    return JsonResponse(burst_data)


# ─── Step 4: Link Anomaly ───────────────────────────────────────────────────

@csrf_exempt
@api_key_required
def link_anomaly_network(request):
    """
    GET /api/link-anomaly/network/
    Returns the network graph data with anomaly detection results.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    network = _pipeline_state.get('network_data')
    if network is None:
        return JsonResponse({'error': 'Pipeline not started or still running'}, status=400)

    return JsonResponse(network)


# ─── Step 5: Executive Summary ──────────────────────────────────────────────

@csrf_exempt
@api_key_required
def summary_trends(request):
    """
    GET /api/summary/trends/
    Returns the final dual-validated trend classification table.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    trends = _pipeline_state.get('trends')
    if trends is None:
        return JsonResponse({'error': 'Pipeline not started or still running'}, status=400)

    return JsonResponse({'trends': trends})


# ─── Legacy Endpoints (preserved) ───────────────────────────────────────────

@csrf_exempt
@api_key_required
def get_csv_headers(request):
    if request.method == 'POST' and request.FILES.get('file'):
        csv_file = request.FILES['file']
        if not csv_file.name.endswith('.csv'):
            return JsonResponse({'error': 'File must be a CSV'}, status=400)

        try:
            df = pd.read_csv(csv_file, nrows=0)
            headers = df.columns.tolist()
            return JsonResponse({'headers': headers})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
@api_key_required
def process_gsdmm(request):
    """
    Run GSDMM topic modeling on an uploaded CSV file.

    POST parameters:
      - file: CSV file (multipart upload)
      - text_column: Name of the column containing text data
      - num_topics: (optional) Maximum number of topics, default 15

    Returns JSON with:
      - topics: List of discovered topics with top words
      - documents: Sample documents with their topic assignments
      - topics_csv_url: Download URL for full topics CSV
      - documents_csv_url: Download URL for full documents CSV
    """
    if request.method == 'POST' and request.FILES.get('file'):
        csv_file = request.FILES['file']
        text_column = request.POST.get('text_column')
        num_topics = int(request.POST.get('num_topics', 15))

        if not csv_file.name.endswith('.csv'):
            return JsonResponse({'error': 'File must be a CSV'}, status=400)
        if not text_column:
            return JsonResponse({'error': 'text_column is required'}, status=400)
        if num_topics < 2 or num_topics > 50:
            return JsonResponse({'error': 'num_topics must be between 2 and 50'}, status=400)

        try:
            topics, documents, iteration_logs = process_csv_gsdmm(csv_file, text_column, K=num_topics)

            # Save results to media directory
            results_dir = os.path.join(settings.MEDIA_ROOT, 'results')
            os.makedirs(results_dir, exist_ok=True)

            # Save topics CSV
            topics_filename = 'gsdmm_topics_output.csv'
            topics_path = os.path.join(results_dir, topics_filename)
            df_topics = pd.DataFrame([
                {
                    'Topic': t['topic_label'],
                    'Document Count': t['doc_count'],
                    'Top Words': ', '.join(t['top_words']),
                }
                for t in topics
            ])
            df_topics.to_csv(topics_path, index=False)

            # Save documents CSV
            docs_filename = 'gsdmm_documents_output.csv'
            docs_path = os.path.join(results_dir, docs_filename)
            df_docs = pd.DataFrame(documents)
            df_docs.to_csv(docs_path, index=False)

            topics_url = f"{settings.MEDIA_URL}results/{topics_filename}"
            docs_url = f"{settings.MEDIA_URL}results/{docs_filename}"

            return JsonResponse({
                'message': 'GSDMM topic modeling successful',
                'num_topics_found': len(topics),
                'num_documents': len(documents),
                'topics': topics,
                'documents': documents[:50],
                'iteration_logs': iteration_logs,
                'topics_csv_url': request.build_absolute_uri(topics_url),
                'documents_csv_url': request.build_absolute_uri(docs_url),
            })

        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)
