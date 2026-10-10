import csv

from django.http import HttpResponse

CSV_COLUMNS = [
    "reference", "username", "email", "card_last4", "amount", "currency",
    "status", "failure_reason", "description", "created_at",
]


def _safe(value) -> str:
    
    text = "" if value is None else str(value)
    return "'" + text if text and text[0] in ("=", "+", "-", "@", "\t", "\r") else text


def build_csv_response(queryset, filename: str) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(CSV_COLUMNS)
    for txn in queryset.select_related("user").iterator(chunk_size=2000):
        writer.writerow(
            [_safe(v) for v in (
                txn.reference, txn.user.username, txn.user.email, txn.card_last4, txn.amount,
                txn.currency, txn.status, txn.failure_reason, txn.description, txn.created_at.isoformat(),
            )]
        )
    return response
