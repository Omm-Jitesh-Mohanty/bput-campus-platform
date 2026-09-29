"""
Dynamic form schema utilities.

Handles validation, rendering, and data extraction for JSON-Schema-driven
custom form fields on tickets.
"""
import logging
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


# =====================================================================
# Supported field types
# =====================================================================
FIELD_TYPES = [
    ('text', 'Short Text'),
    ('textarea', 'Long Text'),
    ('number', 'Number'),
    ('date', 'Date'),
    ('datetime', 'Date + Time'),
    ('select', 'Dropdown (single)'),
    ('multiselect', 'Multi-select'),
    ('radio', 'Radio buttons'),
    ('checkbox', 'Single checkbox'),
    ('file', 'File upload'),
    ('email', 'Email'),
    ('phone', 'Phone'),
]


# =====================================================================
# Validation
# =====================================================================
def validate_schema(schema):
    """
    Validate a schema dict.
    Returns (is_valid, errors:list[str])
    """
    errors = []
    if not isinstance(schema, dict):
        return False, ["Schema must be a dict"]

    fields = schema.get('fields', [])
    if not isinstance(fields, list):
        return False, ["'fields' must be a list"]

    seen_names = set()
    valid_types = {t[0] for t in FIELD_TYPES}

    for i, f in enumerate(fields):
        if not isinstance(f, dict):
            errors.append(f"Field #{i} must be a dict")
            continue

        name = f.get('name', '').strip()
        if not name:
            errors.append(f"Field #{i} missing 'name'")
        elif not name.replace('_', '').isalnum():
            errors.append(f"Field #{i}: name must be alphanumeric + underscores")
        elif name in seen_names:
            errors.append(f"Field '{name}' is duplicated")
        else:
            seen_names.add(name)

        if not f.get('label', '').strip():
            errors.append(f"Field '{name}' missing 'label'")

        ftype = f.get('type', '')
        if ftype not in valid_types:
            errors.append(f"Field '{name}' has invalid type '{ftype}'")

        # Types that require 'options'
        if ftype in ('select', 'multiselect', 'radio'):
            opts = f.get('options', [])
            if not isinstance(opts, list) or len(opts) == 0:
                errors.append(f"Field '{name}' needs 'options' for type '{ftype}'")
            else:
                for j, opt in enumerate(opts):
                    if not isinstance(opt, dict):
                        errors.append(f"Field '{name}' option #{j} must be a dict")
                    elif 'value' not in opt or 'label' not in opt:
                        errors.append(f"Field '{name}' option #{j} needs 'value' and 'label'")

    return len(errors) == 0, errors


# =====================================================================
# Extraction & coercion
# =====================================================================
def extract_dynamic_data(schema, post_data, files=None):
    """
    Extract and coerce form data based on schema.

    Args:
        schema: dict from TicketType.dynamic_schema
        post_data: request.POST (a QueryDict)
        files: request.FILES (optional, for file fields)

    Returns:
        (cleaned_data:dict, errors:list[str])
    """
    cleaned = {}
    errors = []
    fields = (schema or {}).get('fields', [])

    for field in fields:
        name = field.get('name')
        label = field.get('label', name)
        ftype = field.get('type', 'text')
        required = field.get('required', False)

        # --- checkbox: presence is the value ---
        if ftype == 'checkbox':
            cleaned[name] = name in post_data
            if required and not cleaned[name]:
                errors.append(f"{label} must be accepted")
            continue

        # --- multiselect ---
        if ftype == 'multiselect':
            values = post_data.getlist(name)
            if required and not values:
                errors.append(f"{label} is required")
                continue
            cleaned[name] = values
            continue

        # --- file ---
        if ftype == 'file':
            # File handling is deferred to attachment logic; skip here
            # (or handle separately if we add per-field files later)
            continue

        # --- everything else ---
        raw = post_data.get(name, '').strip()

        if not raw:
            if required:
                errors.append(f"{label} is required")
            else:
                cleaned[name] = None
            continue

        # Type-specific coercion
        try:
            if ftype == 'number':
                cleaned[name] = float(raw) if '.' in raw else int(raw)
            elif ftype == 'date':
                cleaned[name] = datetime.strptime(raw, '%Y-%m-%d').date().isoformat()
            elif ftype == 'datetime':
                cleaned[name] = datetime.strptime(raw, '%Y-%m-%dT%H:%M').isoformat()
            elif ftype == 'email':
                if '@' not in raw:
                    raise ValueError('Invalid email')
                cleaned[name] = raw
            elif ftype == 'select':
                # Validate against options
                opts = {o['value'] for o in field.get('options', [])}
                if raw not in opts:
                    raise ValueError(f"Invalid option for {label}")
                cleaned[name] = raw
            else:
                # text, textarea, phone, radio
                cleaned[name] = raw

            # Length validations
            v = field.get('validation', {}) or {}
            if 'min_length' in v and len(str(cleaned[name])) < v['min_length']:
                errors.append(f"{label} must be at least {v['min_length']} characters")
            if 'max_length' in v and len(str(cleaned[name])) > v['max_length']:
                errors.append(f"{label} must be at most {v['max_length']} characters")
        except (ValueError, KeyError) as e:
            errors.append(f"{label}: invalid value ({e})")

    return cleaned, errors


# =====================================================================
# Template rendering helper
# =====================================================================
def prepare_fields_for_render(schema, existing_data=None):
    """
    Enhance each field for template consumption:
      - Add 'value' (from existing_data for edit views)
      - Add 'id' (for label/input binding)
      - Normalize options
    """
    fields = list((schema or {}).get('fields', []))
    existing_data = existing_data or {}

    prepared = []
    for f in fields:
        f = dict(f)  # copy
        f['id'] = f"dyn_{f['name']}"
        if existing_data.get(f['name']) is not None:
            f['value'] = existing_data[f['name']]
        else:
            f['value'] = f.get('default', '')
        prepared.append(f)

    return prepared