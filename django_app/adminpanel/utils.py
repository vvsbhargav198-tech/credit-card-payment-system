from .models import AdminLog


def log_admin_action(admin_user, action, target_type="", target_id="", details="", request=None):
    
    ip = request.META.get("REMOTE_ADDR") if request is not None else None
    return AdminLog.objects.create(
        admin=admin_user if getattr(admin_user, "pk", None) else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        details=details,
        ip_address=ip or None,
    )
