from collections import OrderedDict
from importlib import import_module

from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.fields import GenericRelation
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

def get_related_content(object, object_type, *related_types,
    relationships=settings.VELCRO_RELATIONSHIPS):
    """
    Return a dictionary of related content (of given related type(s)) for an
    object. Each key is a related type and its value is a list of related
    content of that type. If no related types are given, related content of
    all types is returned.

    Usage:
        from data.models import Data
        data_set = DataSet.objects.first()
        get_related_content(data_set, 'data')                               # all related types
        get_related_content(data_set, 'data', 'publications')               # one related type
        get_related_content(data_set, 'data', 'publications', 'scientists') # two related types
    """
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

def get_related_content_sametype(object, object_type, *related_types,
    relationships=settings.VELCRO_RELATIONSHIPS):
    """
    Return a list of related content for an object of the same type as that
    object. This related content of the same type is retrieved indirectly via
    mutually-related content of all other related types. To limit the results
    to specific relationships, specify related types of interest.

    Usage:
        from data.models import Data
        data_set = DataSet.objects.first()
        get_related_content_sametype(data_set, 'data')               # via all related types
        get_related_content_sametype(data_set, 'data', 'scientists') # via one related type
    """
    related_content_sametype = []
    for related_type, related_objects in get_related_content(object,
            object_type, relationships=relationships).items():

        if related_types and (related_type not in related_types):
            continue

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

def relations_abstract_base(object_type, relationships=None, related_types=None):
    """
    Create an abstract base class with generic relations to related content.

    Usage:

        # settings.py:

        VELCRO_RELATIONSHIPS = [
            ('data', 'publications'),
            ('data', 'scientists'),
            ('publications', 'scientists'),
        ]

        # data/models.py:

        from django.conf import settings

        if 'django_velcro' in settings.INSTALLED_APPS:
            from django_velcro.utils import relations_abstract_base
            DataRelationsBase = relations_abstract_base('data',
                relationships=settings.VELCRO_RELATIONSHIPS)
        else:
            DataRelationsBase = models.Model


    Equivalent To:

        class DataRelationsBase(models.Model):
            related_publications = GenericRelation(DataPublicationsRelationship,
                content_type_field='publications_content_type',
                object_id_field='publications_object_id',
                related_query_name='data',
            )
            related_scientists = GenericRelation(DataScientistsRelationship,
                content_type_field='scientists_content_type',
                object_id_field='scientists_object_id',
                related_query_name='data',
            )

            class Meta:
                abstract = True
    """
    related_types = validate_and_process_related(object_type, relationships,
        related_types)

    class Meta:
        abstract = True

    typedict = {
        '__module__': __name__,
        'Meta': Meta,
    }

    for related in related_types:
        relationship_class_name = '{}{}Relationship'.format(
            *sorted([object_type.capitalize(), related.capitalize()]))
        relationship_class = getattr(import_module(".models", package=__package__),
            relationship_class_name)

        typedict['related_{}'.format(related.lower())] = GenericRelation(
            relationship_class,
            content_type_field='{}_content_type'.format(related.lower()),
            object_id_field='{}_object_id'.format(related.lower()),
            related_query_name=object_type.lower(),
        )

    klass_name = '{}RelationsBase'.format(object_type.capitalize())
    klass = type(
        klass_name,
        (models.Model,),
        typedict
    )
    return klass

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
