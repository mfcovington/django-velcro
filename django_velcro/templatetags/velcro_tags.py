from django import template
from django.conf import settings
from django.core.urlresolvers import reverse


register = template.Library()

def find_dict_in_list(list_, key, value):
    for idx, dict_ in enumerate(list_):
        if dict_[key] == value:
            return list_[idx]
    return []

@register.simple_tag(takes_context=True)
def velcro_url(context, object=None, object_type=None):
    """
    Template tag to get the reverse URL for a related object.
    Only requires arguments if 'object' and/or 'object_type' are not defined.
    """
    if object == None:
        object = context['object']
    if object_type == None:
        object_type = context['object_type']

    object_type_metadata = settings.VELCRO_METADATA[object_type]
    model_metadata = find_dict_in_list(object_type_metadata, 'model',
        object.__class__.__name__)
    view = model_metadata['view']
    url_args = model_metadata['url_args']
    return reverse(view, args=[getattr(object, arg) for arg in url_args])
