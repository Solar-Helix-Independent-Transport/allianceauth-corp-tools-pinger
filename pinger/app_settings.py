from django.conf import settings

CT_PINGER_VALID_STATES = getattr(settings, 'CT_PINGER_VALID_STATES', ["Member"])
