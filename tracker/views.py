import io

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
import pandas as pd
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from .models import Issue, Comment, Label, IssueHistory
from .serializers import (
    IssueListSerializer, IssueDetailSerializer,
    IssueCreateSerializer, IssueUpdateSerializer,
    CommentSerializer, LabelSerializer,
    BulkStatusUpdateSerializer, LabelAssignmentSerializer,
    IssueHistorySerializer,
)


class IssueViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Issue CRUD operations.

    Supports:
    - List with filtering and pagination
    - Create new issues
    - Retrieve with comments and labels
    - Update with optimistic concurrency (version check)
    - Bulk status updates
    - CSV import
    - Label management
    - Timeline (history)
    """
    queryset = Issue.objects.select_related('reporter', 'assignee').prefetch_related('labels', 'comments')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'assignee', 'reporter']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'status']

    def get_serializer_class(self):
        if self.action == 'list':
            return IssueListSerializer
        elif self.action == 'retrieve':
            return IssueDetailSerializer
        elif self.action == 'create':
            return IssueCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return IssueUpdateSerializer
        return IssueDetailSerializer

    def perform_update(self, serializer):
        """Update issue with version increment and history tracking."""
        instance = serializer.instance
        old_status = instance.status
        old_assignee = instance.assignee_id

        # Increment version
        serializer.save(version=F('version') + 1)

        # Refresh to get actual values after F() expression
        instance.refresh_from_db()

        # Track status change
        if 'status' in serializer.validated_data and serializer.validated_data['status'] != old_status:
            IssueHistory.objects.create(
                issue=instance,
                change_type=IssueHistory.ChangeType.STATUS_CHANGED,
                old_value=old_status,
                new_value=serializer.validated_data['status']
            )

        # Track assignee change
        new_assignee = serializer.validated_data.get('assignee_id')
        if new_assignee != old_assignee:
            IssueHistory.objects.create(
                issue=instance,
                change_type=IssueHistory.ChangeType.ASSIGNEE_CHANGED,
                old_value=str(old_assignee) if old_assignee else None,
                new_value=str(new_assignee) if new_assignee else None
            )

    @action(detail=True, methods=['post'])
    def comments(self, request, pk=None):
        """Add a comment to an issue."""
        issue = self.get_object()
        serializer = CommentSerializer(data=request.data)

        if serializer.is_valid():
            comment = Comment.objects.create(
                issue=issue,
                author_id=serializer.validated_data['author_id'],
                body=serializer.validated_data['body']
            )

            # Track in history
            IssueHistory.objects.create(
                issue=issue,
                change_type=IssueHistory.ChangeType.COMMENT_ADDED,
                changed_by_id=serializer.validated_data['author_id'],
                new_value=f"Comment added: {comment.body[:100]}..."
            )

            return Response(
                CommentSerializer(comment).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'])
    def labels(self, request, pk=None):
        """Replace all labels on an issue atomically."""
        issue = self.get_object()
        serializer = LabelAssignmentSerializer(data=request.data)

        if serializer.is_valid():
            old_labels = list(issue.labels.values_list('name', flat=True))

            with transaction.atomic():
                label_ids = serializer.validated_data['label_ids']
                labels = Label.objects.filter(id__in=label_ids)

                if len(labels) != len(label_ids):
                    found_ids = set(labels.values_list('id', flat=True))
                    missing_ids = set(label_ids) - found_ids
                    return Response(
                        {'error': f'Labels not found: {list(missing_ids)}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                issue.labels.set(labels)

                # Track in history
                new_labels = list(labels.values_list('name', flat=True))
                IssueHistory.objects.create(
                    issue=issue,
                    change_type=IssueHistory.ChangeType.LABELS_CHANGED,
                    old_value=', '.join(old_labels),
                    new_value=', '.join(new_labels)
                )

            return Response(
                LabelSerializer(issue.labels.all(), many=True).data,
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        """Get issue history/timeline (bonus feature)."""
        issue = self.get_object()
        history = issue.history.all()
        serializer = IssueHistorySerializer(history, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='bulk-status')
    def bulk_status(self, request):
        """Bulk update status of multiple issues transactionally."""
        serializer = BulkStatusUpdateSerializer(data=request.data)

        if serializer.is_valid():
            issue_ids = serializer.validated_data['issue_ids']
            new_status = serializer.validated_data['status']

            try:
                with transaction.atomic():
                    issues = Issue.objects.select_for_update().filter(id__in=issue_ids)

                    if issues.count() != len(issue_ids):
                        found_ids = set(issues.values_list('id', flat=True))
                        missing_ids = set(issue_ids) - found_ids
                        raise ValueError(f"Issues not found: {list(missing_ids)}")

                    # Validate status transitions
                    for issue in issues:
                        # Example rule: can't reopen closed issues
                        if issue.status == Issue.Status.CLOSED and new_status != Issue.Status.CLOSED:
                            raise ValueError(f"Cannot reopen closed issue #{issue.id}")

                    # Perform the update
                    updated_count = 0
                    for issue in issues:
                        old_status = issue.status
                        if old_status != new_status:
                            issue.status = new_status
                            issue.version = F('version') + 1
                            issue.save()

                            # Track history
                            IssueHistory.objects.create(
                                issue=issue,
                                change_type=IssueHistory.ChangeType.STATUS_CHANGED,
                                old_value=old_status,
                                new_value=new_status
                            )
                            updated_count += 1

                    return Response({
                        'message': f'Successfully updated {updated_count} issues',
                        'updated_count': updated_count
                    })

            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='import', parser_classes=[MultiPartParser])
    def import_csv(self, request):
        """
        Import issues from CSV file.

        Expected columns: title, description, status, reporter_username, assignee_username
        """
        if 'file' not in request.FILES:
            return Response(
                {'error': 'No file provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        csv_file = request.FILES['file']

        try:
            df = pd.read_csv(io.StringIO(csv_file.read().decode('utf-8')))
        except Exception as e:
            return Response(
                {'error': f'Failed to parse CSV: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        required_columns = ['title', 'reporter_username']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return Response(
                {'error': f'Missing required columns: {missing_columns}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = {
            'total_rows': len(df),
            'successful': 0,
            'failed': 0,
            'errors': []
        }

        # Cache users for performance
        usernames = set(df['reporter_username'].dropna().tolist())
        if 'assignee_username' in df.columns:
            usernames.update(df['assignee_username'].dropna().tolist())
        users = {u.username: u for u in User.objects.filter(username__in=usernames)}

        for idx, row in df.iterrows():
            row_num = idx + 2  # Account for header and 0-indexing

            try:
                # Validate reporter
                reporter_username = row.get('reporter_username')
                if pd.isna(reporter_username) or reporter_username not in users:
                    raise ValueError(f"Reporter '{reporter_username}' not found")
                reporter = users[reporter_username]

                # Validate assignee if provided
                assignee = None
                assignee_username = row.get('assignee_username')
                if not pd.isna(assignee_username) and assignee_username:
                    if assignee_username not in users:
                        raise ValueError(f"Assignee '{assignee_username}' not found")
                    assignee = users[assignee_username]

                # Validate status
                status_value = row.get('status', 'open')
                if pd.isna(status_value):
                    status_value = 'open'
                valid_statuses = [s[0] for s in Issue.Status.choices]
                if status_value not in valid_statuses:
                    raise ValueError(f"Invalid status '{status_value}'")

                # Validate title
                title = row.get('title')
                if pd.isna(title) or not str(title).strip():
                    raise ValueError("Title cannot be empty")

                # Create issue
                Issue.objects.create(
                    title=str(title).strip(),
                    description=str(row.get('description', '')).strip() if not pd.isna(row.get('description')) else '',
                    status=status_value,
                    reporter=reporter,
                    assignee=assignee
                )
                results['successful'] += 1

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'row': row_num,
                    'error': str(e)
                })

        return Response(results, status=status.HTTP_201_CREATED if results['successful'] > 0 else status.HTTP_400_BAD_REQUEST)


class LabelViewSet(viewsets.ModelViewSet):
    """ViewSet for Label CRUD operations."""
    queryset = Label.objects.all()
    serializer_class = LabelSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class CommentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for reading comments (creation via issues endpoint)."""
    queryset = Comment.objects.select_related('author', 'issue')
    serializer_class = CommentSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['issue', 'author']
