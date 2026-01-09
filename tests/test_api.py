import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from tracker.models import Issue, Comment, Label


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_users(db):
    """Create test users."""
    user1 = User.objects.create_user(username='testuser1', email='test1@example.com', password='testpass')
    user2 = User.objects.create_user(username='testuser2', email='test2@example.com', password='testpass')
    return user1, user2


@pytest.fixture
def create_labels(db):
    """Create test labels."""
    label1 = Label.objects.create(name='bug')
    label2 = Label.objects.create(name='feature')
    return label1, label2


@pytest.fixture
def create_issue(db, create_users, create_labels):
    """Create a test issue."""
    user1, user2 = create_users
    label1, label2 = create_labels
    issue = Issue.objects.create(
        title='Test Issue',
        description='Test Description',
        reporter=user1,
        assignee=user2,
        status='open'
    )
    issue.labels.add(label1)
    return issue


class TestIssueEndpoints:
    """Test Issue CRUD operations."""

    def test_list_issues(self, api_client, create_issue):
        """Test listing issues."""
        url = reverse('issue-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['title'] == 'Test Issue'

    def test_create_issue(self, api_client, create_users):
        """Test creating a new issue."""
        user1, _ = create_users
        url = reverse('issue-list')
        data = {
            'title': 'New Issue',
            'description': 'New Description',
            'reporter_id': user1.id,
            'status': 'open'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'New Issue'
        assert response.data['version'] == 1

    def test_retrieve_issue(self, api_client, create_issue):
        """Test retrieving a single issue."""
        url = reverse('issue-detail', kwargs={'pk': create_issue.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['title'] == 'Test Issue'
        assert 'comments' in response.data
        assert 'labels' in response.data

    def test_update_issue_with_version(self, api_client, create_issue):
        """Test updating an issue with version check."""
        url = reverse('issue-detail', kwargs={'pk': create_issue.id})
        data = {
            'title': 'Updated Issue',
            'version': 1  # Current version
        }
        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK

    def test_update_issue_version_conflict(self, api_client, create_issue):
        """Test version conflict detection."""
        url = reverse('issue-detail', kwargs={'pk': create_issue.id})
        data = {
            'title': 'Updated Issue',
            'version': 99  # Wrong version
        }
        response = api_client.patch(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'version' in response.data


class TestCommentEndpoints:
    """Test Comment operations."""

    def test_add_comment(self, api_client, create_issue, create_users):
        """Test adding a comment to an issue."""
        user1, _ = create_users
        url = reverse('issue-comments', kwargs={'pk': create_issue.id})
        data = {
            'body': 'This is a test comment',
            'author_id': user1.id
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['body'] == 'This is a test comment'

    def test_add_empty_comment(self, api_client, create_issue, create_users):
        """Test that empty comments are rejected."""
        user1, _ = create_users
        url = reverse('issue-comments', kwargs={'pk': create_issue.id})
        data = {
            'body': '   ',  # Empty/whitespace
            'author_id': user1.id
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLabelEndpoints:
    """Test Label operations."""

    def test_list_labels(self, api_client, create_labels):
        """Test listing labels."""
        url = reverse('label-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 2

    def test_replace_issue_labels(self, api_client, create_issue, create_labels):
        """Test replacing labels on an issue."""
        label1, label2 = create_labels
        url = reverse('issue-labels', kwargs={'pk': create_issue.id})
        data = {
            'label_ids': [label1.id, label2.id]
        }
        response = api_client.put(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2


class TestBulkOperations:
    """Test bulk operations."""

    def test_bulk_status_update(self, api_client, create_issue):
        """Test bulk status update."""
        url = reverse('issue-bulk-status')
        data = {
            'issue_ids': [create_issue.id],
            'status': 'in_progress'
        }
        response = api_client.post(url, data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['updated_count'] == 1


class TestReports:
    """Test report endpoints."""

    def test_top_assignees(self, api_client, create_issue):
        """Test top assignees report."""
        url = reverse('top-assignees')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_latency_report(self, api_client, create_issue):
        """Test latency report."""
        url = reverse('latency-report')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK


class TestTimeline:
    """Test timeline (bonus feature)."""

    def test_issue_timeline(self, api_client, create_issue):
        """Test getting issue timeline."""
        url = reverse('issue-timeline', kwargs={'pk': create_issue.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Should have at least the creation event
        assert isinstance(response.data, list)
