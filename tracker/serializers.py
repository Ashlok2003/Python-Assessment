from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Issue, Comment, Label, IssueHistory


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class LabelSerializer(serializers.ModelSerializer):
    """Serializer for Label model."""
    class Meta:
        model = Label
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['created_at']


class CommentSerializer(serializers.ModelSerializer):
    """Serializer for Comment model."""
    author = UserSerializer(read_only=True)
    author_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'body', 'author', 'author_id', 'created_at']
        read_only_fields = ['created_at']

    def validate_body(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Comment body cannot be empty.")
        return value.strip()

    def validate_author_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Author does not exist.")
        return value


class IssueListSerializer(serializers.ModelSerializer):
    """Serializer for listing issues (lightweight)."""
    reporter = UserSerializer(read_only=True)
    assignee = UserSerializer(read_only=True)
    labels = LabelSerializer(many=True, read_only=True)

    class Meta:
        model = Issue
        fields = [
            'id', 'title', 'status', 'version',
            'reporter', 'assignee', 'labels',
            'created_at', 'updated_at'
        ]


class IssueDetailSerializer(serializers.ModelSerializer):
    """Serializer for issue details with comments."""
    reporter = UserSerializer(read_only=True)
    assignee = UserSerializer(read_only=True)
    labels = LabelSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Issue
        fields = [
            'id', 'title', 'description', 'status', 'version',
            'reporter', 'assignee', 'labels', 'comments',
            'created_at', 'updated_at', 'resolved_at'
        ]


class IssueCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating issues."""
    reporter_id = serializers.IntegerField()
    assignee_id = serializers.IntegerField(required=False, allow_null=True)
    label_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Issue
        fields = [
            'id', 'title', 'description', 'status',
            'reporter_id', 'assignee_id', 'label_ids',
            'version', 'created_at'
        ]
        read_only_fields = ['id', 'version', 'created_at']

    def validate_reporter_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Reporter does not exist.")
        return value

    def validate_assignee_id(self, value):
        if value and not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Assignee does not exist.")
        return value

    def create(self, validated_data):
        label_ids = validated_data.pop('label_ids', [])
        reporter_id = validated_data.pop('reporter_id')
        assignee_id = validated_data.pop('assignee_id', None)

        issue = Issue.objects.create(
            reporter_id=reporter_id,
            assignee_id=assignee_id,
            **validated_data
        )

        if label_ids:
            labels = Label.objects.filter(id__in=label_ids)
            issue.labels.set(labels)

        # Record history
        IssueHistory.objects.create(
            issue=issue,
            change_type=IssueHistory.ChangeType.CREATED,
            changed_by_id=reporter_id,
            new_value=f"Created issue: {issue.title}"
        )

        return issue


class IssueUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating issues with version check."""
    version = serializers.IntegerField(required=True)
    assignee_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = Issue
        fields = ['title', 'description', 'status', 'version', 'assignee_id']

    def validate_assignee_id(self, value):
        if value and not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Assignee does not exist.")
        return value

    def validate(self, attrs):
        instance = self.instance
        if instance and attrs.get('version') != instance.version:
            raise serializers.ValidationError({
                'version': f'Version conflict. Current version is {instance.version}.'
            })
        return attrs


class BulkStatusUpdateSerializer(serializers.Serializer):
    """Serializer for bulk status updates."""
    issue_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    status = serializers.ChoiceField(choices=Issue.Status.choices)


class LabelAssignmentSerializer(serializers.Serializer):
    """Serializer for replacing labels on an issue."""
    label_ids = serializers.ListField(
        child=serializers.IntegerField()
    )


class IssueHistorySerializer(serializers.ModelSerializer):
    """Serializer for issue history (timeline)."""
    changed_by = UserSerializer(read_only=True)

    class Meta:
        model = IssueHistory
        fields = ['id', 'change_type', 'changed_by', 'old_value', 'new_value', 'timestamp']


class CSVImportResultSerializer(serializers.Serializer):
    """Serializer for CSV import response."""
    total_rows = serializers.IntegerField()
    successful = serializers.IntegerField()
    failed = serializers.IntegerField()
    errors = serializers.ListField(
        child=serializers.DictField()
    )


class TopAssigneeSerializer(serializers.Serializer):
    """Serializer for top assignees report."""
    assignee_id = serializers.IntegerField()
    username = serializers.CharField()
    issue_count = serializers.IntegerField()


class LatencyReportSerializer(serializers.Serializer):
    """Serializer for average resolution time report."""
    status = serializers.CharField()
    avg_resolution_hours = serializers.FloatField()
    issue_count = serializers.IntegerField()
