from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("client", "0009_add_fecha_publicada"),
    ]

    operations = [
        migrations.AlterField(
            model_name="codigolegal",
            name="fecha_publicada",
            field=models.DateField(null=True, blank=True),
        ),
    ]
