from django.conf import settings

VELCRO_METADATA = getattr(settings, 'VELCRO_METADATA', {})
VELCRO_RELATIONSHIPS = getattr(settings, 'VELCRO_RELATIONSHIPS', [(), ()])
