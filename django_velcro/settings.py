from django.conf import settings


VELCRO_INLINES = getattr(settings, 'VELCRO_INLINES', True)
VELCRO_INLINES_EXTRA = getattr(settings, 'VELCRO_INLINES_EXTRA', 3)
VELCRO_INLINES_MAX_NUM = getattr(settings, 'VELCRO_INLINES_MAX_NUM', None)
VELCRO_INLINES_TABULAR = getattr(settings, 'VELCRO_INLINES_TABULAR', True)
VELCRO_METADATA = getattr(settings, 'VELCRO_METADATA', {})
VELCRO_METHODS = getattr(settings, 'VELCRO_METHODS', True)
VELCRO_RELATIONSHIPS = getattr(settings, 'VELCRO_RELATIONSHIPS', [(), ()])
