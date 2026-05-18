from django.db import models
from django.utils import timezone
from django.utils.formats import date_format

from authentication.models import User
from core.mixins import TimestampedModel


class Prompt(TimestampedModel):
    question = models.CharField(max_length=255)
    mail_day = models.DateTimeField()
    override_html = models.TextField(default=None, blank=True, null=True)
    category = models.CharField(max_length=255, default=None, null=True)

    def __str__(self):
        return self.question


class Entry(TimestampedModel):
    content = models.TextField()
    pub_date = models.DateTimeField('date published')
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    prompt = models.ForeignKey(Prompt, on_delete=models.PROTECT)
    archived_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        # Serves the home page's filter(author=...).order_by('-pub_date').
        indexes = [
            models.Index(fields=['author', '-pub_date']),
        ]

    def __str__(self):
        date = date_format(self.pub_date,
                           format='SHORT_DATE_FORMAT',
                           use_l10n=True)
        return f"{self.author.email} - {self.prompt.question[:12]} - {date}"


class PromptSend(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'prompt'],
                name='unique_user_prompt_send'),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.prompt.question[:12]}"
