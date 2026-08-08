from pathlib import Path
import shutil
import sys

ROOT = Path.cwd()
COURSES = ROOT / "courses"

WORKFLOWS = COURSES / "workflows.py"
BUILDERS = COURSES / "emails" / "builders.py"
DELIVERY = COURSES / "emails" / "delivery.py"
TESTS = COURSES / "tests" / "test_workflow_completion_artifacts.py"

required = [WORKFLOWS, BUILDERS, DELIVERY]
missing = [str(path) for path in required if not path.exists()]
if missing:
    print("CHYBA: Skript spusťte z kořene projektu Elektroakademie.")
    print("Chybí:", ", ".join(missing))
    sys.exit(1)


def replace_between(text, start, end, replacement, label):
    start_index = text.find(start)
    if start_index == -1:
        raise RuntimeError(
            f"{label}: nenalezen začátek cílového bloku."
        )

    end_index = text.find(end, start_index)
    if end_index == -1:
        raise RuntimeError(
            f"{label}: nenalezen konec cílového bloku."
        )

    return (
        text[:start_index]
        + replacement
        + text[end_index:]
    )


workflows = WORKFLOWS.read_text(encoding="utf-8")
builders = BUILDERS.read_text(encoding="utf-8")
delivery = DELIVERY.read_text(encoding="utf-8")

# ------------------------------------------------------------------
# workflows.py
# ------------------------------------------------------------------
old_builder_import = """from .emails.builders import (
    build_course_completed_email,
    build_participant_activation_email,
    build_payment_completed_email,
)
"""
new_builder_import = """from .emails.builders import (
    COURSE_COMPLETED_SUBJECT,
    build_course_completed_email,
    build_participant_activation_email,
    build_payment_completed_email,
)
"""
if workflows.count(old_builder_import) != 1:
    raise RuntimeError(
        "workflows.py: neočekávaný stav importu builderů."
    )
workflows = workflows.replace(
    old_builder_import,
    new_builder_import,
    1,
)

old_delivery_import = (
    "from .emails.delivery import deliver_email\n"
)
new_delivery_import = """from .emails.delivery import (
    deliver_email,
    record_email_failure,
)
"""
if workflows.count(old_delivery_import) != 1:
    raise RuntimeError(
        "workflows.py: neočekávaný import delivery."
    )
workflows = workflows.replace(
    old_delivery_import,
    new_delivery_import,
    1,
)

old_services_import = (
    "from .services import generate_certificate, "
    "mark_order_as_paid\n"
)
new_services_import = """from .services import (
    generate_certificate,
    generate_certificate_pdf,
    generate_quiz_result_pdf,
    mark_order_as_paid,
)
"""
if workflows.count(old_services_import) != 1:
    raise RuntimeError(
        "workflows.py: neočekávaný import services."
    )
workflows = workflows.replace(
    old_services_import,
    new_services_import,
    1,
)

completion_start = "def process_quiz_completion(attempt):\n"
completion_index = workflows.find(completion_start)
if completion_index == -1:
    raise RuntimeError(
        "workflows.py: process_quiz_completion nebyl nalezen."
    )
workflows = (
    workflows[:completion_index]
    + 'def _validate_pdf_content(content, label):\n    if not isinstance(content, (bytes, bytearray)):\n        raise ValueError(\n            f"{label} nebylo vygenerováno jako binární PDF."\n        )\n\n    content = bytes(content)\n\n    if not content.startswith(b"%PDF"):\n        raise ValueError(\n            f"{label} nemá platnou PDF hlavičku."\n        )\n\n    return content\n\n\ndef _record_course_completion_failure(\n    attempt,\n    error_message,\n):\n    return record_email_failure(\n        email_type=EmailLog.TYPE_COURSE_COMPLETED,\n        recipient=attempt.user.email,\n        subject=COURSE_COMPLETED_SUBJECT,\n        error=error_message,\n        quiz_attempt=attempt,\n    )\n\n\ndef process_quiz_completion(attempt):\n    """\n    Dokončí workflow úspěšně odeslaného testu.\n\n    Jednotlivé kroky jsou idempotentní na úrovni výsledného\n    e-mailového workflow:\n\n    1. vytvoření / načtení certifikátu,\n    2. PDF certifikátu,\n    3. PDF výsledku testu,\n    4. sestavení závěrečného e-mailu,\n    5. předání aktivnímu transportu,\n    6. záznam výsledku do EmailLog.\n\n    PREVIEW/SENT záznam další běh zastaví. FAILED záznam další\n    pokus neblokuje, takže je možné bezpečně opravit dočasné\n    selhání generování PDF nebo e-mailového transportu.\n    """\n    attempt = (\n        QuizAttempt.objects\n        .select_related("user", "course")\n        .get(pk=attempt.pk)\n    )\n\n    if attempt.status != QuizAttempt.STATUS_SUBMITTED:\n        raise ValueError(\n            "Workflow dokončení kurzu vyžaduje odeslaný test."\n        )\n\n    if not attempt.passed:\n        raise ValueError(\n            "Workflow dokončení kurzu vyžaduje úspěšný test."\n        )\n\n    certificate, certificate_created = generate_certificate(\n        attempt\n    )\n\n    # Současný model dovoluje účastníkovi právě jeden certifikát.\n    # Pokud už existuje certifikát navázaný na jiný pokus,\n    # tento pozdější pokus nesmí pracovat s nesouvisejícím\n    # certifikátem.\n    if certificate.quiz_attempt_id != attempt.pk:\n        return QuizCompletionWorkflowResult(\n            attempt=attempt,\n            certificate=certificate,\n            certificate_created=certificate_created,\n            email_log=None,\n            errors=(),\n        )\n\n    log_filters = {\n        "email_type": EmailLog.TYPE_COURSE_COMPLETED,\n        "quiz_attempt": attempt,\n        "recipient": attempt.user.email,\n    }\n\n    if _email_already_completed(**log_filters):\n        return QuizCompletionWorkflowResult(\n            attempt=attempt,\n            certificate=certificate,\n            certificate_created=certificate_created,\n            email_log=None,\n            errors=(),\n        )\n\n    try:\n        certificate_pdf = _validate_pdf_content(\n            generate_certificate_pdf(certificate),\n            "PDF certifikátu",\n        )\n        quiz_result_pdf = _validate_pdf_content(\n            generate_quiz_result_pdf(attempt),\n            "PDF výsledku testu",\n        )\n\n        email = build_course_completed_email(\n            attempt,\n            certificate=certificate,\n            certificate_pdf=certificate_pdf,\n            quiz_result_pdf=quiz_result_pdf,\n        )\n\n    except Exception as exc:\n        error_message = (\n            "Příprava závěrečného e-mailu selhala: "\n            f"{exc}"\n        )\n        _record_course_completion_failure(\n            attempt,\n            error_message,\n        )\n        logger.exception(\n            "Nepodařilo se připravit závěrečný e-mail "\n            "pro QuizAttempt %s.",\n            attempt.pk,\n        )\n        return QuizCompletionWorkflowResult(\n            attempt=attempt,\n            certificate=certificate,\n            certificate_created=certificate_created,\n            email_log=None,\n            errors=(error_message,),\n        )\n\n    try:\n        log = deliver_email(\n            email,\n            email_type=EmailLog.TYPE_COURSE_COMPLETED,\n            quiz_attempt=attempt,\n        )\n    except Exception as exc:\n        # deliver_email zapisuje FAILED záznam samo, takže zde\n        # chybu pouze vracíme volajícímu a nevytváříme duplicitu.\n        error_message = (\n            "Doručení závěrečného e-mailu selhalo: "\n            f"{exc}"\n        )\n        logger.exception(\n            "Nepodařilo se doručit závěrečný e-mail "\n            "pro QuizAttempt %s.",\n            attempt.pk,\n        )\n        return QuizCompletionWorkflowResult(\n            attempt=attempt,\n            certificate=certificate,\n            certificate_created=certificate_created,\n            email_log=None,\n            errors=(error_message,),\n        )\n\n    return QuizCompletionWorkflowResult(\n        attempt=attempt,\n        certificate=certificate,\n        certificate_created=certificate_created,\n        email_log=log,\n        errors=(),\n    )\n'
)

# ------------------------------------------------------------------
# builders.py
# ------------------------------------------------------------------
builders = replace_between(
    builders,
    "def build_course_completed_email(attempt):\n",
    "def build_payment_completed_email(\n",
    'COURSE_COMPLETED_SUBJECT = (\n    "Úspěšné dokončení kurzu – "\n    "certifikát a výsledek testu"\n)\n\n\ndef build_course_completed_email(\n    attempt,\n    *,\n    certificate=None,\n    certificate_pdf=None,\n    quiz_result_pdf=None,\n):\n    """\n    Sestaví závěrečný e-mail.\n\n    Pokud PDF přílohy nejsou předané, vygeneruje je builder sám.\n    To zachovává funkčnost administrátorských preview view.\n\n    Workflow dokončení kurzu naopak předává již připravené PDF,\n    aby bylo možné každý krok samostatně zachytit a auditovat.\n    """\n    if attempt.status != attempt.STATUS_SUBMITTED:\n        raise ValueError(\n            "Závěrečný e-mail lze vytvořit pouze "\n            "pro odeslaný test."\n        )\n\n    if not attempt.passed:\n        raise ValueError(\n            "Závěrečný e-mail lze vytvořit pouze "\n            "pro úspěšně dokončený test."\n        )\n\n    if certificate is None:\n        certificate = (\n            Certificate.objects\n            .select_related(\n                "participant",\n                "quiz_attempt",\n                "quiz_attempt__course",\n            )\n            .filter(\n                quiz_attempt=attempt,\n            )\n            .first()\n        )\n\n    if certificate is None:\n        raise ValueError(\n            "K úspěšnému testu nebyl nalezen certifikát."\n        )\n\n    if certificate.quiz_attempt_id != attempt.pk:\n        raise ValueError(\n            "Certifikát nepatří k zadanému testovému pokusu."\n        )\n\n    if certificate_pdf is None:\n        certificate_pdf = generate_certificate_pdf(\n            certificate\n        )\n\n    if quiz_result_pdf is None:\n        quiz_result_pdf = generate_quiz_result_pdf(\n            attempt\n        )\n\n    certificate_attachment = EmailAttachment(\n        filename=(\n            f"certifikat-"\n            f"{certificate.certificate_number}.pdf"\n        ),\n        content=certificate_pdf,\n        mimetype="application/pdf",\n    )\n    quiz_result_attachment = EmailAttachment(\n        filename=(\n            f"vysledek-testu-"\n            f"{attempt.id}.pdf"\n        ),\n        content=quiz_result_pdf,\n        mimetype="application/pdf",\n    )\n\n    context = {\n        "attempt": attempt,\n        "user": attempt.user,\n        "course": attempt.course,\n        "certificate": certificate,\n    }\n\n    return render_email(\n        subject=COURSE_COMPLETED_SUBJECT,\n        recipient=attempt.user.email,\n        html_template="emails/course_completed.html",\n        text_template="emails/course_completed.txt",\n        context=context,\n        attachments=(\n            certificate_attachment,\n            quiz_result_attachment,\n        ),\n    )\n\n\n',
    "builders.py / build_course_completed_email",
)

# ------------------------------------------------------------------
# delivery.py
# ------------------------------------------------------------------
if "def record_email_failure(" in delivery:
    raise RuntimeError(
        "delivery.py již obsahuje record_email_failure; "
        "etapa 2 možná už byla aplikována."
    )

if "def deliver_email(" not in delivery:
    raise RuntimeError(
        "delivery.py neodpovídá očekávanému stavu."
    )

delivery = 'from django.utils import timezone\n\nfrom courses.models import EmailLog\n\nfrom .transport import send_email\nfrom .types import RenderedEmail\n\n\ndef record_email_failure(\n    *,\n    email_type,\n    recipient,\n    subject,\n    error,\n    order=None,\n    quiz_attempt=None,\n):\n    """\n    Zapíše neúspěšný e-mailový krok do společné EmailLog historie.\n\n    Používá se jak pro chyby transportu, tak pro chyby přípravy\n    e-mailu před samotným transportem (například generování PDF).\n    """\n    return EmailLog.objects.create(\n        email_type=email_type,\n        recipient=recipient,\n        subject=subject,\n        status=EmailLog.STATUS_FAILED,\n        error_message=str(error),\n        order=order,\n        quiz_attempt=quiz_attempt,\n    )\n\n\ndef deliver_email(\n    email: RenderedEmail,\n    *,\n    email_type,\n    order=None,\n    quiz_attempt=None,\n):\n    """\n    Předá sestavený e-mail aktivnímu transportu\n    a zaznamená výsledek do EmailLog.\n\n    Samotný obsah e-mailu ani přílohy se do databáze\n    neukládají.\n    """\n    try:\n        result = send_email(email)\n    except Exception as exc:\n        record_email_failure(\n            email_type=email_type,\n            recipient=email.recipient,\n            subject=email.subject,\n            error=exc,\n            order=order,\n            quiz_attempt=quiz_attempt,\n        )\n        raise\n\n    if result.status == "preview":\n        status = EmailLog.STATUS_PREVIEW\n        sent_at = None\n\n    elif result.status == "sent":\n        status = EmailLog.STATUS_SENT\n        sent_at = timezone.now()\n\n    else:\n        error = ValueError(\n            f"Neznámý stav doručení e-mailu: {result.status}"\n        )\n        record_email_failure(\n            email_type=email_type,\n            recipient=email.recipient,\n            subject=email.subject,\n            error=error,\n            order=order,\n            quiz_attempt=quiz_attempt,\n        )\n        raise error\n\n    log = EmailLog.objects.create(\n        email_type=email_type,\n        recipient=email.recipient,\n        subject=email.subject,\n        status=status,\n        order=order,\n        quiz_attempt=quiz_attempt,\n        sent_at=sent_at,\n    )\n\n    return log\n'

# Všechny kontroly proběhly. Teprve teď zapisujeme.
for path in [WORKFLOWS, BUILDERS, DELIVERY]:
    backup = path.with_suffix(
        path.suffix + ".workflow2-stage2.bak"
    )
    if not backup.exists():
        shutil.copy2(path, backup)

WORKFLOWS.write_text(
    workflows,
    encoding="utf-8",
)
BUILDERS.write_text(
    builders,
    encoding="utf-8",
)
DELIVERY.write_text(
    delivery,
    encoding="utf-8",
)
TESTS.write_text(
    'from unittest.mock import patch\n\nfrom django.contrib.auth import get_user_model\nfrom django.test import TestCase, override_settings\nfrom django.utils import timezone\n\nfrom courses.models import (\n    Course,\n    EmailLog,\n    Order,\n    OrderParticipant,\n    QuizAttempt,\n)\nfrom courses.workflows import process_quiz_completion\n\n\nUser = get_user_model()\n\n\n@override_settings(\n    EMAIL_TRANSPORT="preview",\n    SITE_URL="http://testserver",\n)\nclass QuizCompletionArtifactWorkflowTests(TestCase):\n    def setUp(self):\n        self.user = User.objects.create_user(\n            username="artifact@example.com",\n            email="artifact@example.com",\n            first_name="Jan",\n            last_name="Novák",\n            password="Testheslo1",\n            is_paid=True,\n        )\n        self.course = Course.objects.create(\n            title="§4 – osoba poučená",\n            description="Testovací kurz",\n            video_url="https://example.com/video",\n        )\n        self.order = Order.objects.create(\n            course_type="4",\n            total_price=990,\n            status="paid",\n            paid_at=timezone.now(),\n            company_name="Testovací firma s.r.o.",\n            street="Testovací 1",\n            city="Praha",\n            zip_code="11000",\n            country="CZ",\n            contact_email="kontakt@example.com",\n        )\n        self.participant = OrderParticipant.objects.create(\n            order=self.order,\n            user=self.user,\n            first_name="Jan",\n            last_name="Novák",\n            email=self.user.email,\n            registration_number="EA-04-202608-00002",\n            activation_completed_at=timezone.now(),\n        )\n        self.attempt = QuizAttempt.objects.create(\n            user=self.user,\n            course=self.course,\n            attempt_number=1,\n            status=QuizAttempt.STATUS_SUBMITTED,\n            total_questions=10,\n            correct_answers=8,\n            score_percent=80,\n            passed=True,\n            submitted_at=timezone.now(),\n        )\n\n    @patch(\n        "courses.workflows.generate_quiz_result_pdf",\n        return_value=b"%PDF quiz",\n    )\n    @patch(\n        "courses.workflows.generate_certificate_pdf",\n        return_value=b"%PDF certificate",\n    )\n    def test_success_generates_both_artifacts_and_preview_log(\n        self,\n        mock_certificate_pdf,\n        mock_quiz_pdf,\n    ):\n        result = process_quiz_completion(\n            self.attempt\n        )\n\n        self.assertEqual(result.errors, ())\n        mock_certificate_pdf.assert_called_once()\n        mock_quiz_pdf.assert_called_once_with(\n            self.attempt\n        )\n\n        log = EmailLog.objects.get(\n            email_type=EmailLog.TYPE_COURSE_COMPLETED,\n            quiz_attempt=self.attempt,\n        )\n        self.assertEqual(\n            log.status,\n            EmailLog.STATUS_PREVIEW,\n        )\n\n    @patch(\n        "courses.workflows.generate_quiz_result_pdf"\n    )\n    @patch(\n        "courses.workflows.generate_certificate_pdf",\n        side_effect=RuntimeError(\n            "Chromium není dostupný"\n        ),\n    )\n    def test_certificate_pdf_failure_is_logged(\n        self,\n        mock_certificate_pdf,\n        mock_quiz_pdf,\n    ):\n        result = process_quiz_completion(\n            self.attempt\n        )\n\n        self.assertTrue(result.errors)\n        mock_certificate_pdf.assert_called_once()\n        mock_quiz_pdf.assert_not_called()\n\n        log = EmailLog.objects.get(\n            email_type=EmailLog.TYPE_COURSE_COMPLETED,\n            quiz_attempt=self.attempt,\n        )\n        self.assertEqual(\n            log.status,\n            EmailLog.STATUS_FAILED,\n        )\n        self.assertIn(\n            "Chromium není dostupný",\n            log.error_message,\n        )\n\n    @patch(\n        "courses.workflows.generate_quiz_result_pdf",\n        side_effect=RuntimeError(\n            "ReportLab chyba"\n        ),\n    )\n    @patch(\n        "courses.workflows.generate_certificate_pdf",\n        return_value=b"%PDF certificate",\n    )\n    def test_quiz_pdf_failure_is_logged(\n        self,\n        mock_certificate_pdf,\n        mock_quiz_pdf,\n    ):\n        result = process_quiz_completion(\n            self.attempt\n        )\n\n        self.assertTrue(result.errors)\n        mock_certificate_pdf.assert_called_once()\n        mock_quiz_pdf.assert_called_once_with(\n            self.attempt\n        )\n\n        log = EmailLog.objects.get(\n            email_type=EmailLog.TYPE_COURSE_COMPLETED,\n            quiz_attempt=self.attempt,\n        )\n        self.assertEqual(\n            log.status,\n            EmailLog.STATUS_FAILED,\n        )\n        self.assertIn(\n            "ReportLab chyba",\n            log.error_message,\n        )\n\n    @patch(\n        "courses.workflows.generate_quiz_result_pdf",\n        return_value=b"%PDF quiz",\n    )\n    @patch(\n        "courses.workflows.generate_certificate_pdf",\n        return_value=b"not-a-pdf",\n    )\n    def test_invalid_pdf_content_is_logged_as_failure(\n        self,\n        mock_certificate_pdf,\n        mock_quiz_pdf,\n    ):\n        result = process_quiz_completion(\n            self.attempt\n        )\n\n        self.assertTrue(result.errors)\n        mock_quiz_pdf.assert_not_called()\n\n        log = EmailLog.objects.get(\n            email_type=EmailLog.TYPE_COURSE_COMPLETED,\n            quiz_attempt=self.attempt,\n        )\n        self.assertEqual(\n            log.status,\n            EmailLog.STATUS_FAILED,\n        )\n        self.assertIn(\n            "platnou PDF hlavičku",\n            log.error_message,\n        )\n\n    @patch(\n        "courses.workflows.generate_quiz_result_pdf",\n        return_value=b"%PDF quiz",\n    )\n    @patch(\n        "courses.workflows.generate_certificate_pdf",\n        side_effect=[\n            RuntimeError("Dočasná chyba"),\n            b"%PDF certificate",\n        ],\n    )\n    def test_failed_artifact_generation_can_be_retried(\n        self,\n        mock_certificate_pdf,\n        mock_quiz_pdf,\n    ):\n        first_result = process_quiz_completion(\n            self.attempt\n        )\n        second_result = process_quiz_completion(\n            self.attempt\n        )\n\n        self.assertTrue(first_result.errors)\n        self.assertEqual(second_result.errors, ())\n        self.assertEqual(\n            mock_certificate_pdf.call_count,\n            2,\n        )\n        mock_quiz_pdf.assert_called_once_with(\n            self.attempt\n        )\n\n        logs = EmailLog.objects.filter(\n            email_type=EmailLog.TYPE_COURSE_COMPLETED,\n            quiz_attempt=self.attempt,\n        )\n        self.assertEqual(\n            logs.filter(\n                status=EmailLog.STATUS_FAILED,\n            ).count(),\n            1,\n        )\n        self.assertEqual(\n            logs.filter(\n                status=EmailLog.STATUS_PREVIEW,\n            ).count(),\n            1,\n        )\n\n    @patch(\n        "courses.workflows.generate_quiz_result_pdf",\n        return_value=b"%PDF quiz",\n    )\n    @patch(\n        "courses.workflows.generate_certificate_pdf",\n        return_value=b"%PDF certificate",\n    )\n    def test_completed_preview_does_not_regenerate_artifacts(\n        self,\n        mock_certificate_pdf,\n        mock_quiz_pdf,\n    ):\n        process_quiz_completion(\n            self.attempt\n        )\n        process_quiz_completion(\n            self.attempt\n        )\n\n        mock_certificate_pdf.assert_called_once()\n        mock_quiz_pdf.assert_called_once()\n\n        self.assertEqual(\n            EmailLog.objects.filter(\n                email_type=EmailLog.TYPE_COURSE_COMPLETED,\n                quiz_attempt=self.attempt,\n                status=EmailLog.STATUS_PREVIEW,\n            ).count(),\n            1,\n        )\n',
    encoding="utf-8",
)

print("Workflow + e-mailový systém 2.0 / etapa 2 aplikována.")
print("Změněno:")
print(" - courses/workflows.py")
print(" - courses/emails/builders.py")
print(" - courses/emails/delivery.py")
print(" - courses/tests/test_workflow_completion_artifacts.py")
print("Modely nebyly změněny a nevznikají migrace.")
