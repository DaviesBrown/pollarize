from django.contrib import admin

from .models import Choice, Poll, Question, Vote, VoteSession


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'creator', 'is_public', 'is_active', 'created_at')
    list_filter = ('is_public', 'is_active', 'created_at')
    search_fields = ('title', 'description')
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'poll', 'text', 'question_type', 'order')
    list_filter = ('question_type',)
    search_fields = ('text',)
    inlines = [ChoiceInline]


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'text', 'vote_count', 'order')
    search_fields = ('text',)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'choice', 'ip_address', 'created_at')


@admin.register(VoteSession)
class VoteSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'poll', 'ip_address', 'created_at')
    search_fields = ('ip_address',)
