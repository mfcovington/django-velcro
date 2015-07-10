from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models

from genericadmin.admin import GenericAdminModelAdmin


def generic_admin_base(object_type, relationships=None, related_types=None):
    """
    Create an abstract base class that has inlines for related content
    and extends GenericAdminModelAdmin (from 'genericadmin.admin').

    Usage:

        # settings.py:

        RELATIONSHIPS = [
            ('data', 'publications'),
            ('data', 'scientists'),
            ('publications', 'scientists'),
        ]

        # data/admin.py:

        from django.conf import settings

        if 'django_velcro' in settings.INSTALLED_APPS:
            from django_velcro.utils import generic_admin_base
            DataGenericAdminBase = generic_admin_base('data',
                relationships=settings.RELATIONSHIPS)
        else:
            DataGenericAdminBase = admin.ModelAdmin


    Equivalent To:

        class DataGenericAdminBase(GenericAdminModelAdmin):
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

def get_all_object_types(relationships=settings.RELATIONSHIPS):
    """
    Return a list of all object types defined in 'settings.RELATIONSHIPS'.
    """
    return sorted(set([object_type for r in relationships for object_type in r]))

def get_all_related_content(object, relationships=settings.RELATIONSHIPS):
    """
    Return a dictionary of related content for an object. Each key is a
    related type and its value is a list of related content of that type.

    Usage:
        from data.models import Data
        data_set = DataSet.objects.first()
        get_all_related_content(data_set)
    """
    object_type = ContentType.objects.get_for_model(object).name
    related_types = validate_and_process_related(object_type, relationships)

    related_content = {}
    for rt in related_types:
        related_content[rt] = get_related_content(object, rt)
    return related_content

def get_related_content(object, object_type, related_type):
    """
    Return a list of related content (of given related type) for an object.

    Usage:
        from data.models import Data
        data_set = DataSet.objects.first()
        get_related_content(data_set, 'data', publication')
    """
    content_type = ContentType.objects.get_for_model(object)
    kwargs = {
        '{}_content_type__pk'.format(object_type): content_type.id,
        '{}_object_id'.format(object_type): object.id,
    }
    relationships = getattr(object,
        'related_{}'.format(related_type)).model.objects.filter(**kwargs)

    related_content_object = '{}_content_object'.format(related_type)

    return [getattr(related, related_content_object)
        for related in sorted(relationships,
            key=lambda x: (
                type(getattr(x, related_content_object)).__name__.lower(),
                getattr(x, related_content_object).name.lower()))]

def get_relationship_inlines(object_type, relationships=None, related_types=None):
    """
    Import relevant relationship inline models for an admin model.

    Usage:

        # settings.py:

        RELATIONSHIPS = [
            ('data', 'publications'),
            ('data', 'scientists'),
            ('publications', 'scientists'),
        ]

        # data/admin.py:

        @admin.register(Data, DataSet)
        class DataAdmin(GenericAdminModelAdmin):
            if 'django_velcro' in settings.INSTALLED_APPS:
                from django_velcro.relationships import RELATIONSHIPS
                from django_velcro.utils import get_relationship_inlines
                inlines = get_relationship_inlines('data', relationships=RELATIONSHIPS)


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

    from importlib import import_module

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

        RELATIONSHIPS = [
            ('data', 'publications'),
            ('data', 'scientists'),
            ('publications', 'scientists'),
        ]

        # data/models.py:

        from django.conf import settings

        if 'django_velcro' in settings.INSTALLED_APPS:
            from django_velcro.relationships import RELATIONSHIPS
            from django_velcro.utils import relations_abstract_base
            DataRelationsBase = relations_abstract_base('data', relationships=RELATIONSHIPS)
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

    from importlib import import_module

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

def is_valid_object_type(object_type, relationships=settings.RELATIONSHIPS):
    """
    Return 'True' if the provided object type is defined in 'settings.RELATIONSHIPS'.
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
