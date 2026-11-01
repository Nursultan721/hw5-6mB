from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Post


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "posts-test-cache",
        }
    }
)
class PostCacheTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("post_list")
        cache.clear()

    def test_second_get_uses_cache_without_querying_posts(self):
        post = Post.objects.create(title="First post", content="Body")

        with CaptureQueriesContext(connection) as first_request:
            first_response = self.client.get(self.url)
        with CaptureQueriesContext(connection) as second_request:
            second_response = self.client.get(self.url)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(first_response.data, second_response.data)
        self.assertTrue(
            any("testapp_post" in query["sql"] for query in first_request.captured_queries)
        )
        self.assertFalse(
            any("testapp_post" in query["sql"] for query in second_request.captured_queries)
        )
        self.assertEqual(first_response.data[0]["id"], post.pk)

    def test_creating_post_invalidates_cached_list(self):
        Post.objects.create(title="Existing post", content="Old body")
        self.client.get(self.url)

        response = self.client.post(
            self.url,
            {"title": "New post", "content": "New body"},
            format="json",
        )
        refreshed_response = self.client.get(self.url)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(refreshed_response.data), 2)
        self.assertEqual(refreshed_response.data[0]["title"], "New post")

    def test_post_requires_title_and_content(self):
        response = self.client.post(self.url, {"title": "Incomplete"}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Post.objects.count(), 0)
