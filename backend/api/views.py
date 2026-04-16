import os
import json
import pandas as pd
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from .auth import api_key_required
from .utils.gsdmm_utils import process_csv_gsdmm


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
                'documents': documents[:50],  # Return first 50 for preview
                'iteration_logs': iteration_logs,
                'topics_csv_url': request.build_absolute_uri(topics_url),
                'documents_csv_url': request.build_absolute_uri(docs_url),
            })
            
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request'}, status=400)
