from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client as HttpClient
from django.test import TestCase

from .models import (
    AcaoAtribuicao,
    AcaoMelhoria,
    Cliente,
    Diagnostico,
    Equipe,
    Funcionario,
    Indicador,
    IndicadorHistoricoMensal,
    PerfilUsuario,
    RegistroDiario,
    Tarefa,
    UsuarioCliente,
)
from .forms import DiagnosticoForm


class BaseMonitoramentoTestCase(TestCase):
    def setUp(self):
        self.cliente_org = Cliente.objects.create(nome="Fazenda Maracaja", codigo_acesso="maracaja")
        self.equipe = Equipe.objects.create(cliente=self.cliente_org, nome="Equipe 1")
        self.gestor = User.objects.create_user(username="gestor", password="gestor123")
        PerfilUsuario.objects.create(
            user=self.gestor,
            tipo=PerfilUsuario.TipoPerfil.CLIENTE,
            cliente=self.cliente_org,
        )
        UsuarioCliente.objects.create(
            user=self.gestor,
            cliente=self.cliente_org,
            tipo=PerfilUsuario.TipoPerfil.CLIENTE,
        )

        self.func_user = User.objects.create_user(username="suel", password="func123", first_name="Sueldison")
        PerfilUsuario.objects.create(
            user=self.func_user,
            tipo=PerfilUsuario.TipoPerfil.FUNCIONARIO,
            cliente=self.cliente_org,
        )
        UsuarioCliente.objects.create(
            user=self.func_user,
            cliente=self.cliente_org,
            tipo=PerfilUsuario.TipoPerfil.FUNCIONARIO,
        )
        self.funcionario = Funcionario.objects.create(
            cliente=self.cliente_org,
            equipe=self.equipe,
            user=self.func_user,
            funcao="Supervisor",
        )

        self.diagnostico = Diagnostico.objects.create(
            cliente=self.cliente_org,
            titulo="Dobrar producao",
            periodo_inicio=date(2026, 1, 1),
            periodo_fim=date(2026, 12, 31),
        )
        self.indicador = Indicador.objects.create(
            diagnostico=self.diagnostico,
            nome="Producao de queijo",
            meta_valor=Decimal("500"),
            valor_atual=Decimal("100"),
        )
        self.acao = AcaoMelhoria.objects.create(
            indicador=self.indicador,
            nome="Transportar o leite mais rapido",
            meta_mensal=Decimal("30"),
        )
        self.client_http = HttpClient()

    def login_gestor(self):
        self.client_http.post("/accounts/organizacao/", {"codigo": "maracaja"})
        self.client_http.post("/accounts/login/", {"username": "gestor", "password": "gestor123"})


class LoginOrganizacaoTests(BaseMonitoramentoTestCase):
    def test_codigo_organizacao_redireciona_para_login(self):
        response = self.client_http.post("/accounts/organizacao/", {"codigo": "maracaja"})
        self.assertRedirects(response, "/accounts/login/")

    def test_login_no_contexto_da_organizacao_funciona(self):
        self.client_http.post("/accounts/organizacao/", {"codigo": "maracaja"})
        response = self.client_http.post("/accounts/login/", {"username": "gestor", "password": "gestor123"})
        self.assertRedirects(response, "/")

    def test_funcionario_e_redirecionado_para_area_de_metas(self):
        self.client_http.post("/accounts/organizacao/", {"codigo": "maracaja"})
        self.client_http.post("/accounts/login/", {"username": "suel", "password": "func123"})
        response = self.client_http.get("/")
        self.assertRedirects(response, "/app/metas/")


class AtribuicaoAcaoTests(BaseMonitoramentoTestCase):
    def test_confirma_lote_de_atribuicoes_pendentes(self):
        self.login_gestor()

        response = self.client_http.post(
            f"/acoes/?diagnostico={self.diagnostico.id}&indicador={self.indicador.id}&acao={self.acao.id}&modal=atribuir_acao",
            {
                "form_name": "confirmar_atribuicoes",
                "acao_id": self.acao.id,
                "pending_assignments": (
                    '[{"tipo_destino":"funcionario","profissional":"%s","equipe_destino":"","nome_exibicao":"Sueldison","valor_mensal":"20","ativo":true}]'
                    % self.funcionario.id
                ),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            AcaoAtribuicao.objects.filter(
                acao=self.acao,
                funcionario=self.funcionario,
                valor_mensal=Decimal("20"),
                ativo=True,
            ).exists()
        )
        self.assertTrue(
            Tarefa.objects.filter(
                acao=self.acao,
                funcionario=self.funcionario,
                titulo=self.acao.nome,
                meta_quantidade=Decimal("20"),
            ).exists()
        )

    def test_modal_mostra_atribuicao_existente(self):
        AcaoAtribuicao.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            valor_mensal=Decimal("150"),
            ativo=True,
        )
        self.login_gestor()

        response = self.client_http.get(
            f"/acoes/?diagnostico={self.diagnostico.id}&indicador={self.indicador.id}&acao={self.acao.id}&modal=atribuir_acao"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sueldison")
        self.assertContains(response, "150")

    def test_atribuicao_para_equipe_gera_tarefas_para_membros_ativos(self):
        outro_user = User.objects.create_user(username="manoel", password="func123", first_name="Manoel")
        PerfilUsuario.objects.create(
            user=outro_user,
            tipo=PerfilUsuario.TipoPerfil.FUNCIONARIO,
            cliente=self.cliente_org,
        )
        UsuarioCliente.objects.create(
            user=outro_user,
            cliente=self.cliente_org,
            tipo=PerfilUsuario.TipoPerfil.FUNCIONARIO,
        )
        outro_funcionario = Funcionario.objects.create(
            cliente=self.cliente_org,
            equipe=self.equipe,
            user=outro_user,
            funcao="Operador",
        )

        self.login_gestor()

        response = self.client_http.post(
            f"/acoes/?diagnostico={self.diagnostico.id}&indicador={self.indicador.id}&acao={self.acao.id}&modal=atribuir_acao",
            {
                "form_name": "confirmar_atribuicoes",
                "acao_id": self.acao.id,
                "pending_assignments": (
                    '[{"tipo_destino":"equipe","profissional":"","equipe_destino":"%s","nome_exibicao":"Equipe 1","valor_mensal":"10","ativo":true}]'
                    % self.equipe.id
                ),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Tarefa.objects.filter(acao=self.acao, funcionario=self.funcionario, meta_quantidade=Decimal("10")).exists())
        self.assertTrue(Tarefa.objects.filter(acao=self.acao, funcionario=outro_funcionario, meta_quantidade=Decimal("10")).exists())

    def test_bloqueia_confirmacao_quando_soma_ultrapassa_meta_da_acao(self):
        self.login_gestor()

        response = self.client_http.post(
            f"/acoes/?diagnostico={self.diagnostico.id}&indicador={self.indicador.id}&acao={self.acao.id}&modal=atribuir_acao",
            {
                "form_name": "confirmar_atribuicoes",
                "acao_id": self.acao.id,
                "pending_assignments": (
                    '[{"tipo_destino":"funcionario","profissional":"%s","equipe_destino":"","nome_exibicao":"Sueldison","valor_mensal":"31","ativo":true}]'
                    % self.funcionario.id
                ),
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A soma dos valores mensais vinculados nao pode ultrapassar 30")
        self.assertFalse(AcaoAtribuicao.objects.filter(acao=self.acao, funcionario=self.funcionario, valor_mensal=Decimal("31")).exists())


class DiagnosticoStatusTests(BaseMonitoramentoTestCase):
    def test_formulario_de_edicao_mostra_datas_preenchidas(self):
        self.diagnostico.periodo_melhoria_inicio = date(2026, 2, 1)
        self.diagnostico.periodo_melhoria_fim = date(2026, 11, 30)
        self.diagnostico.save()

        form = DiagnosticoForm(instance=self.diagnostico)

        self.assertIn('value="2026-01-01"', str(form["periodo_inicio"]))
        self.assertIn('value="2026-12-31"', str(form["periodo_fim"]))
        self.assertIn('value="2026-02-01"', str(form["periodo_melhoria_inicio"]))
        self.assertIn('value="2026-11-30"', str(form["periodo_melhoria_fim"]))

    def test_edita_status_do_diagnostico(self):
        self.login_gestor()

        response = self.client_http.post(
            "/diagnosticos/",
            {
                "form_name": "editar_diagnostico",
                "diagnostico_id": self.diagnostico.id,
                "titulo": self.diagnostico.titulo,
                "status": "execucao",
                "periodo_inicio": "2026-01-01",
                "periodo_fim": "2026-12-31",
                "periodo_melhoria_inicio": "",
                "periodo_melhoria_fim": "",
                "descricao": "",
                "causa_gargalo": "Transporte lento",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.diagnostico.refresh_from_db()
        self.assertEqual(self.diagnostico.status, "execucao")
        self.assertEqual(self.diagnostico.causa_gargalo, "Transporte lento")


class IndicadorTests(BaseMonitoramentoTestCase):
    def test_novo_indicador_gera_codigo_automaticamente(self):
        self.login_gestor()

        response = self.client_http.post(
            "/indicadores/",
            {
                "form_name": "novo_indicador",
                "nome": "Producao de leite fermentado",
                "valor_atual": "0",
                "meta_valor": "100",
            },
        )

        self.assertEqual(response.status_code, 302)
        novo_indicador = Indicador.objects.get(nome="Producao de leite fermentado")
        self.assertTrue(novo_indicador.codigo.startswith("IND-"))

    def test_pagina_indicadores_exibe_modal_de_acoes(self):
        self.login_gestor()
        AcaoMelhoria.objects.create(
            indicador=self.indicador,
            nome="Acao modal",
            meta_mensal=Decimal("20"),
        )

        response = self.client_http.get(
            f"/indicadores/?diagnostico={self.diagnostico.id}&indicador={self.indicador.id}&modal=acoes_indicador"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acoes Vinculadas ao Indicador")
        self.assertContains(response, "Acao modal")


class FuncionarioAreaTests(BaseMonitoramentoTestCase):
    def test_funcionario_lanca_producao_na_tarefa(self):
        self.client_http.post("/accounts/organizacao/", {"codigo": "maracaja"})
        self.client_http.post("/accounts/login/", {"username": "suel", "password": "func123"})

        tarefa = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Pesar criancas",
            meta_quantidade=Decimal("7"),
        )

        response = self.client_http.post(
            f"/app/metas/?tarefa={tarefa.id}",
            {
                "tarefa_id": tarefa.id,
                "descricao_atividade": "Pesou os atendimentos do dia",
                "quantidade_realizada": "5",
                "justificativa": "Faltaram dois registros",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(RegistroDiario.objects.filter(tarefa=tarefa, funcionario=self.funcionario, quantidade_realizada=Decimal("5")).exists())

    def test_lancamento_do_funcionario_atualiza_indicador_automaticamente(self):
        self.client_http.post("/accounts/organizacao/", {"codigo": "maracaja"})
        self.client_http.post("/accounts/login/", {"username": "suel", "password": "func123"})

        tarefa = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Tarefa automatica",
            meta_quantidade=Decimal("30"),
        )

        response = self.client_http.post(
            f"/app/metas/?tarefa={tarefa.id}",
            {
                "tarefa_id": tarefa.id,
                "descricao_atividade": "Executou o processo do dia",
                "quantidade_realizada": "12",
                "justificativa": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.indicador.refresh_from_db()
        self.assertEqual(self.indicador.valor_atual, Decimal("12"))
        self.assertTrue(
            IndicadorHistoricoMensal.objects.filter(
                indicador=self.indicador,
                competencia=date(2026, 4, 1),
                valor=Decimal("12"),
            ).exists()
        )


class DashboardTests(BaseMonitoramentoTestCase):
    def test_dashboard_filtra_indicador_por_competencia(self):
        self.login_gestor()
        tarefa = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Coleta mensal",
            meta_quantidade=Decimal("30"),
        )
        RegistroDiario.objects.create(
            tarefa=tarefa,
            funcionario=self.funcionario,
            data=date(2026, 3, 10),
            descricao_atividade="Executou em marco",
            quantidade_prevista=Decimal("30"),
            quantidade_realizada=Decimal("250"),
        )

        response = self.client_http.get(
            f"/?competencia=2026-03&indicador={self.indicador.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["competencia_input"], "2026-03")
        self.assertEqual(response.context["indicador_percentual"], Decimal("50"))

    def test_dashboard_cards_de_indicador_refletem_registros_do_mes(self):
        self.login_gestor()
        tarefa = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Lote da Bia",
            meta_quantidade=Decimal("30"),
        )
        RegistroDiario.objects.create(
            tarefa=tarefa,
            funcionario=self.funcionario,
            data=date(2026, 4, 12),
            descricao_atividade="Entrega do dia",
            quantidade_prevista=Decimal("30"),
            quantidade_realizada=Decimal("110"),
        )

        response = self.client_http.get(f"/?competencia=2026-04&indicador={self.indicador.id}")

        self.assertEqual(response.status_code, 200)
        indicador_card = next(item for item in response.context["indicadores_cards"] if item["id"] == self.indicador.id)
        self.assertEqual(indicador_card["valor"], Decimal("110"))
        self.assertEqual(response.context["indicador_valor_competencia"], Decimal("110"))

    def test_dashboard_mostra_tarefas_ativas_do_profissional_selecionado(self):
        outro_user = User.objects.create_user(username="marcos", password="func123", first_name="Sr Marcos")
        PerfilUsuario.objects.create(
            user=outro_user,
            tipo=PerfilUsuario.TipoPerfil.FUNCIONARIO,
            cliente=self.cliente_org,
        )
        UsuarioCliente.objects.create(
            user=outro_user,
            cliente=self.cliente_org,
            tipo=PerfilUsuario.TipoPerfil.FUNCIONARIO,
        )
        outro_funcionario = Funcionario.objects.create(
            cliente=self.cliente_org,
            equipe=self.equipe,
            user=outro_user,
            funcao="Operador",
        )
        tarefa_suel = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Tarefa do Sueldison",
            meta_quantidade=Decimal("10"),
            situacao=Tarefa.Situacao.PENDENTE,
        )
        Tarefa.objects.create(
            acao=self.acao,
            funcionario=outro_funcionario,
            titulo="Tarefa do Marcos",
            meta_quantidade=Decimal("8"),
            situacao=Tarefa.Situacao.EM_ANDAMENTO,
        )

        self.login_gestor()
        response = self.client_http.get(
            f"/?competencia=2026-04&indicador={self.indicador.id}&funcionario={self.funcionario.id}"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["funcionario_selecionado"]["funcionario"].id, self.funcionario.id)
        self.assertIn(tarefa_suel, response.context["funcionario_tarefas_ativas"])
        modal_item = next(item for item in response.context["profissionais_modal_data"] if item["id"] == self.funcionario.id)
        self.assertTrue(any(tarefa["titulo"] == "Tarefa do Sueldison" for tarefa in modal_item["tarefas"]))

    def test_dashboard_kpi_de_acoes_usa_mesmo_consolidado_do_grafico(self):
        self.login_gestor()
        segunda_acao = AcaoMelhoria.objects.create(
            indicador=self.indicador,
            nome="Ajustar fermentacao",
            meta_mensal=Decimal("70"),
        )
        tarefa_1 = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Executar coleta",
            meta_quantidade=Decimal("30"),
        )
        tarefa_2 = Tarefa.objects.create(
            acao=segunda_acao,
            funcionario=self.funcionario,
            titulo="Ajustar tanque",
            meta_quantidade=Decimal("70"),
        )
        RegistroDiario.objects.create(
            tarefa=tarefa_1,
            funcionario=self.funcionario,
            data=date(2026, 4, 10),
            descricao_atividade="Coleta parcial",
            quantidade_prevista=Decimal("30"),
            quantidade_realizada=Decimal("4"),
        )
        RegistroDiario.objects.create(
            tarefa=tarefa_2,
            funcionario=self.funcionario,
            data=date(2026, 4, 10),
            descricao_atividade="Ajuste parcial",
            quantidade_prevista=Decimal("70"),
            quantidade_realizada=Decimal("0"),
        )

        response = self.client_http.get(f"/?competencia=2026-04&indicador={self.indicador.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["acao_media"], 4.0)
        self.assertEqual(response.context["comparativo_series"][-1]["acoes"], 4.0)

    def test_dashboard_entrega_dados_para_modal_de_tarefas_do_profissional(self):
        self.login_gestor()
        Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Visitar propriedade",
            meta_quantidade=Decimal("10"),
            situacao=Tarefa.Situacao.EM_ANDAMENTO,
        )

        response = self.client_http.get(f"/?competencia=2026-04&indicador={self.indicador.id}")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-open-worker-modal')
        self.assertContains(response, "dashboard-profissionais-modal-data")
        self.assertTrue(
            any(item["nome"] == "Sueldison" for item in response.context["profissionais_modal_data"])
        )
