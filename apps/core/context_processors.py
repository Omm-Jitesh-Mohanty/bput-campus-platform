"""
Context processors — inject config-derived data into every template.
"""
from .services import ConfigService


def campus_config(request):
    """
    Adds commonly needed config to every template context.
    Cached via ConfigService, so zero DB cost per request.
    """
    return {
        'campus_site_name': ConfigService.get_setting(
            'site.name', 'Campus Platform'
        ),
        'campus_ticket_types': ConfigService.ticket_type_choices(),
        'campus_priorities': ConfigService.priority_choices(),
        'campus_lite_mode': request.session.get('lite_mode', False),
    }