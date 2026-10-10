from datetime import date

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm as DjangoUserChangeForm
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.urls import path

from accounts.models import User
from cards.models import Card
from transactions.exports import build_csv_response
from transactions.models import Transaction

from .models import AdminLog
from .services import daily_summary
from .utils import log_admin_action


class ReadOnlyAdmin(admin.ModelAdmin):
    

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class UserCreationForm(DjangoUserCreationForm):
    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class UserChangeForm(DjangoUserChangeForm):
    class Meta(DjangoUserChangeForm.Meta):
        model = User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    

    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ("id", "username", "email", "is_active", "is_staff", "date_joined", "last_login")
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("username", "email")
    ordering = ("-date_joined",)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + ((None, {"fields": ("email",)}),)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        changed = ", ".join(f for f in form.changed_data if "password" not in f) or "-"
        log_admin_action(
            request.user, "USER_UPDATED" if change else "USER_CREATED", "User", obj.pk,
            f"username={obj.username}; changed fields: {changed}", request,
        )

    def delete_model(self, request, obj):
        pk, username = obj.pk, obj.username
        super().delete_model(request, obj)
        log_admin_action(request.user, "USER_DELETED", "User", pk, f"username={username}", request)

    def delete_queryset(self, request, queryset):
        ids = list(queryset.values_list("pk", flat=True))
        super().delete_queryset(request, queryset)
        log_admin_action(request.user, "USER_DELETED", "User", ",".join(map(str, ids)), "bulk delete", request)


@admin.register(Card)
class CardAdmin(ReadOnlyAdmin):
    list_display = ("id", "user", "brand", "card_type", "masked_number", "expiry_month", "expiry_year", "created_at")
    list_filter = ("brand", "card_type")
    search_fields = ("user__username", "user__email", "last4", "cardholder_name")
    list_select_related = ("user",)


@admin.register(Transaction)
class TransactionAdmin(ReadOnlyAdmin):
    list_display = ("id", "reference", "user", "card_last4", "amount", "currency", "status", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("reference", "user__username", "user__email", "card_last4")
    date_hierarchy = "created_at"
    list_select_related = ("user",)
    actions = ["export_selected_csv"]
    change_list_template = "admin/transactions/transaction/change_list.html"

    @admin.action(description="Export selected transactions to CSV")
    def export_selected_csv(self, request, queryset):
        log_admin_action(request.user, "EXPORT_CSV", "Transaction", "", f"{queryset.count()} rows (admin action)", request)
        return build_csv_response(queryset, "transactions_selected.csv")

    def get_urls(self):
        custom = [
            path(
                "daily-summary/",
                self.admin_site.admin_view(self.daily_summary_view),
                name="daily-payment-summary",
            )
        ]
        return custom + super().get_urls()

    def daily_summary_view(self, request):
        if not self.has_view_permission(request):
            raise PermissionDenied

        def parse(name):
            try:
                return date.fromisoformat(request.GET.get(name, ""))
            except ValueError:
                return None

        date_from, date_to = parse("date_from"), parse("date_to")
        rows = daily_summary(date_from, date_to)
        log_admin_action(request.user, "VIEW_DAILY_SUMMARY", "Transaction", "", "admin panel", request)
        context = {
            **self.admin_site.each_context(request),
            "title": "Daily Payment Summary",
            "opts": self.model._meta,
            "rows": rows,
            "date_from": date_from.isoformat() if date_from else "",
            "date_to": date_to.isoformat() if date_to else "",
        }
        return TemplateResponse(request, "admin/adminpanel/daily_summary.html", context)


@admin.register(AdminLog)
class AdminLogAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "admin", "action", "target_type", "target_id", "ip_address")
    list_filter = ("action",)
    search_fields = ("admin__username", "action", "details")
    list_select_related = ("admin",)
