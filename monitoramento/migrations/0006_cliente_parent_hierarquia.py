from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("monitoramento", "0005_indicadormetavigencia"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="parent",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="children", to="monitoramento.cliente"),
        ),
    ]
