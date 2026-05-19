from django import template
from django.urls import reverse
from django.utils.formats import date_format

register = template.Library()


def build_trail(page, entry=None, prompt=None):
    """Return the breadcrumb trail for a page.

    Each crumb is a dict ``{'label': str, 'url': str | None}``. Ancestor
    crumbs carry a url; the final (current-page) crumb has ``url=None``.
    """
    writing = {'label': 'Your writing', 'url': reverse('dash')}
    archived = {'label': 'Archived', 'url': reverse('archived_entries')}
    prompts = {'label': 'Prompts', 'url': reverse('prompts')}

    if page == 'dashboard':
        return [{**writing, 'url': None}]
    if page == 'settings':
        return [writing, {'label': 'Settings', 'url': None}]
    if page == 'archived':
        return [writing, {'label': 'Archived', 'url': None}]
    if page == 'about':
        return [{'label': 'About', 'url': None}]
    if page == 'prompts':
        return [{**prompts, 'url': None}]
    if page == 'prompt':
        if prompt is None:
            raise ValueError("sitenav page 'prompt' requires a prompt argument")
        return [prompts, {
            'label': date_format(prompt.mail_day, 'M j, Y'),
            'url': None,
        }]
    if page == 'entry':
        if entry is None:
            raise ValueError("sitenav page 'entry' requires an entry argument")
        crumbs = [writing]
        if entry.archived_at:
            crumbs.append(archived)
        crumbs.append({
            'label': date_format(entry.pub_date, 'M j, Y'),
            'url': None,
        })
        return crumbs
    raise ValueError(f"unknown sitenav page: {page!r}")


@register.inclusion_tag('core/_sitenav.html', takes_context=True)
def sitenav(context, page, entry=None, prompt=None):
    return {
        'crumbs': build_trail(page, entry=entry, prompt=prompt),
        'user': context['user'],
    }
