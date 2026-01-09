from django.contrib import admin
from .models import Issue, Comment, Label, IssueHistory


@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'created_at']
    search_fields = ['name']


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'status', 'reporter', 'assignee', 'version', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'description']
    raw_id_fields = ['reporter', 'assignee']
    filter_horizontal = ['labels']
    readonly_fields = ['version', 'created_at', 'updated_at', 'resolved_at']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'issue', 'author', 'created_at']
    list_filter = ['created_at']
    search_fields = ['body']
    raw_id_fields = ['issue', 'author']


@admin.register(IssueHistory)
class IssueHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'issue', 'change_type', 'changed_by', 'timestamp']
    list_filter = ['change_type', 'timestamp']
    raw_id_fields = ['issue', 'changed_by']
    readonly_fields = ['timestamp']
