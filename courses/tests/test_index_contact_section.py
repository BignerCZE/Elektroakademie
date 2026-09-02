from django.test import TestCase
from django.urls import reverse


class IndexContactSectionTests(TestCase):
    def test_contact_section_contains_expected_subject_choices(self):
        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Potřebujete poradit? Rádi vám pomůžeme")
        self.assertContains(response, "Předmět")

        expected_choices = (
            ("obecne-informace", "Obecné informace"),
            ("paragraf-4", "§4 – osoba poučená"),
            ("paragraf-6", "§6 – elektrotechnik"),
            ("paragraf-7", "§7 – vedoucí elektrotechnik"),
            ("individualni-skoleni", "Individuální školení"),
            ("firemni-skoleni", "Firemní školení"),
        )
        for value, label in expected_choices:
            self.assertContains(
                response,
                f'<option value="{value}">{label}</option>',
                html=True,
            )

    def test_contact_section_contains_company_information(self):
        response = self.client.get(reverse("index"))

        self.assertContains(response, "O Elektroakademii")
        self.assertContains(response, "více než 40 lety praxe")
        self.assertContains(response, "REVITEC.cz")
        self.assertContains(response, "HlídáníRevizí.cz")
        self.assertContains(response, "Fakturační údaje")
        self.assertContains(response, "CZ249 44 769")
