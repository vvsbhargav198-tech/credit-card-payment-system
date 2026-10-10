from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from cards.models import Card
from transactions.exports import build_csv_response
from transactions.filters import TransactionFilterSerializer, apply_filters
from transactions.models import Transaction
from transactions.serializers import AdminTransactionSerializer

from .models import AdminLog
from .serializers import (
    AdminCardSerializer,
    AdminLogSerializer,
    AdminUserSerializer,
    DailySummaryQuerySerializer,
    DailySummaryRowSerializer,
)
from .services import daily_summary
from .utils import log_admin_action


class AdminUserListView(generics.ListAPIView):
    

    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer
    queryset = User.objects.order_by("id")


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    

    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer
    queryset = User.objects.order_by("id")
    http_method_names = ["get", "patch", "head", "options"]

    def perform_update(self, serializer):
        if serializer.instance.pk == self.request.user.pk and serializer.validated_data.get("is_active") is False:
            raise ValidationError({"is_active": "You cannot deactivate your own account."})
        user = serializer.save()
        log_admin_action(
            self.request.user, "USER_ACTIVATED" if user.is_active else "USER_DEACTIVATED",
            "User", user.pk, f"username={user.username}", self.request,
        )


class AdminCardListView(generics.ListAPIView):
    

    permission_classes = [IsAdminUser]
    serializer_class = AdminCardSerializer
    queryset = Card.objects.select_related("user")


@extend_schema(parameters=[TransactionFilterSerializer])
class AdminTransactionListView(generics.ListAPIView):
    

    permission_classes = [IsAdminUser]
    serializer_class = AdminTransactionSerializer

    def get_queryset(self):
        return apply_filters(Transaction.objects.select_related("user"), self.request.query_params)


class AdminLogListView(generics.ListAPIView):
    

    permission_classes = [IsAdminUser]
    serializer_class = AdminLogSerializer
    queryset = AdminLog.objects.select_related("admin")


class AdminDailySummaryView(APIView):
    

    permission_classes = [IsAdminUser]

    @extend_schema(parameters=[DailySummaryQuerySerializer], responses=DailySummaryRowSerializer(many=True))
    def get(self, request):
        query = DailySummaryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        rows = daily_summary(query.validated_data.get("date_from"), query.validated_data.get("date_to"))
        log_admin_action(request.user, "VIEW_DAILY_SUMMARY", "Transaction", "", str(dict(query.validated_data)), request)
        return Response(DailySummaryRowSerializer(rows, many=True).data)


@extend_schema(parameters=[TransactionFilterSerializer], responses={(200, "text/csv"): OpenApiTypes.STR})
class AdminTransactionExportView(APIView):
    

    permission_classes = [IsAdminUser]

    def get(self, request):
        queryset = apply_filters(Transaction.objects.all(), request.query_params)
        log_admin_action(request.user, "EXPORT_CSV", "Transaction", "", f"filters={dict(request.query_params)}", request)
        return build_csv_response(queryset, "transactions.csv")
