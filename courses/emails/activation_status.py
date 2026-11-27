from courses.models import EmailLog

from .transport import smtp_enabled_for


def activation_email_status(order, participant_emails):
    recipients = set(participant_emails)
    logs = order.email_logs.filter(
        email_type=EmailLog.TYPE_PARTICIPANT_ACTIVATION,
        recipient__in=recipients,
        status__in=(EmailLog.STATUS_SENT, EmailLog.STATUS_PREVIEW),
    ).values_list("recipient", "status")

    sent = set()
    previews = set()
    for recipient, status in logs:
        if status == EmailLog.STATUS_SENT:
            sent.add(recipient)
        elif not smtp_enabled_for(recipient):
            previews.add(recipient)

    return {
        "sent": len(sent),
        "preview": len(previews - sent),
        "pending": len(recipients - sent - previews),
    }
