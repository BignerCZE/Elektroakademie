from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class ElektroakademiePasswordValidator:
    """
    Heslo musí mít alespoň 8 znaků a splnit alespoň
    dvě ze tří podmínek:

    - obsahuje malé písmeno,
    - obsahuje velké písmeno,
    - obsahuje číslici.
    """

    def validate(self, password, user=None):
        errors = []

        if len(password) < 8:
            errors.append(
                ValidationError(
                    _(
                        "Heslo musí obsahovat alespoň 8 znaků."
                    ),
                    code="password_too_short",
                )
            )

        conditions_met = sum(
            [
                any(character.islower() for character in password),
                any(character.isupper() for character in password),
                any(character.isdigit() for character in password),
            ]
        )

        if conditions_met < 2:
            errors.append(
                ValidationError(
                    _(
                        "Heslo musí obsahovat alespoň dvě z těchto "
                        "tří možností: malé písmeno, velké písmeno "
                        "a číslo."
                    ),
                    code="password_not_complex_enough",
                )
            )

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _(
            "Heslo musí mít alespoň 8 znaků a obsahovat alespoň "
            "dvě z těchto tří možností: malé písmeno, velké "
            "písmeno a číslo."
        )