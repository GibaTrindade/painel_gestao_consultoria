from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitoramento", "0006_justificativanaoatingimentomensal"),
    ]

    operations = [
        migrations.AlterField(
            model_name="registrodiario",
            name="descricao_atividade",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="justificativanaoatingimentomensal",
            name="categoria",
            field=models.CharField(
                choices=[
                    ("falta_insumo", "Falta de insumo"),
                    ("falta_pessoal", "Falta de pessoal"),
                    ("problema_logistico", "Problema logistico"),
                    ("problema_sistema", "Problema no sistema"),
                    ("demanda_abaixo", "Demanda abaixo do previsto"),
                    ("ausencia_profissional", "Ausencia do profissional"),
                    ("outro", "Outro"),
                ],
                default="outro",
                max_length=40,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="justificativanaoatingimentomensal",
            name="detalhe_outro",
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name="justificativanaoatingimentomensal",
            name="justificativa",
            field=models.TextField(blank=True),
        ),
    ]
