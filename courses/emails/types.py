from dataclasses import dataclass


@dataclass(frozen=True)
class EmailAttachment:
    filename: str
    content: bytes
    mimetype: str


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    recipient: str
    text_body: str
    html_body: str
    attachments: tuple[EmailAttachment, ...] = ()
    from_email: str | None = None
    reply_to: tuple[str, ...] = ()
