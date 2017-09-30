from django.db import models
from authentication.models import User


class Prompt(models.Model):
    question = models.CharField(max_length=255)
    mail_day = models.DateTimeField()
    override_html = models.TextField(null=True)

    def __str__(self):
        return self.question


class Entry(models.Model):
    content = models.TextField()
    pub_date = models.DateTimeField('date published')
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    prompt = models.ForeignKey(Prompt, on_delete=models.PROTECT)

    def __str__(self):
        return self.content[:16]
