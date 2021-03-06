from django import template

from django_velcro.settings import VELCRO_METADATA
from django_velcro.utils import (get_velcro_type, get_related_content,
    get_url_of_object, has_related_content, plural_velcro_type)


register = template.Library()

@register.assignment_tag
def get_velcro_related(obj, verbose=False):
    """
    Get related content and assign it to a variable.

    Example:
        {% get_velcro_related object as related_content %}
    """
    return get_related_content(obj, verbose=verbose)

@register.simple_tag
def velcro_url(related_object, related_type=None):
    """
    Template tag to get the reverse URL for a related object.
    If 'related_type' is not defined, the velcro type of the related object
    will be retrieved.
    """
    return get_url_of_object(obj=related_object, velcro_type=related_type)

@register.inclusion_tag('django_velcro/velcro_link.html')
def velcro_link(related_object, related_type=None):
    """
    Make a link to a related object. Contains entire '<a href>' tag.
    The text is derived from 'related_object.__str__()'.
    If 'related_type' is not defined, the velcro type of the related object
    will be retrieved.
    """
    if related_type is None:
        related_type = get_velcro_type(related_object)

    return {
        'related_object': related_object,
        'related_type': related_type,
    }

@register.filter
def velcro_plural(value, arg=None):
    """
    Take a velcro type and return the plural version of it.
    If an argument is provided, it is place vefore the pluralized velcro type.
    Output is in Title Case.

    Returns 'Publications':
        {{ 'publication' | velcro_plural }}

    Returns 'Related Publications':
        {{ 'publication' | velcro_plural:'related' }}
    """
    plural = plural_velcro_type(value)
    if arg:
        plural = ' '.join([arg, plural])

    return plural.title()

@register.inclusion_tag('django_velcro/related_content.html')
def velcro_related(obj, label=None, label_tag='h3', prefix=None):
    """
    Template tag to list related content organized by related type.

    Default label is '<h3>Related Content</h3>'. Use 'label' and 'label_tag'
    arguments to customize the label.

    Use the 'prefix' argument to prepend related type names with a word
    (e.g., 'Related').

    Basic usage example:
        {% velcro_related obj %}

    Custom label example:
        {% velcro_related obj label='Related Junk' label_tag='h1' prefix='Related' %}

    The resulting list of related content can be styled with CSS using the
    following classes:
      - .related-content-label
      - .related-type
      - .related-object
    """
    return {
        'has_related_content': has_related_content(obj),
        'related_content': get_related_content(obj),
        'related_content_label': label,
        'related_content_label_tag': label_tag,
        'related_content_prefix': prefix,
    }
