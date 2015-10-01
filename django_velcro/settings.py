from django.conf import settings

VELCRO_INLINES_TABULAR = getattr(settings, 'VELCRO_INLINES_TABULAR', True)
VELCRO_METADATA = getattr(settings, 'VELCRO_METADATA', {})
VELCRO_METHODS = getattr(settings, 'VELCRO_METHODS', True)
VELCRO_RELATIONSHIPS = getattr(settings, 'VELCRO_RELATIONSHIPS', [(), ()])
