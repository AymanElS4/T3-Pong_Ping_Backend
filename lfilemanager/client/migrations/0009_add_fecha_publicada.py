from django.db import migrations, models
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0008_alter_codigolegal_archivo_pdf_and_more'),
    ]

    operations = [
        # Add the new non-nullable date field with a one-off default 
        # for existing rows
        migrations.AddField(
            model_name='codigolegal',
            name='fecha_publicada',
            field=models.DateField(default=datetime.date(2026, 6, 30)),
        ),
        # Future created objects use auto_now_add behavior defined in the model
        migrations.AlterField(
            model_name='codigolegal',
            name='fecha_publicada',
            field=models.DateField(auto_now_add=True),
        ),
    ]
