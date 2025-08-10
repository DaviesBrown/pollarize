import uuid
from django.db.models import F, Sum
from rest_framework import serializers
from django.utils import timezone

from apps.core.serializers import UserSerializer
from .models import Choice, Poll, Question, Vote, VoteSession, Bookmark, PollShare


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'vote_count', 'order']
        read_only_fields = ['vote_count']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type',
                  'is_required', 'order', 'choices']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        question = Question.objects.create(**validated_data)
        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)
        return question


class PollListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    question_count = serializers.IntegerField(source='questions.count', read_only=True)
    vote_count = serializers.SerializerMethodField()
    creator_username = serializers.ReadOnlyField(source='creator.username')
    category_name = serializers.ReadOnlyField(source='category.name')
    
    class Meta:
        model = Poll
        fields = ['id', 'title', 'description', 'creator_username', 
                 'is_active', 'expires_at', 'is_public', 'created_at',
                 'question_count', 'vote_count', 'category_name']
    
    def get_vote_count(self, obj):
        return Choice.objects.filter(question__poll=obj).aggregate(
            total_votes=Sum('vote_count'))['total_votes'] or 0


class PollDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with nested questions and choices"""
    questions = QuestionSerializer(many=True, read_only=True)
    creator = UserSerializer(read_only=True)
    is_bookmarked = serializers.SerializerMethodField()
    category_name = serializers.ReadOnlyField(source='category.name')
    
    class Meta:
        model = Poll
        fields = ['id', 'title', 'description', 'creator', 'is_active',
                 'expires_at', 'is_public', 'created_at', 'questions',
                 'allows_revote', 'category', 'category_name', 'is_bookmarked']
    
    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Bookmark.objects.filter(user=request.user, poll=obj).exists()
        return False


class PollSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, required=False)
    creator = serializers.ReadOnlyField(source='creator.username')

    class Meta:
        model = Poll
        fields = [
            'id',
            'title',
            'description',
            'creator',
            'category',
            'is_active',
            'expires_at',
            'is_public',
            'allows_revote',
            'created_at',
            'questions',
        ]

    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        poll = Poll.objects.create(**validated_data)

        for question_data in questions_data:
            choices_data = question_data.pop('choices', [])
            question = Question.objects.create(poll=poll, **question_data)
            for choice_data in choices_data:
                Choice.objects.create(question=question, **choice_data)
        return poll


class VoteSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoteSession
        fields = ['id', 'poll', 'ip_address']
        read_only_fields = ['ip_address']


class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = ['id', 'choice', 'ip_address']
        read_only_fields = ['ip_address']

    def validate(self, attrs):
        choice = attrs['choice']
        poll = choice.question.poll
        request = self.context.get('request')
        ip_address = request.META.get('REMOTE_ADDR') if request else None

        if not ip_address:
            raise serializers.ValidationError(
                {'non_field_errors': ['IP address not found']})

        if VoteSession.objects.filter(poll=poll, ip_address=ip_address).exists():
            raise serializers.ValidationError(
                {'non_field_errors': ['You have already voted on this poll']}
            )
        return attrs


class BookmarkSerializer(serializers.ModelSerializer):
    poll_title = serializers.ReadOnlyField(source='poll.title')
    
    class Meta:
        model = Bookmark
        fields = ['id', 'poll', 'poll_title', 'created_at']
        read_only_fields = ['created_at']
    
    def validate(self, attrs):
        request = self.context.get('request')
        if Bookmark.objects.filter(user=request.user, poll=attrs['poll']).exists():
            raise serializers.ValidationError("Poll already bookmarked")
        return attrs


class PollShareSerializer(serializers.ModelSerializer):
    class Meta:
        model = PollShare
        fields = ['id', 'poll', 'platform', 'shared_at', 
                 'referral_code', 'clicks', 'conversions']
        read_only_fields = ['shared_at', 'clicks', 'conversions', 'referral_code']
    
    def create(self, validated_data):
        # Generate a unique referral code
        validated_data['referral_code'] = uuid.uuid4().hex[:10]
        return super().create(validated_data)
