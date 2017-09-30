from django.db import models
from authentication.models import User


class Entry(models.Model):
    content = models.TextField()
    pub_date = models.DateTimeField('date published')
    author = models.ForeignKey(User, on_delete=models.PROTECT)
