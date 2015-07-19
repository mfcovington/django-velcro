from django.core.management.base import BaseCommand, CommandError

from django_velcro import models


class Command(BaseCommand):
    help = 'Display functions that specify model to inherit from depending ' \
           'on whether django_velcro is installed.'

    def handle(self, *args, **kwargs):

        self.stdout.write(
"""
Dynamic RelationsBase Model
===========================

    Function to include in 'models.py'
    ---------------------------------

        def relations_base(object_type):
            if 'django_velcro' in settings.INSTALLED_APPS:
                from django_velcro.utils import relations_abstract_base
                RelationsBase = relations_abstract_base(object_type)
            else:
                RelationsBase = models.Model
            return RelationsBase

    Usage Example
    -------------

        class Publication(relations_base('publications')):
            ...


        class PublicationSet(relations_base('publications')):
            ...

""")

        self.stdout.write(
"""
Dynamic GenericAdminBase Model
==============================

    Function to include in 'admin.py'
    ---------------------------------

        def admin_base(object_type):
            if 'django_velcro' in settings.INSTALLED_APPS:
                from django_velcro.utils import generic_admin_base
                GenericAdminBase = generic_admin_base(object_type)
            else:
                GenericAdminBase = admin.ModelAdmin
            return GenericAdminBase

    Usage Example
    -------------

        @admin.register(Publication, PublicationSet)
        class PublicationAdmin(admin_base('publications')):
            pass

""")
