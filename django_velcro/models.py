import operator
from functools import reduce

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models

from .settings import VELCRO_METADATA, VELCRO_RELATIONSHIPS


def _startup():
    """
    Generate relationship classes.
    """
    for r in VELCRO_RELATIONSHIPS:
        generate_relationship_model(r)

def _generate_relationship_model_difftype(relationship, typedict):
    """
    Return RelationshipBase model and updated typedict for relationship models
    with different object types.
    """
    class RelationshipBase(models.Model):
        """
        Base class for relationship models with different object types.
        """
        class Meta:
            abstract = True
            ordering = ['order_by']

        def save(self, *args, **kwargs):
            query = {
                '{}_content_type'.format(content_1):
                    getattr(self, '{}_content_type'.format(content_1)),
                '{}_object_id'.format(content_1):
                    getattr(self, '{}_object_id'.format(content_1)),
                '{}_content_type'.format(content_2):
                    getattr(self, '{}_content_type'.format(content_2)),
                '{}_object_id'.format(content_2):
                    getattr(self, '{}_object_id'.format(content_2)),
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
                getattr(self, '{}_content_type'.format(content_1)).name.upper(),
                getattr(self, '{}_content_object'.format(content_1)),
                getattr(self, '{}_content_type'.format(content_2)).name.upper(),
                getattr(self, '{}_content_object'.format(content_2)),
            )


    content_1, content_2 = sorted(relationship)

    for content in map(lambda x: x.lower(), relationship):
        queries = []
        for lim in VELCRO_METADATA[content]['apps']:
            queries.append(
                models.Q(**{k: lim[k].lower() for k in ('app_label', 'model')}))
        limit = reduce(operator.or_, queries, models.Q())

        typedict.update({
            '{}_content_type'.format(content): models.ForeignKey(ContentType,
                limit_choices_to=limit,
                related_name='%(app_label)s_%(class)s_related_{}'.format(content)),
            '{}_object_id'.format(content): models.PositiveIntegerField(),
            '{}_content_object'.format(content): GenericForeignKey(
                '{}_content_type'.format(content), '{}_object_id'.format(content)),
        })

    return RelationshipBase, typedict

def _generate_relationship_model_sametype(object_type):
    """
    Return RelationshipBase model for relationship models with matching object
    types.
    """
    queries = []
    for lim in VELCRO_METADATA[object_type.lower()]['apps']:
        queries.append(
            models.Q(**{k: lim[k].lower() for k in ('app_label', 'model')}))
    limit = reduce(operator.or_, queries, models.Q())

    class RelationshipBase(models.Model):
        """
        Base class for relationship models with matching object types.
        """
        content_type_1 = models.ForeignKey(ContentType,
            limit_choices_to=limit,
            related_name='%(app_label)s_%(class)s_related_1')
        object_id_1 = models.PositiveIntegerField()
        content_object_1 = GenericForeignKey(
            'content_type_1', 'object_id_1')

        content_type_2 = models.ForeignKey(ContentType,
            limit_choices_to=limit,
            related_name='%(app_label)s_%(class)s_related_2')
        object_id_2 = models.PositiveIntegerField()
        content_object_2 = GenericForeignKey(
            'content_type_2', 'object_id_2')

        class Meta:
            abstract = True
            ordering = ['order_by']

        def save(self, *args, **kwargs):
            query = models.Q(
                content_type_1=self.content_type_1,
                object_id_1=self.object_id_1,
                content_type_2=self.content_type_2,
                object_id_2=self.object_id_2,
            ) | models.Q(
                content_type_1=self.content_type_2,
                object_id_1=self.object_id_2,
                content_type_2=self.content_type_1,
                object_id_2=self.object_id_1,
            )

            try:
                relationship = self.__class__.objects.get(query)
                self.pk = relationship.pk
            except:
                pass

            self.order_by = self.__str__()

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
            'publications': {
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
        generate_relationship_model(('data', 'publications'))


    Equivalent To:

        class DataPublicationsRelationship(models.Model):

            data_limit = models.Q(app_label='data', model='data') | \\
                models.Q(app_label='data', model='dataset')
            data_content_type = models.ForeignKey(ContentType,
                limit_choices_to=data_limit,
                related_name='%(app_label)s_%(class)s_related_data')
            data_object_id = models.PositiveIntegerField()
            data_content_object = GenericForeignKey(
                'data_content_type', 'data_object_id')

            publications_limit = models.Q(app_label='publication', model='publication') | \\
                models.Q(app_label='publication', model='publicationset')
            publications_content_type = models.ForeignKey(ContentType,
                limit_choices_to=publications_limit,
                related_name='%(app_label)s_%(class)s_related_publications')
            publications_object_id = models.PositiveIntegerField()
            publications_content_object = GenericForeignKey(
                'publications_content_type', 'publications_object_id')

            order_by = models.CharField(max_length=255, blank=True)

            class Meta:
                ordering = ['order_by']

            def save(self, *args, **kwargs):
                query = {
                    'data_content_type': self.data_content_type,
                    'data_object_id': self.data_object_id,
                    'publications_content_type': self.publications_content_type,
                    'publications_object_id': self.publications_object_id,
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
                    self.publications_content_type.name.upper(),
                    self.publications_content_object
                )

    When generating relationship models for matching object types, '1' or '2'
    will be appended to field names instead of field names being prefixed by
    their object type. For example, 'content_type_1' and 'content_type_2'
    would be used for matching object types, whereas 'data_content_type'
    and 'publications_content_type' might be used for differing object types.
    """
    content_1, content_2 = sorted(relationship)
    klass_name = '{}{}Relationship'.format(content_1.capitalize(),
        content_2.capitalize())
    typedict = {
        '__module__': __name__,
        'order_by': models.CharField(max_length=255, blank=True)
    }

    if content_1 == content_2:
        RelationshipBase = _generate_relationship_model_sametype(content_1)
    else:
        RelationshipBase, typedict = _generate_relationship_model_difftype(
            relationship, typedict)

    klass = type(klass_name, (RelationshipBase,), typedict)
    globals()[klass_name] = klass


_startup()
