from pathlib import Path
import shutil
import sys

ROOT = Path.cwd()
TEST_FILE = ROOT / "courses" / "tests" / "test_quiz.py"

if not TEST_FILE.exists():
    print("CHYBA: Skript spusťte z kořene projektu Elektroakademie.")
    sys.exit(1)

text = TEST_FILE.read_text(encoding="utf-8")

start = '    @patch("courses.views.deliver_email")\n    @patch("courses.views.build_course_completed_email")\n    @patch("courses.views.generate_certificate")\n    def test_first_successful_attempt_processes_completion_email(\n'

if start not in text:
    print("CHYBA: test_quiz.py neodpovídá očekávanému stavu. Nic nebylo změněno.")
    sys.exit(1)

block_start = text.index(start)

replacement = '''    @patch("courses.views.process_quiz_completion")
    def test_first_successful_attempt_processes_completion_workflow(
        self,
        mock_process_quiz_completion,
    ):
        attempt = self.create_active_attempt()
        self.answer_all(attempt)

        response = self.submit_attempt(attempt)

        attempt.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertTrue(attempt.passed)
        mock_process_quiz_completion.assert_called_once()

        workflow_attempt = mock_process_quiz_completion.call_args.args[0]
        self.assertEqual(workflow_attempt.pk, attempt.pk)

    @patch("courses.views.process_quiz_completion")
    def test_successful_attempt_with_existing_certificate_still_runs_workflow(
        self,
        mock_process_quiz_completion,
    ):
        attempt = self.create_active_attempt()
        self.answer_all(attempt)

        self.submit_attempt(attempt)

        attempt.refresh_from_db()

        self.assertTrue(attempt.passed)
        mock_process_quiz_completion.assert_called_once()

        workflow_attempt = mock_process_quiz_completion.call_args.args[0]
        self.assertEqual(workflow_attempt.pk, attempt.pk)

    @patch("courses.views.process_quiz_completion")
    def test_failed_attempt_does_not_process_completion_workflow(
        self,
        mock_process_quiz_completion,
    ):
        attempt = self.create_active_attempt()

        self.answer_all(
            attempt,
            correct_orders={1, 2},
        )
        self.submit_attempt(attempt)

        attempt.refresh_from_db()

        self.assertFalse(attempt.passed)
        mock_process_quiz_completion.assert_not_called()
'''

new_text = text[:block_start] + replacement

backup = TEST_FILE.with_suffix(".py.workflow2-testfix.bak")
if not backup.exists():
    shutil.copy2(TEST_FILE, backup)

TEST_FILE.write_text(new_text, encoding="utf-8")

print("Oprava testů Workflow 2.0 aplikována.")
print("Změněn pouze courses/tests/test_quiz.py.")
print("Modely ani produkční kód nebyly změněny.")
