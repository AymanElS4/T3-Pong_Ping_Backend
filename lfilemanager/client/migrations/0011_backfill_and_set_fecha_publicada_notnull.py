from django.db import migrations, models
import datetime


def backfill_fecha_publicada(apps, schema_editor):
    CodigoLegal = apps.get_model("client", "CodigoLegal")
    default = datetime.date(2026, 6, 30)
    # Update rows where fecha_publicada is NULL
    CodigoLegal.objects.filter(fecha_publicada__isnull=True).update(
        fecha_publicada=default
    )


class Migration(migrations.Migration):

    dependencies = [
        ("client", "0010_alter_fecha_publicada_nullable"),
    ]

    operations = [
        migrations.RunPython(
            backfill_fecha_publicada, reverse_code=migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name="codigolegal",
            name="fecha_publicada",
            field=models.DateField(auto_now_add=True),
        ),
    ]
