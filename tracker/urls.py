from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import IssueViewSet, LabelViewSet, CommentViewSet
from .reports import TopAssigneesView, LatencyReportView


# Create router for viewsets
router = DefaultRouter()
router.register(r'issues', IssueViewSet, basename='issue')
router.register(r'labels', LabelViewSet, basename='label')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),

    # Report endpoints
    path('reports/top-assignees/', TopAssigneesView.as_view(), name='top-assignees'),
    path('reports/latency/', LatencyReportView.as_view(), name='latency-report'),
]
