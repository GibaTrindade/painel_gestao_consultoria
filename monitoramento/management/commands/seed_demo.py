from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from monitoramento.models import (
    AcaoMelhoria,
    AcaoAtribuicao,
    Cliente,
    Diagnostico,
    Equipe,
    Funcionario,
    Indicador,
    PerfilUsuario,
    RegistroDiario,
    Tarefa,
    UsuarioCliente,
)


class Command(BaseCommand):
    help = "Cria dados de exemplo para validar o painel rapidamente."

    def handle(self, *args, **options):
        admin_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={"first_name": "Administrador", "last_name": "SMR", "email": "admin@smr.local"},
        )
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.set_password("admin123")
        admin_user.save()
        PerfilUsuario.objects.update_or_create(user=admin_user, defaults={"tipo": PerfilUsuario.TipoPerfil.ADMIN})

        cliente, _ = Cliente.objects.update_or_create(
            nome="Fazenda Maracaja",
            defaults={
                "codigo_acesso": "maracaja",
                "tipo": "empresa",
                "responsavel": "Marcos Lima",
                "email": "contato@maracaja.local",
                "cidade": "Maracajau",
                "uf": "RN",
            },
        )

        equipe, _ = Equipe.objects.update_or_create(
            cliente=cliente,
            nome="Equipe 1",
            defaults={"descricao": "Operacao de producao"},
        )
        equipe2, _ = Equipe.objects.update_or_create(
            cliente=cliente,
            nome="Equipe 2",
            defaults={"descricao": "Apoio logistico"},
        )

        gestor_user, _ = User.objects.get_or_create(
            username="gestor",
            defaults={
                "first_name": "Marcos",
                "last_name": "Gestor",
                "email": "gestor@maracaja.local",
            },
        )
        gestor_user.set_password("gestor123")
        gestor_user.save()
        PerfilUsuario.objects.update_or_create(
            user=gestor_user,
            defaults={
                "tipo": PerfilUsuario.TipoPerfil.CLIENTE,
                "cliente": cliente,
                "cargo": "Gestor",
            },
        )
        UsuarioCliente.objects.update_or_create(
            user=gestor_user,
            cliente=cliente,
            defaults={"tipo": PerfilUsuario.TipoPerfil.CLIENTE, "ativo": True},
        )

        profissionais = []
        for username, first_name, equipe_obj, dias, funcao in [
            ("suel", "Sueldison", equipe, "Segunda / Quarta / Sexta", "Supervisor"),
            ("marcosp", "Sr Marcos", equipe, "Terca / Quinta", "Operador"),
            ("manoel", "Manoel", equipe2, "Sabado / Domingo", "Auxiliar"),
        ]:
            user, _ = User.objects.get_or_create(username=username, defaults={"first_name": first_name})
            user.first_name = first_name
            user.set_password("func123")
            user.save()
            PerfilUsuario.objects.update_or_create(
                user=user,
                defaults={"tipo": PerfilUsuario.TipoPerfil.FUNCIONARIO, "cliente": cliente, "cargo": funcao},
            )
            UsuarioCliente.objects.update_or_create(
                user=user,
                cliente=cliente,
                defaults={"tipo": PerfilUsuario.TipoPerfil.FUNCIONARIO, "ativo": True},
            )
            profissionais.append(
                Funcionario.objects.update_or_create(
                    user=user,
                    cliente=cliente,
                    defaults={
                        "equipe": equipe_obj,
                        "funcao": funcao,
                        "dias_trabalho": dias,
                    },
                )[0]
            )

        diagnostico, _ = Diagnostico.objects.update_or_create(
            cliente=cliente,
            titulo="Dobrar producao de leite e derivados",
            defaults={
                "descricao": "Plano estruturado para ampliar produtividade.",
                "periodo_inicio": date(2026, 1, 1),
                "periodo_fim": date(2026, 12, 31),
                "periodo_melhoria_inicio": date(2026, 1, 1),
                "periodo_melhoria_fim": date(2026, 12, 31),
                "status": Diagnostico.Status.EXECUCAO,
                "causa_gargalo": "Transporte lento e baixa capacidade de fermentacao.",
            },
        )

        indicador_queijo, _ = Indicador.objects.update_or_create(
            diagnostico=diagnostico,
            nome="Producao de queijo",
            defaults={
                "codigo": "77",
                "meta_valor": Decimal("500"),
                "valor_atual": Decimal("110"),
                "unidade": "mensal",
            },
        )
        indicador_iogurte, _ = Indicador.objects.update_or_create(
            diagnostico=diagnostico,
            nome="Producao de leite fermentado",
            defaults={
                "codigo": "103",
                "meta_valor": Decimal("100"),
                "valor_atual": Decimal("13"),
                "unidade": "mensal",
            },
        )

        acao1, _ = AcaoMelhoria.objects.update_or_create(
            indicador=indicador_queijo,
            nome="Transportar o leite mais rapido",
            defaults={
                "meta_mensal": Decimal("30"),
                "status": AcaoMelhoria.Status.ATIVA,
                "responsavel": profissionais[0].user,
            },
        )
        acao2, _ = AcaoMelhoria.objects.update_or_create(
            indicador=indicador_queijo,
            nome="Colocar produtos para fermentacao",
            defaults={
                "meta_mensal": Decimal("15"),
                "status": AcaoMelhoria.Status.ATIVA,
                "responsavel": profissionais[1].user,
            },
        )
        acao3, _ = AcaoMelhoria.objects.update_or_create(
            indicador=indicador_iogurte,
            nome="Armazenar em potes novos",
            defaults={
                "meta_mensal": Decimal("50"),
                "status": AcaoMelhoria.Status.INATIVA,
                "responsavel": profissionais[2].user,
            },
        )

        AcaoAtribuicao.objects.update_or_create(
            acao=acao1,
            funcionario=profissionais[0],
            defaults={"valor_mensal": Decimal("200"), "ativo": True},
        )
        AcaoAtribuicao.objects.update_or_create(
            acao=acao1,
            funcionario=profissionais[1],
            defaults={"valor_mensal": Decimal("100"), "ativo": False},
        )

        tarefas = [
            Tarefa.objects.update_or_create(
                acao=acao1,
                funcionario=profissionais[0],
                titulo="Acelerar coleta de leite",
                defaults={"meta_quantidade": Decimal("10"), "prazo": date(2026, 4, 30)},
            )[0],
            Tarefa.objects.update_or_create(
                acao=acao2,
                funcionario=profissionais[1],
                titulo="Organizar nova fermentacao",
                defaults={"meta_quantidade": Decimal("8"), "prazo": date(2026, 4, 30)},
            )[0],
            Tarefa.objects.update_or_create(
                acao=acao3,
                funcionario=profissionais[2],
                titulo="Separar novos potes",
                defaults={"meta_quantidade": Decimal("12"), "prazo": date(2026, 4, 30)},
            )[0],
        ]

        RegistroDiario.objects.update_or_create(
            tarefa=tarefas[0],
            funcionario=profissionais[0],
            data=date.today(),
            defaults={
                "descricao_atividade": "Reduziu o tempo de coleta da materia-prima.",
                "quantidade_realizada": Decimal("6"),
                "justificativa": "Equipe completa em campo.",
            },
        )
        RegistroDiario.objects.update_or_create(
            tarefa=tarefas[1],
            funcionario=profissionais[1],
            data=date.today(),
            defaults={
                "descricao_atividade": "Organizou a area de fermentacao e iniciou o lote.",
                "quantidade_realizada": Decimal("4"),
                "justificativa": "Parte do lote atrasou por manutencao.",
            },
        )
        RegistroDiario.objects.update_or_create(
            tarefa=tarefas[2],
            funcionario=profissionais[2],
            data=date.today(),
            defaults={
                "descricao_atividade": "Separou estoque de potes e revisou perdas.",
                "quantidade_realizada": Decimal("2"),
                "justificativa": "Fornecedor entregou abaixo do esperado.",
            },
        )

        self.stdout.write(self.style.SUCCESS("Base demo criada."))
        self.stdout.write("Usuarios de acesso:")
        self.stdout.write("codigo da organizacao: maracaja")
        self.stdout.write("codigo mestre: smr-admin")
        self.stdout.write("admin / admin123")
        self.stdout.write("gestor / gestor123")
        self.stdout.write("suel / func123")
