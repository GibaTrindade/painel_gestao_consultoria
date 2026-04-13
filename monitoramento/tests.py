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
    IndicadorMetaVigencia,
    JustificativaNaoAtingimentoMensal,
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

    def test_usuario_hibrido_pode_alternar_entre_gestor_e_funcionario(self):
        hybrid_user = User.objects.create_user(username="lider", password="lider123", first_name="Lider")
        UsuarioCliente.objects.create(
            user=hybrid_user,
            cliente=self.cliente_org,
            tipo=PerfilUsuario.TipoPerfil.CLIENTE,
        )
        Funcionario.objects.create(
            cliente=self.cliente_org,
            equipe=self.equipe,
            user=hybrid_user,
            funcao="Lider de campo",
        )

        self.client_http.post("/accounts/organizacao/", {"codigo": "maracaja"})
        self.client_http.post("/accounts/login/", {"username": "lider", "password": "lider123"})

        response_dashboard = self.client_http.get("/")
        self.assertEqual(response_dashboard.status_code, 200)
        self.assertContains(response_dashboard, "Entrar como funcionario")

        response_switch = self.client_http.post(
            "/alternar-modo/",
            {"modo": "funcionario", "next": "/"},
        )
        self.assertEqual(response_switch.status_code, 302)
        self.assertEqual(response_switch.url, "/")

        response_worker = self.client_http.get("/")
        self.assertRedirects(response_worker, "/app/metas/")

        response_back = self.client_http.post(
            "/alternar-modo/",
            {"modo": "gestor", "next": "/"},
        )
        self.assertEqual(response_back.status_code, 302)
        self.assertEqual(response_back.url, "/")

        response_dashboard_again = self.client_http.get("/")
        self.assertEqual(response_dashboard_again.status_code, 200)
        self.assertContains(response_dashboard_again, "Entrar como funcionario")


class AtribuicaoAcaoTests(BaseMonitoramentoTestCase):
    def test_nova_acao_pode_definir_responsavel(self):
        self.login_gestor()

        response = self.client_http.post(
            f"/acoes/?diagnostico={self.diagnostico.id}&indicador={self.indicador.id}&competencia=2026-04",
            {
                "form_name": "nova_acao",
                "nome": "Buscar faltosos",
                "meta_mensal": "45",
                "status": "ativa",
                "responsavel": str(self.gestor.id),
            },
        )

        self.assertEqual(response.status_code, 302)
        acao = AcaoMelhoria.objects.get(nome="Buscar faltosos")
        self.assertEqual(acao.responsavel, self.gestor)

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
        self.assertTrue(Tarefa.objects.filter(acao=self.acao, funcionario=self.funcionario, meta_quantidade=Decimal("5")).exists())
        self.assertTrue(Tarefa.objects.filter(acao=self.acao, funcionario=outro_funcionario, meta_quantidade=Decimal("5")).exists())

    def test_rateio_para_equipe_preserva_valor_total_com_inteiros(self):
        outro_user = User.objects.create_user(username="manoel2", password="func123", first_name="Manoel")
        terceiro_user = User.objects.create_user(username="joana", password="func123", first_name="Joana")
        for user in [outro_user, terceiro_user]:
            PerfilUsuario.objects.create(
                user=user,
                tipo=PerfilUsuario.TipoPerfil.FUNCIONARIO,
                cliente=self.cliente_org,
            )
            UsuarioCliente.objects.create(
                user=user,
                cliente=self.cliente_org,
                tipo=PerfilUsuario.TipoPerfil.FUNCIONARIO,
            )
        Funcionario.objects.create(
            cliente=self.cliente_org,
            equipe=self.equipe,
            user=outro_user,
            funcao="Operador",
        )
        Funcionario.objects.create(
            cliente=self.cliente_org,
            equipe=self.equipe,
            user=terceiro_user,
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
        metas = list(Tarefa.objects.filter(acao=self.acao).order_by("id").values_list("meta_quantidade", flat=True))
        self.assertEqual(sum(metas, Decimal("0")), Decimal("10"))
        self.assertEqual(metas, [Decimal("3"), Decimal("3"), Decimal("4")])

    def test_atribuicao_manual_para_equipe_respeita_distribuicao_por_membro(self):
        outro_user = User.objects.create_user(username="manoel3", password="func123", first_name="Manoel")
        terceiro_user = User.objects.create_user(username="joana2", password="func123", first_name="Joana")
        funcionarios = [self.func_user, outro_user, terceiro_user]
        for user in [outro_user, terceiro_user]:
            PerfilUsuario.objects.create(
                user=user,
                tipo=PerfilUsuario.TipoPerfil.FUNCIONARIO,
                cliente=self.cliente_org,
            )
            UsuarioCliente.objects.create(
                user=user,
                cliente=self.cliente_org,
                tipo=PerfilUsuario.TipoPerfil.FUNCIONARIO,
            )
        outro_funcionario = Funcionario.objects.create(
            cliente=self.cliente_org,
            equipe=self.equipe,
            user=outro_user,
            funcao="Operador",
        )
        terceiro_funcionario = Funcionario.objects.create(
            cliente=self.cliente_org,
            equipe=self.equipe,
            user=terceiro_user,
            funcao="Operador",
        )

        self.login_gestor()

        response = self.client_http.post(
            f"/acoes/?diagnostico={self.diagnostico.id}&indicador={self.indicador.id}&acao={self.acao.id}&modal=atribuir_acao",
            {
                "form_name": "confirmar_atribuicoes",
                "acao_id": self.acao.id,
                "pending_assignments": (
                    '[{"tipo_destino":"equipe","profissional":"","equipe_destino":"%s","nome_exibicao":"Equipe 1","valor_mensal":"10","ativo":true,"modo_rateio":"manual","distribuicoes":[{"funcionario_id":"%s","valor_mensal":"2"},{"funcionario_id":"%s","valor_mensal":"3"},{"funcionario_id":"%s","valor_mensal":"5"}]}]'
                    % (self.equipe.id, self.funcionario.id, outro_funcionario.id, terceiro_funcionario.id)
                ),
            },
        )

        self.assertEqual(response.status_code, 302)
        atribuicao = AcaoAtribuicao.objects.get(acao=self.acao, equipe=self.equipe)
        self.assertEqual(atribuicao.modo_rateio, "manual")
        self.assertEqual(atribuicao.distribuicoes.count(), 3)
        metas = {
            tarefa.funcionario_id: tarefa.meta_quantidade
            for tarefa in Tarefa.objects.filter(acao=self.acao)
        }
        self.assertEqual(metas[self.funcionario.id], Decimal("2"))
        self.assertEqual(metas[outro_funcionario.id], Decimal("3"))
        self.assertEqual(metas[terceiro_funcionario.id], Decimal("5"))

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

    def test_pagina_acoes_considera_apenas_competencia_selecionada(self):
        self.login_gestor()
        tarefa = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Transportar leite",
            meta_quantidade=Decimal("30"),
            previsto_quantidade=Decimal("30"),
        )
        RegistroDiario.objects.create(
            tarefa=tarefa,
            funcionario=self.funcionario,
            data=date(2026, 3, 15),
            descricao_atividade="Entrega de marco",
            quantidade_prevista=Decimal("30"),
            quantidade_realizada=Decimal("18"),
            situacao=Tarefa.Situacao.EM_ANDAMENTO,
        )
        RegistroDiario.objects.create(
            tarefa=tarefa,
            funcionario=self.funcionario,
            data=date(2026, 4, 10),
            descricao_atividade="Entrega de abril",
            quantidade_prevista=Decimal("30"),
            quantidade_realizada=Decimal("6"),
            situacao=Tarefa.Situacao.EM_ANDAMENTO,
        )

        response = self.client_http.get(
            f"/acoes/?diagnostico={self.diagnostico.id}&indicador={self.indicador.id}&competencia=2026-04"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["competencia_input"], "2026-04")
        self.assertEqual(response.context["acoes_lista"][0]["realizado_total"], Decimal("6"))
        self.assertEqual(response.context["acoes_lista"][0]["percentual_realizado"], Decimal("20"))

    def test_botao_ver_equipes_aparece_somente_quando_acao_tem_equipe_vinculada(self):
        self.login_gestor()

        response_sem_equipe = self.client_http.get(
            f"/acoes/?diagnostico={self.diagnostico.id}&indicador={self.indicador.id}&competencia=2026-04"
        )
        self.assertEqual(response_sem_equipe.status_code, 200)
        self.assertNotContains(response_sem_equipe, "Ver equipes")

        AcaoAtribuicao.objects.create(
            acao=self.acao,
            equipe=self.equipe,
            valor_mensal=Decimal("20"),
            modo_rateio="automatico",
            ativo=True,
        )

        response_com_equipe = self.client_http.get(
            f"/acoes/?diagnostico={self.diagnostico.id}&indicador={self.indicador.id}&competencia=2026-04"
        )
        self.assertEqual(response_com_equipe.status_code, 200)
        self.assertContains(response_com_equipe, "Ver equipes")

    def test_modal_equipes_mostra_meta_oficial_e_contribuicao_individual(self):
        outro_user = User.objects.create_user(username="bia", password="func123", first_name="Bia")
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
            funcao="Vacinadora",
        )
        AcaoAtribuicao.objects.create(
            acao=self.acao,
            equipe=self.equipe,
            valor_mensal=Decimal("20"),
            modo_rateio="automatico",
            ativo=True,
        )
        tarefa_suel = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Meta Sueldison",
            meta_quantidade=Decimal("10"),
            previsto_quantidade=Decimal("10"),
        )
        tarefa_bia = Tarefa.objects.create(
            acao=self.acao,
            funcionario=outro_funcionario,
            titulo="Meta Bia",
            meta_quantidade=Decimal("10"),
            previsto_quantidade=Decimal("10"),
        )
        RegistroDiario.objects.create(
            tarefa=tarefa_suel,
            funcionario=self.funcionario,
            data=date(2026, 4, 10),
            descricao_atividade="Atendimento",
            quantidade_prevista=Decimal("10"),
            quantidade_realizada=Decimal("6"),
            justificativa="Equipe reduzida",
            situacao=Tarefa.Situacao.EM_ANDAMENTO,
        )
        RegistroDiario.objects.create(
            tarefa=tarefa_bia,
            funcionario=outro_funcionario,
            data=date(2026, 4, 10),
            descricao_atividade="Atendimento",
            quantidade_prevista=Decimal("10"),
            quantidade_realizada=Decimal("8"),
            justificativa="Cobriu setor vizinho",
            situacao=Tarefa.Situacao.EM_ANDAMENTO,
        )

        self.login_gestor()
        response = self.client_http.get(
            f"/acoes/?diagnostico={self.diagnostico.id}&indicador={self.indicador.id}&competencia=2026-04&acao={self.acao.id}&modal=detalhe_equipes"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Meta da equipe: 20")
        self.assertContains(response, "Realizado da equipe: 14")
        self.assertContains(response, "Sueldison")
        self.assertContains(response, "Bia")
        self.assertContains(response, "Equipe reduzida")


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
                "meta_valor": "100",
                "vigencia_inicio": "2026-04",
            },
        )

        self.assertEqual(response.status_code, 302)
        novo_indicador = Indicador.objects.get(nome="Producao de leite fermentado")
        self.assertTrue(novo_indicador.codigo.startswith("IND-"))
        self.assertEqual(novo_indicador.valor_atual, Decimal("0"))
        self.assertTrue(
            IndicadorMetaVigencia.objects.filter(
                indicador=novo_indicador,
                inicio_vigencia=date(2026, 4, 1),
                valor_meta=Decimal("100"),
            ).exists()
        )

    def test_criacao_de_indicador_ignora_valor_manual_enviado_no_post(self):
        self.login_gestor()

        response = self.client_http.post(
            "/indicadores/",
            {
                "form_name": "novo_indicador",
                "nome": "Cobertura vacinal",
                "meta_valor": "250",
                "vigencia_inicio": "2026-04",
                "valor_atual": "999",
            },
        )

        self.assertEqual(response.status_code, 302)
        indicador = Indicador.objects.get(nome="Cobertura vacinal")
        self.assertEqual(indicador.valor_atual, Decimal("0"))

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

    def test_editar_indicador_atualiza_dados_basicos(self):
        self.login_gestor()

        response = self.client_http.post(
            f"/indicadores/?diagnostico={self.diagnostico.id}",
            {
                "form_name": "editar_indicador",
                "indicador_id": self.indicador.id,
                "nome": "Producao de queijo premium",
                "meta_valor": "650",
                "vigencia_inicio": "2026-04",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.indicador.refresh_from_db()
        self.assertEqual(self.indicador.nome, "Producao de queijo premium")
        self.assertEqual(self.indicador.meta_valor, Decimal("650"))
        self.assertEqual(self.indicador.valor_atual, Decimal("0"))

    def test_edicao_de_indicador_ignora_valor_manual_enviado_no_post(self):
        self.login_gestor()

        response = self.client_http.post(
            f"/indicadores/?diagnostico={self.diagnostico.id}",
            {
                "form_name": "editar_indicador",
                "indicador_id": self.indicador.id,
                "nome": "Producao de queijo premium",
                "meta_valor": "650",
                "vigencia_inicio": "2026-04",
                "valor_atual": "999",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.indicador.refresh_from_db()
        self.assertEqual(self.indicador.valor_atual, Decimal("0"))

    def test_edicao_de_meta_cria_nova_vigencia_e_fecha_anterior(self):
        IndicadorMetaVigencia.objects.create(
            indicador=self.indicador,
            inicio_vigencia=date(2026, 1, 1),
            valor_meta=Decimal("500"),
        )
        self.login_gestor()

        response = self.client_http.post(
            f"/indicadores/?diagnostico={self.diagnostico.id}",
            {
                "form_name": "editar_indicador",
                "indicador_id": self.indicador.id,
                "nome": self.indicador.nome,
                "meta_valor": "650",
                "vigencia_inicio": "2026-05",
            },
        )

        self.assertEqual(response.status_code, 302)
        vigencia_anterior = IndicadorMetaVigencia.objects.get(
            indicador=self.indicador,
            inicio_vigencia=date(2026, 1, 1),
        )
        nova_vigencia = IndicadorMetaVigencia.objects.get(
            indicador=self.indicador,
            inicio_vigencia=date(2026, 5, 1),
        )
        self.assertEqual(vigencia_anterior.fim_vigencia, date(2026, 4, 30))
        self.assertEqual(nova_vigencia.valor_meta, Decimal("650"))


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
                "descricao_atividade": "Atendeu parcialmente a meta do dia.",
                "quantidade_realizada": "5",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(RegistroDiario.objects.filter(tarefa=tarefa, funcionario=self.funcionario, quantidade_realizada=Decimal("5")).exists())

    def test_funcionario_pode_lancar_producao_sem_justificativa_diaria(self):
        self.client_http.post("/accounts/organizacao/", {"codigo": "maracaja"})
        self.client_http.post("/accounts/login/", {"username": "suel", "password": "func123"})

        tarefa = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Atualizar painel",
            meta_quantidade=Decimal("7"),
        )

        response = self.client_http.post(
            f"/app/metas/?tarefa={tarefa.id}",
            {
                "tarefa_id": tarefa.id,
                "descricao_atividade": "",
                "quantidade_realizada": "3",
            },
        )

        self.assertEqual(response.status_code, 302)
        registro = RegistroDiario.objects.get(tarefa=tarefa, funcionario=self.funcionario)
        self.assertEqual(registro.descricao_atividade, "")
        self.assertEqual(registro.justificativa, "")

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
                "descricao_atividade": "Observacao opcional do dia",
                "quantidade_realizada": "12",
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

    def test_area_de_metas_mostra_realizado_apenas_da_competencia_atual(self):
        self.client_http.post("/accounts/organizacao/", {"codigo": "maracaja"})
        self.client_http.post("/accounts/login/", {"username": "suel", "password": "func123"})

        tarefa = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Pesar criancas",
            meta_quantidade=Decimal("20"),
            previsto_quantidade=Decimal("20"),
        )
        RegistroDiario.objects.create(
            tarefa=tarefa,
            funcionario=self.funcionario,
            data=date(2026, 3, 20),
            descricao_atividade="Entrega de marco",
            quantidade_prevista=Decimal("20"),
            quantidade_realizada=Decimal("12"),
        )
        RegistroDiario.objects.create(
            tarefa=tarefa,
            funcionario=self.funcionario,
            data=date(2026, 4, 10),
            descricao_atividade="Entrega de abril",
            quantidade_prevista=Decimal("20"),
            quantidade_realizada=Decimal("5"),
        )

        response = self.client_http.get(f"/app/metas/?tarefa={tarefa.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["competencia_label"], "Abril de 2026")
        self.assertEqual(response.context["tarefa_alvo"]["realizado_total"], Decimal("5"))
        tarefa_lista = next(item for item in response.context["tarefas_funcionario"] if item["id"] == tarefa.id)
        self.assertEqual(tarefa_lista["realizado_total"], Decimal("5"))

    def test_resultados_mostram_pendencias_do_mes_anterior(self):
        self.client_http.post("/accounts/organizacao/", {"codigo": "maracaja"})
        self.client_http.post("/accounts/login/", {"username": "suel", "password": "func123"})

        tarefa_abaixo = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Aplicar vacinas UPA 1",
            meta_quantidade=Decimal("10"),
        )
        tarefa_atingida = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Aplicar vacinas UPA 2",
            meta_quantidade=Decimal("8"),
        )
        RegistroDiario.objects.create(
            tarefa=tarefa_abaixo,
            funcionario=self.funcionario,
            data=date(2026, 3, 20),
            descricao_atividade="Parcial de marco",
            quantidade_prevista=Decimal("10"),
            quantidade_realizada=Decimal("4"),
        )
        RegistroDiario.objects.create(
            tarefa=tarefa_atingida,
            funcionario=self.funcionario,
            data=date(2026, 3, 21),
            descricao_atividade="Meta fechada",
            quantidade_prevista=Decimal("8"),
            quantidade_realizada=Decimal("8"),
        )

        response = self.client_http.get("/app/resultados/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["competencia_input"], "2026-03")
        self.assertEqual(len(response.context["pendencias_justificativa"]), 1)
        self.assertEqual(response.context["pendencias_justificativa"][0]["obj"].id, tarefa_abaixo.id)
        pendencias_ids = [item["obj"].id for item in response.context["pendencias_justificativa"]]
        self.assertIn(tarefa_abaixo.id, pendencias_ids)
        self.assertNotIn(tarefa_atingida.id, pendencias_ids)

    def test_funcionario_registra_justificativa_mensal_para_tarefa_abaixo_da_meta(self):
        self.client_http.post("/accounts/organizacao/", {"codigo": "maracaja"})
        self.client_http.post("/accounts/login/", {"username": "suel", "password": "func123"})

        tarefa = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Aplicar vacinas UPA 1",
            meta_quantidade=Decimal("10"),
        )
        RegistroDiario.objects.create(
            tarefa=tarefa,
            funcionario=self.funcionario,
            data=date(2026, 3, 20),
            descricao_atividade="Parcial de marco",
            quantidade_prevista=Decimal("10"),
            quantidade_realizada=Decimal("4"),
        )

        response = self.client_http.post(
            "/app/resultados/?competencia=2026-03",
            {
                "tarefa_id": tarefa.id,
                "categoria": "falta_pessoal",
                "justificativa": "Faltou equipe em dois plantoes.",
            },
        )

        self.assertEqual(response.status_code, 302)
        justificativa = JustificativaNaoAtingimentoMensal.objects.get(tarefa=tarefa, competencia=date(2026, 3, 1))
        self.assertEqual(justificativa.funcionario, self.funcionario)
        self.assertEqual(justificativa.categoria, "falta_pessoal")
        self.assertEqual(justificativa.justificativa, "Faltou equipe em dois plantoes.")

    def test_justificativa_mensal_com_outro_exige_detalhamento(self):
        self.client_http.post("/accounts/organizacao/", {"codigo": "maracaja"})
        self.client_http.post("/accounts/login/", {"username": "suel", "password": "func123"})

        tarefa = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Aplicar vacinas UPA 1",
            meta_quantidade=Decimal("10"),
        )
        RegistroDiario.objects.create(
            tarefa=tarefa,
            funcionario=self.funcionario,
            data=date(2026, 3, 20),
            descricao_atividade="Parcial de marco",
            quantidade_prevista=Decimal("10"),
            quantidade_realizada=Decimal("4"),
        )

        response = self.client_http.post(
            "/app/resultados/?competencia=2026-03",
            {
                "tarefa_id": tarefa.id,
                "categoria": "outro",
                "justificativa": "",
                "detalhe_outro": "",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "descreva o motivo no campo complementar")
        self.assertFalse(
            JustificativaNaoAtingimentoMensal.objects.filter(tarefa=tarefa, competencia=date(2026, 3, 1)).exists()
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

    def test_menu_exibe_link_da_analise_de_problemas(self):
        self.login_gestor()

        response = self.client_http.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analise de Problemas")

    def test_analise_de_problemas_consolida_gargalos_do_periodo(self):
        self.login_gestor()
        tarefa = Tarefa.objects.create(
            acao=self.acao,
            funcionario=self.funcionario,
            titulo="Triagem de abril",
            meta_quantidade=Decimal("20"),
            previsto_quantidade=Decimal("20"),
        )
        RegistroDiario.objects.create(
            tarefa=tarefa,
            funcionario=self.funcionario,
            data=date(2026, 4, 10),
            descricao_atividade="Atendimento parcial",
            quantidade_prevista=Decimal("20"),
            quantidade_realizada=Decimal("8"),
        )
        JustificativaNaoAtingimentoMensal.objects.create(
            tarefa=tarefa,
            funcionario=self.funcionario,
            competencia=date(2026, 4, 1),
            categoria="falta_pessoal",
            justificativa="Equipe reduzida no turno da tarde.",
        )

        response = self.client_http.get("/analises/problemas/?competencia=2026-04")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["competencia_input"], "2026-04")
        self.assertEqual(response.context["total_abaixo_meta"], 1)
        self.assertEqual(response.context["total_justificadas"], 1)
        self.assertEqual(response.context["ocorrencias"][0]["categoria"], "Falta de pessoal")
        self.assertTrue(any(item["label"] == "Falta de pessoal" for item in response.context["categorias_series"]))
