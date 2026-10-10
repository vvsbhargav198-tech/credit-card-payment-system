from django.urls import path

from .views import CardDetailView, CardListCreateView

urlpatterns = [
    path("", CardListCreateView.as_view(), name="card-list"),
    path("<int:pk>/", CardDetailView.as_view(), name="card-detail"),
]
