from django.core.management.base import BaseCommand, CommandError

from django_velcro.utils import (get_all_velcro_types,
    get_relationship_inlines, is_valid_velcro_type)

from django_velcro.settings import VELCRO_INLINES


def validate_velcro_types(velcro_types):
    """
    Raise 'Command Error' if a provided velcro type is not defined in
    'settings.VELCRO_METADATA'.
    """
    for vt in velcro_types:
        if not is_valid_velcro_type(vt):
            raise CommandError("Object type '{}' does not exist.".format(vt))

class Command(BaseCommand):
    args = '<velcro_type velcro_type ...>'
    help = 'Display names of generated models for a list of velcro types. \n' \
           'If no velcro type is given, models for all velcro types are ' \
           'returned.'

    def handle(self, *args, **kwargs):
        velcro_types = args

        if velcro_types:
            validate_velcro_types(velcro_types)
        else:
            velcro_types = get_all_velcro_types()

        for vt in velcro_types:
            self.stdout.write("\n[{}]".format(vt))

            if VELCRO_INLINES:
                self.stdout.write("\n  inlines\n  -------\n")
                for r in get_relationship_inlines(vt):
                    self.stdout.write('  {}'.format(r.__name__))
            self.stdout.write("\n")
