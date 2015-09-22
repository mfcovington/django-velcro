from django import template
from django.core.urlresolvers import reverse

from django_velcro.settings import VELCRO_METADATA
from django_velcro.utils import get_related_content


register = template.Library()

def find_dict_in_list(list_, key, value):
    for idx, dict_ in enumerate(list_):
        if dict_[key] == value:
            return list_[idx]
    return []

@register.simple_tag(takes_context=True)
def velcro_url(context, related_object=None, related_type=None):
    """
    Template tag to get the reverse URL for a related object.
    Only requires arguments if 'related_object' and/or 'related_type'
    are not defined.
    """
    if related_object is None:
        related_object = context['related_object']
    if related_type is None:
        related_type = context['related_type']

    related_type_metadata = VELCRO_METADATA[related_type]
    related_model_metadata = find_dict_in_list(
        related_type_metadata, 'model', related_object.__class__.__name__)
    view = related_model_metadata['view']
    url_args = related_model_metadata['url_args']
    return reverse(
        view, args=[getattr(related_object, arg) for arg in url_args])

@register.inclusion_tag('django_velcro/related_content.html')
def velcro_related(object):
    """
    Template tag to list related content organized by related type.
    """
    related_content = get_related_content(object)
    return {'related_content': related_content}
