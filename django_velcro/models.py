import operator
from functools import reduce

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models

from .app_settings import VELCRO_METADATA, VELCRO_RELATIONSHIPS


def _startup():
    """
    Generate relationship classes.
    """
    for r in VELCRO_RELATIONSHIPS:
        generate_relationship_model(r)

def _generate_relationship_model_difftype(relationship, typedict):
    """
    Return RelationshipBase model and updated typedict for relationship models
    with differing velcro types.
    """
    class RelationshipBase(models.Model):
        """
        Base class for relationship models with differing velcro types.
        """
        class Meta:
            abstract = True
            ordering = ['order_by']

        def save(self, *args, **kwargs):
            query = {
                '{}_content_type'.format(object_1_velcro_type):
                    getattr(
                        self, '{}_content_type'.format(object_1_velcro_type)),
                '{}_object_pk'.format(object_1_velcro_type):
                    getattr(self, '{}_object_pk'.format(object_1_velcro_type)),
                '{}_content_type'.format(object_2_velcro_type):
                    getattr(
                        self, '{}_content_type'.format(object_2_velcro_type)),
                '{}_object_pk'.format(object_2_velcro_type):
                    getattr(self, '{}_object_pk'.format(object_2_velcro_type)),
            }

            try:
                relationship = self.__class__.objects.get(**query)
                self.pk = relationship.pk
            except:
                pass

            self.order_by = self.__str__()

            super().save(*args, **kwargs)

        def __str__(self):
            return '{}: {} ⟷  {}: {}'.format(
                getattr(self, '{}_content_type'.format(
                    object_1_velcro_type)).name.upper(),
                getattr(
                    self, '{}_content_object'.format(object_1_velcro_type)),
                getattr(self, '{}_content_type'.format(
                    object_2_velcro_type)).name.upper(),
                getattr(
                    self, '{}_content_object'.format(object_2_velcro_type)),
            )


    object_1_velcro_type, object_2_velcro_type = sorted(relationship)

    for velcro_type in relationship:
        queries = []
        for model_metadata in VELCRO_METADATA[velcro_type]['apps']:
            queries.append(models.Q(**{
                k: model_metadata[k].lower() for k in ('app_label', 'model')}))
        limit = reduce(operator.or_, queries, models.Q())

        typedict.update({
            '{}_content_type'.format(velcro_type): models.ForeignKey(
                ContentType, limit_choices_to=limit,
                related_name='%(app_label)s_%(class)s_related_{}'.format(
                    velcro_type)),
            '{}_object_pk'.format(velcro_type): models.PositiveIntegerField(),
            '{}_content_object'.format(velcro_type): GenericForeignKey(
                '{}_content_type'.format(velcro_type),
                '{}_object_pk'.format(velcro_type)),
        })

    return RelationshipBase, typedict

def _generate_relationship_model_sametype(velcro_type):
    """
    Return RelationshipBase model for relationship models with matching velcro
    types.
    """
    queries = []
    for model_metadata in VELCRO_METADATA[velcro_type]['apps']:
        queries.append(models.Q(**{
            k: model_metadata[k].lower() for k in ('app_label', 'model')}))
    limit = reduce(operator.or_, queries, models.Q())

    class RelationshipBase(models.Model):
        """
        Base class for relationship models with matching velcro types.
        """
        content_type_1 = models.ForeignKey(ContentType,
            limit_choices_to=limit,
            related_name='%(app_label)s_%(class)s_related_1')
        object_pk_1 = models.PositiveIntegerField()
        content_object_1 = GenericForeignKey(
            'content_type_1', 'object_pk_1')

        content_type_2 = models.ForeignKey(ContentType,
            limit_choices_to=limit,
            related_name='%(app_label)s_%(class)s_related_2')
        object_pk_2 = models.PositiveIntegerField()
        content_object_2 = GenericForeignKey(
            'content_type_2', 'object_pk_2')

        class Meta:
            abstract = True
            ordering = ['order_by']

        def save(self, *args, **kwargs):
            query = models.Q(
                content_type_1=self.content_type_1,
                object_pk_1=self.object_pk_1,
                content_type_2=self.content_type_2,
                object_pk_2=self.object_pk_2,
            ) | models.Q(
                content_type_1=self.content_type_2,
                object_pk_1=self.object_pk_2,
                content_type_2=self.content_type_1,
                object_pk_2=self.object_pk_1,
            )

            try:
                relationship = self.__class__.objects.get(query)
                self.pk = relationship.pk
            except:
                pass

            self.order_by = self.__str__()

            if (self.content_type_1 == self.content_type_2 and
                    self.object_pk_1 == self.object_pk_2):
                print("Object can't be related to itself.")
            else:
                super().save(*args, **kwargs)

        def __str__(self):
            return '{}: {} ⟷  {}: {}'.format(
                self.content_type_1.name.upper(),
                self.content_object_1,
                self.content_type_2.name.upper(),
                self.content_object_2
            )


    return RelationshipBase

def generate_relationship_model(relationship):
    """
    Generates a relationship model from a relationship tuple.

    Usage:

        # settings.py:
        VELCRO_METADATA = {
            'data': {
                'apps': [
                    {
                        'app_label': 'data',
                        'model': 'Data',
                        'view': 'data:data-detail',
                        'url_args': ['pk']
                    },
                    {
                        'app_label': 'data',
                        'model': 'DataSet',
                        'view': 'data:dataset-detail',
                        'url_args': ['pk']
                    },
                ],
                'options': {
                    'verbose_name': 'data',
                    'verbose_name_plural': 'data',
                },
            },
            'publication': {
                'apps': [
                    {
                        'app_label': 'publication',
                        'model': 'Publication',
                        'view': 'publications:publication-detail',
                        'url_args': ['pk']
                    },
                    {
                        'app_label': 'publication',
                        'model': 'PublicationSet',
                        'view': 'publications:publicationset-detail',
                        'url_args': ['pk']
                    },
                ],
                'options': {
                    'verbose_name': 'publication',
                    'verbose_name_plural': 'publications',
                },
            },
        }

        # models.py
        generate_relationship_model(('data', 'publication'))


    Equivalent To:

        class DataPublicationRelationship(models.Model):

            data_limit = models.Q(app_label='data', model='data') | \\
                models.Q(app_label='data', model='dataset')
            data_content_type = models.ForeignKey(ContentType,
                limit_choices_to=data_limit,
                related_name='%(app_label)s_%(class)s_related_data')
            data_object_pk = models.PositiveIntegerField()
            data_content_object = GenericForeignKey(
                'data_content_type', 'data_object_pk')

            publication_limit = models.Q(app_label='publication', model='publication') | \\
                models.Q(app_label='publication', model='publicationset')
            publication_content_type = models.ForeignKey(ContentType,
                limit_choices_to=publication_limit,
                related_name='%(app_label)s_%(class)s_related_publication')
            publication_object_pk = models.PositiveIntegerField()
            publication_content_object = GenericForeignKey(
                'publication_content_type', 'publication_object_pk')

            order_by = models.CharField(max_length=255, blank=True)

            class Meta:
                ordering = ['order_by']

            def save(self, *args, **kwargs):
                query = {
                    'data_content_type': self.data_content_type,
                    'data_object_pk': self.data_object_pk,
                    'publication_content_type': self.publication_content_type,
                    'publication_object_pk': self.publication_object_pk,
                }

                try:
                    relationship = self.__class__.objects.get(**query)
                    self.pk = relationship.pk
                except:
                    pass

                self.order_by = self.__str__()

                super().save(*args, **kwargs)

            def __str__(self):
                return '{}: {} ⟷  {}: {}'.format(
                    self.data_content_type.name.upper(),
                    self.data_content_object,
                    self.publication_content_type.name.upper(),
                    self.publication_content_object
                )

    When generating relationship models for matching velcro types, '1' or '2'
    will be appended to field names instead of field names being prefixed by
    their velcro type. For example, 'content_type_1' and 'content_type_2'
    would be used for matching velcro types, whereas 'data_content_type'
    and 'publication_content_type' might be used for differing velcro types.
    """
    object_1_velcro_type, object_2_velcro_type = sorted(relationship)
    klass_name = '{}{}Relationship'.format(object_1_velcro_type.capitalize(),
        object_2_velcro_type.capitalize())
    typedict = {
        '__module__': __name__,
        'order_by': models.CharField(max_length=255, blank=True)
    }

    if object_1_velcro_type == object_2_velcro_type:
        RelationshipBase = _generate_relationship_model_sametype(
            object_1_velcro_type)
    else:
        RelationshipBase, typedict = _generate_relationship_model_difftype(
            relationship, typedict)

    klass = type(klass_name, (RelationshipBase,), typedict)
    globals()[klass_name] = klass


_startup()
