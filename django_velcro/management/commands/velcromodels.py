from django.core.management.base import BaseCommand, CommandError

from django_velcro.utils import (get_all_object_types,
    get_relationship_inlines, is_valid_object_type)


def validate_object_types(object_types):
    """
    Raise 'Command Error' if a provided object type is not defined in
    'settings.VELCRO_METADATA'.
    """
    for ot in object_types:
        if not is_valid_object_type(ot):
            raise CommandError("Object type '{}' does not exist.".format(ot))

class Command(BaseCommand):
    args = '<object_type object_type ...>'
    help = 'Display names of generated models for a list of object types. \n' \
           'If no object type is given, models for all object types are returned.'

    def handle(self, *args, **kwargs):
        object_types = args

        if object_types:
            validate_object_types(object_types)
        else:
            object_types = get_all_object_types()

        for ot in object_types:
            self.stdout.write("\n[{}]".format(ot))
            self.stdout.write("\n  inlines\n  -------\n")

            for r in get_relationship_inlines(ot):
                self.stdout.write('  {}'.format(r.__name__))

            self.stdout.write("\n")
