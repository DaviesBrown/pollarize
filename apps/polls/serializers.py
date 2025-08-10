from django.db.models import F
from rest_framework import serializers

from .models import Choice, Poll, Question, Vote, VoteSession


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'text', 'vote_count', 'order']
        read_only_fields = ['vote_count']


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = ['id', 'text', 'question_type', 'is_required', 'order', 'choices']

    def create(self, validated_data):
        choices_data = validated_data.pop('choices', [])
        question = Question.objects.create(**validated_data)
        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)
        return question


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
            'is_active',
            'expires_at',
            'is_public',
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
            raise serializers.ValidationError({'non_field_errors': ['IP address not found']})

        if VoteSession.objects.filter(poll=poll, ip_address=ip_address).exists():
            raise serializers.ValidationError(
                {'non_field_errors': ['You have already voted on this poll']}
            )
        return attrs
