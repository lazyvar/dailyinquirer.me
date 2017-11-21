from django.db import models
from django.utils.formats import date_format

from authentication.models import User


class Prompt(models.Model):
    question = models.CharField(max_length=255)
    mail_day = models.DateTimeField()
    override_html = models.TextField(default=None, blank=True, null=True)
    category = models.CharField(max_length=255, default=None, null=True)

    def __str__(self):
        return self.question


class Entry(models.Model):
    content = models.TextField()
    pub_date = models.DateTimeField('date published')
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    prompt = models.ForeignKey(Prompt, on_delete=models.PROTECT)

    def __str__(self):
        date = date_format(self.pub_date,
                           format='SHORT_DATE_FORMAT',
                           use_l10n=True)
        return f"{self.author.email} - {self.prompt.question[:12]} - {date}"
