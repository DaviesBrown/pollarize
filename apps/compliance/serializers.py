from rest_framework import serializers
from .models import ComplianceLog, GeolocationCache, ComplianceRule


class ComplianceLogSerializer(serializers.ModelSerializer):
    poll_title = serializers.CharField(source='poll.title', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ComplianceLog
        fields = [
            'id', 'poll', 'poll_title', 'user', 'username', 'ip_address',
            'action', 'status', 'country_code', 'blocked_reason',
            'metadata', 'request_path', 'user_agent', 'created_at'
        ]
        read_only_fields = fields


class GeolocationCacheSerializer(serializers.ModelSerializer):
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = GeolocationCache
        fields = [
            'id', 'ip_address', 'country_code', 'country_name',
            'region', 'city', 'latitude', 'longitude', 'provider',
            'is_valid', 'is_expired', 'created_at', 'updated_at', 'expires_at'
        ]
        read_only_fields = fields


class ComplianceRuleSerializer(serializers.ModelSerializer):
    specific_polls_count = serializers.IntegerField(
        source='specific_polls.count',
        read_only=True
    )

    class Meta:
        model = ComplianceRule
        fields = [
            'id', 'name', 'rule_type', 'description', 'is_active',
            'config', 'applies_to_all_polls', 'specific_polls',
            'specific_polls_count', 'created_at', 'updated_at'
        ]

    def validate_config(self, value):
        """Validate rule configuration based on rule type"""
        rule_type = self.initial_data.get('rule_type')

        if rule_type == 'geo_restriction':
            required_fields = ['allowed_countries', 'blocked_countries']
            if not any(field in value for field in required_fields):
                raise serializers.ValidationError(
                    "Geographic restrictions require 'allowed_countries' or 'blocked_countries'"
                )

        elif rule_type == 'age_verification':
            if 'minimum_age' not in value:
                raise serializers.ValidationError(
                    "Age verification requires 'minimum_age'"
                )

            try:
                min_age = int(value['minimum_age'])
                if min_age < 0 or min_age > 150:
                    raise serializers.ValidationError(
                        "Minimum age must be between 0 and 150"
                    )
            except (ValueError, TypeError):
                raise serializers.ValidationError(
                    "Minimum age must be a valid number"
                )

        elif rule_type == 'payment_limit':
            required_fields = ['max_amount', 'period']
            for field in required_fields:
                if field not in value:
                    raise serializers.ValidationError(
                        f"Payment limits require '{field}'"
                    )

        return value


class ComplianceStatsSerializer(serializers.Serializer):
    """Serializer for compliance statistics"""
    total_logs = serializers.IntegerField()
    blocked_requests = serializers.IntegerField()
    allowed_requests = serializers.IntegerField()
    flagged_requests = serializers.IntegerField()
    top_blocked_countries = serializers.ListField()
    top_blocked_actions = serializers.ListField()
    block_rate_by_hour = serializers.DictField()
    geographic_distribution = serializers.DictField()
