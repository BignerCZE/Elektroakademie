from unittest.mock import patch
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse
from courses.models import BillingRecord, Invoice, InvoiceSequence
from courses.invoices import issue_invoice
from courses.tests.test_invoices import make_order


@override_settings(ALLOWED_HOSTS=['testserver'], EMAIL_TRANSPORT='preview')
class BillingOverviewTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_user('staff', is_staff=True)
        self.order = make_order()
        self.invoice = issue_invoice(self.order.pk)
        self.invoice.pdf_content = b'%PDF-saved-immutable'
        self.invoice.save(update_fields=['pdf_content'])
        self.url = reverse('admin_invoice_pdf', args=[self.order.pk])
        self.list_url = reverse('admin:courses_billingrecord_changelist')
        self.client.force_login(self.staff)

    def grant(self):
        self.staff.user_permissions.add(Permission.objects.get(codename='view_invoice'))

    def test_staff_without_explicit_right_cannot_list_or_open_pdf_even_with_checkout_grant(self):
        session = self.client.session
        session['invoice_order_ids'] = [self.order.pk]
        session.save()
        self.assertEqual(self.client.get(self.list_url).status_code, 403)
        for suffix in ['', '?download=1']:
            self.assertEqual(self.client.get(self.url + suffix).status_code, 404)
        self.assertNotContains(self.client.get(reverse('admin:index')), self.list_url)

    def test_preview_download_and_search_preserve_issued_document(self):
        self.grant()
        before = (self.invoice.number, self.invoice.snapshot, InvoiceSequence.objects.get().last_number)
        with patch('courses.invoices.issue_invoice', side_effect=AssertionError('Must not issue')), patch('courses.invoices.generate_html_pdf', side_effect=AssertionError('Must not render')):
            for suffix, disposition in [('', 'inline'), ('?download=1', 'attachment')]*2:
                response = self.client.get(self.url + suffix)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b'%PDF-saved-immutable')
                self.assertTrue(response['Content-Disposition'].startswith(disposition + ';'))
                self.assertEqual(response['Content-Type'], 'application/pdf')
        response = self.client.get(self.list_url, {'q': self.invoice.number})
        self.assertContains(response, self.invoice.number)
        self.assertContains(response, 'Náhled PDF')
        self.assertContains(response, 'Stáhnout PDF')
        self.assertEqual(len(response.context['cl'].result_list), 1)
        self.invoice.refresh_from_db()
        self.assertEqual(before, (self.invoice.number, self.invoice.snapshot, InvoiceSequence.objects.get().last_number))
        self.assertEqual(Invoice.objects.count(), 1)

    def test_unissued_order_has_clear_state_and_no_links(self):
        self.grant()
        order = make_order(status='pending_payment')
        response = self.client.get(self.list_url, {'q': order.company_name})
        self.assertContains(response, 'Faktura nevystavena')
        self.assertNotContains(response, reverse('admin_invoice_pdf', args=[order.pk]))
        self.assertEqual(self.client.get(reverse('admin_invoice_pdf', args=[order.pk])).status_code, 404)

    def test_missing_saved_pdf_does_not_generate_one(self):
        self.grant()
        self.invoice.pdf_content = b''
        self.invoice.save(update_fields=['pdf_content'])
        self.assertEqual(self.client.get(self.url).status_code, 503)
        self.invoice.refresh_from_db()
        self.assertEqual(bytes(self.invoice.pdf_content), b'')

    def test_columns_do_not_query_per_row(self):
        for _ in range(4):
            issue_invoice(make_order().pk)
        model_admin = admin.site._registry[BillingRecord]
        request = RequestFactory().get('/')
        request.user = self.staff
        with self.assertNumQueries(1):
            for obj in model_admin.get_queryset(request):
                model_admin.invoice_number(obj)
                model_admin.invoice_date(obj)
                model_admin.preview_pdf(obj)
                model_admin.download_pdf(obj)
