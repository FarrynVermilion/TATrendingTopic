import os
import pandas as pd
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from .auth import api_key_required
from .utils.tfidf_utils import process_csv_tfidf

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
def process_tfidf(request):
    if request.method == 'POST' and request.FILES.get('file'):
        csv_file = request.FILES['file']
        text_column = request.POST.get('text_column')
        
        if not csv_file.name.endswith('.csv'):
            return JsonResponse({'error': 'File must be a CSV'}, status=400)
        if not text_column:
            return JsonResponse({'error': 'text_column is required'}, status=400)
            
        try:
            df_words, df_sentences = process_csv_tfidf(csv_file, text_column)
            
            # Save results to media directory
            results_dir = os.path.join(settings.MEDIA_ROOT, 'results')
            os.makedirs(results_dir, exist_ok=True)
            
            words_filename = 'tfidf_words_output.csv'
            sentences_filename = 'tfidf_sentences_output.csv'
            
            words_path = os.path.join(results_dir, words_filename)
            sentences_path = os.path.join(results_dir, sentences_filename)
            
            df_words.to_csv(words_path, index=False)
            df_sentences.to_csv(sentences_path, index=False)
            
            words_url = f"{settings.MEDIA_URL}results/{words_filename}"
            sentences_url = f"{settings.MEDIA_URL}results/{sentences_filename}"
            
            return JsonResponse({
                'message': 'TF-IDF processing successful',
                'word_weights_url': request.build_absolute_uri(words_url),
                'sentence_weights_url': request.build_absolute_uri(sentences_url),
                'top_words': df_words.head(20).to_dict('records'),
                'top_sentences': df_sentences.head(20).to_dict('records')
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Invalid request'}, status=400)
