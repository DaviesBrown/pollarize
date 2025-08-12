import logging
import requests
from typing import Optional, Dict, Any
from django.core.cache import cache
from django.utils import timezone
from django.conf import settings
from .models import GeolocationCache, ComplianceLog

logger = logging.getLogger(__name__)


class GeolocationService:
    """Service for handling IP geolocation with caching and fallback providers"""

    DEFAULT_PROVIDERS = [
        {
            'name': 'ipapi.co',
            'url': 'https://ipapi.co/{ip}/json/',
            'timeout': 3,
            'rate_limit': 1000,  # requests per day
        },
        {
            'name': 'ip-api.com',
            'url': 'http://ip-api.com/json/{ip}',
            'timeout': 3,
            'rate_limit': 45,  # requests per minute
        }
    ]

    def __init__(self):
        self.providers = getattr(
            settings, 'GEOLOCATION_PROVIDERS', self.DEFAULT_PROVIDERS)

    def get_location_data(self, ip_address: str) -> Optional[Dict[str, Any]]:
        """Get geolocation data for an IP address with caching"""

        # Check database cache first
        try:
            cached = GeolocationCache.objects.get(
                ip_address=ip_address,
                is_valid=True
            )
            if not cached.is_expired():
                return {
                    'country_code': cached.country_code,
                    'country_name': cached.country_name,
                    'region': cached.region,
                    'city': cached.city,
                    'latitude': cached.latitude,
                    'longitude': cached.longitude,
                    'cached': True
                }
        except GeolocationCache.DoesNotExist:
            pass

        # Try each provider
        for provider in self.providers:
            try:
                data = self._fetch_from_provider(ip_address, provider)
                if data:
                    # Cache the result
                    self._cache_location_data(
                        ip_address, data, provider['name'])
                    return data
            except Exception as e:
                logger.warning(
                    f"Geolocation provider {provider['name']} failed: {e}")
                continue

        # Return default if all providers fail
        return self._get_default_location()

    def _fetch_from_provider(self, ip_address: str, provider: Dict) -> Optional[Dict]:
        """Fetch data from a specific provider"""
        url = provider['url'].format(ip=ip_address)

        try:
            response = requests.get(url, timeout=provider['timeout'])
            if response.status_code == 200:
                data = response.json()
                return self._normalize_response(data, provider['name'])
        except Exception as e:
            logger.error(f"Error fetching from {provider['name']}: {e}")

        return None

    def _normalize_response(self, data: Dict, provider: str) -> Dict:
        """Normalize response from different providers to a standard format"""
        if provider == 'ipapi.co':
            return {
                'country_code': data.get('country_code', 'XX'),
                'country_name': data.get('country_name', ''),
                'region': data.get('region', ''),
                'city': data.get('city', ''),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
            }
        elif provider == 'ip-api.com':
            return {
                'country_code': data.get('countryCode', 'XX'),
                'country_name': data.get('country', ''),
                'region': data.get('regionName', ''),
                'city': data.get('city', ''),
                'latitude': data.get('lat'),
                'longitude': data.get('lon'),
            }

        return {}

    def _cache_location_data(self, ip_address: str, data: Dict, provider: str):
        """Cache location data in the database"""
        try:
            GeolocationCache.objects.update_or_create(
                ip_address=ip_address,
                defaults={
                    'country_code': data.get('country_code', 'XX'),
                    'country_name': data.get('country_name', ''),
                    'region': data.get('region', ''),
                    'city': data.get('city', ''),
                    'latitude': data.get('latitude'),
                    'longitude': data.get('longitude'),
                    'provider': provider,
                    'is_valid': True,
                    'expires_at': timezone.now() + timezone.timedelta(hours=24)
                }
            )
        except Exception as e:
            logger.error(f"Error caching geolocation data: {e}")

    def _get_default_location(self) -> Dict:
        """Return default location when all providers fail"""
        return {
            'country_code': 'XX',
            'country_name': 'Unknown',
            'region': '',
            'city': '',
            'latitude': None,
            'longitude': None,
        }


class ComplianceService:
    """Service for handling compliance checks and logging"""

    def __init__(self):
        self.geo_service = GeolocationService()

    def check_geographic_restrictions(self, poll, ip_address: str, user=None) -> Dict[str, Any]:
        """Check if a poll is accessible from the user's location"""

        # Get user's location
        location_data = self.geo_service.get_location_data(ip_address)
        country_code = location_data.get('country_code', 'XX')

        # Check if poll has geographic restrictions
        is_blocked = False
        reason = ""

        # For now, we'll add the region_lock field to Poll model later
        # This is a placeholder for the logic
        if hasattr(poll, 'region_lock') and poll.region_lock:
            allowed_countries = getattr(
                poll, 'allowed_countries', '').split(',')
            if country_code not in allowed_countries:
                is_blocked = True
                reason = f"Poll not available in {country_code}"

        # Log the compliance check
        self.log_compliance_action(
            action='geo_block' if is_blocked else 'geo_check',
            poll=poll,
            user=user,
            ip_address=ip_address,
            country_code=country_code,
            status='blocked' if is_blocked else 'allowed',
            reason=reason or "Geographic check passed",
            metadata=location_data
        )

        return {
            'blocked': is_blocked,
            'reason': reason,
            'country_code': country_code,
            'location': location_data
        }

    def check_voting_limits(self, poll, user, ip_address: str) -> Dict[str, Any]:
        """Check voting frequency and limits"""
        from apps.polls.models import VoteSession

        # Check if user has already voted (for non-revote polls)
        if not poll.allows_revote and user:
            existing_session = VoteSession.objects.filter(
                poll=poll,
                user=user
            ).first()

            if existing_session:
                self.log_compliance_action(
                    action='vote_limit',
                    poll=poll,
                    user=user,
                    ip_address=ip_address,
                    status='blocked',
                    reason="User has already voted on this poll"
                )
                return {
                    'blocked': True,
                    'reason': "You have already voted on this poll"
                }

        # Check IP-based voting for anonymous users
        if not user:
            existing_session = VoteSession.objects.filter(
                poll=poll,
                ip_address=ip_address
            ).first()

            if existing_session and not poll.allows_revote:
                self.log_compliance_action(
                    action='vote_limit',
                    poll=poll,
                    user=None,
                    ip_address=ip_address,
                    status='blocked',
                    reason="IP address has already voted on this poll"
                )
                return {
                    'blocked': True,
                    'reason': "This device has already voted on this poll"
                }

        return {'blocked': False, 'reason': ''}

    def log_compliance_action(self, action: str, poll=None, user=None,
                              ip_address: str = '', country_code: str = '',
                              status: str = 'blocked', reason: str = '',
                              metadata: Dict = None, request_path: str = '',
                              user_agent: str = ''):
        """Log a compliance action"""
        try:
            ComplianceLog.objects.create(
                poll=poll,
                user=user,
                ip_address=ip_address,
                action=action,
                status=status,
                country_code=country_code,
                blocked_reason=reason,
                metadata=metadata or {},
                request_path=request_path,
                user_agent=user_agent
            )
        except Exception as e:
            logger.error(f"Error logging compliance action: {e}")

    def get_client_ip(self, request) -> str:
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')

        # Handle localhost/development
        if ip in ['127.0.0.1', '::1', 'localhost']:
            return '8.8.8.8'  # Use public IP for testing

        return ip
