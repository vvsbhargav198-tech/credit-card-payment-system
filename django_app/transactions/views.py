from drf_spectacular.utils import extend_schema
from rest_framework import generics

from .filters import TransactionFilterSerializer, apply_filters
from .models import Transaction
from .serializers import TransactionSerializer


@extend_schema(parameters=[TransactionFilterSerializer])
class TransactionListView(generics.ListAPIView):
    

    serializer_class = TransactionSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Transaction.objects.none()
        queryset = Transaction.objects.filter(user=self.request.user)
        return apply_filters(queryset, self.request.query_params)


class TransactionDetailView(generics.RetrieveAPIView):
    

    serializer_class = TransactionSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Transaction.objects.none()
        return Transaction.objects.filter(user=self.request.user)
