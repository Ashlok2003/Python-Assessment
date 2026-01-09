from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Label(models.Model):
    """Unique labels that can be assigned to issues."""
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Issue(models.Model):
    """Issue with versioning for optimistic concurrency control."""

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        IN_PROGRESS = 'in_progress', 'In Progress'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )
    version = models.PositiveIntegerField(default=1)

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reported_issues'
    )
    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_issues'
    )
    labels = models.ManyToManyField(Label, blank=True, related_name='issues')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['assignee']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"#{self.id} - {self.title}"

    def save(self, *args, **kwargs):
        # Track when issue is resolved
        if self.status == self.Status.RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)


class Comment(models.Model):
    """Comments on issues with validation for non-empty body and author."""
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on #{self.issue.id}"

    def clean(self):
        if not self.body or not self.body.strip():
            raise ValidationError({'body': 'Comment body cannot be empty.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class IssueHistory(models.Model):
    """Track issue changes for timeline feature (bonus)."""

    class ChangeType(models.TextChoices):
        CREATED = 'created', 'Created'
        STATUS_CHANGED = 'status_changed', 'Status Changed'
        ASSIGNEE_CHANGED = 'assignee_changed', 'Assignee Changed'
        LABELS_CHANGED = 'labels_changed', 'Labels Changed'
        COMMENT_ADDED = 'comment_added', 'Comment Added'
        UPDATED = 'updated', 'Updated'

    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='history'
    )
    change_type = models.CharField(max_length=20, choices=ChangeType.choices)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True
    )
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Issue histories'

    def __str__(self):
        return f"{self.change_type} on #{self.issue.id} at {self.timestamp}"
