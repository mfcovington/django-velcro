from collections import OrderedDict
from importlib import import_module

from django.apps import apps
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .settings import VELCRO_METADATA, VELCRO_RELATIONSHIPS


def _relationship_query(object_1, object_1_type, object_2, object_2_type):
    """
    Return a dict for making relationship object queries.
    """
    return {
        '{}_content_type'.format(object_1_type):
            ContentType.objects.get_for_model(object_1),
        '{}_object_id'.format(object_1_type): object_1.id,
        '{}_content_type'.format(object_2_type):
            ContentType.objects.get_for_model(object_2),
        '{}_object_id'.format(object_2_type): object_2.id,
    }

def add_related_content(object_1, object_2):
    """
    Get or create a relationship between two objects.

    Returns the relationship object and a boolean indicating whether
    the relationship was created.
    """
    object_1_type = get_object_type(object_1)
    object_2_type = get_object_type(object_2)

    relationship_class = get_relationship_class(object_1_type, object_2_type)
    query = _relationship_query(object_1, object_1_type, object_2,
        object_2_type)

    return relationship_class.objects.get_or_create(**query)

def get_all_object_types():
    """
    Return a list of all object types defined in 'settings.VELCRO_METADATA'.
    """
    return sorted(list(VELCRO_METADATA.keys()))

def get_object_type(object):
    """
    Return the object type for a given object based on Django Velcro metadata.
    """
    app_label = object.__class__._meta.app_label.lower()
    model = object.__class__._meta.object_name

    for object_type, type_metadata in sorted(VELCRO_METADATA.items()):
        for model_metadata in type_metadata['apps']:
            if (model_metadata['app_label'] == app_label and
                    model_metadata['model'] == model):
                return object_type

def get_or_validate_related_types(object_type, related_types=None):
    """
    Given an object type, return all related types.
    Given an object type and a list of related types, return a list of the
    valid related types.
    """
    if related_types:
        related_types = validate_related_types(object_type, related_types)
    else:
        related_types = get_related_types(object_type)

    return related_types

def get_related_content(object, *related_types, grouped=True, limit=None,
    object_type=None):
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
        get_related_content(data_set)                               # all related types
        get_related_content(data_set, 'publications')               # one related type
        get_related_content(data_set, 'publications', 'scientists') # two related types
    """
    if object_type is None:
        object_type = get_object_type(object)

    related_types = get_or_validate_related_types(object_type, related_types)
    related_content = {}

    for rt in related_types:
        relationship_class = get_relationship_class(object_type, rt)

        content_type = ContentType.objects.get_for_model(object)
        query = {
            '{}_object_id'.format(object_type): object.id,
            '{}_content_type'.format(object_type): content_type,
        }
        relationships = relationship_class.objects.filter(**query)[:limit]
        related_content_object = '{}_content_object'.format(rt)

        related_content[rt] = [getattr(related, related_content_object)
            for related in sorted(relationships,
                key=lambda x: (
                    type(getattr(x, related_content_object)).__name__.lower(),
                    getattr(x, related_content_object).__str__().lower()))]

    related_dict = OrderedDict(sorted(related_content.items(),
        key=lambda t: t[0].lower()))

    if grouped:
        return related_dict
    else:
        related_list = list(related_dict.values())
        return [item for sublist in related_list for item in sublist]

def get_related_content_sametype(object, *related_types, object_type=None):
    """
    Return a list of related content for an object of the same type as that
    object. This related content of the same type is retrieved indirectly via
    mutually-related content of all other related types. To limit the results
    to specific relationships, specify related types of interest.

    Usage:
        from data.models import Data
        data_set = DataSet.objects.first()
        get_related_content_sametype(data_set)               # via all related types
        get_related_content_sametype(data_set, 'scientists') # via one related type
        get_related_content_sametype(data_set, 't1', 't2')   # via two related types
    """
    if object_type is None:
        object_type = get_object_type(object)

    related_types = get_or_validate_related_types(object_type, related_types)
    related_content_sametype = []

    for related_type, related_objects in get_related_content(object,
            *related_types, object_type=object_type).items():

        for r in related_objects:
            related_content_sametype.extend(
                get_related_content(r, object_type,
                    object_type=related_type)[object_type])

    related_content_sametype = list(set(related_content_sametype))

    if related_content_sametype:
        related_content_sametype.remove(object)

    return sorted(related_content_sametype,
        key=lambda x: (type(x).__name__.lower(), x.__str__().lower()))

def get_related_types(object_type):
    """
    Given an object type, return all related types.
    """
    related_types = []
    for r in VELCRO_RELATIONSHIPS:
        if object_type in r:
            related_types.extend([related for related in r
                if related != object_type])
    return sorted(related_types)

def get_relationship_class(object_1_type, object_2_type):
    """
    Given two object types, import and return the corresponding relationship
    class.
    """
    relationship_class_name = "{}{}Relationship".format(
        *sorted((object_1_type.capitalize(), object_2_type.capitalize())))
    return apps.get_model(__package__, relationship_class_name)

def get_relationship_inlines(object_type, related_types=None):
    """
    Given an object type and, optionally, a list of related types, import
    and return all relevant relationship inline models for an admin model.
    """
    related_types = get_or_validate_related_types(object_type, related_types)
    inlines = []

    for related in related_types:
        inline_class_name = '{}To{}RelationshipInline'.format(object_type.capitalize(), related.capitalize())
        inline_class = getattr(import_module('.admin', package=__package__),
            inline_class_name)
        globals()[inline_class_name] = inline_class
        inlines.append(inline_class)

    return inlines

def has_related_content(object, *related_types, object_type=None):
    """
    Return Boolean True/False depending on whether object has related content.
    """
    related_content = get_related_content(object, *related_types, limit=1,
        object_type=object_type)

    has_related = False

    for related_type, related_objects in related_content.items():
        if related_objects:
            has_related = True
            break

    return has_related

def is_valid_object_type(object_type):
    """
    Return 'True' if the provided object type is defined in
    'settings.VELCRO_METADATA'.
    """
    if object_type in VELCRO_METADATA.keys():
        return True

def remove_related_content(object_1, object_2):
    """
    Delete a relationship between two objects.
    """
    object_1_type = get_object_type(object_1)
    object_2_type = get_object_type(object_2)

    relationship_class = get_relationship_class(object_1_type, object_2_type)
    query = _relationship_query(object_1, object_1_type, object_2,
        object_2_type)

    relationship_class.objects.get(**query).delete()

def validate_related_types(object_type, related_types):
    """
    Given an object type and a list of related types, return a list of the
    valid related types.
    """
    all_related_types = get_related_types(object_type)
    valid_related_types = []
    errors = []

    for rt in related_types[:]:
        if not is_valid_object_type(rt):
            errors.append("'{}' is not a valid object type.".format(rt))
        elif rt not in all_related_types:
            errors.append("'{}' is not a related object type for '{}'.".format(
                rt, object_type))
        elif rt in valid_related_types:
            errors.append("'{}' is a valid related object type, but occurs " \
                "multiple times.".format(rt, object_type))
        else:
            valid_related_types.append(rt)

    for e in set(errors):
        print('Warning: {}'.format(e))

    return valid_related_types
