from pathlib import Path
import re
import shutil
import sys

ROOT = Path.cwd()
COURSES = ROOT / "courses"

required = [COURSES / "views.py", COURSES / "admin.py", COURSES / "emails" / "builders.py"]
missing = [str(path) for path in required if not path.exists()]
if missing:
    print("CHYBA: Skript spusťte z kořene projektu Elektroakademie.")
    print("Chybí:", ", ".join(missing))
    sys.exit(1)

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: očekáván 1 výskyt, nalezeno {count}.")
    return text.replace(old, new, 1)

def replace_between(text, start, end, replacement, label):
    start_index = text.find(start)
    if start_index == -1:
        raise RuntimeError(f"{label}: nenalezen začátek bloku.")
    end_index = text.find(end, start_index)
    if end_index == -1:
        raise RuntimeError(f"{label}: nenalezen konec bloku.")
    return text[:start_index] + replacement + text[end_index:]

workflows_source = 'import logging\nfrom dataclasses import dataclass\n\nfrom django.conf import settings\n\nfrom .emails.builders import (\n    build_course_completed_email,\n    build_participant_activation_email,\n    build_payment_completed_email,\n)\nfrom .emails.delivery import deliver_email\nfrom .models import EmailLog, QuizAttempt\nfrom .services import generate_certificate, mark_order_as_paid\n\n\nlogger = logging.getLogger(__name__)\n\n\n@dataclass(frozen=True)\nclass OrderPaymentWorkflowResult:\n    order: object\n    participants: tuple\n    status_changed: bool\n    errors: tuple\n\n\n@dataclass(frozen=True)\nclass QuizCompletionWorkflowResult:\n    attempt: object\n    certificate: object\n    certificate_created: bool\n    email_log: object\n    errors: tuple\n\n\ndef _completed_email_statuses():\n    """\n    V preview režimu je náhled považovaný za dokončené zpracování,\n    aby opakované spuštění workflow nevytvářelo duplicitní logy.\n\n    Po budoucím přepnutí na skutečný transport se PREVIEW log\n    nepovažuje za odeslaný. Staré náhledy tak nebudou blokovat\n    první skutečné odeslání přes SMTP.\n    """\n    transport_name = getattr(\n        settings,\n        "EMAIL_TRANSPORT",\n        "preview",\n    )\n\n    if transport_name == "preview":\n        return (\n            EmailLog.STATUS_PREVIEW,\n            EmailLog.STATUS_SENT,\n        )\n\n    return (EmailLog.STATUS_SENT,)\n\n\ndef _email_already_completed(**filters):\n    return EmailLog.objects.filter(\n        status__in=_completed_email_statuses(),\n        **filters,\n    ).exists()\n\n\ndef process_order_payment(order_id):\n    """\n    Kompletní workflow po přijetí platby.\n\n    Platba a evidenční čísla jsou řešeny existující službou.\n    E-mailové kroky se následně reconciliují i pro již zaplacenou\n    objednávku, takže workflow umí opravit dříve nedokončený krok.\n    """\n    order, participants, status_changed = mark_order_as_paid(\n        order_id\n    )\n    participants = tuple(participants)\n    errors = []\n\n    for participant in participants:\n        log_filters = {\n            "email_type": EmailLog.TYPE_PARTICIPANT_ACTIVATION,\n            "order": order,\n            "recipient": participant.email,\n        }\n\n        if _email_already_completed(**log_filters):\n            continue\n\n        try:\n            email = build_participant_activation_email(\n                participant\n            )\n            log = deliver_email(\n                email,\n                email_type=(\n                    EmailLog.TYPE_PARTICIPANT_ACTIVATION\n                ),\n                order=order,\n            )\n\n            if (\n                log.status == EmailLog.STATUS_SENT\n                and participant.activation_sent_at is None\n            ):\n                participant.activation_sent_at = log.sent_at\n                participant.save(\n                    update_fields=["activation_sent_at"]\n                )\n\n        except Exception as exc:\n            errors.append(\n                (\n                    "Aktivační e-mail pro účastníka "\n                    f"{participant.pk}: {exc}"\n                )\n            )\n            logger.exception(\n                "Nepodařilo se zpracovat aktivační e-mail "\n                "pro účastníka %s.",\n                participant.pk,\n            )\n\n    payment_log_filters = {\n        "email_type": EmailLog.TYPE_PAYMENT_COMPLETED,\n        "order": order,\n        "recipient": order.contact_email,\n    }\n\n    if not _email_already_completed(\n        **payment_log_filters\n    ):\n        try:\n            email = build_payment_completed_email(\n                order,\n                participants,\n            )\n            deliver_email(\n                email,\n                email_type=EmailLog.TYPE_PAYMENT_COMPLETED,\n                order=order,\n            )\n        except Exception as exc:\n            errors.append(\n                (\n                    "Potvrzení platby pro objednávku "\n                    f"{order.pk}: {exc}"\n                )\n            )\n            logger.exception(\n                "Nepodařilo se zpracovat potvrzení o přijetí "\n                "platby pro objednávku %s.",\n                order.pk,\n            )\n\n    return OrderPaymentWorkflowResult(\n        order=order,\n        participants=participants,\n        status_changed=status_changed,\n        errors=tuple(errors),\n    )\n\n\ndef process_quiz_completion(attempt):\n    """\n    Dokončí workflow úspěšně odeslaného testu.\n\n    Vytvoření certifikátu je idempotentní. Závěrečný e-mail se\n    posuzuje samostatně podle EmailLog, takže předchozí FAILED stav\n    neblokuje další pokus.\n    """\n    attempt = (\n        QuizAttempt.objects\n        .select_related("user", "course")\n        .get(pk=attempt.pk)\n    )\n\n    if attempt.status != QuizAttempt.STATUS_SUBMITTED:\n        raise ValueError(\n            "Workflow dokončení kurzu vyžaduje odeslaný test."\n        )\n\n    if not attempt.passed:\n        raise ValueError(\n            "Workflow dokončení kurzu vyžaduje úspěšný test."\n        )\n\n    certificate, certificate_created = generate_certificate(\n        attempt\n    )\n\n    # Současný model dovoluje účastníkovi právě jeden certifikát.\n    # Pokud už existuje certifikát navázaný na jiný pokus,\n    # tento pozdější pokus nesmí vytvořit závěrečný e-mail\n    # s nesouvisejícím certifikátem.\n    if certificate.quiz_attempt_id != attempt.pk:\n        return QuizCompletionWorkflowResult(\n            attempt=attempt,\n            certificate=certificate,\n            certificate_created=certificate_created,\n            email_log=None,\n            errors=(),\n        )\n\n    log_filters = {\n        "email_type": EmailLog.TYPE_COURSE_COMPLETED,\n        "quiz_attempt": attempt,\n        "recipient": attempt.user.email,\n    }\n\n    if _email_already_completed(**log_filters):\n        return QuizCompletionWorkflowResult(\n            attempt=attempt,\n            certificate=certificate,\n            certificate_created=certificate_created,\n            email_log=None,\n            errors=(),\n        )\n\n    try:\n        email = build_course_completed_email(\n            attempt\n        )\n        log = deliver_email(\n            email,\n            email_type=EmailLog.TYPE_COURSE_COMPLETED,\n            quiz_attempt=attempt,\n        )\n    except Exception as exc:\n        logger.exception(\n            "Nepodařilo se zpracovat závěrečný e-mail "\n            "pro QuizAttempt %s.",\n            attempt.pk,\n        )\n        return QuizCompletionWorkflowResult(\n            attempt=attempt,\n            certificate=certificate,\n            certificate_created=certificate_created,\n            email_log=None,\n            errors=(str(exc),),\n        )\n\n    return QuizCompletionWorkflowResult(\n        attempt=attempt,\n        certificate=certificate,\n        certificate_created=certificate_created,\n        email_log=log,\n        errors=(),\n    )\n'
tests_source = 'from unittest.mock import patch\n\nfrom django.contrib.auth import get_user_model\nfrom django.test import TestCase, override_settings\nfrom django.utils import timezone\n\nfrom courses.emails.types import RenderedEmail\nfrom courses.models import (\n    Certificate,\n    Course,\n    EmailLog,\n    Order,\n    OrderParticipant,\n    QuizAttempt,\n)\nfrom courses.workflows import (\n    process_order_payment,\n    process_quiz_completion,\n)\n\n\nUser = get_user_model()\n\n\n@override_settings(\n    EMAIL_TRANSPORT="preview",\n    SITE_URL="http://testserver",\n)\nclass OrderPaymentWorkflowTests(TestCase):\n    def setUp(self):\n        self.order = Order.objects.create(\n            course_type="4",\n            total_price=1980,\n            status="pending_payment",\n            company_name="Testovací firma s.r.o.",\n            street="Testovací 1",\n            city="Praha",\n            zip_code="11000",\n            country="CZ",\n            contact_first_name="Petr",\n            contact_last_name="Svoboda",\n            contact_email="kontakt@example.com",\n        )\n        self.participant_1 = OrderParticipant.objects.create(\n            order=self.order,\n            first_name="Jan",\n            last_name="Novák",\n            email="jan@example.com",\n        )\n        self.participant_2 = OrderParticipant.objects.create(\n            order=self.order,\n            first_name="Eva",\n            last_name="Nováková",\n            email="eva@example.com",\n        )\n\n    def test_payment_workflow_completes_whole_preview_flow(self):\n        result = process_order_payment(\n            self.order.pk\n        )\n\n        self.order.refresh_from_db()\n        self.participant_1.refresh_from_db()\n        self.participant_2.refresh_from_db()\n\n        self.assertTrue(result.status_changed)\n        self.assertEqual(self.order.status, "paid")\n        self.assertIsNotNone(self.order.paid_at)\n        self.assertTrue(\n            self.participant_1.registration_number\n        )\n        self.assertTrue(\n            self.participant_2.registration_number\n        )\n        self.assertEqual(\n            EmailLog.objects.filter(\n                order=self.order,\n                status=EmailLog.STATUS_PREVIEW,\n            ).count(),\n            3,\n        )\n\n    def test_payment_workflow_is_idempotent(self):\n        process_order_payment(self.order.pk)\n        original_paid_at = (\n            Order.objects.get(pk=self.order.pk).paid_at\n        )\n\n        result = process_order_payment(\n            self.order.pk\n        )\n\n        self.order.refresh_from_db()\n\n        self.assertFalse(result.status_changed)\n        self.assertEqual(\n            self.order.paid_at,\n            original_paid_at,\n        )\n        self.assertEqual(\n            EmailLog.objects.filter(\n                order=self.order,\n            ).count(),\n            3,\n        )\n\n    def test_already_paid_order_with_missing_logs_is_reconciled(self):\n        self.order.status = "paid"\n        self.order.paid_at = timezone.now()\n        self.order.save(\n            update_fields=["status", "paid_at"]\n        )\n\n        result = process_order_payment(\n            self.order.pk\n        )\n\n        self.assertFalse(result.status_changed)\n        self.assertEqual(\n            EmailLog.objects.filter(\n                order=self.order,\n                status=EmailLog.STATUS_PREVIEW,\n            ).count(),\n            3,\n        )\n\n\n@override_settings(\n    EMAIL_TRANSPORT="preview",\n    SITE_URL="http://testserver",\n)\nclass QuizCompletionWorkflowTests(TestCase):\n    def setUp(self):\n        self.user = User.objects.create_user(\n            username="jan@example.com",\n            email="jan@example.com",\n            first_name="Jan",\n            last_name="Novák",\n            password="Testheslo1",\n            is_paid=True,\n        )\n        self.course = Course.objects.create(\n            title="§4 – osoba poučená",\n            description="Testovací kurz",\n            video_url="https://example.com/video",\n        )\n        self.order = Order.objects.create(\n            course_type="4",\n            total_price=990,\n            status="paid",\n            paid_at=timezone.now(),\n            company_name="Testovací firma s.r.o.",\n            street="Testovací 1",\n            city="Praha",\n            zip_code="11000",\n            country="CZ",\n            contact_email="kontakt@example.com",\n        )\n        self.participant = OrderParticipant.objects.create(\n            order=self.order,\n            user=self.user,\n            first_name="Jan",\n            last_name="Novák",\n            email="jan@example.com",\n            registration_number="EA-04-202608-00001",\n            activation_completed_at=timezone.now(),\n        )\n        self.attempt = QuizAttempt.objects.create(\n            user=self.user,\n            course=self.course,\n            attempt_number=1,\n            status=QuizAttempt.STATUS_SUBMITTED,\n            total_questions=10,\n            correct_answers=8,\n            score_percent=80,\n            passed=True,\n            submitted_at=timezone.now(),\n        )\n\n    def _rendered_email(self):\n        return RenderedEmail(\n            subject="Dokončení kurzu",\n            recipient=self.user.email,\n            text_body="Text",\n            html_body="<p>HTML</p>",\n        )\n\n    @patch(\n        "courses.workflows.build_course_completed_email"\n    )\n    def test_quiz_workflow_creates_certificate_and_email_log(\n        self,\n        mock_builder,\n    ):\n        mock_builder.return_value = self._rendered_email()\n\n        result = process_quiz_completion(\n            self.attempt\n        )\n\n        self.assertTrue(result.certificate_created)\n        self.assertTrue(\n            Certificate.objects.filter(\n                quiz_attempt=self.attempt,\n            ).exists()\n        )\n        self.assertEqual(\n            EmailLog.objects.filter(\n                email_type=EmailLog.TYPE_COURSE_COMPLETED,\n                quiz_attempt=self.attempt,\n                status=EmailLog.STATUS_PREVIEW,\n            ).count(),\n            1,\n        )\n\n    @patch(\n        "courses.workflows.build_course_completed_email"\n    )\n    def test_quiz_workflow_does_not_duplicate_completed_email(\n        self,\n        mock_builder,\n    ):\n        mock_builder.return_value = self._rendered_email()\n\n        process_quiz_completion(self.attempt)\n        process_quiz_completion(self.attempt)\n\n        self.assertEqual(\n            EmailLog.objects.filter(\n                email_type=EmailLog.TYPE_COURSE_COMPLETED,\n                quiz_attempt=self.attempt,\n            ).count(),\n            1,\n        )\n\n    @patch(\n        "courses.workflows.build_course_completed_email"\n    )\n    def test_failed_log_does_not_block_retry(\n        self,\n        mock_builder,\n    ):\n        mock_builder.return_value = self._rendered_email()\n\n        Certificate.objects.create(\n            participant=self.participant,\n            quiz_attempt=self.attempt,\n            certificate_number=(\n                self.participant.registration_number\n            ),\n            issued_at=self.attempt.submitted_at,\n            valid_until=timezone.localdate(),\n        )\n        EmailLog.objects.create(\n            email_type=EmailLog.TYPE_COURSE_COMPLETED,\n            recipient=self.user.email,\n            subject="Předchozí pokus",\n            status=EmailLog.STATUS_FAILED,\n            error_message="Testovací chyba",\n            quiz_attempt=self.attempt,\n        )\n\n        process_quiz_completion(self.attempt)\n\n        self.assertEqual(\n            EmailLog.objects.filter(\n                email_type=EmailLog.TYPE_COURSE_COMPLETED,\n                quiz_attempt=self.attempt,\n                status=EmailLog.STATUS_PREVIEW,\n            ).count(),\n            1,\n        )\n'

views_path = COURSES / "views.py"
admin_path = COURSES / "admin.py"
builders_path = COURSES / "emails" / "builders.py"

views = views_path.read_text(encoding="utf-8")
admin_text = admin_path.read_text(encoding="utf-8")
builders = builders_path.read_text(encoding="utf-8")

# ---- views.py ----
views = replace_once(views, "from .emails.delivery import deliver_email\n", "", "views.py / delivery import")
old_services = 'from .services import (\n    generate_certificate,\n    generate_certificate_pdf,\n    generate_quiz_result_pdf,\n    mark_order_as_paid,\n)\n'
new_services = 'from .services import (\n    generate_certificate_pdf,\n    generate_quiz_result_pdf,\n)\nfrom .workflows import (\n    process_order_payment,\n    process_quiz_completion,\n)\n'
views = replace_once(views, old_services, new_services, "views.py / import služeb")
payment_start = 'def order_payment_success(request, order_id):\n'
payment_end = '@staff_member_required\n@require_GET\ndef participant_activation_email_preview'
payment_replacement = 'def order_payment_success(request, order_id):\n    workflow_result = process_order_payment(\n        order_id\n    )\n    order = workflow_result.order\n    participants = workflow_result.participants\n\n    activation_links = [\n        {\n            "participant": participant,\n            "url": request.build_absolute_uri(\n                reverse(\n                    "participant_activation",\n                    kwargs={\n                        "token": participant.activation_token,\n                    },\n                )\n            ),\n            "email_preview_url": reverse(\n                "participant_activation_email_preview",\n                kwargs={\n                    "token": participant.activation_token,\n                },\n            ),\n        }\n        for participant in participants\n    ]\n\n    return render(\n        request,\n        "registration/order_payment_success.html",\n        {\n            "order": order,\n            "participants": participants,\n            "activation_links": activation_links,\n        },\n    )\n\n\n'
views = replace_between(views, payment_start, payment_end, payment_replacement, "views.py / order_payment_success")
quiz_start = '    if passed:\n        request.user.passed_quiz = True\n'
quiz_end = '    detail_url = reverse(\n'
quiz_replacement = '    if passed:\n        request.user.passed_quiz = True\n        request.user.save(\n            update_fields=["passed_quiz"]\n        )\n\n        try:\n            workflow_result = process_quiz_completion(\n                attempt\n            )\n            if workflow_result.errors:\n                logger.warning(\n                    "Workflow dokončení QuizAttempt %s skončil "\n                    "s chybami e-mailu: %s",\n                    attempt.id,\n                    "; ".join(workflow_result.errors),\n                )\n        except ValueError as error:\n            logger.warning(\n                "Workflow dokončení QuizAttempt %s nebyl dokončen: %s",\n                attempt.id,\n                error,\n            )\n        except Exception:\n            logger.exception(\n                "Neočekávaná chyba workflow dokončení "\n                "QuizAttempt %s.",\n                attempt.id,\n            )\n\n'
views = replace_between(views, quiz_start, quiz_end, quiz_replacement, "views.py / dokončení testu")

# ---- admin.py ----
# Import v admin.py může být jednořádkový i součástí víceřádkového bloku.
# Odstraníme pouze jméno mark_order_as_paid a workflow import přidáme zvlášť.
admin_text, removed_service_imports = re.subn(
    r"^from \.services import mark_order_as_paid\s*$",
    "",
    admin_text,
    count=1,
    flags=re.MULTILINE,
)

if removed_service_imports == 0:
    admin_text, removed_service_names = re.subn(
        r"^(\s*)mark_order_as_paid,?\s*$",
        "",
        admin_text,
        count=1,
        flags=re.MULTILINE,
    )
    if removed_service_names == 0:
        raise RuntimeError(
            "admin.py / mark_order_as_paid nebyl nalezen ani "
            "v jednořádkovém, ani ve víceřádkovém importu."
        )

# Případný prázdný víceřádkový import po odebrání jediného jména odstraníme.
admin_text = re.sub(
    r"^from \.services import \(\s*\)\s*\n?",
    "",
    admin_text,
    count=1,
    flags=re.MULTILINE,
)

if "from .workflows import process_order_payment" not in admin_text:
    models_import = re.search(
        r"from \.models import \(\n.*?^\)\n",
        admin_text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not models_import:
        raise RuntimeError(
            "admin.py / nenalezen blok importu .models pro bezpečné "
            "vložení workflow importu."
        )
    insert_at = models_import.end()
    admin_text = (
        admin_text[:insert_at]
        + "\nfrom .workflows import process_order_payment\n"
        + admin_text[insert_at:]
    )
admin_start = '    @admin.action(\n        description="Označit vybrané objednávky jako zaplacené"\n    )\n    def mark_selected_orders_as_paid(self, request, queryset):\n'
admin_end = '    @staticmethod\n    def _participant_badge'
admin_replacement = '    @admin.action(\n        description="Označit vybrané objednávky jako zaplacené"\n    )\n    def mark_selected_orders_as_paid(self, request, queryset):\n        newly_paid_count = 0\n        already_paid_count = 0\n        error_count = 0\n        email_error_count = 0\n\n        for order in queryset.order_by("id"):\n            try:\n                workflow_result = process_order_payment(\n                    order.pk\n                )\n            except Order.DoesNotExist:\n                error_count += 1\n                continue\n            except Exception:\n                error_count += 1\n                continue\n\n            if workflow_result.status_changed:\n                newly_paid_count += 1\n            else:\n                already_paid_count += 1\n\n            email_error_count += len(\n                workflow_result.errors\n            )\n\n        if newly_paid_count:\n            self.message_user(\n                request,\n                (\n                    "Počet nově zaplacených objednávek: "\n                    f"{newly_paid_count}."\n                ),\n                level=messages.SUCCESS,\n            )\n\n        if already_paid_count:\n            self.message_user(\n                request,\n                (\n                    "Počet objednávek, které již byly "\n                    f"zaplacené: {already_paid_count}."\n                ),\n                level=messages.INFO,\n            )\n\n        if email_error_count:\n            self.message_user(\n                request,\n                (\n                    "Workflow dokončil platbu, ale počet "\n                    "e-mailových operací s chybou je "\n                    f"{email_error_count}. Podrobnosti jsou "\n                    "v E-mailové historii."\n                ),\n                level=messages.WARNING,\n            )\n\n        if error_count:\n            self.message_user(\n                request,\n                (\n                    "Počet objednávek, které se nepodařilo "\n                    f"zpracovat: {error_count}."\n                ),\n                level=messages.ERROR,\n            )\n\n'
admin_text = replace_between(admin_text, admin_start, admin_end, admin_replacement, "admin.py / platební akce")

# ---- builders.py ----
old_lookup = '    certificate = (\n        Certificate.objects\n        .select_related(\n            "participant",\n            "quiz_attempt",\n            "quiz_attempt__course",\n        )\n        .filter(\n            participant__user=attempt.user,\n            quiz_attempt__course=attempt.course,\n        )\n        .order_by(\n            "-issued_at",\n            "-id",\n        )\n        .first()\n    )\n'
new_lookup = '    certificate = (\n        Certificate.objects\n        .select_related(\n            "participant",\n            "quiz_attempt",\n            "quiz_attempt__course",\n        )\n        .filter(\n            quiz_attempt=attempt,\n        )\n        .first()\n    )\n'
builders = replace_once(builders, old_lookup, new_lookup, "builders.py / přesná vazba certifikátu")

# Všechny kotvy prošly. Teprve teď zapisujeme.
targets = [views_path, admin_path, builders_path]
for path in targets:
    backup_path = path.with_suffix(path.suffix + '.workflow2.bak')
    if not backup_path.exists():
        shutil.copy2(path, backup_path)

views_path.write_text(views, encoding="utf-8")
admin_path.write_text(admin_text, encoding="utf-8")
builders_path.write_text(builders, encoding="utf-8")
(COURSES / "workflows.py").write_text(workflows_source, encoding="utf-8")
(COURSES / "tests" / "test_workflows.py").write_text(tests_source, encoding="utf-8")

print("Workflow + e-mailový systém 2.0 / etapa 1 aplikována.")
print("Nevznikají žádné migrace.")
print("Zálohy změněných souborů mají příponu .workflow2.bak.")
