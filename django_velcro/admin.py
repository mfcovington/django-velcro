from django.conf import settings
from django.contrib import admin

from genericadmin.admin import (GenericAdminModelAdmin, GenericStackedInline,
    GenericTabularInline)


##############################################
# ADMIN & INLINE CLASS GENERATORS            #
##############################################
# Define VELCRO_RELATIONSHIPS in settings.py #
##############################################

def import_relationship_model(relationship):
    """
    Imports a relationship model.

    Usage:

        import_relationship_model(('data', 'publications'))


    Equivalent To:

        import DataPublicationsRelationship
    """
    from importlib import import_module
    content_1, content_2 = sorted(map(lambda x: x.capitalize(), relationship))
    relationship_class_name = '{}{}Relationship'.format(content_1, content_2)
    relationship_class = getattr(import_module(".models", package=__package__),
        relationship_class_name)
    globals()[relationship_class_name] = relationship_class

def generate_inline_model(relationship, tabular=True):
    """
    Generates a tabular inline model from a relationship tuple.

    Usage:

        generate_inline_model(('data', 'publications'))


    Equivalent To:

        class DataToPublicationsRelationshipInline(GenericTabularInline):
            model = DataPublicationsRelationship
            ct_field = 'data_content_type'
            ct_fk_field = 'data_object_id'
            ordering = ['publications_content_type']
    """
    content_1, content_2 = relationship
    klass_name = '{}To{}RelationshipInline'.format(content_1.capitalize(), content_2.capitalize())

    if tabular:
        inline_style = GenericTabularInline
    else:
        inline_style = GenericStackedInline

    klass = type(
        klass_name,
        (inline_style,),
        {
            'ct_field': '{}_content_type'.format(content_1.lower()),
            'ct_fk_field': '{}_object_id'.format(content_1.lower()),
            'ordering': ['{}_content_type'.format(content_2.lower())],
            'model': eval('{}{}Relationship'.format(*sorted(map(lambda x: x.capitalize(), r)))),
            '__module__': __name__,
        }
    )
    globals()[klass_name] = klass

def generate_and_register_admin_model(relationship):
    """
    Generates and registers an admin model from a relationship tuple.

    Usage:

        generate_and_register_admin_model(('data', 'publications'))

    Equivalent To:

        class DataPublicationsAdmin(GenericAdminModelAdmin):
            pass
        admin.site.register(DataPublicationsRelationship, DataPublicationsAdmin)
    """
    content_1, content_2 = sorted(map(lambda x: x.capitalize(), relationship))
    klass_name = ''.format(content_1, content_2)
    klass = type(
        klass_name,
        (GenericAdminModelAdmin,),
        {
            '__module__': __name__,
        }
    )
    globals()[klass_name] = klass

    model = eval('{}{}Relationship'.format(content_1, content_2))
    admin.site.register(model, klass_name)


##############################################
# GENERATE ADMIN & INLINE CLASSES            #
##############################################
# Define VELCRO_RELATIONSHIPS in settings.py #
##############################################

for r in settings.VELCRO_RELATIONSHIPS:
    import_relationship_model(r)
    generate_inline_model(sorted(r))
    generate_inline_model(sorted(r, reverse=True))
    generate_and_register_admin_model(r)
