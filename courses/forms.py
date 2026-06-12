from django import forms


class ParticipantForm(forms.Form):
    first_name = forms.CharField(
        label="Jméno",
        max_length=100,
        widget=forms.TextInput(attrs={
            "placeholder": "Jan"
        })
    )

    last_name = forms.CharField(
        label="Příjmení",
        max_length=100,
        widget=forms.TextInput(attrs={
            "placeholder": "Novák"
        })
    )

    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={
            "placeholder": "jan.novak@email.cz"
        })
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