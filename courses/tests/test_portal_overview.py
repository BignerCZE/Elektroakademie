from unittest.mock import patch
from django.urls import reverse
from django.contrib.auth import get_user_model
from courses.models import QuizAttempt
from courses.tests.test_certificates import CertificateTestBase


class PortalOverviewTests(CertificateTestBase):
    def test_account_bar_and_video_stay_in_overview(self):
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'portal-topbar')
        self.assertContains(response, 'Přehrát výukové video')
        self.assertContains(response, 'portal-video-dialog')
        self.assertContains(response, 'Historie testů')
        self.assertNotContains(response, 'Přejít na Online Kurz')
        self.assertNotContains(response, 'id="top-navigation"')
        account = response.content.decode().split('<nav class="portal-account-actions"', 1)[1].split('</nav>', 1)[0]
        self.assertIn('Odhlásit se', account)
        self.assertIn(reverse('profile'), account)
        self.assertNotContains(response, 'dashboard-shell-sidebar')
        self.assertContains(response, 'Vítejte,')
        self.assertNotContains(response, 'portal-course-description')
        self.assertContains(response, 'Jan Novák')
        self.assertContains(response, 'EA-04-202608-00001')
        for name in ('video_detail', 'quiz', 'certificate_success'):
            self.assertNotIn(reverse(name, args=[self.course.pk]), account)

    def test_certificate_preview_uses_existing_document_and_download(self):
        certificate, _ = self.create_certificate()
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'portal-certificate-dialog')
        self.assertContains(response, certificate.certificate_number)
        self.assertContains(response, 'Jan Novák')
        self.assertContains(response, reverse('certificate_pdf', args=[self.course.pk]) + '?download=1')
        self.assertNotContains(response, 'class="certificate-course"')
        with patch('courses.views.generate_certificate_pdf', return_value=b'%PDF-test'):
            download = self.client.get(reverse('certificate_pdf', args=[self.course.pk]), {'download': '1'})
            self.assertTrue(download['Content-Disposition'].startswith('attachment;'))
            inline = self.client.get(reverse('certificate_pdf', args=[self.course.pk]))
            self.assertTrue(inline['Content-Disposition'].startswith('inline;'))

    def test_no_false_certificate_link_when_document_does_not_exist(self):
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Certifikát zatím není k dispozici')
        self.assertNotContains(response, 'id="portal-certificate-dialog"')
        self.assertNotContains(response, '?download=1')

    def test_unpassed_user_can_start_or_resume_without_leaving_overview(self):
        self.user.passed_quiz = False
        self.user.save(update_fields=['passed_quiz'])
        self.attempt.delete()
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Spustit test')
        self.assertContains(response, 'Certifikát bude dostupný po úspěšném splnění testu')
        attempt = QuizAttempt.objects.create(user=self.user, course=self.course, attempt_number=2)
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Pokračovat v testu')
        self.assertContains(response, reverse('quiz_start', args=[self.course.pk]))
        attempt.delete()
        QuizAttempt.objects.create(user=self.user, course=self.course, attempt_number=3,
                                   status=QuizAttempt.STATUS_SUBMITTED, passed=False, score_percent=0)
        self.assertContains(self.client.get(reverse('dashboard')), 'Spustit nový test')

    def test_history_does_not_include_other_users(self):
        other = get_user_model().objects.create_user(username='other', is_paid=True)
        hidden = QuizAttempt.objects.create(user=other, course=self.course, attempt_number=999,
                                           status=QuizAttempt.STATUS_SUBMITTED, passed=False)
        response = self.client.get(reverse('dashboard'))
        self.assertNotContains(response, 'Pokus 999')
        self.assertNotIn(hidden, list(response.context['past_attempts']))
        self.assertContains(response, 'Pokus 1')

    def test_unpaid_account_does_not_get_media_history_or_certificate(self):
        self.create_certificate()
        self.user.is_paid = False
        self.user.save(update_fields=['is_paid'])
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Přístup ke kurzu není aktivní')
        self.assertNotContains(response, 'id="portal-video-dialog"')
        self.assertNotContains(response, 'id="portal-certificate-dialog"')

    def test_logout_is_post_and_redirects_home(self):
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('index'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_history_is_a_dialog_and_certificate_is_inside_test_panel(self):
        self.create_certificate()
        response = self.client.get(reverse('dashboard'))
        html = response.content.decode()
        panel = html.split('<section class="portal-test-card"', 1)[1].split('</section>', 1)[0]
        self.assertIn('data-portal-open="portal-history-dialog"', panel)
        self.assertIn('class="portal-certificate-card"', panel)
        self.assertNotIn('class="portal-history-row"', panel)
        self.assertIn('<dialog class="portal-dialog portal-history-dialog"', html)
        history = html.split('id="portal-history-dialog"', 1)[1].split('</dialog>', 1)[0]
        self.assertIn('Pokus 1', history)
        self.assertIn('Zavřít okno testů', history)

    def test_profile_keeps_account_bar_and_return_to_overview(self):
        response = self.client.get(reverse('profile'))
        self.assertContains(response, 'portal-account-bar')
        self.assertContains(response, 'Přehled kurzu')
        self.assertContains(response, 'aria-current="page"')
        self.assertNotContains(response, 'dashboard-shell-sidebar')
