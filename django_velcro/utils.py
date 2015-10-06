import inspect
from collections import OrderedDict
from importlib import import_module

from django.apps import apps
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db import models

from .settings import VELCRO_METADATA, VELCRO_METHODS, VELCRO_RELATIONSHIPS


def _startup():
    """
    Add methods to velcro-managed models to add, get, and remove related content.
    """
    if VELCRO_METHODS == False:
        return

    for velcro_type, velcro_type_metadata in VELCRO_METADATA.items():
        for model_metadata in velcro_type_metadata['apps']:
            app_name = model_metadata['app_label']
            model_name = model_metadata['model']
            model = apps.get_model(app_name, model_name)
            model.add_velcro_content = add_related_content
            model.get_velcro_content = get_related_content
            model.get_velcro_content_sametype = get_related_content_sametype
            model.remove_velcro_content = remove_related_content
            model.velcro_url = get_url_of_object

            for related_type in get_related_types(velcro_type):
                def get_velcro_content_for_related_type(
                        self, related_type=related_type, **kwargs):
                    if 'grouped' not in kwargs.keys():
                        kwargs['grouped'] = False
                    related_content = get_related_content(
                        self, related_type, **kwargs)
                    return related_content

                setattr(
                    model,
                    'get_velcro_{}_content'.format(related_type),
                    get_velcro_content_for_related_type
                )

                def get_velcro_content_sametype_for_related_type(
                        self, related_type=related_type):
                    related_content = get_related_content_sametype(
                        self, related_type)
                    return related_content

                setattr(
                    model,
                    'get_velcro_{}_content_sametype'.format(related_type),
                    get_velcro_content_sametype_for_related_type
                )

def _add_or_remove_related_content_difftype(
        object_1, object_2, object_1_velcro_type, object_2_velcro_type,
        add_or_remove):
    """
    Add or remove a relationship between two objects with differing velcro
    types depending on whether 'add_or_remove' equals 'add' or 'remove'.

    If adding a relationship, returns the relationship object and a boolean
    indicating whether the relationship was created.
    """
    relationship_class = get_relationship_class(
        object_1_velcro_type, object_2_velcro_type)
    query = _relationship_query(
        object_1, object_1_velcro_type, object_2, object_2_velcro_type)

    if add_or_remove == 'add':
        return relationship_class.objects.get_or_create(**query)
    elif add_or_remove == 'remove':
        relationship_class.objects.get(**query).delete()

def _add_or_remove_related_content_sametype(
        object_1, object_2, object_1_velcro_type, object_2_velcro_type,
        add_or_remove):
    """
    Add or remove a relationship between two objects with matching velcro
    types depending on whether 'add_or_remove' equals 'add' or 'remove'.

    If adding a relationship, returns the relationship object and a boolean
    indicating whether the relationship was created.
    """
    if object_1 == object_2:
        raise ValueError("{} can't be related to itself.".format(object_1))

    relationship_class = get_relationship_class(
        object_1_velcro_type, object_2_velcro_type)

    query = models.Q(
        content_type_1=ContentType.objects.get_for_model(object_1),
        object_id_1=object_1.id,
        content_type_2=ContentType.objects.get_for_model(object_2),
        object_id_2=object_2.id,
    ) | models.Q(
        content_type_1=ContentType.objects.get_for_model(object_2),
        object_id_1=object_2.id,
        content_type_2=ContentType.objects.get_for_model(object_1),
        object_id_2=object_1.id,
    )

    if add_or_remove == 'add':
        try:
            relationship = relationship_class.objects.get(query)
            created = False
        except:
            params = {
                'content_type_1': ContentType.objects.get_for_model(object_1),
                'object_id_1': object_1.id,
                'content_type_2': ContentType.objects.get_for_model(object_2),
                'object_id_2': object_2.id,
            }
            relationship = relationship_class.objects.create(**params)
            created = True

        return relationship, created
    elif add_or_remove == 'remove':
        relationship_class.objects.get(query).delete()

def _find_dict_in_list(list_, key, value):
    """
    Given a list of dicts, a key, and a value, return the dict with the
    matching key:value pair.
    """
    for idx, dict_ in enumerate(list_):
        if dict_[key] == value:
            return list_[idx]
    return []

def _relationship_query(
        object_1, object_1_velcro_type, object_2, object_2_velcro_type):
    """
    Return a dict for making relationship object queries.
    """
    return {
        '{}_content_type'.format(object_1_velcro_type):
            ContentType.objects.get_for_model(object_1),
        '{}_object_id'.format(object_1_velcro_type): object_1.id,
        '{}_content_type'.format(object_2_velcro_type):
            ContentType.objects.get_for_model(object_2),
        '{}_object_id'.format(object_2_velcro_type): object_2.id,
    }

def add_related_content(object_1, object_2):
    """
    Get or create a relationship between two objects.

    Returns the relationship object and a boolean indicating whether
    the relationship was created.
    """
    object_1_velcro_type = get_velcro_type(object_1)
    object_2_velcro_type = get_velcro_type(object_2)

    kwargs = {
        'add_or_remove': 'add',
        'object_1': object_1,
        'object_2': object_2,
        'object_1_velcro_type': object_1_velcro_type,
        'object_2_velcro_type': object_2_velcro_type,
    }

    if object_1_velcro_type == object_2_velcro_type:
        return _add_or_remove_related_content_sametype(**kwargs)
    else:
        return _add_or_remove_related_content_difftype(**kwargs)

def get_all_velcro_types():
    """
    Return a list of all velcro types defined in 'settings.VELCRO_METADATA'.
    """
    return sorted(list(VELCRO_METADATA.keys()))

def get_velcro_type(object):
    """
    Return the velcro type for a given object based on Django Velcro metadata.
    """
    if inspect.isclass(object):
        object_class = object
    else:
        object_class = object.__class__

    app_label = object_class._meta.app_label.lower()
    model = object_class._meta.object_name

    for velcro_type, velcro_type_metadata in sorted(VELCRO_METADATA.items()):
        for model_metadata in velcro_type_metadata['apps']:
            if (model_metadata['app_label'] == app_label and
                    model_metadata['model'] == model):
                return velcro_type

def get_or_validate_related_types(velcro_type, related_types=None):
    """
    Given a velcro type, return all related types.
    Given a velcro type and a list of related types, return a list of the
    valid related types.
    """
    if related_types:
        related_types = validate_related_types(velcro_type, related_types)
    else:
        related_types = get_related_types(velcro_type)

    return related_types

def _get_related_content_difftype(
        object, velcro_type, related_type, content_type, relationship_class,
        limit):
    """
    Get related content for a related type that differs from the query object's
    type.
    """
    query = {
        '{}_object_id'.format(velcro_type): object.id,
        '{}_content_type'.format(velcro_type): content_type,
    }
    relationships = relationship_class.objects.filter(**query)[:limit]
    related_content_object = '{}_content_object'.format(related_type)

    return [
        getattr(related, related_content_object) for related in
        sorted(relationships, key=lambda x: (
            type(getattr(x, related_content_object)).__name__.lower(),
            getattr(x, related_content_object).__str__().lower()))
    ]

def _get_related_content_sametype(
        object, related_type, content_type, relationship_class, limit):
    """
    Get related content for a related type that matches the query object's
    type.
    """
    query = models.Q(
        content_type_1=content_type,
        object_id_1=object.id,
    ) | models.Q(
        content_type_2=content_type,
        object_id_2=object.id,
    )

    related_content = []
    relationships = [
        (r.content_object_1, r.content_object_2)
        for r in relationship_class.objects.filter(query)[:limit]
    ]

    for relationship in relationships:
        if relationship.index(object) == 0:
            related_content.append(relationship[1])
        else:
            related_content.append(relationship[0])

    return sorted(
        related_content, key=lambda x: (type(x).__name__.lower(), x.__str__()))

def get_related_content(
        object, *related_types, grouped=True, limit=None, velcro_type=None,
        verbose=False):
    """
    Return a dictionary of related content (of given related type(s)) for an
    object. Each key is a related type and its value is a list of related
    content of that type. If no related types are given, related content of
    all types is returned.

    Optionally, return a flattened list of related objects with 'grouped=False'.

    Related content queries can be restricted using the 'limit' argument.
    For example, 'limit=500' restricts results to 500 objects per related type.

    Usage:
        from data.models import Data
        data_set = DataSet.objects.first()
        get_related_content(data_set)                              # all related types
        get_related_content(data_set, 'publication')               # one related type
        get_related_content(data_set, 'publication', 'scientists') # two related types
    """
    if velcro_type is None:
        velcro_type = get_velcro_type(object)

    related_types = get_or_validate_related_types(velcro_type, related_types)
    related_content = {}

    for rt in related_types:
        relationship_class = get_relationship_class(velcro_type, rt)

        content_type = ContentType.objects.get_for_model(object)

        kwargs = {
            'content_type': content_type,
            'limit': limit,
            'object': object,
            'related_type': rt,
            'relationship_class': relationship_class,
        }

        rt_raw = rt
        if verbose:
            rt = plural_velcro_type(rt)

        if velcro_type == rt_raw:
            related_content[rt] = _get_related_content_sametype(**kwargs)
        else:
            related_content[rt] = _get_related_content_difftype(
                velcro_type=velcro_type, **kwargs)

    related_dict = OrderedDict(sorted(related_content.items(),
        key=lambda t: t[0].lower()))

    if grouped:
        return related_dict
    else:
        related_list = list(related_dict.values())
        return [item for sublist in related_list for item in sublist]

def get_related_content_sametype(object, *related_types, velcro_type=None):
    """
    Return a list of related content for an object of the same velcro type as
    that object. This related content of the same type is retrieved indirectly
    via mutually-related content of all other related types. To limit the
    results to specific relationships, specify related types of interest.

    Usage:
        from data.models import Data
        data_set = DataSet.objects.first()
        get_related_content_sametype(data_set)               # via all related types
        get_related_content_sametype(data_set, 'scientists') # via one related type
        get_related_content_sametype(data_set, 't1', 't2')   # via two related types
    """
    if velcro_type is None:
        velcro_type = get_velcro_type(object)

    related_types = get_or_validate_related_types(velcro_type, related_types)
    related_content_sametype = []

    for related_type, related_objects in get_related_content(
            object, *related_types, velcro_type=velcro_type).items():

        for r in related_objects:
            related_content_sametype.extend(
                get_related_content(
                    r, velcro_type, velcro_type=related_type)[velcro_type])

    related_content_sametype = list(set(related_content_sametype))

    if related_content_sametype:
        related_content_sametype.remove(object)

    return sorted(related_content_sametype,
        key=lambda x: (type(x).__name__.lower(), x.__str__().lower()))

def get_related_types(velcro_type):
    """
    Given a velcro type, return all related types.
    """
    related_types = []
    for r in VELCRO_RELATIONSHIPS:
        if velcro_type in r:
            related_types.append(r[1] if r.index(velcro_type) == 0 else r[0])
    return sorted(related_types)

def get_relationship_class(object_1_velcro_type, object_2_velcro_type):
    """
    Given two velcro types, import and return the corresponding relationship
    class.
    """
    relationship_class_name = "{}{}Relationship".format(
        *sorted((object_1_velcro_type.capitalize(),
                 object_2_velcro_type.capitalize())))
    return apps.get_model(__package__, relationship_class_name)

def get_relationship_inlines(velcro_type, related_types=None):
    """
    Given a velcro type and, optionally, a list of related types, import
    and return all relevant relationship inline models for an admin model.
    """
    related_types = get_or_validate_related_types(velcro_type, related_types)
    inlines = []

    for related in related_types:
        inline_class_name = '{}To{}RelationshipInline'.format(
            velcro_type.capitalize(), related.capitalize())
        inline_class = getattr(
            import_module('.admin', package=__package__), inline_class_name)
        globals()[inline_class_name] = inline_class
        inlines.append(inline_class)

        if velcro_type == related:
            inline_class_name = '{}To{}RelationshipReverseInline'.format(
                velcro_type.capitalize(), related.capitalize())
            inline_class = getattr(
                import_module(
                    '.admin', package=__package__), inline_class_name)
            globals()[inline_class_name] = inline_class
            inlines.append(inline_class)

    return inlines

def get_url_of_object(object, velcro_type=None):
    """
    Get the reverse URL for an object.
    If 'velcro_type' is not defined, the velcro type of the object will be
    retrieved.
    """
    if velcro_type is None:
        velcro_type = get_velcro_type(object)

    velcro_type_metadata = VELCRO_METADATA[velcro_type]['apps']
    model_metadata = _find_dict_in_list(
        velcro_type_metadata, 'model', object.__class__.__name__)
    view = model_metadata['view']
    url_args = model_metadata['url_args']
    return reverse(
        view, args=[getattr(object, arg) for arg in url_args])

def has_related_content(object, *related_types, velcro_type=None):
    """
    Return Boolean True/False depending on whether object has related content.
    """
    related_content = get_related_content(
        object, *related_types, limit=1, velcro_type=velcro_type)

    has_related = False

    for related_type, related_objects in related_content.items():
        if related_objects:
            has_related = True
            break

    return has_related

def is_valid_velcro_type(velcro_type):
    """
    Return 'True' if the provided velcro type is defined in
    'settings.VELCRO_METADATA'.
    """
    if velcro_type in VELCRO_METADATA.keys():
        return True

def remove_related_content(object_1, object_2):
    """
    Delete a relationship between two objects.
    """
    object_1_velcro_type = get_velcro_type(object_1)
    object_2_velcro_type = get_velcro_type(object_2)

    kwargs = {
        'add_or_remove': 'remove',
        'object_1': object_1,
        'object_2': object_2,
        'object_1_velcro_type': object_1_velcro_type,
        'object_2_velcro_type': object_2_velcro_type,
    }

    if object_1_velcro_type == object_2_velcro_type:
        _add_or_remove_related_content_sametype(**kwargs)
    else:
        _add_or_remove_related_content_difftype(**kwargs)

def plural_velcro_type(velcro_type):
    """
    Take a velcro type and return the plural version of it.
    """
    velcro_type_metadata = VELCRO_METADATA[velcro_type]
    try:
        plural = velcro_type_metadata['options']['verbose_name_plural']
    except:
        plural = '{}s'.format(velcro_type)

    return(plural)

def singular_velcro_type(velcro_type):
    """
    Take a velcro type and return the singular version of it.
    """
    velcro_type_metadata = VELCRO_METADATA[velcro_type]
    try:
        singular = velcro_type_metadata['options']['verbose_name']
    except:
        singular = velcro_type

    return(singular)

def validate_related_types(velcro_type, related_types):
    """
    Given a velcro type and a list of related types, return a list of the
    valid related types.
    """
    all_related_types = get_related_types(velcro_type)
    valid_related_types = []
    errors = []

    for rt in related_types[:]:
        if not is_valid_velcro_type(rt):
            errors.append("'{}' is not a valid velcro type.".format(rt))
        elif rt not in all_related_types:
            errors.append("'{}' is not a related velcro type for '{}'.".format(
                rt, velcro_type))
        elif rt in valid_related_types:
            errors.append("'{}' is a valid related velcro type, but occurs "
                          "multiple times.".format(rt, velcro_type))
        else:
            valid_related_types.append(rt)

    for e in set(errors):
        print('Warning: {}'.format(e))

    return valid_related_types


_startup()
