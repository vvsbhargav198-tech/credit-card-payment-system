from rest_framework import generics

from .models import Card
from .serializers import CardSerializer


class _OwnCardsMixin:
    serializer_class = CardSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Card.objects.none()
        # Always scoped to the caller: other users' cards are simply "404 Not Found".
        return Card.objects.filter(user=self.request.user)


class CardListCreateView(_OwnCardsMixin, generics.ListCreateAPIView):
    

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CardDetailView(_OwnCardsMixin, generics.RetrieveDestroyAPIView):
    """GET: view one saved card. DELETE: remove it (past transactions are kept)."""
