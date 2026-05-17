from django.contrib import admin

from core.models import Prompt, Entry


class EntryAdmin(admin.ModelAdmin):
    fields = ('pub_date', 'author', 'prompt')


admin.site.register(Prompt)
admin.site.register(Entry, EntryAdmin)
