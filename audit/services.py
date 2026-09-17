from .models import AuditLog


def create_audit_log(
    *,
    user_id,
    action,
    entity_type,
    entity_id,
    old_data=None,
    new_data=None,
):
    return AuditLog.objects.create(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_data=old_data,
        new_data=new_data,
    )