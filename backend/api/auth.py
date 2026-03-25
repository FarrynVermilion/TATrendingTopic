from django.http import JsonResponse
from django.conf import settings

def api_key_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        api_key = request.headers.get('X-Api-Key')
        if api_key != settings.API_KEY:
            return JsonResponse({'error': 'Invalid or absent API Key'}, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view
