from django.apps import apps
from django.conf import settings
from django.contrib import admin

from genericadmin.admin import (GenericAdminModelAdmin, GenericStackedInline,
    GenericTabularInline)

from .utils import get_relationship_inlines


##############################################
# ADMIN & INLINE CLASS GENERATORS            #
##############################################
# Define VELCRO_RELATIONSHIPS in settings.py #
##############################################

def add_velcro_to_third_party_admin(app_name, model_name, object_type):
    """
    Update third party admin models with inline classes for relationships
    and inheritance from 'GenericAdminModelAdmin'.
    """
    model = apps.get_model(app_name, model_name)
    orig_model_admin = admin.site._registry[model].__class__

    orig_inlines = orig_model_admin.inlines
    relationship_inlines = get_relationship_inlines(object_type)
    inlines = orig_inlines + relationship_inlines

    updated_model_admin = type(
        orig_model_admin.__name__,
        (GenericAdminModelAdmin, orig_model_admin),
        {
            '__module__': __name__,
            'inlines': inlines,
        }
    )

    admin.site.unregister(model)
    admin.site.register(model, updated_model_admin)

def import_relationship_model(relationship):
    """
    Imports a relationship model.

    Usage:

        import_relationship_model(('data', 'publications'))


    Equivalent To:

        import DataPublicationsRelationship
    """
    content_1, content_2 = sorted(map(lambda x: x.capitalize(), relationship))
    relationship_class_name = '{}{}Relationship'.format(content_1, content_2)
    relationship_class = apps.get_model(__package__, relationship_class_name)
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
            fields = ['publications_content_type', 'publications_object_id']
            ordering = ['publications_content_type', 'order_by']
            verbose_name = 'Related Publications'
            verbose_name_plural = 'Related Publications'
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
            'fields': [
                '{}_content_type'.format(content_2.lower()),
                '{}_object_id'.format(content_2.lower()),
            ],
            'ordering': [
                '{}_content_type'.format(content_2.lower()),
                'order_by',
            ],
            'model': eval('{}{}Relationship'.format(
                *sorted(map(lambda x: x.capitalize(), relationship)))),
            '__module__': __name__,
            'verbose_name': 'Related {}'.format(content_2).title(),
            'verbose_name_plural': 'Related {}'.format(content_2).title(),
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
            readonly_fields = ['order_by']
        admin.site.register(DataPublicationsRelationship, DataPublicationsAdmin)
    """
    content_1, content_2 = sorted(map(lambda x: x.capitalize(), relationship))
    klass_name = ''.format(content_1, content_2)
    klass = type(
        klass_name,
        (GenericAdminModelAdmin,),
        {
            '__module__': __name__,
            'readonly_fields': ['order_by'],
        }
    )
    globals()[klass_name] = klass

    model = eval('{}{}Relationship'.format(content_1, content_2))
    admin.site.register(model, klass)


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


###################################################################
# MODIFY ADMIN MODELS FOR MODELS WITH ENTRIES IN VELCRO_METADATA: #
# - ADD INHERITANCE FROM GenericAdminModelAdmin                   #
# - ADD INLINE CLASSES FOR RELATIONSHIP MODELS                    #
###################################################################
# Define VELCRO_METADATA in settings.py                           #
###################################################################

for object_type, object_type_metadata in settings.VELCRO_METADATA.items():
    for model_metadata in object_type_metadata:
        app_name = model_metadata['app_label']
        model_name = model_metadata['model']
        add_velcro_to_third_party_admin(app_name, model_name, object_type)
