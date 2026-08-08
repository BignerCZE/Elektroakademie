import os

from datetime import timedelta
from io import BytesIO

from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.template.loader import get_template
from django.utils import timezone
from django.conf import settings
from django.contrib.staticfiles import finders


from xhtml2pdf import pisa

from xml.sax.saxutils import escape

from django.contrib.staticfiles import finders

from django.template.loader import render_to_string
from playwright.sync_api import sync_playwright

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import (
    Certificate,
    Order,
    OrderParticipant,
    QuizAttempt,
    RegistrationNumberSequence,
)


@transaction.atomic
def generate_registration_number(course_type):
    """
    Vytvoří evidenční číslo například:

    EA-04-202607-00001

    Číselná řada je samostatná pro každý typ kurzu a měsíc.
    """

    now = timezone.localdate()
    course_code = str(course_type).zfill(2)

    sequence, _ = RegistrationNumberSequence.objects.get_or_create(
        course_type=str(course_type),
        year=now.year,
        month=now.month,
        defaults={"last_number": 0},
    )

    sequence = (
        RegistrationNumberSequence.objects
        .select_for_update()
        .get(pk=sequence.pk)
    )

    sequence.last_number += 1
    sequence.save(update_fields=["last_number"])

    return (
        f"EA-{course_code}-"
        f"{now.year}{now.month:02d}-"
        f"{sequence.last_number:05d}"
    )


@transaction.atomic
def mark_order_as_paid(order_id):
    """
    Bezpečně označí objednávku jako zaplacenou a všem jejím
    účastníkům, kteří ještě nemají evidenční číslo, jej přidělí.

    Funkce je idempotentní:
    opakované zavolání nezmění datum zaplacení a nevygeneruje
    účastníkům nová evidenční čísla.
    """

    order = Order.objects.select_for_update().get(pk=order_id)
    status_changed = False

    if order.status != "paid":
        order.status = "paid"
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at"])
        status_changed = True

    participants = list(
        order.participants.select_for_update().order_by("id")
    )

    for participant in participants:
        if participant.registration_number:
            continue

        participant.registration_number = generate_registration_number(
            order.course_type
        )
        participant.save(update_fields=["registration_number"])

    return order, participants, status_changed


@transaction.atomic
def generate_certificate(quiz_attempt):
    """
    Vytvoří nebo vrátí osvědčení pro úspěšný odeslaný pokus.

    Platnost osvědčení končí jeden den před třetím výročím
    data vystavení.
    """

    quiz_attempt = (
        QuizAttempt.objects
        .select_for_update()
        .select_related("user", "course")
        .get(pk=quiz_attempt.pk)
    )

    if quiz_attempt.status != QuizAttempt.STATUS_SUBMITTED:
        raise ValueError(
            "Osvědčení lze vytvořit pouze pro odeslaný test."
        )

    if not quiz_attempt.passed:
        raise ValueError(
            "Osvědčení lze vytvořit pouze pro úspěšný test."
        )

    participant = (
        OrderParticipant.objects
        .select_for_update()
        .select_related("order", "profile")
        .filter(
            user=quiz_attempt.user,
            registration_number__isnull=False,
        )
        .exclude(registration_number="")
        .order_by("-activation_completed_at", "-id")
        .first()
    )

    if participant is None:
        raise ValueError(
            "K uživateli nebyl nalezen aktivovaný účastník "
            "s evidenčním číslem."
        )

    issued_at = quiz_attempt.submitted_at or timezone.now()
    valid_until = (
        issued_at.date()
        + relativedelta(years=3)
        - timedelta(days=1)
    )

    certificate, created = Certificate.objects.get_or_create(
        participant=participant,
        defaults={
            "quiz_attempt": quiz_attempt,
            "certificate_number": participant.registration_number,
            "issued_at": issued_at,
            "valid_until": valid_until,
        },
    )

    return certificate, created

def load_static_text(path):
    absolute_path = finders.find(path)

    if not absolute_path:
        raise ValueError(
            f"Statický soubor nebyl nalezen: {path}"
        )

    with open(
        absolute_path,
        "r",
        encoding="utf-8",
    ) as file:
        return file.read()





def generate_certificate_pdf(certificate):
    """
    Vygeneruje certifikát pomocí stejného HTML a CSS,
    které používá náhled certifikátu v dashboardu.
    """

    certificate = (
        Certificate.objects
        .select_related(
            "participant",
            "participant__user",
            "participant__profile",
            "participant__order",
            "quiz_attempt",
            "quiz_attempt__course",
        )
        .get(pk=certificate.pk)
    )

    participant = certificate.participant

    certificate_css = load_static_text(
        "courses/css/certificate.css"
    )

    html = render_to_string(
        "courses/certificate_pdf_browser.html",
        {
            "course": certificate.quiz_attempt.course,
            "certificate": certificate,
            "participant": participant,
            "participant_profile": getattr(
                participant,
                "profile",
                None,
            ),
            "completion_date": certificate.issued_at,
        },
    )

    return generate_html_pdf(
        html,
        css=certificate_css,
    )

def register_quiz_pdf_fonts():
    regular_path = finders.find(
        "courses/fonts/NotoSans-Regular.ttf"
    )
    bold_path = finders.find(
        "courses/fonts/NotoSans-Bold.ttf"
    )

    if not regular_path or not bold_path:
        raise ValueError(
            "Fonty Noto Sans pro generování PDF nebyly nalezeny."
        )

    registered_fonts = pdfmetrics.getRegisteredFontNames()

    if "NotoSans" not in registered_fonts:
        pdfmetrics.registerFont(
            TTFont(
                "NotoSans",
                regular_path,
            )
        )

    if "NotoSans-Bold" not in registered_fonts:
        pdfmetrics.registerFont(
            TTFont(
                "NotoSans-Bold",
                bold_path,
            )
        )

    pdfmetrics.registerFontFamily(
        "NotoSans",
        normal="NotoSans",
        bold="NotoSans-Bold",
        italic="NotoSans",
        boldItalic="NotoSans-Bold",
    )


def generate_quiz_result_pdf(quiz_attempt):
    """
    Vygeneruje PDF s kompletním výsledkem úspěšného testu
    a vrátí jeho obsah jako bytes.

    PDF obsahuje souhrnný výsledek a všechny otázky,
    včetně odpovědi účastníka a správné odpovědi.
    """

    register_quiz_pdf_fonts()

    quiz_attempt = (
        QuizAttempt.objects
        .select_related(
            "user",
            "course",
        )
        .get(pk=quiz_attempt.pk)
    )

    if quiz_attempt.status != QuizAttempt.STATUS_SUBMITTED:
        raise ValueError(
            "PDF výsledku lze vytvořit pouze pro odeslaný test."
        )

    if not quiz_attempt.passed:
        raise ValueError(
            "PDF výsledku lze vytvořit pouze pro úspěšný test."
        )

    participant = (
        OrderParticipant.objects
        .select_related(
            "order",
            "profile",
        )
        .filter(
            user=quiz_attempt.user,
            registration_number__isnull=False,
        )
        .exclude(
            registration_number=""
        )
        .order_by(
            "-activation_completed_at",
            "-id",
        )
        .first()
    )

    if participant is None:
        raise ValueError(
            "K uživateli nebyl nalezen aktivovaný účastník "
            "s evidenčním číslem."
        )

    attempt_questions = (
        quiz_attempt.attempt_questions
        .select_related(
            "question",
            "selected_choice",
            "question__category",
        )
        .prefetch_related(
            "question__choice_set",
        )
        .order_by("order")
    )

    result = BytesIO()

    document = SimpleDocTemplate(
        result,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Výsledek testu",
        author="Elektroakademie",
    )

    styles = {
        "brand": ParagraphStyle(
            "Brand",
            fontName="NotoSans-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#175985"),
            spaceAfter=2 * mm,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontName="NotoSans",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#687781"),
            spaceAfter=8 * mm,
        ),
        "title": ParagraphStyle(
            "Title",
            fontName="NotoSans-Bold",
            fontSize=19,
            leading=24,
            textColor=colors.HexColor("#17232d"),
            spaceAfter=6 * mm,
        ),
        "section": ParagraphStyle(
            "Section",
            fontName="NotoSans-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#17232d"),
            spaceBefore=5 * mm,
            spaceAfter=4 * mm,
        ),
        "question_number": ParagraphStyle(
            "QuestionNumber",
            fontName="NotoSans-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#175985"),
            spaceAfter=1.5 * mm,
        ),
        "question": ParagraphStyle(
            "Question",
            fontName="NotoSans-Bold",
            fontSize=10.5,
            leading=15,
            textColor=colors.HexColor("#202b33"),
            spaceAfter=3 * mm,
        ),
        "normal": ParagraphStyle(
            "Normal",
            fontName="NotoSans",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#202b33"),
        ),
        "label": ParagraphStyle(
            "Label",
            fontName="NotoSans-Bold",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#64727d"),
        ),
        "correct": ParagraphStyle(
            "Correct",
            fontName="NotoSans",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#287044"),
        ),
        "wrong": ParagraphStyle(
            "Wrong",
            fontName="NotoSans",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#a13d35"),
        ),
        "correct_bold": ParagraphStyle(
            "CorrectBold",
            fontName="NotoSans-Bold",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#287044"),
        ),
        "wrong_bold": ParagraphStyle(
            "WrongBold",
            fontName="NotoSans-Bold",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#a13d35"),
        ),
        "footer": ParagraphStyle(
            "Footer",
            fontName="NotoSans",
            fontSize=7.5,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#7a8792"),
        ),
    }

    story = []

    story.append(
        Paragraph(
            "Elektroakademie",
            styles["brand"],
        )
    )

    story.append(
        Paragraph(
            "Odborné vzdělávání v elektrotechnice",
            styles["subtitle"],
        )
    )

    story.append(
        Paragraph(
            "Výsledek testu",
            styles["title"],
        )
    )

    submitted_at = (
        timezone.localtime(quiz_attempt.submitted_at)
        if quiz_attempt.submitted_at
        else None
    )

    submitted_at_text = (
        submitted_at.strftime("%d. %m. %Y %H:%M")
        if submitted_at
        else "—"
    )

    summary_data = [
        [
            Paragraph("Účastník", styles["label"]),
            Paragraph(
                escape(
                    f"{participant.first_name} "
                    f"{participant.last_name}"
                ),
                styles["normal"],
            ),
        ],
        [
            Paragraph("Evidenční číslo", styles["label"]),
            Paragraph(
                escape(participant.registration_number),
                styles["normal"],
            ),
        ],
        [
            Paragraph("Kurz", styles["label"]),
            Paragraph(
                escape(quiz_attempt.course.title),
                styles["normal"],
            ),
        ],
        [
            Paragraph("Datum testu", styles["label"]),
            Paragraph(
                submitted_at_text,
                styles["normal"],
            ),
        ],
        [
            Paragraph("Pokus", styles["label"]),
            Paragraph(
                str(quiz_attempt.attempt_number),
                styles["normal"],
            ),
        ],
        [
            Paragraph("Správné odpovědi", styles["label"]),
            Paragraph(
                (
                    f"{quiz_attempt.correct_answers} / "
                    f"{quiz_attempt.total_questions}"
                ),
                styles["normal"],
            ),
        ],
        [
            Paragraph("Úspěšnost", styles["label"]),
            Paragraph(
                f"{quiz_attempt.score_percent:.0f} %",
                styles["normal"],
            ),
        ],
        [
            Paragraph("Výsledek", styles["label"]),
            Paragraph(
                "SPLNĚNO",
                styles["correct_bold"],
            ),
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[
            52 * mm,
            120 * mm,
        ],
    )

    summary_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                colors.HexColor("#f3f7fa"),
            ),
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.5,
                colors.HexColor("#dce5eb"),
            ),
            (
                "INNERGRID",
                (0, 0),
                (-1, -1),
                0.25,
                colors.HexColor("#e6ecef"),
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP",
            ),
            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                7,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                7,
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                5,
            ),
        ])
    )

    story.append(summary_table)

    story.append(
        Paragraph(
            "Přehled otázek a odpovědí",
            styles["section"],
        )
    )

    for attempt_question in attempt_questions:
        correct_choices = list(
            attempt_question.question.choice_set
            .filter(is_correct=True)
        )

        correct_choice = (
            correct_choices[0]
            if correct_choices
            else None
        )

        selected_choice = (
            attempt_question.selected_choice
        )

        is_correct = bool(
            selected_choice
            and selected_choice.is_correct
        )

        selected_text = (
            selected_choice.text
            if selected_choice
            else "Bez odpovědi"
        )

        correct_text = (
            correct_choice.text
            if correct_choice
            else "—"
        )

        selected_style = (
            styles["correct"]
            if is_correct
            else styles["wrong"]
        )

        result_style = (
            styles["correct_bold"]
            if is_correct
            else styles["wrong_bold"]
        )

        block = [
            Paragraph(
                f"Otázka {attempt_question.order}",
                styles["question_number"],
            ),
            Paragraph(
                escape(
                    attempt_question.question.text
                ),
                styles["question"],
            ),
            Table(
                [
                    [
                        Paragraph(
                            "Vaše odpověď:",
                            styles["label"],
                        ),
                        Paragraph(
                            escape(selected_text),
                            selected_style,
                        ),
                    ],
                    [
                        Paragraph(
                            "Správná odpověď:",
                            styles["label"],
                        ),
                        Paragraph(
                            escape(correct_text),
                            styles["correct"],
                        ),
                    ],
                ],
                colWidths=[
                    42 * mm,
                    130 * mm,
                ],
                style=TableStyle([
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        2,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        2,
                    ),
                ]),
            ),
            Spacer(1, 1.5 * mm),
            Paragraph(
                (
                    "SPRÁVNĚ"
                    if is_correct
                    else "CHYBNĚ"
                ),
                result_style,
            ),
            Spacer(1, 5 * mm),
        ]

        story.append(
            KeepTogether(block)
        )

    story.append(
        Spacer(1, 5 * mm)
    )

    story.append(
        Paragraph(
            (
                "Dokument byl automaticky vygenerován "
                "systémem Elektroakademie."
            ),
            styles["footer"],
        )
    )

    document.build(story)

    return result.getvalue()

def generate_html_pdf(
    html,
    *,
    css=None,
):
    """
    Vyrenderuje HTML pomocí Chromium
    a vrátí PDF jako bytes.
    """

    with sync_playwright() as playwright:
        chromium_path = os.getenv(
            "CHROMIUM_EXECUTABLE_PATH"
        )

        launch_kwargs = {
            "headless": True,
        }

        if chromium_path:
            launch_kwargs.update({
                "executable_path": chromium_path,
                "args": [
                    "--disable-gpu",
                    "--no-sandbox",
                    "--headless",
                ],
            })

        browser = playwright.chromium.launch(
            **launch_kwargs
        )

        try:
            page = browser.new_page()

            page.set_content(
                html,
                wait_until="networkidle",
            )

            if css:
                page.add_style_tag(
                    content=css
                )

            return page.pdf(
                format="A4",
                print_background=True,
                margin={
                    "top": "0",
                    "right": "0",
                    "bottom": "0",
                    "left": "0",
                },
                prefer_css_page_size=True,
            )

        finally:
            browser.close()