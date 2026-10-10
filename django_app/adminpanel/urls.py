from django.urls import path

from . import views

urlpatterns = [
    path("users/", views.AdminUserListView.as_view(), name="admin-user-list"),
    path("users/<int:pk>/", views.AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("cards/", views.AdminCardListView.as_view(), name="admin-card-list"),
    path("transactions/", views.AdminTransactionListView.as_view(), name="admin-transaction-list"),
    path("transactions/export/", views.AdminTransactionExportView.as_view(), name="admin-transaction-export"),
    path("summary/daily/", views.AdminDailySummaryView.as_view(), name="admin-daily-summary"),
    path("logs/", views.AdminLogListView.as_view(), name="admin-log-list"),
]
