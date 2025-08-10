import json
from typing import Any, Dict, Optional

from django.http import HttpRequest, JsonResponse
from django.utils.deprecation import MiddlewareMixin


class ResponseEnvelopeMiddleware(MiddlewareMixin):
    """
    Wrap successful JSON responses in a consistent envelope and normalize errors.
    Only wraps DRF JsonResponse-like payloads.
    """

    def process_response(self, request: HttpRequest, response):
        # Pass through non-JSON responses
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            return response

        try:
            if hasattr(response, 'data'):
                data = response.data
            else:
                data = json.loads(response.content.decode('utf-8'))
        except Exception:
            return response

        status = getattr(response, 'status_code', 200)
        if 200 <= status < 300:
            body: Dict[str, Any] = {
                'success': True,
                'data': data,
                'error': None,
            }
            return JsonResponse(body, status=status)
        else:
            # Normalize error format
            error: Dict[str, Any] = {
                'code': getattr(response, 'status_code', 400),
                'message': None,
                'details': data,
            }
            body = {'success': False, 'data': None, 'error': error}
            return JsonResponse(body, status=status)
