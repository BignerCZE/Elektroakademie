from django.template.loader import render_to_string

from .types import RenderedEmail


def render_email(
    *,
    subject,
    recipient,
    html_template,
    text_template,
    context=None,
    attachments=(),
):
    context = context or {}

    html_body = render_to_string(
        html_template,
        context,
    ).strip()

    text_body = render_to_string(
        text_template,
        context,
    ).strip()

    return RenderedEmail(
        subject=subject,
        recipient=recipient,
        text_body=text_body,
        html_body=html_body,
        attachments=tuple(attachments),
    )