import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.urls import resolve
from .services import ComplianceService

logger = logging.getLogger(__name__)


class GeoRestrictionMiddleware(MiddlewareMixin):
    """Middleware to enforce geographic restrictions on polls"""

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.compliance_service = ComplianceService()

    def process_request(self, request):
        """Process request before it reaches the view"""

        # Only check poll-related endpoints that involve voting
        if not self._should_check_restrictions(request):
            return None

        try:
            # Extract poll information from URL
            poll_info = self._extract_poll_info(request)
            if not poll_info:
                return None

            poll_id = poll_info.get('poll_id')
            if not poll_id:
                return None

            # Get the poll object
            from apps.polls.models import Poll
            try:
                poll = Poll.objects.get(id=poll_id)
            except Poll.DoesNotExist:
                return None

            # Get client IP and user
            ip_address = self.compliance_service.get_client_ip(request)
            user = request.user if request.user.is_authenticated else None

            # Check geographic restrictions
            geo_result = self.compliance_service.check_geographic_restrictions(
                poll=poll,
                ip_address=ip_address,
                user=user
            )

            if geo_result['blocked']:
                return JsonResponse({
                    'success': False,
                    'error': 'GEOGRAPHIC_RESTRICTION',
                    'message': geo_result['reason'],
                    'data': {
                        'country_code': geo_result['country_code']
                    }
                }, status=403)

            # Check voting limits
            voting_result = self.compliance_service.check_voting_limits(
                poll=poll,
                user=user,
                ip_address=ip_address
            )

            if voting_result['blocked']:
                return JsonResponse({
                    'success': False,
                    'error': 'VOTING_LIMIT_EXCEEDED',
                    'message': voting_result['reason']
                }, status=403)

            # Store compliance data in request for use in views
            request.compliance_data = {
                'ip_address': ip_address,
                'country_code': geo_result.get('country_code', 'XX'),
                'location': geo_result.get('location', {}),
                'poll': poll
            }

        except Exception as e:
            logger.error(f"Error in GeoRestrictionMiddleware: {e}")
            # In case of errors, log but don't block the request
            self.compliance_service.log_compliance_action(
                action='middleware_error',
                ip_address=self.compliance_service.get_client_ip(request),
                status='flagged',
                reason=f"Middleware error: {str(e)}",
                request_path=request.path,
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

        return None

    def _should_check_restrictions(self, request) -> bool:
        """Determine if the request should be checked for restrictions"""

        # Check if it's a voting endpoint
        voting_patterns = [
            '/api/v1/polls/',
            '/vote/',
            '/submit-vote/',
        ]

        path = request.path.lower()

        # Must be a POST request for voting
        if request.method != 'POST':
            return False

        # Check if path contains voting patterns
        for pattern in voting_patterns:
            if pattern in path:
                return True

        return False

    def _extract_poll_info(self, request) -> dict:
        """Extract poll information from the request"""
        try:
            # Try to resolve the URL to get parameters
            resolver_match = resolve(request.path)
            if resolver_match and 'poll_id' in resolver_match.kwargs:
                return {'poll_id': resolver_match.kwargs['poll_id']}

            # Fallback: parse URL manually
            path_parts = request.path.strip('/').split('/')

            if 'polls' in path_parts:
                poll_index = path_parts.index('polls')
                if len(path_parts) > poll_index + 1:
                    poll_id = path_parts[poll_index + 1]
                    try:
                        return {'poll_id': int(poll_id)}
                    except ValueError:
                        pass

            return {}

        except Exception as e:
            logger.error(f"Error extracting poll info: {e}")
            return {}


class ComplianceLoggingMiddleware(MiddlewareMixin):
    """Middleware to log all requests for compliance auditing"""

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.compliance_service = ComplianceService()

    def process_response(self, request, response):
        """Log request information after processing"""

        # Only log specific endpoints for compliance
        if self._should_log_request(request):
            try:
                ip_address = self.compliance_service.get_client_ip(request)
                user = request.user if request.user.is_authenticated else None

                # Determine action based on response status
                if response.status_code >= 400:
                    action = 'request_blocked'
                    status = 'blocked'
                    reason = f"HTTP {response.status_code}"
                else:
                    action = 'request_allowed'
                    status = 'allowed'
                    reason = "Request processed successfully"

                self.compliance_service.log_compliance_action(
                    action=action,
                    user=user,
                    ip_address=ip_address,
                    status=status,
                    reason=reason,
                    request_path=request.path,
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    metadata={
                        'method': request.method,
                        'status_code': response.status_code,
                        'content_type': response.get('Content-Type', ''),
                    }
                )

            except Exception as e:
                logger.error(f"Error in ComplianceLoggingMiddleware: {e}")

        return response

    def _should_log_request(self, request) -> bool:
        """Determine if the request should be logged"""

        # Log all API requests
        if request.path.startswith('/api/'):
            return True

        # Log authentication-related requests
        auth_patterns = ['/auth/', '/login/', '/register/', '/token/']
        for pattern in auth_patterns:
            if pattern in request.path:
                return True

        return False
