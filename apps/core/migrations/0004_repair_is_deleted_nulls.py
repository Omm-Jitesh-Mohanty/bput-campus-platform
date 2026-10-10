"""
Repair is_deleted NULL values on soft-deleted models.

When SoftDeleteModel was added to existing tables, existing rows could have
NULL for is_deleted. Django's filter(is_deleted=False) excludes NULL rows,
causing lists to appear empty.

This migration converts existing NULL values to False.
"""

from django.db import migrations


SOFT_DELETE_MODELS = [
    ("tickets", "CampusTicket"),
    ("notices", "Notice"),
    ("documents", "IssuedDocument"),
]


def fix_nulls(apps, schema_editor):
    for app_label, model_name in SOFT_DELETE_MODELS:
        try:
            Model = apps.get_model(app_label, model_name)
        except LookupError:
            continue

        updated = Model.objects.filter(
            is_deleted__isnull=True
        ).update(
            is_deleted=False
        )

        if updated:
            print(
                f"  Fixed {updated} rows in "
                f"{app_label}.{model_name}"
            )


def reverse(apps, schema_editor):
    # No reversal — this migration performs data cleanup.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_complaint_subtypes"),
        ("tickets", "0003_add_dynamic_data"),
        ("notices", "0001_initial"),
        ("documents", "0002_extend_document_models"),
    ]

    operations = [
        migrations.RunPython(fix_nulls, reverse),
    ]