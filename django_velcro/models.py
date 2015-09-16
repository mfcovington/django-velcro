import operator
from functools import reduce

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models


################################################################
# RELATIONSHIP CLASS GENERATOR                                 #
################################################################
# Define VELCRO_METADATA & VELCRO_RELATIONSHIPS in settings.py #
################################################################

def generate_relationship_model(relationship, velcro_metadata):
    """
    Generates a relationship model from a relationship tuple and
    a dictionary with content type limits.

    Usage:

        VELCRO_METADATA = {
            'data': [
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
            'publications': [
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
        }
        generate_relationship_model(('data', 'publications'), VELCRO_METADATA)


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

            def __str__(self):
                return '{}: {} ⟷  {}: {}'.format(
                    self.data_content_type.name.upper(),
                    self.data_content_object,
                    self.publications_content_type.name.upper(),
                    self.publications_content_object
                )
    """
    content_1, content_2 = sorted(relationship)
    klass_name = '{}{}Relationship'.format(content_1.capitalize(),
        content_2.capitalize())
    typedict = {'__module__': __name__,}

    for content in map(lambda x: x.lower(), relationship):
        queries = []
        for lim in velcro_metadata[content]:
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

    class Meta:
        unique_together = (
            '{}_content_type'.format(content_1),
            '{}_object_id'.format(content_1),
            '{}_content_type'.format(content_2),
            '{}_object_id'.format(content_2),
        )

    def __str__(self):
        return '{}: {} ⟷  {}: {}'.format(
            getattr(self, '{}_content_type'.format(content_1)).name.upper(),
            getattr(self, '{}_content_object'.format(content_1)),
            getattr(self, '{}_content_type'.format(content_2)).name.upper(),
            getattr(self, '{}_content_object'.format(content_2)),
        )

    typedict['__str__'] = __str__
    typedict['Meta'] = Meta
    klass = type(klass_name, (models.Model,), typedict)
    globals()[klass_name] = klass


################################################################
# GENERATE RELATIONSHIP CLASSES                                #
################################################################
# Define VELCRO_METADATA & VELCRO_RELATIONSHIPS in settings.py #
################################################################

for r in settings.VELCRO_RELATIONSHIPS:
    generate_relationship_model(r, settings.VELCRO_METADATA)
