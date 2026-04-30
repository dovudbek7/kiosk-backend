from django.db import migrations


DEFAULT_NAME = 'Oltiariq'
DEFAULT_SLUG = 'oltiariq'


def create_default_and_backfill(apps, schema_editor):
    District = apps.get_model('api_v1', 'District')
    district, _ = District.objects.get_or_create(
        slug=DEFAULT_SLUG,
        defaults={'name': DEFAULT_NAME, 'is_active': True},
    )

    for model_name in ('ApplicationTarget', 'Message', 'Ring', 'KioskVisit', 'ServiceRequest'):
        Model = apps.get_model('api_v1', model_name)
        Model.objects.filter(district__isnull=True).update(district=district)


def reverse_noop(apps, schema_editor):
    # We don't unset districts on rollback; keeping them is safe.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api_v1', '0011_add_district'),
    ]

    operations = [
        migrations.RunPython(create_default_and_backfill, reverse_noop),
    ]
