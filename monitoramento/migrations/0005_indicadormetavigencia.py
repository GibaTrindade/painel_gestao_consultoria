from datetime import date

from django.db import migrations, models


def criar_vigencias_iniciais(apps, schema_editor):
    Indicador = apps.get_model("monitoramento", "Indicador")
    IndicadorMetaVigencia = apps.get_model("monitoramento", "IndicadorMetaVigencia")

    for indicador in Indicador.objects.all():
        referencia = indicador.created_at.date() if indicador.created_at else date.today()
        inicio_vigencia = referencia.replace(day=1)
        IndicadorMetaVigencia.objects.get_or_create(
            indicador=indicador,
            inicio_vigencia=inicio_vigencia,
            defaults={
                "valor_meta": indicador.meta_valor,
                "fim_vigencia": None,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("monitoramento", "0004_acaoatribuicao_modo_rateio_and_distribuicao"),
    ]

    operations = [
        migrations.CreateModel(
            name="IndicadorMetaVigencia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("inicio_vigencia", models.DateField(help_text="Use o primeiro dia do mes como inicio da vigencia.")),
                ("fim_vigencia", models.DateField(blank=True, null=True)),
                ("valor_meta", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("indicador", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="meta_vigencias", to="monitoramento.indicador")),
            ],
            options={
                "ordering": ["-inicio_vigencia"],
                "unique_together": {("indicador", "inicio_vigencia")},
            },
        ),
        migrations.RunPython(criar_vigencias_iniciais, migrations.RunPython.noop),
    ]
