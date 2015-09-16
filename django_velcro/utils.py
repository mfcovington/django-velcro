from collections import OrderedDict
from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.db import models


def get_all_object_types(relationships=settings.VELCRO_RELATIONSHIPS):
    """
    Return a list of all object types defined in 'settings.VELCRO_RELATIONSHIPS'.
    """
    return sorted(set([object_type for r in relationships for object_type in r]))

def get_object_type(object, velcro_metadata=settings.VELCRO_METADATA):
    """
    Return the object type for a given object based on Django Velcro metadata.
    """
    app_label = object.__class__._meta.app_label.lower()
    model = object.__class__._meta.object_name

    for object_type, type_metadata in sorted(velcro_metadata.items()):
        for model_metadata in type_metadata:
            if (model_metadata['app_label'] == app_label and
                    model_metadata['model'] == model):
                return object_type

def get_related_content(object, *related_types, grouped=True, limit=None,
    object_type=None, relationships=settings.VELCRO_RELATIONSHIPS):
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

    if not related_types:
        related_types = validate_and_process_related(object_type, relationships)

    related_content = {}

    for rt in related_types:
        relationship_class_name = "{}{}Relationship".format(
            *sorted((object_type.capitalize(), rt.capitalize())))
        relationship_class = apps.get_model(__package__,
            relationship_class_name)

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

def get_related_content_sametype(object, *related_types, object_type=None,
    relationships=settings.VELCRO_RELATIONSHIPS):
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
    """
    if object_type is None:
        object_type = get_object_type(object)

    if not related_types:
        related_types = validate_and_process_related(object_type, relationships)

    related_content_sametype = []

    for related_type, related_objects in get_related_content(object,
            *related_types, object_type=object_type,
            relationships=relationships).items():

        for r in related_objects:
            related_content_sametype.extend(
                get_related_content(r, object_type, object_type=related_type,
                    relationships=relationships)[object_type])

    related_content_sametype = list(set(related_content_sametype))

    if related_content_sametype:
        related_content_sametype.remove(object)

    return sorted(related_content_sametype,
        key=lambda x: (type(x).__name__.lower(), x.__str__().lower()))

def get_relationship_inlines(object_type, relationships=None, related_types=None):
    """
    Import relevant relationship inline models for an admin model.

    Usage:

        # settings.py:

        VELCRO_RELATIONSHIPS = [
            ('data', 'publications'),
            ('data', 'scientists'),
            ('publications', 'scientists'),
        ]

        # data/admin.py:

        @admin.register(Data, DataSet)
        class DataAdmin(GenericAdminModelAdmin):
            if 'django_velcro' in settings.INSTALLED_APPS:
                from django_velcro.utils import get_relationship_inlines
                inlines = get_relationship_inlines('data',
                    relationships=settings.VELCRO_RELATIONSHIPS)


    Equivalent To:

        # data/admin.py:

        from django_velcro.admin import (DataToPublicationsRelationshipInline,
            DataToScientistsRelationshipInline)

        @admin.register(Data, DataSet)
        class DataAdmin(GenericAdminModelAdmin):
            inlines = [
                DataToPublicationsRelationshipInline,
                DataToScientistsRelationshipInline
            ]
    """
    related_types = validate_and_process_related(object_type, relationships,
        related_types)

    inlines = []
    for related in related_types:
        inline_class_name = '{}To{}RelationshipInline'.format(object_type.capitalize(), related.capitalize())
        inline_class = getattr(import_module('.admin', package=__package__),
            inline_class_name)
        globals()[inline_class_name] = inline_class
        inlines.append(inline_class)

    return inlines

def is_valid_object_type(object_type, relationships=settings.VELCRO_RELATIONSHIPS):
    """
    Return 'True' if the provided object type is defined in 'settings.VELCRO_RELATIONSHIPS'.
    """
    if object_type in [object_type for r in relationships for object_type in r]:
        return True

def validate_and_process_related(object_type, relationships=None, related_types=None):
    """
    Validate that either 'relationships' or 'related_types' has content.
    If 'relationships' is used, extract, sort, and return relevant 'related_types'.
    If 'related_types' is used, return contents in their original order.
    """
    if relationships is None:
        relationships = []

    if related_types is None:
        related_types = []

    if (relationships and related_types) or (not relationships and not related_types):
        raise ValueError("Either 'relationships' or 'related_types' must be defined.")

    if relationships:
        for r in relationships:
            if object_type in r:
                related_types.extend([related for related in r
                    if related != object_type])
        related_types = sorted(related_types)

    return related_types
