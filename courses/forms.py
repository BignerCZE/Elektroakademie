from django import forms


class ParticipantForm(forms.Form):
    first_name = forms.CharField(
        label="Jméno *",
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Jméno *"}),
    )

    last_name = forms.CharField(
        label="Příjmení *",
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Příjmení *"}),
    )

    title = forms.CharField(
        label="Titul",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Titul (nepovinné)"}),
    )

    email = forms.EmailField(
        label="E-mail *",
        widget=forms.EmailInput(attrs={"placeholder": "E-mail *"}),
    )

    phone_prefix = forms.CharField(
        label="Předvolba",
        initial="+420",
        widget=forms.TextInput(attrs={"placeholder": "+420"}),
    )

    phone = forms.CharField(
        label="Telefon *",
        widget=forms.TextInput(attrs={"placeholder": "123 456 789"}),
    )


class BillingForm(forms.Form):
    ico = forms.CharField(
        label="IČ",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "IČ (nepovinné)"}),
    )

    dic = forms.CharField(
        label="DIČ",
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "DIČ (nepovinné)"}),
    )

    company_name = forms.CharField(
        label="Název firmy nebo jméno *",
        widget=forms.TextInput(attrs={"placeholder": "Název firmy nebo jméno *"}),
    )

    street = forms.CharField(
        label="Ulice a č.p. *",
        widget=forms.TextInput(attrs={"placeholder": "Ulice a č.p. *"}),
    )

    city = forms.CharField(
        label="Město *",
        widget=forms.TextInput(attrs={"placeholder": "Město *"}),
    )

    zip_code = forms.CharField(
        label="PSČ *",
        widget=forms.TextInput(attrs={"placeholder": "PSČ *"}),
    )

    country = forms.ChoiceField(
        label="Země *",
        choices=[
            ("CZ", "Česká republika"),
            ("SK", "Slovensko"),
        ],
        initial="CZ",
    )

    contact_person = forms.BooleanField(
        label="Chci vyplnit kontaktní osobu",
        required=False,
    )

    note = forms.CharField(
        label="Poznámka",
        required=False,
        widget=forms.Textarea(attrs={"placeholder": "Poznámka k objednávce (nepovinné)"}),
    )