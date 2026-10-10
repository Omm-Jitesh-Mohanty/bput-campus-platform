"""
Context processors — inject config + permissions into every template.
"""
from .services import ConfigService
from .permissions import user_permissions


def campus_config(request):
    return {
        'campus_site_name': ConfigService.get_setting(
            'site.name', 'Campus Platform'
        ),
        'campus_ticket_types': ConfigService.ticket_type_choices(),
        'campus_priorities': ConfigService.priority_choices(),
        'campus_lite_mode': request.session.get('lite_mode', False),
    }


def user_permissions_context(request):
    """Add user's permission set to context for template checks."""
    if not request.user.is_authenticated:
        return {'user_perms': set()}
    return {'user_perms': user_permissions(request.user)}