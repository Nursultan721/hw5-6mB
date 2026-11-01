from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Post
from .serializers import PostSerializer


class PostListView(APIView):
    def get(self, request):
        posts = cache.get("posts_list")
        if posts is None:
            posts = PostSerializer(Post.objects.all(), many=True).data
            cache.set("posts_list", posts, 60)
        return Response(posts)

    def post(self, request):
        serializer = PostSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        post = serializer.save()
        cache.delete("posts_list")
        return Response(
            PostSerializer(post).data,
            status=status.HTTP_201_CREATED,
        )
