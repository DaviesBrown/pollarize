from django.contrib import admin

from .models import Choice, Poll, Question, Vote, VoteSession, Bookmark, PollShare


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 1


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'creator', 'category', 'is_public',
                    'is_active', 'allows_revote', 'created_at')
    list_filter = ('is_public', 'is_active', 'allows_revote', 'category', 'created_at')
    search_fields = ('title', 'description', 'creator__username')
    inlines = [QuestionInline]
    readonly_fields = ('created_at',)


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
    list_filter = ('created_at',)
    search_fields = ('choice__text', 'ip_address')
    readonly_fields = ('created_at',)


@admin.register(VoteSession)
class VoteSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'poll', 'ip_address', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('poll__title', 'ip_address')
    readonly_fields = ('created_at',)


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'poll', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'poll__title')
    readonly_fields = ('created_at',)


@admin.register(PollShare)
class PollShareAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'poll', 'platform', 'referral_code', 'clicks', 'shared_at')
    list_filter = ('platform', 'shared_at')
    search_fields = ('user__username', 'poll__title', 'referral_code')
    readonly_fields = ('referral_code', 'shared_at')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('clicks', 'conversions')
        return self.readonly_fields
