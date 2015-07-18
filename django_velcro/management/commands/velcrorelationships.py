from django.core.management.base import BaseCommand, CommandError

from django_velcro import models


class Command(BaseCommand):
    help = 'Display names of generated relationship models (django_velcro.models).'

    def handle(self, *args, **kwargs):
        verbosity = int(kwargs['verbosity'])

        if verbosity > 0:
            self.stdout.write('\n')
            self.stdout.write('relationship models (django_velcro.models)')
            self.stdout.write('------------------------------------------')

        for model_name in sorted([name for name, cls in models.__dict__.items()
            if isinstance(cls, type)]):

            # Ignore models imported within django_velcro.models
            if model_name in ['ContentType', 'GenericForeignKey']:
                continue

            self.stdout.write('{}'.format(model_name))

        if verbosity > 0:
            self.stdout.write('\n')
