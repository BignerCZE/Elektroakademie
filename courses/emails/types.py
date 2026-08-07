from dataclasses import dataclass


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    recipient: str
    text_body: str
    html_body: str