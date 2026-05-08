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
from .utils.json_encoder import NumpyJSONEncoder
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
# Configuration: Storage path for the active dataset
DATA_DIR = PROJECT_ROOT / 'data'
DATASET_PATH = DATA_DIR / 'active_dataset.csv'


def _load_datasets():
    """Load the single active CSV into pipeline state."""
    global _pipeline_state

    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    
    # We use the same dataframe for both, but different columns will be used
    # df_raw will use 'text' and 'handle'
    # df_cleaned will use 'cleaned_text'
    if 'cleaned_text' not in df.columns and 'text' in df.columns:
        df['cleaned_text'] = df['text']
        
    _pipeline_state['df_raw'] = df
    _pipeline_state['df_cleaned'] = df


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
def dataset_upload(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    print(f"[*] Upload request received. Files: {request.FILES.keys()}")
    print(f"[*] Headers: {dict(request.headers)}")
    dataset_file = request.FILES.get('file')

    if not dataset_file:
        print("[!] No file found in request.FILES under key 'file'")
        return JsonResponse({'error': 'Dataset file is required'}, status=400)

    try:
        # Create directory if it doesn't exist
        DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Save file
        with open(DATASET_PATH, 'wb+') as destination:
            for chunk in dataset_file.chunks():
                destination.write(chunk)

        # Reload datasets into memory
        _load_datasets()

        # Clear existing pipeline results since data changed
        global _pipeline_state
        for key in ['ngrams', 'edge_list', 'burst_analysis', 'network_data', 'trends', 'overview']:
            _pipeline_state[key] = None
        _pipeline_state['status'] = 'idle'

        # Compute new overview
        from .utils.preprocessing import compute_dataset_overview
        _pipeline_state['overview'] = compute_dataset_overview(
            _pipeline_state['df_raw'],
            _pipeline_state['df_cleaned'],
        )

        return JsonResponse({
            'message': 'Datasets uploaded successfully',
            'overview': _pipeline_state['overview']
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
        if _pipeline_state['df_raw'] is None:
            if DATASET_PATH.exists():
                _load_datasets()
            else:
                return JsonResponse({'error': 'No dataset loaded. Please upload CSV files.'}, status=404)

        if _pipeline_state['overview'] is None:
            from .utils.preprocessing import compute_dataset_overview
            _pipeline_state['overview'] = compute_dataset_overview(
                _pipeline_state['df_raw'],
                _pipeline_state['df_cleaned'],
            )

        return JsonResponse(_pipeline_state['overview'], encoder=NumpyJSONEncoder)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ─── Pipeline Start ─────────────────────────────────────────────────────────

def _run_pipeline_background(top_n_terms=50, bin_hours=1, s=2.0, gamma=1.0, anomaly_threshold=0.5):
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

        # Ensure cleaned_text exists even if loaded prior to fix
        if 'cleaned_text' not in df_cleaned.columns and 'text' in df_cleaned.columns:
            df_cleaned['cleaned_text'] = df_cleaned['text']

        # Step 2: Preprocessing
        cleaned_texts = df_cleaned['cleaned_text'].dropna().astype(str).tolist()
        ngrams_df, total_tokens = extract_ngrams(cleaned_texts, n_range=(1, 2), min_df=5)
        edge_df = extract_edge_list(df_raw)

        _pipeline_state['ngrams'] = ngrams_df
        _pipeline_state['total_tokens'] = total_tokens
        _pipeline_state['edge_list'] = edge_df

        # Step 3: Burst Detection
        time_series = build_term_time_series(
            df_cleaned, text_col='cleaned_text', time_col='datetime',
            top_n_terms=top_n_terms, bin_hours=bin_hours,
        )

        burst_result = run_burst_detection(
            time_series['term_series'],
            time_series['bins'],
            s=s, gamma=gamma,
        )

        _pipeline_state['burst_analysis'] = burst_result

        # Step 4: Link Anomaly Detection
        anomaly_result = run_link_anomaly_analysis(
            edge_df,
            burst_result['burst_periods'],
            anomaly_threshold=anomaly_threshold,
        )

        _pipeline_state['network_data'] = anomaly_result['network']
        _pipeline_state['anomaly_result'] = anomaly_result

        # Step 5: Trend Validation
        trends = build_trend_summary(
            burst_result['burst_periods'],
            anomaly_result['burst_anomaly_scores'],
            edge_df,
            anomaly_threshold=anomaly_threshold,
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
            if DATASET_PATH.exists():
                _load_datasets()
            else:
                return JsonResponse({'error': 'No dataset loaded. Please upload CSVs first.'}, status=400)

        # Parse configuration from request body
        config = {}
        if request.body:
            try:
                config = json.loads(request.body)
            except json.JSONDecodeError:
                pass

        _pipeline_state['status'] = 'running'
        _pipeline_state['error'] = None

        thread = threading.Thread(
            target=_run_pipeline_background,
            kwargs={
                'top_n_terms': int(config.get('top_n_terms', 50)),
                'bin_hours': int(config.get('bin_hours', 1)),
                's': float(config.get('kleinberg_s', 2.0)),
                'gamma': float(config.get('kleinberg_gamma', 1.0)),
                'anomaly_threshold': float(config.get('anomaly_threshold', 0.5)),
            },
            daemon=True
        )
        thread.start()

        return JsonResponse({
            'pipeline_id': 'main',
            'status': 'started',
            'config': config
        }, encoder=NumpyJSONEncoder)

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
    }, encoder=NumpyJSONEncoder)


# ─── Step 2: Preprocessing ──────────────────────────────────────────────────

@csrf_exempt
@api_key_required
def preprocessing_run(request):
    """
    POST /api/preprocessing/run/
    Runs preprocessing (N-grams & Edge extraction) with column configurations.
    """
    global _pipeline_state
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
        
    if _pipeline_state.get('df_cleaned') is None:
        return JsonResponse({'error': 'No dataset loaded'}, status=400)
        
    try:
        config = json.loads(request.body) if request.body else {}
        text_col = config.get('text_column', 'cleaned_text')
        time_col = config.get('time_column', 'datetime')
        handle_col = config.get('handle_column', 'handle')
        
        # Save these configurations so later steps can use them
        _pipeline_state['config'] = {
            'text_column': text_col,
            'time_column': time_col,
            'handle_column': handle_col
        }
        
        from .utils.preprocessing import extract_ngrams, extract_edge_list
        df_cleaned = _pipeline_state['df_cleaned']
        df_raw = _pipeline_state['df_raw']
        
        # Ensure column exists or fallback
        if text_col not in df_cleaned.columns and 'text' in df_cleaned.columns:
            df_cleaned[text_col] = df_cleaned['text']
            
        texts = df_cleaned[text_col].dropna().astype(str).tolist()
        ngrams_df, total_tokens = extract_ngrams(texts, n_range=(1, 2), min_df=5)
        
        edge_df = extract_edge_list(df_raw, text_col='text', handle_col=handle_col, time_col=time_col)
        
        _pipeline_state['ngrams'] = ngrams_df
        _pipeline_state['total_tokens'] = total_tokens
        _pipeline_state['edge_list'] = edge_df
        
        return JsonResponse({'message': 'Preprocessing complete', 'total_tokens': total_tokens})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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

    response_data = _paginate(records, page, page_size=20)
    response_data['total_tokens'] = _pipeline_state.get('total_tokens', 0)

    return JsonResponse(response_data, encoder=NumpyJSONEncoder)


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

    return JsonResponse(_paginate(records, page, page_size=20), encoder=NumpyJSONEncoder)


# ─── Step 3: Burst Detection ────────────────────────────────────────────────

@csrf_exempt
@api_key_required
def burst_analysis(request):
    """
    GET /api/burst/analysis/?term=perang - Returns current burst data
    POST /api/burst/analysis/ - Runs burst detection with custom parameters
    """
    global _pipeline_state
    
    if request.method == 'POST':
        # Re-run burst detection with parameters
        if _pipeline_state.get('df_cleaned') is None:
            return JsonResponse({'error': 'No dataset loaded'}, status=400)
            
        try:
            config = json.loads(request.body) if request.body else {}
            top_n_terms = int(config.get('top_n_terms', 50))
            bin_hours = int(config.get('bin_hours', 1))
            s = float(config.get('kleinberg_s', 2.0))
            gamma = float(config.get('kleinberg_gamma', 1.0))
            
            from .utils.preprocessing import build_term_time_series
            from .utils.kleinberg import run_burst_detection
            
            # Use configured columns if available
            p_config = _pipeline_state.get('config', {})
            text_col = p_config.get('text_column', 'cleaned_text')
            time_col = p_config.get('time_column', 'datetime')
            
            time_series = build_term_time_series(
                _pipeline_state['df_cleaned'], text_col=text_col, time_col=time_col,
                top_n_terms=top_n_terms, bin_hours=bin_hours,
            )
            
            burst_result = run_burst_detection(
                time_series['term_series'],
                time_series['bins'],
                s=s, gamma=gamma,
            )
            
            _pipeline_state['burst_analysis'] = burst_result
            return JsonResponse(burst_result, encoder=NumpyJSONEncoder)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    elif request.method == 'GET':
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
            return JsonResponse(filtered_result, encoder=NumpyJSONEncoder)

        return JsonResponse(burst_data, encoder=NumpyJSONEncoder)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ─── Step 4: Link Anomaly ───────────────────────────────────────────────────

@csrf_exempt
@api_key_required
def link_anomaly_network(request):
    """
    GET /api/link-anomaly/network/
    POST /api/link-anomaly/network/
    """
    global _pipeline_state

    if request.method == 'POST':
        edge_df = _pipeline_state.get('edge_list')
        burst_result = _pipeline_state.get('burst_analysis')
        
        if edge_df is None or burst_result is None:
            return JsonResponse({'error': 'Previous steps not completed'}, status=400)
            
        try:
            config = json.loads(request.body) if request.body else {}
            anomaly_threshold = float(config.get('anomaly_threshold', 0.5))
            
            from .utils.link_anomaly import run_link_anomaly_analysis
            anomaly_result = run_link_anomaly_analysis(
                edge_df,
                burst_result['burst_periods'],
                anomaly_threshold=anomaly_threshold,
            )
            
            _pipeline_state['network_data'] = anomaly_result['network']
            _pipeline_state['anomaly_result'] = anomaly_result # store for step 5
            return JsonResponse(anomaly_result['network'], encoder=NumpyJSONEncoder)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    elif request.method == 'GET':
        network = _pipeline_state.get('network_data')
        if network is None:
            return JsonResponse({'error': 'Pipeline not started or still running'}, status=400)

        return JsonResponse(network, encoder=NumpyJSONEncoder)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


# ─── Step 5: Executive Summary ──────────────────────────────────────────────

@csrf_exempt
@api_key_required
def summary_trends(request):
    """
    GET /api/summary/trends/
    POST /api/summary/trends/
    """
    global _pipeline_state

    if request.method == 'POST':
        burst_result = _pipeline_state.get('burst_analysis')
        edge_df = _pipeline_state.get('edge_list')
        anomaly_result = _pipeline_state.get('anomaly_result')
        
        if not all([burst_result, edge_df, anomaly_result]):
            # If anomaly_result isn't saved separately in state, we might need to recreate it
            # But we added it in link_anomaly POST handler above.
            return JsonResponse({'error': 'Previous steps not completed'}, status=400)

        try:
            config = json.loads(request.body) if request.body else {}
            anomaly_threshold = float(config.get('anomaly_threshold', 0.5))
            
            from .utils.trend_validator import build_trend_summary
            trends = build_trend_summary(
                burst_result['burst_periods'],
                anomaly_result['burst_anomaly_scores'],
                edge_df,
                anomaly_threshold=anomaly_threshold,
            )
            
            _pipeline_state['trends'] = trends
            _pipeline_state['status'] = 'completed'
            return JsonResponse({'trends': trends}, encoder=NumpyJSONEncoder)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    elif request.method == 'GET':
        trends = _pipeline_state.get('trends')
        if trends is None:
            return JsonResponse({'error': 'Pipeline not started or still running'}, status=400)

        return JsonResponse({'trends': trends}, encoder=NumpyJSONEncoder)
        
    return JsonResponse({'error': 'Method not allowed'}, status=405)


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
