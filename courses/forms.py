from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError

class ParticipantForm(forms.Form):
    first_name = forms.CharField(
        label="Jméno",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Jan",
                "autocomplete": "given-name",
            }
        ),
    )

    last_name = forms.CharField(
        label="Příjmení",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Novák",
                "autocomplete": "family-name",
            }
        ),
    )

    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "jan.novak@email.cz",
                "autocomplete": "email",
            }
        ),
    )


class BillingForm(forms.Form):
    ico = forms.CharField(
        label="IČO",
        required=False,
        max_length=8,
        widget=forms.TextInput(
            attrs={
                "placeholder": "IČO (nepovinné)",
                "inputmode": "numeric",
                "maxlength": "8",
                "autocomplete": "organization",
            }
        ),
    )

    dic = forms.CharField(
        label="DIČ",
        required=False,
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "placeholder": "DIČ (nepovinné)",
            }
        ),
    )

    company_name = forms.CharField(
        label="Název firmy nebo jméno",
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Název firmy nebo jméno *",
                "autocomplete": "organization",
            }
        ),
    )

    street = forms.CharField(
        label="Ulice a č.p.",
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Ulice a č.p. *",
                "autocomplete": "street-address",
            }
        ),
    )

    city = forms.CharField(
        label="Město",
        max_length=120,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Město *",
                "autocomplete": "address-level2",
            }
        ),
    )

    zip_code = forms.CharField(
        label="PSČ",
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "placeholder": "PSČ *",
                "autocomplete": "postal-code",
            }
        ),
    )

    country = forms.ChoiceField(
        label="Země",
        choices=[
            ("CZ", "Česká republika"),
            ("SK", "Slovensko"),
        ],
        initial="CZ",
    )

    contact_first_name = forms.CharField(
        label="Jméno kontaktní osoby",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Jméno *",
                "autocomplete": "given-name",
            }
        ),
    )

    contact_last_name = forms.CharField(
        label="Příjmení kontaktní osoby",
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Příjmení *",
                "autocomplete": "family-name",
            }
        ),
    )

    contact_phone_prefix = forms.CharField(
        label="Předvolba",
        max_length=8,
        initial="+420",
        widget=forms.TextInput(
            attrs={
                "placeholder": "+420",
                "inputmode": "tel",
                "autocomplete": "tel-country-code",
            }
        ),
    )

    contact_phone = forms.CharField(
        label="Telefonní číslo",
        max_length=30,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Telefonní číslo *",
                "inputmode": "tel",
                "autocomplete": "tel-national",
            }
        ),
    )

    contact_email = forms.EmailField(
        label="E-mail kontaktní osoby",
        widget=forms.EmailInput(
            attrs={
                "placeholder": "E-mail *",
                "autocomplete": "email",
            }
        ),
    )

    note = forms.CharField(
        label="Poznámka",
        required=False,
        widget=forms.Textarea(
            attrs={
                "placeholder": "Poznámka k objednávce (nepovinné)",
            }
        ),
    )

    def clean_ico(self):
        ico = self.cleaned_data.get("ico", "").strip()

        if not ico:
            return ""

        normalized_ico = "".join(character for character in ico if character.isdigit())

        if len(normalized_ico) != 8:
            raise forms.ValidationError("IČO musí obsahovat přesně 8 číslic.")

        return normalized_ico

    def clean_contact_phone_prefix(self):
        prefix = self.cleaned_data.get("contact_phone_prefix", "").strip()

        if not prefix:
            raise forms.ValidationError("Vyplňte telefonní předvolbu.")

        normalized_prefix = prefix.replace(" ", "")

        if not normalized_prefix.startswith("+"):
            normalized_prefix = f"+{normalized_prefix}"

        if not normalized_prefix[1:].isdigit():
            raise forms.ValidationError("Telefonní předvolba není platná.")

        return normalized_prefix

    def clean_contact_phone(self):
        phone = self.cleaned_data.get("contact_phone", "").strip()

        normalized_phone = (
            phone.replace(" ", "")
            .replace("-", "")
            .replace("/", "")
        )

        if not normalized_phone.isdigit():
            raise forms.ValidationError("Telefonní číslo může obsahovat pouze číslice.")

        if len(normalized_phone) < 7:
            raise forms.ValidationError("Telefonní číslo je příliš krátké.")

        return normalized_phone
    

class ParticipantActivationForm(forms.Form):
    password1 = forms.CharField(
        label="Heslo",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Zadejte heslo",
                "autocomplete": "new-password",
            }
        ),
    )

    password2 = forms.CharField(
        label="Potvrzení hesla",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Zadejte heslo znovu",
                "autocomplete": "new-password",
            }
        ),
    )

    birth_date = forms.DateField(
        label="Datum narození",
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "autocomplete": "bday",
            }
        ),
    )

    birth_place = forms.CharField(
        label="Místo narození",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Místo narození",
            }
        ),
    )

    permanent_address = forms.CharField(
        label="Trvalé bydliště",
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Ulice, číslo, město, PSČ",
                "autocomplete": "street-address",
            }
        ),
    )

    employer_name = forms.CharField(
        label="Zaměstnavatel",
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Název zaměstnavatele",
                "autocomplete": "organization",
            }
        ),
    )

    employer_address = forms.CharField(
        label="Adresa zaměstnavatele",
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Adresa zaměstnavatele",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                "Zadaná hesla se neshodují."
            )

        return password2

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password1")

        if password:
            try:
                password_validation.validate_password(
                    password,
                    user=self.user,
                )
            except ValidationError as error:
                self.add_error(
                    "password1",
                    error,
                )

        return cleaned_data