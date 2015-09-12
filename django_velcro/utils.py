from collections import OrderedDict
from importlib import import_module

from django.conf import settings
from django.contrib import admin
from django.db import models

from genericadmin.admin import GenericAdminModelAdmin


def generic_admin_base(object_type, relationships=None, related_types=None):
    """
    Create an abstract base class that has inlines for related content
    and extends GenericAdminModelAdmin (from 'genericadmin.admin').

    Usage:

        # settings.py:

        VELCRO_RELATIONSHIPS = [
            ('data', 'publications'),
            ('data', 'scientists'),
            ('publications', 'scientists'),
        ]

        # data/admin.py:

        from django.conf import settings


        def admin_base(object_type):
            if 'django_velcro' in settings.INSTALLED_APPS:
                from django_velcro.utils import generic_admin_base
                GenericAdminBase = generic_admin_base(object_type,
                    relationships=settings.VELCRO_RELATIONSHIPS)
            else:
                GenericAdminBase = admin.ModelAdmin
            return GenericAdminBase


        @admin.register(Data)
        class DataAdmin(admin_base('data')):
            pass


    Equivalent To:

        class DataAdminBase(GenericAdminModelAdmin):
            inlines = [
                DataToPublicationsRelationshipInline,
                DataToScientistsRelationshipInline,
            ]

            class Meta:
                abstract = True
    """
    inlines = get_relationship_inlines(object_type,
        relationships=relationships, related_types=related_types)

    class Meta:
        abstract = True

    typedict = {
        '__module__': __name__,
        'Meta': Meta,
        'inlines': inlines
    }

    klass_name = '{}GenericAdminBase'.format(object_type.capitalize())
    klass = type(
        klass_name,
        (GenericAdminModelAdmin,),
        typedict
    )
    return klass

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

def get_related_content(object, *related_types, object_type=None,
    relationships=settings.VELCRO_RELATIONSHIPS):
    """
    Return a dictionary of related content (of given related type(s)) for an
    object. Each key is a related type and its value is a list of related
    content of that type. If no related types are given, related content of
    all types is returned.

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
        relationship_class = getattr(import_module(".models", package=__package__),
            relationship_class_name)

        relationships = relationship_class.objects.filter(
            **{'{}_object_id'.format(object_type): object.id})
        related_content_object = '{}_content_object'.format(rt)

        related_content[rt] = [getattr(related, related_content_object)
            for related in sorted(relationships,
                key=lambda x: (
                    type(getattr(x, related_content_object)).__name__.lower(),
                    getattr(x, related_content_object).__str__().lower()))]

    return OrderedDict(sorted(related_content.items(),
        key=lambda t: t[0].lower()))

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
            object_type, *related_types, relationships=relationships).items():

        for r in related_objects:
            related_content_sametype.extend(
                get_related_content(r, related_type, object_type,
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
