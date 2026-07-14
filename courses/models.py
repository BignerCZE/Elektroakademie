import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CustomUser(AbstractUser):
    is_paid = models.BooleanField(default=False)
    passed_quiz = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    video_url = models.URLField()

    def __str__(self):
        return self.title


class QuestionCategory(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="question_categories",
        verbose_name="Kurz",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Název kategorie",
    )
    slug = models.SlugField(
        max_length=100,
        verbose_name="Slug",
    )
    questions_per_quiz = models.PositiveIntegerField(
        default=1,
        verbose_name="Počet otázek v testu",
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="Pořadí",
    )

    class Meta:
        ordering = ["course", "order", "name"]
        verbose_name = "Kategorie otázek"
        verbose_name_plural = "Kategorie otázek"
        unique_together = ("course", "slug")

    def __str__(self):
        return f"{self.course} – {self.name}"


class Question(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
    )
    category = models.ForeignKey(
        QuestionCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="questions",
        verbose_name="Kategorie",
    )
    text = models.CharField(max_length=255)

    def __str__(self):
        return self.text


class Choice(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
    )
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class Payment(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
    )
    amount = models.DecimalField(
        max_digits=6,
        decimal_places=2,
    )
    is_successful = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.course}"


class Order(models.Model):
    COURSE_CHOICES = [
        ("4", "§4 – osoba poučená"),
        ("6", "§6 – elektrotechnik"),
        ("7", "§7 – vedoucí elektrotechnik"),
    ]

    STATUS_CHOICES = [
        ("pending_payment", "Čeká na platbu"),
        ("paid", "Zaplaceno"),
    ]

    course_type = models.CharField(
        max_length=10,
        choices=COURSE_CHOICES,
    )
    total_price = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending_payment",
    )

    ico = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="IČO",
    )
    dic = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="DIČ",
    )
    company_name = models.CharField(
        max_length=255,
        verbose_name="Název firmy / jméno objednatele",
    )
    street = models.CharField(
        max_length=255,
        verbose_name="Ulice a číslo",
    )
    city = models.CharField(
        max_length=120,
        verbose_name="Město",
    )
    zip_code = models.CharField(
        max_length=20,
        verbose_name="PSČ",
    )
    country = models.CharField(
        max_length=120,
        default="Česká republika",
        verbose_name="Země",
    )

    contact_first_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Jméno kontaktní osoby",
    )

    contact_last_name = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Příjmení kontaktní osoby",
    )

    contact_phone_prefix = models.CharField(
        max_length=8,
        default="+420",
        verbose_name="Telefonní předvolba",
    )

    contact_phone = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="Telefonní číslo",
    )

    contact_email = models.EmailField(
        blank=True,
        default="",
        verbose_name="E-mail kontaktní osoby",
    )

    note = models.TextField(
        blank=True,
        verbose_name="Poznámka",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __str__(self):
        return (
            f"Objednávka #{self.id} – "
            f"{self.get_course_type_display()}"
        )

    @property
    def contact_full_name(self):
        return f"{self.contact_first_name} {self.contact_last_name}".strip()

    @property
    def contact_full_phone(self):
        return f"{self.contact_phone_prefix} {self.contact_phone}".strip()


class OrderParticipant(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="participants",
        verbose_name="Objednávka",
    )

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_participations",
        verbose_name="Uživatelský účet",
    )

    first_name = models.CharField(
        max_length=100,
        verbose_name="Jméno",
    )

    last_name = models.CharField(
        max_length=100,
        verbose_name="Příjmení",
    )

    email = models.EmailField(
        verbose_name="E-mail",
    )

    registration_number = models.CharField(
        max_length=30,
        unique=True,
        null=True,
        blank=True,
        verbose_name="Evidenční číslo",
    )

    activation_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Aktivační token",
    )

    activation_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Datum odeslání aktivačního odkazu",
    )

    activation_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Datum dokončení aktivace",
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    

class RegistrationNumberSequence(models.Model):
    course_type = models.CharField(
        max_length=10,
        choices=Order.COURSE_CHOICES,
        verbose_name="Typ kurzu",
    )

    year = models.PositiveIntegerField(
        verbose_name="Rok",
    )

    month = models.PositiveSmallIntegerField(
        verbose_name="Měsíc",
    )

    last_number = models.PositiveIntegerField(
        default=0,
        verbose_name="Poslední pořadové číslo",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "course_type",
                    "year",
                    "month",
                ],
                name="unique_registration_sequence_month",
            ),
        ]
        verbose_name = "Řada evidenčních čísel"
        verbose_name_plural = "Řady evidenčních čísel"

    def __str__(self):
        return (
            f"§{self.course_type} – "
            f"{self.year}/{self.month:02d} – "
            f"{self.last_number}"
        )

class ParticipantProfile(models.Model):
    participant = models.OneToOneField(
        OrderParticipant,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="Účastník",
    )

    birth_date = models.DateField(
        verbose_name="Datum narození",
    )

    birth_place = models.CharField(
        max_length=150,
        verbose_name="Místo narození",
    )

    permanent_address = models.CharField(
        max_length=255,
        verbose_name="Trvalé bydliště",
    )

    employer_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Zaměstnavatel",
    )

    employer_address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Adresa zaměstnavatele",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Vytvořeno",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Profil účastníka"
        verbose_name_plural = "Profily účastníků"

    def __str__(self):
        return (
            f"{self.participant.registration_number} – "
            f"{self.participant.first_name} "
            f"{self.participant.last_name}"
        )


class QuizAttempt(models.Model):
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_SUBMITTED = "submitted"

    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, "Rozpracovaný"),
        (STATUS_SUBMITTED, "Odeslaný"),
    ]

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )

    attempt_number = models.PositiveIntegerField(default=1)

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_IN_PROGRESS,
    )

    total_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)

    score_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    passed = models.BooleanField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return (
            f"{self.user} - {self.course} - "
            f"pokus č. {self.attempt_number}"
        )

    @property
    def duration(self):
        if self.submitted_at:
            return self.submitted_at - self.started_at

        return timezone.now() - self.started_at

    @property
    def duration_minutes(self):
        duration = self.duration
        total_seconds = int(duration.total_seconds())

        if total_seconds < 60:
            return "< 1 min"

        minutes = total_seconds // 60
        seconds = total_seconds % 60

        if seconds >= 30:
            minutes += 1

        return f"{minutes} min"
    
class Certificate(models.Model):
    participant = models.OneToOneField(
        OrderParticipant,
        on_delete=models.PROTECT,
        related_name="certificate",
        verbose_name="Účastník",
    )

    quiz_attempt = models.OneToOneField(
        QuizAttempt,
        on_delete=models.PROTECT,
        related_name="certificate",
        verbose_name="Úspěšný pokus testu",
    )

    certificate_number = models.CharField(
        max_length=30,
        unique=True,
        verbose_name="Číslo osvědčení",
    )

    issued_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="Datum vystavení",
    )

    valid_until = models.DateField(
        verbose_name="Platnost do",
    )

    pdf_file = models.FileField(
        upload_to="certificates/%Y/%m/",
        null=True,
        blank=True,
        verbose_name="PDF soubor",
    )

    verification_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Ověřovací token",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Vytvořeno",
    )

    class Meta:
        ordering = ["-issued_at"]
        verbose_name = "Osvědčení"
        verbose_name_plural = "Osvědčení"

    def __str__(self):
        return (
            f"{self.certificate_number} – "
            f"{self.participant.first_name} "
            f"{self.participant.last_name}"
        )


class QuizAttemptQuestion(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="attempt_questions",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,
    )
    selected_choice = models.ForeignKey(
        Choice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]
        unique_together = ("attempt", "question")

    def __str__(self):
        return f"{self.attempt} - {self.question}"