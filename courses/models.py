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
    name = models.CharField(max_length=255, verbose_name="Název kategorie")
    slug = models.SlugField(max_length=100, verbose_name="Slug")
    questions_per_quiz = models.PositiveIntegerField(
        default=1,
        verbose_name="Počet otázek v testu",
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Pořadí")

    class Meta:
        ordering = ["course", "order", "name"]
        verbose_name = "Kategorie otázek"
        verbose_name_plural = "Kategorie otázek"
        unique_together = ("course", "slug")

    def __str__(self):
        return f"{self.course} – {self.name}"


class Question(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
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
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text


class Payment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=6, decimal_places=2)
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

    course_type = models.CharField(max_length=10, choices=COURSE_CHOICES)
    total_price = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pending_payment",
    )

    ico = models.CharField(max_length=20, blank=True)
    dic = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=255)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=120)
    note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Objednávka #{self.id} – {self.get_course_type_display()}"


class OrderParticipant(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


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

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

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
    passed = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user} - {self.course} - {self.started_at}"

    @property
    def duration(self):
        if self.submitted_at:
            return self.submitted_at - self.started_at
        return timezone.now() - self.started_at


class QuizAttemptQuestion(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="attempt_questions",
    )
    question = models.ForeignKey(Question, on_delete=models.PROTECT)
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