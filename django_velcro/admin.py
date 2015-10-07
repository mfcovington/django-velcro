from django.apps import apps
from django.contrib import admin

from genericadmin.admin import (GenericAdminModelAdmin, GenericStackedInline,
    GenericTabularInline)

from .settings import (VELCRO_GENERICADMIN, VELCRO_INLINES,
    VELCRO_INLINES_EXTRA, VELCRO_INLINES_MAX_NUM, VELCRO_INLINES_TABULAR,
    VELCRO_METADATA, VELCRO_RELATIONSHIPS)
from .utils import (get_relationship_inlines, plural_velcro_type,
    singular_velcro_type)


def _startup():
    """
    Generate velcro admin and inline classes. Update third party admin
    models  with inline classes for relationships and inheritance from
    'GenericAdminModelAdmin'.
    """
    for r in VELCRO_RELATIONSHIPS:
        import_relationship_model(r)
        if VELCRO_INLINES:
            generate_inline_model(r)
            generate_inline_model(r, reverse=True)
        generate_and_register_admin_model(r)

    for velcro_type, velcro_type_metadata in VELCRO_METADATA.items():
        for model_metadata in velcro_type_metadata['apps']:
            app_name = model_metadata['app_label']
            model_name = model_metadata['model']
            add_velcro_to_third_party_admin(app_name, model_name, velcro_type)

def add_velcro_to_third_party_admin(app_name, model_name, velcro_type):
    """
    Update third party admin models with inline classes for relationships
    and inheritance from 'GenericAdminModelAdmin'.

    To prevent the inheritance third party admin models from inheriting from
    'GenericAdminModelAdmin', add to 'settings.py':

        VELCRO_GENERICADMIN = False

    To prevent the addition of inlines to third party admin models, add to
    'settings.py':

        VELCRO_INLINES = False
    """
    model = apps.get_model(app_name, model_name)
    orig_model_admin = admin.site._registry[model].__class__

    if VELCRO_GENERICADMIN:
        model_admin = (GenericAdminModelAdmin, orig_model_admin)
    else:
        model_admin = (orig_model_admin, )

    orig_inlines = orig_model_admin.inlines

    if VELCRO_INLINES:
        relationship_inlines = get_relationship_inlines(velcro_type)
        inlines = orig_inlines + relationship_inlines
    else:
        inlines = orig_inlines

    updated_model_admin = type(
        orig_model_admin.__name__,
        model_admin,
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

        import_relationship_model(('data', 'publication'))


    Equivalent To:

        import DataPublicationRelationship
    """
    object_1_velcro_type, object_2_velcro_type = sorted(relationship)
    relationship_class_name = '{}{}Relationship'.format(
        object_1_velcro_type.capitalize(), object_2_velcro_type.capitalize())
    relationship_class = apps.get_model(__package__, relationship_class_name)
    globals()[relationship_class_name] = relationship_class

def generate_inline_model(
        relationship, reverse=False, tabular=VELCRO_INLINES_TABULAR):
    """
    Generates a tabular inline model from a relationship tuple.
    For a stacked inline model, add 'VELCRO_INLINES_TABULAR = False' to
    settings.

    Usage:

        generate_inline_model(('data', 'publication'))


    Equivalent To:

        class DataToPublicationsRelationshipInline(GenericTabularInline):
            model = DataPublicationsRelationship
            ct_field = 'data_content_type'
            ct_fk_field = 'data_object_id'
            fields = ['publication_content_type', 'publication_object_id']
            ordering = ['publication_content_type', 'order_by']
            verbose_name = 'Related Publication'
            verbose_name_plural = 'Related Publications'
    """
    object_1_velcro_type, object_2_velcro_type = sorted(
        relationship, reverse=reverse)
    klass_name = '{}To{}RelationshipInline'.format(
        object_1_velcro_type.capitalize(), object_2_velcro_type.capitalize())

    if tabular:
        inline_style = GenericTabularInline
    else:
        inline_style = GenericStackedInline

    typedict = {
        'model': eval('{}{}Relationship'.format(
            *sorted(map(lambda x: x.capitalize(), relationship)))),
        '__module__': __name__,
        'max_num': VELCRO_INLINES_MAX_NUM,
        'verbose_name': 'Related {}'.format(
            singular_velcro_type(object_2_velcro_type)).title(),
    }

    if object_1_velcro_type == object_2_velcro_type:
        if reverse:
            klass_name = '{}To{}RelationshipReverseInline'.format(
                object_1_velcro_type.capitalize(),
                object_2_velcro_type.capitalize())
            typedict.update({
                'ct_field': 'content_type_2',
                'ct_fk_field': 'object_id_2',
                'extra': 0,
                'fields': [
                    'content_type_1',
                    'object_id_1',
                ],
                'ordering': [
                    'order_by',
                ],
                'verbose_name_plural': 'Related {} (Reverse)'.format(
                    plural_velcro_type(object_1_velcro_type)).title(),
            })
        else:
            typedict.update({
                'ct_field': 'content_type_1',
                'ct_fk_field': 'object_id_1',
                'extra': VELCRO_INLINES_EXTRA,
                'fields': [
                    'content_type_2',
                    'object_id_2',
                ],
                'ordering': [
                    'order_by',
                ],
                'verbose_name_plural': 'Related {} (Forward)'.format(
                    plural_velcro_type(object_2_velcro_type)).title(),
            })
    else:
        typedict.update({
            'ct_field': '{}_content_type'.format(object_1_velcro_type),
            'ct_fk_field': '{}_object_id'.format(object_1_velcro_type),
            'extra': VELCRO_INLINES_EXTRA,
            'fields': [
                '{}_content_type'.format(object_2_velcro_type),
                '{}_object_id'.format(object_2_velcro_type),
            ],
            'ordering': [
                '{}_content_type'.format(object_2_velcro_type),
                'order_by',
            ],
            'verbose_name_plural': 'Related {}'.format(
                plural_velcro_type(object_2_velcro_type)).title(),
        })

    klass = type(klass_name, (inline_style,), typedict)
    globals()[klass_name] = klass

def generate_and_register_admin_model(relationship):
    """
    Generates and registers an admin model from a relationship tuple.

    Usage:

        generate_and_register_admin_model(('data', 'publication'))

    Equivalent To:

        class DataPublicationRelationshipAdmin(GenericAdminModelAdmin):
            readonly_fields = ['order_by']
        admin.site.register(DataPublicationRelationship, DataPublicationAdmin)
    """
    object_1_velcro_type, object_2_velcro_type = sorted(relationship)
    model_name = '{}{}Relationship'.format(
        object_1_velcro_type.capitalize(), object_2_velcro_type.capitalize())
    klass_name = '{}Admin'.format(model_name)
    klass = type(
        klass_name,
        (GenericAdminModelAdmin,),
        {
            '__module__': __name__,
            'readonly_fields': ['order_by'],
        }
    )
    globals()[klass_name] = klass

    model = eval(model_name)
    admin.site.register(model, klass)


_startup()
