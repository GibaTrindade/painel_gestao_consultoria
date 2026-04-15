from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from monitoramento.models import (
    AcaoAtribuicao,
    AcaoMelhoria,
    Cliente,
    Diagnostico,
    Equipe,
    Funcionario,
    Indicador,
    JustificativaNaoAtingimentoMensal,
    PerfilUsuario,
    RegistroDiario,
    Tarefa,
    UsuarioCliente,
)
from monitoramento.views import _registrar_meta_vigencia, _sincronizar_indicador_competencia


class Command(BaseCommand):
    help = "Cria dados de exemplo para validar o painel rapidamente."

    def criar_usuario(self, username, password, first_name, last_name="", email=""):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={"first_name": first_name, "last_name": last_name, "email": email},
        )
        user.first_name = first_name
        user.last_name = last_name
        if email:
            user.email = email
        user.set_password(password)
        user.save()
        return user

    def vincular_acesso(self, user, cliente, tipo, cargo=""):
        PerfilUsuario.objects.update_or_create(
            user=user,
            defaults={"tipo": tipo, "cliente": cliente, "cargo": cargo},
        )
        UsuarioCliente.objects.update_or_create(
            user=user,
            cliente=cliente,
            defaults={"tipo": tipo, "ativo": True},
        )

    def criar_funcionario(self, username, nome, cliente, equipe, funcao, password="func123", dias="Segunda / Sexta"):
        user = self.criar_usuario(username, password, nome)
        self.vincular_acesso(user, cliente, PerfilUsuario.TipoPerfil.FUNCIONARIO, funcao)
        funcionario, _ = Funcionario.objects.update_or_create(
            user=user,
            cliente=cliente,
            defaults={
                "equipe": equipe,
                "funcao": funcao,
                "dias_trabalho": dias,
                "ativo": True,
            },
        )
        return funcionario

    def criar_registro(self, tarefa, funcionario, data_ref, previsto, realizado, descricao, situacao, justificativa=""):
        RegistroDiario.objects.update_or_create(
            tarefa=tarefa,
            funcionario=funcionario,
            data=data_ref,
            defaults={
                "descricao_atividade": descricao,
                "quantidade_prevista": previsto,
                "quantidade_realizada": realizado,
                "situacao": situacao,
                "justificativa": justificativa,
            },
        )

    def justificar_mes(self, tarefa, funcionario, competencia, categoria, justificativa):
        JustificativaNaoAtingimentoMensal.objects.update_or_create(
            tarefa=tarefa,
            competencia=competencia,
            defaults={
                "funcionario": funcionario,
                "categoria": categoria,
                "justificativa": justificativa,
            },
        )

    def handle(self, *args, **options):
        admin_user = self.criar_usuario("admin", "admin123", "Administrador", "SMR", "admin@smr.local")
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        PerfilUsuario.objects.update_or_create(user=admin_user, defaults={"tipo": PerfilUsuario.TipoPerfil.ADMIN})

        self.seed_maracaja()
        self.seed_hierarquia_prefeitura()

        self.stdout.write(self.style.SUCCESS("Base demo criada/atualizada com hierarquia."))
        self.stdout.write("Acessos principais:")
        self.stdout.write("codigo mestre: smr-admin")
        self.stdout.write("admin / admin123")
        self.stdout.write("codigo: maracaja -> gestor / gestor123")
        self.stdout.write("codigo: pref-ne -> gestor-pref / gestor123")
        self.stdout.write("codigo: upa-centro-ne -> bia-upa / func123")
        self.stdout.write("codigo: upa-norte-ne -> mirella-upa / func123")

    def seed_maracaja(self):
        cliente, _ = Cliente.objects.update_or_create(
            nome="Fazenda Maracaja",
            defaults={
                "codigo_acesso": "maracaja",
                "tipo": "empresa",
                "responsavel": "Marcos Lima",
                "email": "contato@maracaja.local",
                "cidade": "Maracajau",
                "uf": "RN",
                "parent": None,
            },
        )

        equipe = Equipe.objects.update_or_create(
            cliente=cliente,
            nome="Equipe 1",
            defaults={"descricao": "Operacao de producao"},
        )[0]
        equipe2 = Equipe.objects.update_or_create(
            cliente=cliente,
            nome="Equipe 2",
            defaults={"descricao": "Apoio logistico"},
        )[0]

        gestor_user = self.criar_usuario("gestor", "gestor123", "Marcos", "Gestor", "gestor@maracaja.local")
        self.vincular_acesso(gestor_user, cliente, PerfilUsuario.TipoPerfil.CLIENTE, "Gestor")

        profissionais = [
            self.criar_funcionario("suel", "Sueldison", cliente, equipe, "Supervisor", dias="Segunda / Quarta / Sexta"),
            self.criar_funcionario("marcosp", "Sr Marcos", cliente, equipe, "Operador", dias="Terca / Quinta"),
            self.criar_funcionario("manoel", "Manoel", cliente, equipe2, "Auxiliar", dias="Sabado / Domingo"),
        ]

        diagnostico = Diagnostico.objects.update_or_create(
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
        )[0]

        indicador_queijo = Indicador.objects.update_or_create(
            diagnostico=diagnostico,
            nome="Producao de queijo",
            defaults={"meta_valor": Decimal("500"), "valor_atual": Decimal("0"), "unidade": "mensal"},
        )[0]
        _registrar_meta_vigencia(indicador_queijo, Decimal("500"), date(2026, 1, 1))

        acao1 = AcaoMelhoria.objects.update_or_create(
            indicador=indicador_queijo,
            nome="Transportar o leite mais rapido",
            defaults={
                "meta_mensal": Decimal("30"),
                "status": AcaoMelhoria.Status.ATIVA,
                "responsavel": profissionais[0].user,
            },
        )[0]

        AcaoAtribuicao.objects.update_or_create(
            acao=acao1,
            funcionario=profissionais[0],
            defaults={"valor_mensal": Decimal("30"), "ativo": True},
        )
        tarefa = Tarefa.objects.update_or_create(
            acao=acao1,
            funcionario=profissionais[0],
            titulo="Acelerar coleta de leite",
            defaults={
                "meta_quantidade": Decimal("10"),
                "previsto_quantidade": Decimal("10"),
                "prazo": date(2026, 4, 30),
            },
        )[0]
        self.criar_registro(
            tarefa,
            profissionais[0],
            date(2026, 4, 10),
            Decimal("10"),
            Decimal("6"),
            "Reduziu o tempo de coleta da materia-prima.",
            Tarefa.Situacao.EM_ANDAMENTO,
            "Equipe completa em campo.",
        )
        _sincronizar_indicador_competencia(indicador_queijo, date(2026, 4, 1))

    def seed_hierarquia_prefeitura(self):
        prefeitura = Cliente.objects.update_or_create(
            nome="Prefeitura de Nova Esperanca",
            defaults={
                "codigo_acesso": "pref-ne",
                "tipo": "prefeitura",
                "responsavel": "Helena Duarte",
                "cidade": "Nova Esperanca",
                "uf": "RN",
                "parent": None,
            },
        )[0]
        secretaria = Cliente.objects.update_or_create(
            nome="Secretaria Municipal de Saude",
            defaults={
                "codigo_acesso": "secsaude-ne",
                "tipo": "secretaria",
                "responsavel": "Dr. Paulo Neri",
                "cidade": "Nova Esperanca",
                "uf": "RN",
                "parent": prefeitura,
            },
        )[0]
        upa_centro = Cliente.objects.update_or_create(
            nome="UPA Centro NE",
            defaults={
                "codigo_acesso": "upa-centro-ne",
                "tipo": "upa",
                "responsavel": "Luciana Centro",
                "cidade": "Nova Esperanca",
                "uf": "RN",
                "parent": secretaria,
            },
        )[0]
        upa_norte = Cliente.objects.update_or_create(
            nome="UPA Norte NE",
            defaults={
                "codigo_acesso": "upa-norte-ne",
                "tipo": "upa",
                "responsavel": "Ronaldo Norte",
                "cidade": "Nova Esperanca",
                "uf": "RN",
                "parent": secretaria,
            },
        )[0]

        gestor_pref = self.criar_usuario("gestor-pref", "gestor123", "Helena", "Prefeitura")
        self.vincular_acesso(gestor_pref, prefeitura, PerfilUsuario.TipoPerfil.CLIENTE, "Gestora municipal")
        gestor_secretaria = self.criar_usuario("gestor-saude", "gestor123", "Paulo", "Saude")
        self.vincular_acesso(gestor_secretaria, secretaria, PerfilUsuario.TipoPerfil.CLIENTE, "Secretario de saude")
        gestor_centro = self.criar_usuario("gestor-centro", "gestor123", "Luciana", "Centro")
        self.vincular_acesso(gestor_centro, upa_centro, PerfilUsuario.TipoPerfil.CLIENTE, "Gestora da UPA Centro")
        gestor_norte = self.criar_usuario("gestor-norte", "gestor123", "Ronaldo", "Norte")
        self.vincular_acesso(gestor_norte, upa_norte, PerfilUsuario.TipoPerfil.CLIENTE, "Gestor da UPA Norte")

        equipe_centro_busca = Equipe.objects.update_or_create(
            cliente=upa_centro,
            nome="Busca Ativa Centro",
            defaults={"descricao": "Equipe de visitas e busca ativa"},
        )[0]
        equipe_centro_upa = Equipe.objects.update_or_create(
            cliente=upa_centro,
            nome="Aplicacao UPA Centro",
            defaults={"descricao": "Aplicacao interna na UPA"},
        )[0]
        equipe_norte_busca = Equipe.objects.update_or_create(
            cliente=upa_norte,
            nome="Busca Ativa Norte",
            defaults={"descricao": "Equipe de visitas na zona norte"},
        )[0]

        bia = self.criar_funcionario("bia-upa", "Bia", upa_centro, equipe_centro_upa, "Enfermeira")
        giba = self.criar_funcionario("giba-upa", "Giba", upa_centro, equipe_centro_busca, "Agente")
        arlindo = self.criar_funcionario("arlindo-upa", "Arlindo", upa_centro, equipe_centro_busca, "Agente")
        mirella = self.criar_funcionario("mirella-upa", "Mirella", upa_norte, equipe_norte_busca, "Enfermeira")
        nandinho = self.criar_funcionario("nandinho-upa", "Nandinho", upa_norte, equipe_norte_busca, "Agente")
        victor = self.criar_funcionario("victor-upa", "Victor", upa_norte, equipe_norte_busca, "Agente")

        diag_centro = Diagnostico.objects.update_or_create(
            cliente=upa_centro,
            titulo="Campanha de vacinacao - UPA Centro",
            defaults={
                "descricao": "Acompanhar aplicacao e busca ativa da UPA Centro.",
                "periodo_inicio": date(2026, 1, 1),
                "periodo_fim": date(2026, 12, 31),
                "periodo_melhoria_inicio": date(2026, 1, 1),
                "periodo_melhoria_fim": date(2026, 12, 31),
                "status": Diagnostico.Status.EXECUCAO,
                "causa_gargalo": "Oscilacao de insumos e equipes reduzidas em parte do mes.",
            },
        )[0]
        diag_norte = Diagnostico.objects.update_or_create(
            cliente=upa_norte,
            titulo="Campanha de vacinacao - UPA Norte",
            defaults={
                "descricao": "Acompanhar aplicacao e busca ativa da UPA Norte.",
                "periodo_inicio": date(2026, 1, 1),
                "periodo_fim": date(2026, 12, 31),
                "periodo_melhoria_inicio": date(2026, 1, 1),
                "periodo_melhoria_fim": date(2026, 12, 31),
                "status": Diagnostico.Status.EXECUCAO,
                "causa_gargalo": "Rotas longas e faltas pontuais de profissionais.",
            },
        )[0]

        indicador_centro = Indicador.objects.update_or_create(
            diagnostico=diag_centro,
            nome="Vacinas aplicadas na UPA Centro",
            defaults={"meta_valor": Decimal("50"), "valor_atual": Decimal("0"), "unidade": "mensal"},
        )[0]
        indicador_norte = Indicador.objects.update_or_create(
            diagnostico=diag_norte,
            nome="Vacinas aplicadas na UPA Norte",
            defaults={"meta_valor": Decimal("50"), "valor_atual": Decimal("0"), "unidade": "mensal"},
        )[0]

        _registrar_meta_vigencia(indicador_centro, Decimal("45"), date(2026, 2, 1))
        _registrar_meta_vigencia(indicador_centro, Decimal("50"), date(2026, 4, 1))
        _registrar_meta_vigencia(indicador_norte, Decimal("40"), date(2026, 2, 1))
        _registrar_meta_vigencia(indicador_norte, Decimal("50"), date(2026, 4, 1))

        acao_centro_busca = AcaoMelhoria.objects.update_or_create(
            indicador=indicador_centro,
            nome="Busca ativa de faltosos - Centro",
            defaults={
                "meta_mensal": Decimal("30"),
                "status": AcaoMelhoria.Status.ATIVA,
                "responsavel": gestor_centro,
            },
        )[0]
        acao_centro_upa = AcaoMelhoria.objects.update_or_create(
            indicador=indicador_centro,
            nome="Aplicacao interna na UPA Centro",
            defaults={
                "meta_mensal": Decimal("20"),
                "status": AcaoMelhoria.Status.ATIVA,
                "responsavel": bia.user,
            },
        )[0]
        acao_norte_busca = AcaoMelhoria.objects.update_or_create(
            indicador=indicador_norte,
            nome="Busca ativa de faltosos - Norte",
            defaults={
                "meta_mensal": Decimal("35"),
                "status": AcaoMelhoria.Status.ATIVA,
                "responsavel": gestor_norte,
            },
        )[0]
        acao_norte_upa = AcaoMelhoria.objects.update_or_create(
            indicador=indicador_norte,
            nome="Aplicacao interna na UPA Norte",
            defaults={
                "meta_mensal": Decimal("15"),
                "status": AcaoMelhoria.Status.ATIVA,
                "responsavel": mirella.user,
            },
        )[0]

        AcaoAtribuicao.objects.update_or_create(
            acao=acao_centro_busca,
            equipe=equipe_centro_busca,
            defaults={"valor_mensal": Decimal("30"), "ativo": True, "modo_rateio": AcaoAtribuicao.ModoRateio.AUTOMATICO},
        )
        AcaoAtribuicao.objects.update_or_create(
            acao=acao_centro_upa,
            funcionario=bia,
            defaults={"valor_mensal": Decimal("20"), "ativo": True},
        )
        AcaoAtribuicao.objects.update_or_create(
            acao=acao_norte_busca,
            equipe=equipe_norte_busca,
            defaults={"valor_mensal": Decimal("35"), "ativo": True, "modo_rateio": AcaoAtribuicao.ModoRateio.AUTOMATICO},
        )
        AcaoAtribuicao.objects.update_or_create(
            acao=acao_norte_upa,
            funcionario=mirella,
            defaults={"valor_mensal": Decimal("15"), "ativo": True},
        )

        tarefas = {
            "giba": Tarefa.objects.update_or_create(
                acao=acao_centro_busca,
                funcionario=giba,
                titulo="Busca ativa - Giba",
                defaults={"meta_quantidade": Decimal("15"), "previsto_quantidade": Decimal("15"), "prazo": date(2026, 4, 30)},
            )[0],
            "arlindo": Tarefa.objects.update_or_create(
                acao=acao_centro_busca,
                funcionario=arlindo,
                titulo="Busca ativa - Arlindo",
                defaults={"meta_quantidade": Decimal("15"), "previsto_quantidade": Decimal("15"), "prazo": date(2026, 4, 30)},
            )[0],
            "bia": Tarefa.objects.update_or_create(
                acao=acao_centro_upa,
                funcionario=bia,
                titulo="Aplicacao interna - Bia",
                defaults={"meta_quantidade": Decimal("20"), "previsto_quantidade": Decimal("20"), "prazo": date(2026, 4, 30)},
            )[0],
            "mirella": Tarefa.objects.update_or_create(
                acao=acao_norte_upa,
                funcionario=mirella,
                titulo="Aplicacao interna - Mirella",
                defaults={"meta_quantidade": Decimal("15"), "previsto_quantidade": Decimal("15"), "prazo": date(2026, 4, 30)},
            )[0],
            "nandinho": Tarefa.objects.update_or_create(
                acao=acao_norte_busca,
                funcionario=nandinho,
                titulo="Busca ativa - Nandinho",
                defaults={"meta_quantidade": Decimal("18"), "previsto_quantidade": Decimal("18"), "prazo": date(2026, 4, 30)},
            )[0],
            "victor": Tarefa.objects.update_or_create(
                acao=acao_norte_busca,
                funcionario=victor,
                titulo="Busca ativa - Victor",
                defaults={"meta_quantidade": Decimal("17"), "previsto_quantidade": Decimal("17"), "prazo": date(2026, 4, 30)},
            )[0],
        }

        # Fevereiro
        self.criar_registro(tarefas["giba"], giba, date(2026, 2, 12), Decimal("15"), Decimal("14"), "Visitou quadras da zona central.", Tarefa.Situacao.EM_ANDAMENTO, "Roteiro fluido.")
        self.criar_registro(tarefas["arlindo"], arlindo, date(2026, 2, 12), Decimal("15"), Decimal("13"), "Apoio na busca ativa.", Tarefa.Situacao.EM_ANDAMENTO, "Cobriu microarea extra.")
        self.criar_registro(tarefas["bia"], bia, date(2026, 2, 12), Decimal("20"), Decimal("18"), "Aplicou vacinas no fluxo interno.", Tarefa.Situacao.EM_ANDAMENTO, "Fila controlada.")
        self.criar_registro(tarefas["mirella"], mirella, date(2026, 2, 12), Decimal("15"), Decimal("12"), "Aplicacao na recepcao.", Tarefa.Situacao.EM_ANDAMENTO, "Faltou parte dos insumos.")
        self.criar_registro(tarefas["nandinho"], nandinho, date(2026, 2, 12), Decimal("18"), Decimal("10"), "Busca ativa parcial.", Tarefa.Situacao.EM_ANDAMENTO, "Equipe desfalcada.")
        self.criar_registro(tarefas["victor"], victor, date(2026, 2, 12), Decimal("17"), Decimal("8"), "Rotas externas.", Tarefa.Situacao.EM_ANDAMENTO, "Veiculo em manutencao.")

        # Marco
        self.criar_registro(tarefas["giba"], giba, date(2026, 3, 11), Decimal("15"), Decimal("15"), "Busca ativa batida no mes.", Tarefa.Situacao.CONCLUIDA, "Meta cumprida.")
        self.criar_registro(tarefas["arlindo"], arlindo, date(2026, 3, 11), Decimal("15"), Decimal("15"), "Cobertura completa da agenda.", Tarefa.Situacao.CONCLUIDA, "Meta cumprida.")
        self.criar_registro(tarefas["bia"], bia, date(2026, 3, 11), Decimal("20"), Decimal("20"), "Aplicacao interna concluida.", Tarefa.Situacao.CONCLUIDA, "Meta cumprida.")
        self.criar_registro(tarefas["mirella"], mirella, date(2026, 3, 11), Decimal("15"), Decimal("14"), "Aplicacao quase completa.", Tarefa.Situacao.EM_ANDAMENTO, "Faltou um turno.")
        self.criar_registro(tarefas["nandinho"], nandinho, date(2026, 3, 11), Decimal("18"), Decimal("12"), "Busca ativa com rotas parciais.", Tarefa.Situacao.EM_ANDAMENTO, "Falta de pessoal no turno da tarde.")
        self.criar_registro(tarefas["victor"], victor, date(2026, 3, 11), Decimal("17"), Decimal("11"), "Cobriu visitas de reforco.", Tarefa.Situacao.EM_ANDAMENTO, "Distancias maiores que o previsto.")

        # Abril - mistura de metas cumpridas e nao cumpridas para dashboard atual
        self.criar_registro(tarefas["giba"], giba, date(2026, 4, 10), Decimal("15"), Decimal("15"), "Busca ativa concluida em abril.", Tarefa.Situacao.CONCLUIDA, "Meta cumprida.")
        self.criar_registro(tarefas["arlindo"], arlindo, date(2026, 4, 10), Decimal("15"), Decimal("12"), "Cobertura parcial da area central.", Tarefa.Situacao.EM_ANDAMENTO, "Ausencia de profissional em um dos dias.")
        self.criar_registro(tarefas["bia"], bia, date(2026, 4, 10), Decimal("20"), Decimal("20"), "Fluxo interno completo.", Tarefa.Situacao.CONCLUIDA, "Meta cumprida.")
        self.criar_registro(tarefas["mirella"], mirella, date(2026, 4, 10), Decimal("15"), Decimal("10"), "Aplicacao interna abaixo do esperado.", Tarefa.Situacao.EM_ANDAMENTO, "Falta de insumo em dois dias.")
        self.criar_registro(tarefas["nandinho"], nandinho, date(2026, 4, 10), Decimal("18"), Decimal("9"), "Busca ativa abaixo do planejado.", Tarefa.Situacao.EM_ANDAMENTO, "Equipe reduzida e chuva forte.")
        self.criar_registro(tarefas["victor"], victor, date(2026, 4, 10), Decimal("17"), Decimal("8"), "Visitas externas com atraso.", Tarefa.Situacao.ATRASADA, "Problema logistico no veiculo.")

        self.justificar_mes(
            tarefas["arlindo"],
            arlindo,
            date(2026, 4, 1),
            JustificativaNaoAtingimentoMensal.CategoriaGargalo.AUSENCIA_PROFISSIONAL,
            "Um agente faltou em um dos turnos e a microarea precisou ser redistribuida.",
        )
        self.justificar_mes(
            tarefas["mirella"],
            mirella,
            date(2026, 4, 1),
            JustificativaNaoAtingimentoMensal.CategoriaGargalo.FALTA_INSUMO,
            "Lote de seringas foi entregue abaixo do planejado.",
        )
        self.justificar_mes(
            tarefas["nandinho"],
            nandinho,
            date(2026, 4, 1),
            JustificativaNaoAtingimentoMensal.CategoriaGargalo.FALTA_PESSOAL,
            "Equipe reduzida no turno da tarde.",
        )
        self.justificar_mes(
            tarefas["victor"],
            victor,
            date(2026, 4, 1),
            JustificativaNaoAtingimentoMensal.CategoriaGargalo.PROBLEMA_LOGISTICO,
            "O carro usado nas visitas ficou parado para manutencao.",
        )

        for indicador in [indicador_centro, indicador_norte]:
            for competencia in [date(2026, 2, 1), date(2026, 3, 1), date(2026, 4, 1)]:
                _sincronizar_indicador_competencia(indicador, competencia)
