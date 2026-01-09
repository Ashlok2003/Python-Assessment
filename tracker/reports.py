from datetime import timedelta

from django.contrib.auth.models import User
from django.db.models import Avg, Count, F, ExpressionWrapper, DurationField
from django.db.models.functions import Extract
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import views
from rest_framework.response import Response

from .models import Issue
from .serializers import TopAssigneeSerializer, LatencyReportSerializer


class TopAssigneesView(views.APIView):
    """
    GET /reports/top-assignees

    Returns top N assignees by number of assigned issues.
    Query params:
    - limit: Number of top assignees to return (default: 10)
    """

    @extend_schema(
        responses={200: TopAssigneeSerializer(many=True)},
        description="Get top assignees by issue count"
    )
    def get(self, request):
        limit = int(request.query_params.get('limit', 10))

        top_assignees = (
            User.objects
            .filter(assigned_issues__isnull=False)
            .annotate(issue_count=Count('assigned_issues'))
            .order_by('-issue_count')
            .values('id', 'username', 'issue_count')[:limit]
        )

        result = [
            {
                'assignee_id': a['id'],
                'username': a['username'],
                'issue_count': a['issue_count']
            }
            for a in top_assignees
        ]

        serializer = TopAssigneeSerializer(result, many=True)
        return Response(serializer.data)


class LatencyReportView(views.APIView):
    """
    GET /reports/latency

    Returns average resolution time for resolved issues.
    Groups by status and shows average hours to resolution.
    """

    @extend_schema(
        responses={200: LatencyReportSerializer(many=True)},
        description="Get average resolution time report"
    )
    def get(self, request):
        # Calculate resolution time for resolved issues
        resolved_issues = (
            Issue.objects
            .filter(resolved_at__isnull=False)
            .annotate(
                resolution_time=ExpressionWrapper(
                    F('resolved_at') - F('created_at'),
                    output_field=DurationField()
                )
            )
        )

        overall_stats = []

        # Get average resolution time for all resolved issues
        avg_duration = resolved_issues.aggregate(
            avg_resolution=Avg(F('resolved_at') - F('created_at'))
        )['avg_resolution']

        if avg_duration:
            avg_hours = avg_duration.total_seconds() / 3600
        else:
            avg_hours = 0

        overall_stats.append({
            'status': 'resolved',
            'avg_resolution_hours': round(avg_hours, 2),
            'issue_count': resolved_issues.count()
        })

        # Stats for currently open issues (time since creation)
        open_issues = Issue.objects.filter(status=Issue.Status.OPEN)
        in_progress_issues = Issue.objects.filter(status=Issue.Status.IN_PROGRESS)

        now = timezone.now()

        # Open issues average age
        if open_issues.exists():
            open_avg = open_issues.aggregate(
                avg_age=Avg(now - F('created_at'))
            )['avg_age']
            if open_avg:
                overall_stats.append({
                    'status': 'open',
                    'avg_resolution_hours': round(open_avg.total_seconds() / 3600, 2),
                    'issue_count': open_issues.count()
                })

        # In progress issues average age
        if in_progress_issues.exists():
            in_progress_avg = in_progress_issues.aggregate(
                avg_age=Avg(now - F('created_at'))
            )['avg_age']
            if in_progress_avg:
                overall_stats.append({
                    'status': 'in_progress',
                    'avg_resolution_hours': round(in_progress_avg.total_seconds() / 3600, 2),
                    'issue_count': in_progress_issues.count()
                })

        serializer = LatencyReportSerializer(overall_stats, many=True)
        return Response(serializer.data)
