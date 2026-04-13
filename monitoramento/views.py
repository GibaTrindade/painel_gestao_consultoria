import json
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_DOWN
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import models
from django.db import transaction
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import (
    AcaoForm,
    AtribuicaoAcaoForm,
    CodigoOrganizacaoForm,
    DiagnosticoForm,
    EquipeForm,
    IndicadorForm,
    OrganizacaoLoginForm,
    ProfissionalForm,
    RegistroDiarioForm,
)
from .models import (
    AcaoAtribuicao,
    AcaoAtribuicaoDistribuicao,
    AcaoMelhoria,
    Cliente,
    Diagnostico,
    Equipe,
    Funcionario,
    Indicador,
    IndicadorHistoricoMensal,
    IndicadorMetaVigencia,
    PerfilUsuario,
    RegistroDiario,
    Tarefa,
    UsuarioCliente,
)


def _parse_competencia(value):
    if value:
        try:
            return datetime.strptime(value, "%Y-%m").date().replace(day=1)
        except ValueError:
            pass
    hoje = timezone.localdate()
    return hoje.replace(day=1)


def _proxima_competencia(competencia):
    if competencia.month == 12:
        return date(competencia.year + 1, 1, 1)
    return date(competencia.year, competencia.month + 1, 1)


def _competencia_anterior(competencia):
    if competencia.month == 1:
        return date(competencia.year - 1, 12, 1)
    return date(competencia.year, competencia.month - 1, 1)


def _formatar_competencia(competencia, incluir_ano=True):
    meses = [
        "Janeiro",
        "Fevereiro",
        "Marco",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]
    nome_mes = meses[competencia.month - 1]
    return f"{nome_mes} de {competencia.year}" if incluir_ano else nome_mes


def _normalizar_competencia(data_referencia):
    return data_referencia.replace(day=1)


def _meta_vigente_indicador(indicador, competencia=None):
    if not indicador:
        return Decimal("0")
    competencia = _normalizar_competencia(competencia or timezone.localdate())
    vigencia = (
        indicador.meta_vigencias.filter(inicio_vigencia__lte=competencia)
        .filter(models.Q(fim_vigencia__isnull=True) | models.Q(fim_vigencia__gte=competencia))
        .order_by("-inicio_vigencia")
        .first()
    )
    if vigencia:
        return vigencia.valor_meta
    return indicador.meta_valor or Decimal("0")


def _registrar_meta_vigencia(indicador, valor_meta, inicio_vigencia):
    if not indicador:
        return None

    inicio_vigencia = _normalizar_competencia(inicio_vigencia)

    with transaction.atomic():
        vigencia_anterior = (
            indicador.meta_vigencias.filter(inicio_vigencia__lt=inicio_vigencia)
            .order_by("-inicio_vigencia")
            .first()
        )
        if vigencia_anterior and (
            vigencia_anterior.fim_vigencia is None or vigencia_anterior.fim_vigencia >= inicio_vigencia
        ):
            vigencia_anterior.fim_vigencia = inicio_vigencia - timedelta(days=1)
            vigencia_anterior.save(update_fields=["fim_vigencia", "updated_at"])

        proxima_vigencia = (
            indicador.meta_vigencias.filter(inicio_vigencia__gt=inicio_vigencia)
            .order_by("inicio_vigencia")
            .first()
        )
        fim_vigencia = proxima_vigencia.inicio_vigencia - timedelta(days=1) if proxima_vigencia else None

        vigencia, _ = IndicadorMetaVigencia.objects.update_or_create(
            indicador=indicador,
            inicio_vigencia=inicio_vigencia,
            defaults={
                "valor_meta": valor_meta,
                "fim_vigencia": fim_vigencia,
            },
        )

        indicador.meta_valor = _meta_vigente_indicador(indicador, timezone.localdate())
        indicador.save(update_fields=["meta_valor", "updated_at"])

    return vigencia


def _percentual(realizado, meta):
    realizado_decimal = Decimal(str(realizado or 0))
    meta_decimal = Decimal(str(meta or 0))
    if meta_decimal <= 0:
        return Decimal("0")
    return min((realizado_decimal / meta_decimal) * 100, Decimal("999.99"))


def _snapshot_indicador(indicador, competencia, historicos_map=None, competencia_atual=None):
    historicos_map = historicos_map or {}
    historico = historicos_map.get(indicador.id)
    competencia_atual = competencia_atual or timezone.localdate().replace(day=1)
    meta_vigente = _meta_vigente_indicador(indicador, competencia)

    if historico:
        valor = historico.valor
        meta = historico.meta or meta_vigente
    elif competencia == competencia_atual:
        valor = indicador.valor_atual
        meta = meta_vigente
    else:
        valor = Decimal("0")
        meta = meta_vigente

    return {
        "valor": valor,
        "meta": meta,
        "percentual": _percentual(valor, meta),
    }


def _snapshot_indicador_por_registros(indicador, competencia):
    if not indicador:
        return {"valor": Decimal("0"), "meta": Decimal("0"), "percentual": Decimal("0")}
    competencia_final = _proxima_competencia(competencia)
    valor = (
        RegistroDiario.objects.filter(
            tarefa__acao__indicador=indicador,
            data__gte=competencia,
            data__lt=competencia_final,
        ).aggregate(total=Sum("quantidade_realizada"))["total"]
        or Decimal("0")
    )
    meta = _meta_vigente_indicador(indicador, competencia)
    return {
        "valor": valor,
        "meta": meta,
        "percentual": _percentual(valor, meta),
    }


def _sincronizar_indicador_competencia(indicador, competencia=None):
    if not indicador:
        return None
    competencia = (competencia or timezone.localdate()).replace(day=1)
    competencia_final = _proxima_competencia(competencia)
    valor_total = (
        RegistroDiario.objects.filter(
            tarefa__acao__indicador=indicador,
            data__gte=competencia,
            data__lt=competencia_final,
        ).aggregate(total=Sum("quantidade_realizada"))["total"]
        or Decimal("0")
    )
    meta_vigente = _meta_vigente_indicador(indicador, competencia)
    historico, _ = IndicadorHistoricoMensal.objects.update_or_create(
        indicador=indicador,
        competencia=competencia,
        defaults={
            "valor": valor_total,
            "meta": meta_vigente,
        },
    )
    if competencia == timezone.localdate().replace(day=1):
        indicador.valor_atual = valor_total
        indicador.meta_valor = _meta_vigente_indicador(indicador, timezone.localdate())
        indicador.save(update_fields=["valor_atual", "meta_valor", "updated_at"])
    return historico


def _perfil_usuario(request, membership=None):
    cliente = membership.cliente if membership and membership.cliente_id else None
    tem_vinculo_funcionario = (
        request.user.vinculos_funcionario.filter(cliente=cliente, ativo=True).exists()
        if cliente
        else False
    )
    modo_map = request.session.get("profile_mode_overrides", {})
    modo_preferido = modo_map.get(str(cliente.id)) if cliente else None

    if request.user.is_superuser:
        return "admin"

    if membership and membership.tipo != PerfilUsuario.TipoPerfil.FUNCIONARIO and tem_vinculo_funcionario:
        if modo_preferido == PerfilUsuario.TipoPerfil.FUNCIONARIO:
            return PerfilUsuario.TipoPerfil.FUNCIONARIO
        return membership.tipo

    if membership:
        return membership.tipo
    perfil = getattr(request.user, "perfil", None)
    return perfil.tipo if perfil else "funcionario"


def _clientes_disponiveis_para_usuario(user):
    memberships = list(
        UsuarioCliente.objects.filter(user=user, ativo=True, cliente__ativo=True)
        .select_related("cliente")
        .order_by("cliente__nome")
    )

    if memberships:
        return memberships

    fallback_memberships = []
    perfil = getattr(user, "perfil", None)
    if perfil and perfil.cliente_id:
        fallback_memberships.append(
            UsuarioCliente(user=user, cliente=perfil.cliente, tipo=perfil.tipo, ativo=True)
        )

    for vinculo in user.vinculos_funcionario.select_related("cliente").all():
        if vinculo.cliente_id not in {item.cliente_id for item in fallback_memberships}:
            fallback_memberships.append(
                UsuarioCliente(user=user, cliente=vinculo.cliente, tipo=PerfilUsuario.TipoPerfil.FUNCIONARIO, ativo=vinculo.ativo)
            )

    return fallback_memberships


def _cliente_contexto(request):
    memberships = _clientes_disponiveis_para_usuario(request.user)
    cliente_id = request.GET.get("cliente")
    membership_map = {str(item.cliente_id): item for item in memberships if item.cliente_id}
    selected_membership = None

    if request.user.is_superuser:
        clientes = Cliente.objects.all()
        cliente = clientes.filter(pk=cliente_id).first() or clientes.filter(pk=request.session.get("cliente_contexto_id")).first() or clientes.first()
        perfil = "admin"
    else:
        clientes = Cliente.objects.filter(id__in=[item.cliente_id for item in memberships]) if memberships else Cliente.objects.none()
        selected_membership = membership_map.get(str(cliente_id)) or membership_map.get(str(request.session.get("cliente_contexto_id"))) or (memberships[0] if memberships else None)
        cliente = selected_membership.cliente if selected_membership else None
        perfil = _perfil_usuario(request, selected_membership)

    request.session["cliente_contexto_id"] = cliente.id if cliente else None
    return perfil, cliente, clientes


def _base_context(request, pagina):
    perfil, cliente, clientes = _cliente_contexto(request)
    funcionario_contexto = _funcionario_no_contexto(request, cliente)
    membership_contexto = None
    if request.user.is_authenticated and cliente and not request.user.is_superuser:
        membership_contexto = (
            UsuarioCliente.objects.filter(user=request.user, cliente=cliente, ativo=True)
            .select_related("cliente")
            .first()
        )
    pode_modo_funcionario = funcionario_contexto is not None
    pode_modo_gestor = request.user.is_superuser or (
        membership_contexto is not None and membership_contexto.tipo != PerfilUsuario.TipoPerfil.FUNCIONARIO
    )
    try:
        clientes_count = clientes.count()
    except TypeError:
        clientes_count = len(clientes)
    return {
        "pagina": pagina,
        "perfil_tipo": perfil,
        "cliente_atual": cliente,
        "clientes_menu": clientes,
        "clientes_menu_count": clientes_count,
        "permitir_troca_cliente": perfil == "admin" or clientes_count > 1,
        "funcionario_atual": funcionario_contexto,
        "modo_hibrido_disponivel": pode_modo_funcionario and pode_modo_gestor,
        "pode_entrar_como_funcionario": pode_modo_funcionario,
        "pode_entrar_como_gestor": pode_modo_gestor,
        "modal": request.GET.get("modal", ""),
    }


def _redirect_with_query(view_name, params=None):
    url = reverse(view_name)
    if params:
        return redirect(f"{url}?{urlencode({k: v for k, v in params.items() if v not in [None, '']})}")
    return redirect(url)


def _funcionario_no_contexto(request, cliente):
    if not request.user.is_authenticated or not cliente:
        return None
    return request.user.vinculos_funcionario.filter(cliente=cliente, ativo=True).select_related("equipe", "cliente").first()


def _worker_context(request, pagina):
    context = _base_context(request, pagina)
    funcionario = context["funcionario_atual"]
    context["worker_mode"] = context["perfil_tipo"] == "funcionario" and funcionario is not None
    return context


def _salvar_atribuicoes_pendentes(cliente, acao, raw_payload):
    try:
        payload = json.loads(raw_payload or "[]")
    except json.JSONDecodeError:
        return 0, ["Nao foi possivel interpretar as atribuicoes pendentes."]

    if not isinstance(payload, list):
        return 0, ["Formato invalido para atribuicoes pendentes."]

    salvos = 0
    tarefas_criadas = 0
    erros = []
    atribuicoes_validas = []
    alocacoes_ativas = {}

    def ratear_valor_equipe(valor_total, quantidade_membros):
        if quantidade_membros <= 0:
            return []

        total = Decimal(str(valor_total or 0))
        total_inteiro = int(total.quantize(Decimal("1"), rounding=ROUND_DOWN))
        base_inteira = total_inteiro // quantidade_membros
        resto_inteiro = total_inteiro - (base_inteira * quantidade_membros)
        valores = [Decimal(str(base_inteira)) for _ in range(quantidade_membros)]

        for indice in range(1, resto_inteiro + 1):
            valores[-indice] += Decimal("1")

        resto_decimal = total - Decimal(str(total_inteiro))
        if resto_decimal > 0:
            valores[-1] += resto_decimal

        return valores

    def garantir_tarefa_para_funcionario(funcionario, atribuicao, valor_meta=None):
        nonlocal tarefas_criadas
        tarefa_existente = Tarefa.objects.filter(acao=acao, funcionario=funcionario).order_by("id").first()
        valor_tarefa = valor_meta if valor_meta is not None else atribuicao.valor_mensal
        defaults = {
            "titulo": acao.nome,
            "descricao": acao.descricao or f"Tarefa gerada automaticamente a partir da acao '{acao.nome}'.",
            "meta_quantidade": valor_tarefa,
            "previsto_quantidade": valor_tarefa,
            "situacao": Tarefa.Situacao.PENDENTE,
            "concluida": False,
        }

        if tarefa_existente:
            tarefa_existente.meta_quantidade = valor_tarefa
            tarefa_existente.previsto_quantidade = valor_tarefa
            tarefa_existente.save(update_fields=["meta_quantidade", "previsto_quantidade", "updated_at"])
            return

        Tarefa.objects.create(
            acao=acao,
            funcionario=funcionario,
            **defaults,
        )
        tarefas_criadas += 1

    def validar_distribuicao_manual(atribuicao, distribuicoes_payload):
        membros_ativos = list(atribuicao.equipe.funcionarios.filter(ativo=True).order_by("id"))
        membros_map = {str(membro.id): membro for membro in membros_ativos}
        membros_ids = set(membros_map.keys())

        if not membros_ativos:
            return None, "A equipe selecionada nao possui membros ativos para distribuir a meta."
        if not isinstance(distribuicoes_payload, list):
            return None, "A distribuicao manual enviada para a equipe esta em formato invalido."

        distribuicoes = []
        vistos = set()
        total_distribuido = Decimal("0")

        for item in distribuicoes_payload:
            funcionario_id = str(item.get("funcionario_id") or "")
            if funcionario_id not in membros_map:
                return None, "A distribuicao manual contem um membro que nao pertence a equipe selecionada."
            if funcionario_id in vistos:
                return None, "Um mesmo membro foi informado mais de uma vez na distribuicao manual."

            try:
                valor = Decimal(str(item.get("valor_mensal") or 0))
            except Exception:
                return None, "Um dos valores da distribuicao manual e invalido."

            if valor < 0:
                return None, "Nao e permitido informar valores negativos na distribuicao manual."

            distribuicoes.append({"funcionario": membros_map[funcionario_id], "valor_mensal": valor})
            total_distribuido += valor
            vistos.add(funcionario_id)

        if vistos != membros_ids:
            return None, "A distribuicao manual precisa contemplar todos os membros ativos da equipe."
        if total_distribuido != atribuicao.valor_mensal:
            return None, "A soma da distribuicao manual precisa ser igual ao valor mensal informado para a equipe."

        return distribuicoes, None

    existentes = AcaoAtribuicao.objects.filter(acao=acao)
    for atribuicao_existente in existentes:
        if atribuicao_existente.funcionario_id:
            chave = f"funcionario:{atribuicao_existente.funcionario_id}"
        else:
            chave = f"equipe:{atribuicao_existente.equipe_id}"
        alocacoes_ativas[chave] = float(atribuicao_existente.valor_mensal) if atribuicao_existente.ativo else 0.0

    for item in payload:
        if not isinstance(item, dict):
            erros.append("Uma atribuicao pendente estava em formato invalido.")
            continue

        form_data = {
            "tipo_destino": item.get("tipo_destino"),
            "profissional": item.get("profissional") or "",
            "equipe_destino": item.get("equipe_destino") or "",
            "valor_mensal": item.get("valor_mensal") or "0",
            "ativo": "on" if item.get("ativo", True) else "",
        }
        atribuicao_form = AtribuicaoAcaoForm(form_data, cliente=cliente)
        if not atribuicao_form.is_valid():
            erros.append("Uma atribuicao pendente nao passou na validacao.")
            continue

        atribuicao = atribuicao_form.save(commit=False, acao=acao)
        atribuicao.modo_rateio = item.get("modo_rateio") or AcaoAtribuicao.ModoRateio.AUTOMATICO
        if atribuicao.funcionario_id:
            chave = f"funcionario:{atribuicao.funcionario_id}"
        else:
            chave = f"equipe:{atribuicao.equipe_id}"
        alocacoes_ativas[chave] = float(atribuicao.valor_mensal) if atribuicao.ativo else 0.0
        distribuicoes_manuais = []
        if atribuicao.equipe_id and atribuicao.modo_rateio == AcaoAtribuicao.ModoRateio.MANUAL:
            distribuicoes_manuais, erro_distribuicao = validar_distribuicao_manual(
                atribuicao,
                item.get("distribuicoes", []),
            )
            if erro_distribuicao:
                erros.append(erro_distribuicao)
                continue
        atribuicoes_validas.append((atribuicao, distribuicoes_manuais))

    total_alocado = sum(alocacoes_ativas.values())
    if total_alocado > float(acao.meta_mensal):
        return 0, 0, [f"A soma dos valores mensais vinculados nao pode ultrapassar {acao.meta_mensal}."]

    for atribuicao, distribuicoes_manuais in atribuicoes_validas:
        lookup = {"acao": acao}
        if atribuicao.funcionario_id:
            lookup["funcionario"] = atribuicao.funcionario
        else:
            lookup["equipe"] = atribuicao.equipe

        atribuicao_salva, _ = AcaoAtribuicao.objects.update_or_create(
            **lookup,
            defaults={
                "valor_mensal": atribuicao.valor_mensal,
                "ativo": atribuicao.ativo,
                "modo_rateio": atribuicao.modo_rateio,
            },
        )
        atribuicao_salva.distribuicoes.all().delete()
        if distribuicoes_manuais:
            for distribuicao in distribuicoes_manuais:
                AcaoAtribuicaoDistribuicao.objects.create(
                    atribuicao=atribuicao_salva,
                    funcionario=distribuicao["funcionario"],
                    valor_mensal=distribuicao["valor_mensal"],
                )
        salvos += 1
        if atribuicao.ativo:
            if atribuicao.funcionario_id:
                garantir_tarefa_para_funcionario(atribuicao.funcionario, atribuicao)
            elif atribuicao.equipe_id:
                membros_ativos = list(atribuicao.equipe.funcionarios.filter(ativo=True).order_by("id"))
                if atribuicao.modo_rateio == AcaoAtribuicao.ModoRateio.MANUAL:
                    for distribuicao in distribuicoes_manuais:
                        garantir_tarefa_para_funcionario(
                            distribuicao["funcionario"],
                            atribuicao,
                            distribuicao["valor_mensal"],
                        )
                else:
                    rateio = ratear_valor_equipe(atribuicao.valor_mensal, len(membros_ativos))
                    for membro, valor_rateado in zip(membros_ativos, rateio):
                        garantir_tarefa_para_funcionario(membro, atribuicao, valor_rateado)

    return salvos, tarefas_criadas, erros


def selecionar_organizacao_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = CodigoOrganizacaoForm(request.POST)
        if form.is_valid():
            request.session["login_org_code"] = form.cleaned_data["codigo"]
            request.session["login_cliente_id"] = form.cleaned_data.get("cliente").id if form.cleaned_data.get("cliente") else None
            request.session["login_master_access"] = form.cleaned_data.get("is_master_code", False)
            return redirect("login")
    else:
        form = CodigoOrganizacaoForm()

    return render(request, "registration/select_organization.html", {"form": form})


def login_organizacao_view(request):
    selected_cliente = None
    selected_code = request.session.get("login_org_code")
    master_access = request.session.get("login_master_access", False)

    if not selected_code and not master_access:
        return redirect("select-organization")

    if request.session.get("login_cliente_id"):
        selected_cliente = Cliente.objects.filter(pk=request.session["login_cliente_id"]).first()

    if request.method == "POST":
        form = OrganizacaoLoginForm(
            request.POST,
            cliente=selected_cliente,
            allow_master=master_access,
            request=request,
        )
        if form.is_valid():
            login(request, form.user)
            if master_access:
                request.session["cliente_contexto_id"] = None
            else:
                request.session["cliente_contexto_id"] = selected_cliente.id
            return redirect("dashboard")
    else:
        form = OrganizacaoLoginForm(cliente=selected_cliente, allow_master=master_access, request=request)

    return render(
        request,
        "registration/login.html",
        {
            "form": form,
            "selected_cliente": selected_cliente,
            "selected_code": selected_code,
            "master_access": master_access,
        },
    )


def logout_view(request):
    logout(request)
    for key in ["cliente_contexto_id", "login_org_code", "login_cliente_id", "login_master_access", "profile_mode_overrides"]:
        request.session.pop(key, None)
    return redirect("select-organization")


@login_required
def alternar_modo_view(request):
    cliente = Cliente.objects.filter(pk=request.session.get("cliente_contexto_id")).first()
    if not cliente:
        return redirect("dashboard")

    destino = request.POST.get("modo")
    overrides = request.session.get("profile_mode_overrides", {})
    membership = (
        UsuarioCliente.objects.filter(user=request.user, cliente=cliente, ativo=True)
        .select_related("cliente")
        .first()
    )
    tem_vinculo_funcionario = request.user.vinculos_funcionario.filter(cliente=cliente, ativo=True).exists()
    tem_vinculo_gestor = request.user.is_superuser or (
        membership is not None and membership.tipo != PerfilUsuario.TipoPerfil.FUNCIONARIO
    )

    if destino == PerfilUsuario.TipoPerfil.FUNCIONARIO and tem_vinculo_funcionario:
        overrides[str(cliente.id)] = PerfilUsuario.TipoPerfil.FUNCIONARIO
    elif destino in {"gestor", PerfilUsuario.TipoPerfil.CLIENTE, "admin"} and tem_vinculo_gestor:
        overrides[str(cliente.id)] = "gestor"

    request.session["profile_mode_overrides"] = overrides
    next_url = request.POST.get("next") or reverse("dashboard")
    return redirect(next_url)


@login_required
def dashboard_view(request):
    context = _base_context(request, "dashboard")
    if context["perfil_tipo"] == "funcionario":
        return redirect("funcionario-metas")
    cliente = context["cliente_atual"]

    competencia = _parse_competencia(request.GET.get("competencia"))
    competencia_final = _proxima_competencia(competencia)
    competencia_anterior = _competencia_anterior(competencia)
    competencia_proxima = _proxima_competencia(competencia)

    indicadores = (
        Indicador.objects.filter(diagnostico__cliente=cliente)
        .select_related("diagnostico")
        .prefetch_related("historicos")
        if cliente
        else Indicador.objects.none()
    )
    indicadores_lista = list(indicadores)

    indicador_selecionado = None
    if indicadores_lista:
        indicador_id = request.GET.get("indicador")
        indicador_selecionado = next((item for item in indicadores_lista if str(item.id) == str(indicador_id)), None) or indicadores_lista[0]

    acoes = (
        AcaoMelhoria.objects.filter(indicador=indicador_selecionado).prefetch_related("tarefas__registros")
        if indicador_selecionado
        else AcaoMelhoria.objects.none()
    )
    funcionarios = Funcionario.objects.filter(cliente=cliente, ativo=True).select_related("user", "equipe") if cliente else Funcionario.objects.none()
    tarefas_cliente = (
        Tarefa.objects.filter(funcionario__cliente=cliente)
        .select_related("funcionario__user", "acao__indicador")
        .prefetch_related("registros")
        if cliente
        else Tarefa.objects.none()
    )
    registros_cliente = RegistroDiario.objects.filter(
        funcionario__cliente=cliente,
        data__gte=competencia,
        data__lt=competencia_final,
    ) if cliente else RegistroDiario.objects.none()

    indicadores_cards = []
    for indicador in indicadores_lista:
        snapshot = _snapshot_indicador_por_registros(indicador, competencia)
        indicadores_cards.append(
            {
                "id": indicador.id,
                "nome": indicador.nome,
                "valor": snapshot["valor"],
                "meta": snapshot["meta"],
                "percentual": snapshot["percentual"],
                "selecionado": indicador_selecionado and indicador.id == indicador_selecionado.id,
            }
        )

    indicador_snapshot = (
        _snapshot_indicador_por_registros(indicador_selecionado, competencia)
        if indicador_selecionado
        else {"valor": Decimal("0"), "meta": Decimal("0"), "percentual": Decimal("0")}
    )

    acoes_lista = []
    profissionais_metricas = {}
    for acao in acoes:
        tarefas_acao = list(acao.tarefas.all())
        registros_acao = [
            registro
            for tarefa in tarefas_acao
            for registro in tarefa.registros.all()
            if competencia <= registro.data < competencia_final
        ]
        realizado_total = sum((registro.quantidade_realizada for registro in registros_acao), Decimal("0"))
        percentual_realizado = _percentual(realizado_total, acao.meta_mensal)
        acoes_lista.append(
            {
                "id": acao.id,
                "nome": acao.nome,
                "status": acao.status,
                "status_display": acao.get_status_display(),
                "meta_mensal": acao.meta_mensal,
                "realizado_total": realizado_total,
                "percentual_realizado": percentual_realizado,
            }
        )

        for tarefa in tarefas_acao:
            funcionario = tarefa.funcionario
            metricas = profissionais_metricas.setdefault(
                funcionario.id,
                {
                    "funcionario": funcionario,
                    "realizado_total": Decimal("0"),
                    "meta_total": Decimal("0"),
                    "tarefas_ativas": [],
                    "tarefas_contexto": [],
                },
            )
            metricas["meta_total"] += tarefa.meta_quantidade or Decimal("0")
            realizado_tarefa = sum(
                (
                    registro.quantidade_realizada
                    for registro in tarefa.registros.all()
                    if competencia <= registro.data < competencia_final
                ),
                Decimal("0"),
            )
            metricas["realizado_total"] += realizado_tarefa
            metricas["tarefas_contexto"].append(tarefa)
            if not tarefa.concluida and tarefa.situacao != Tarefa.Situacao.CONCLUIDA:
                metricas["tarefas_ativas"].append(tarefa)

    profissionais_lista = []
    profissionais_modal_data = []
    funcionario_selecionado = None
    funcionario_id = request.GET.get("funcionario")
    for metrica in sorted(
        profissionais_metricas.values(),
        key=lambda item: (item["funcionario"].user.get_full_name() or item["funcionario"].user.username).lower(),
    ):
        percentual_realizado = _percentual(metrica["realizado_total"], metrica["meta_total"])
        item = {
            "funcionario": metrica["funcionario"],
            "realizado_total": metrica["realizado_total"],
            "meta_total": metrica["meta_total"],
            "percentual_realizado": percentual_realizado,
            "tarefas_ativas": metrica["tarefas_ativas"],
            "tarefas_contexto": metrica["tarefas_contexto"],
            "tarefas_ativas_count": len(metrica["tarefas_ativas"]),
            "tarefas_total_count": len(metrica["tarefas_contexto"]),
            "tarefas_concluidas_count": sum(1 for tarefa in metrica["tarefas_contexto"] if tarefa.concluida or tarefa.situacao == Tarefa.Situacao.CONCLUIDA),
            "selecionado": str(metrica["funcionario"].id) == str(funcionario_id),
        }
        if item["selecionado"]:
            funcionario_selecionado = item
        profissionais_lista.append(item)
        profissionais_modal_data.append(
            {
                "id": metrica["funcionario"].id,
                "nome": metrica["funcionario"].user.get_full_name() or metrica["funcionario"].user.username,
                "equipe": metrica["funcionario"].equipe.nome if metrica["funcionario"].equipe else "Sem equipe",
                "percentual_realizado": round(float(percentual_realizado), 1),
                "tarefas_ativas_count": len(metrica["tarefas_ativas"]),
                "tarefas_total_count": len(metrica["tarefas_contexto"]),
                "tarefas_concluidas_count": sum(1 for tarefa in metrica["tarefas_contexto"] if tarefa.concluida or tarefa.situacao == Tarefa.Situacao.CONCLUIDA),
                "tarefas": [
                    {
                        "titulo": tarefa.titulo,
                        "acao": tarefa.acao.nome,
                        "situacao": tarefa.get_situacao_display(),
                        "situacao_codigo": tarefa.situacao,
                        "meta": float(tarefa.meta_quantidade or 0),
                        "realizado": float(tarefa.realizado_total or 0),
                        "prazo": tarefa.prazo.strftime("%d/%m/%Y") if tarefa.prazo else "Nao definido",
                    }
                    for tarefa in metrica["tarefas_contexto"]
                ],
            }
        )

    if not funcionario_selecionado and profissionais_lista:
        funcionario_selecionado = profissionais_lista[0]
        funcionario_selecionado["selecionado"] = True

    total_realizado_acoes = sum((item["realizado_total"] for item in acoes_lista), Decimal("0"))
    total_meta_acoes = sum((item["meta_mensal"] for item in acoes_lista), Decimal("0"))
    acao_media = round(float(_percentual(total_realizado_acoes, total_meta_acoes)), 1) if acoes_lista else 0
    indicador_media = round(
        sum(float(item["percentual"]) for item in indicadores_cards) / len(indicadores_cards),
        1,
    ) if indicadores_cards else 0

    comparativo_meses = []
    for offset in range(5, -1, -1):
        mes = competencia.month - offset
        ano = competencia.year
        while mes <= 0:
            mes += 12
            ano -= 1
        competencia_item = date(ano, mes, 1)
        proxima_item = _proxima_competencia(competencia_item)
        snapshot_mes = (
            _snapshot_indicador_por_registros(indicador_selecionado, competencia_item)
            if indicador_selecionado
            else {"percentual": Decimal("0")}
        )
        registros_mes = registros_cliente.filter(
            tarefa__acao__indicador=indicador_selecionado,
            data__gte=competencia_item,
            data__lt=proxima_item,
        ) if indicador_selecionado else RegistroDiario.objects.none()
        realizado_mes = registros_mes.aggregate(total=Sum("quantidade_realizada"))["total"] or Decimal("0")
        meta_acoes_mes = (
            AcaoMelhoria.objects.filter(indicador=indicador_selecionado).aggregate(total=Sum("meta_mensal"))["total"] or Decimal("0")
        ) if indicador_selecionado else Decimal("0")
        comparativo_meses.append(
            {
                "rotulo": competencia_item.strftime("%b/%y"),
                "indicador_percentual": snapshot_mes["percentual"],
                "acoes_percentual": _percentual(realizado_mes, meta_acoes_mes),
                "indicador_bar": min(float(snapshot_mes["percentual"]), 100.0),
                "acoes_bar": min(float(_percentual(realizado_mes, meta_acoes_mes)), 100.0),
            }
        )

    tarefas_cliente_count = tarefas_cliente.count()
    tarefas_concluidas = tarefas_cliente.filter(concluida=True).count()
    comparativo_series = [
        {
            "label": item["rotulo"],
            "acoes": item["acoes_bar"],
            "indicador": item["indicador_bar"],
        }
        for item in comparativo_meses
    ]
    profissionais_series = [
        {
            "label": (
                item["funcionario"].user.get_full_name()
                or item["funcionario"].user.username
            ),
            "realizado": round(float(item["percentual_realizado"]), 1),
            "meta": 100.0,
        }
        for item in profissionais_lista[:6]
    ]
    context.update(
        {
            "competencia_input": competencia.strftime("%Y-%m"),
            "competencia_label": _formatar_competencia(competencia),
            "competencia_nome": _formatar_competencia(competencia, incluir_ano=False),
            "competencia_anterior_input": competencia_anterior.strftime("%Y-%m"),
            "competencia_proxima_input": competencia_proxima.strftime("%Y-%m"),
            "indicadores_cards": indicadores_cards,
            "indicador_selecionado": indicador_selecionado,
            "indicador_percentual": indicador_snapshot["percentual"],
            "indicador_valor_competencia": indicador_snapshot["valor"],
            "indicador_meta_competencia": indicador_snapshot["meta"],
            "acoes_lista": acoes_lista,
            "profissionais_lista": profissionais_lista,
            "funcionario_selecionado": funcionario_selecionado,
            "funcionario_tarefas_ativas": funcionario_selecionado["tarefas_ativas"] if funcionario_selecionado else [],
            "indicador_media": indicador_media,
            "acao_media": acao_media,
            "total_funcionarios": funcionarios.count(),
            "total_tarefas": tarefas_cliente_count,
            "tarefas_concluidas": tarefas_concluidas,
            "producao_total": registros_cliente.aggregate(total=Sum("quantidade_realizada"))["total"] or 0,
            "gargalos": (
                sum(1 for item in indicadores_cards if item["percentual"] < 100)
                if cliente
                else 0
            ),
            "percentual_tarefas_concluidas": round((tarefas_concluidas / tarefas_cliente_count * 100), 1)
            if tarefas_cliente_count
            else 0,
            "comparativo_meses": comparativo_meses,
            "comparativo_series": comparativo_series,
            "profissionais_series": profissionais_series,
            "profissionais_modal_data": profissionais_modal_data,
            "gauges_data": [
                {
                    "id": "acoes",
                    "titulo": "Performance das Acoes",
                    "subtitulo": "Consolidado mensal das acoes vinculadas ao indicador selecionado",
                    "percentual": round(float(acao_media), 1),
                    "valor_label": f"{total_realizado_acoes:.2f}",
                    "meta_label": f"{total_meta_acoes:.2f}",
                    "cor": "#7CFFB2",
                },
                {
                    "id": "indicador",
                    "titulo": "Performance do Indicador",
                    "subtitulo": "Valor real medido frente a meta da competencia selecionada",
                    "percentual": round(float(indicador_snapshot["percentual"]), 1),
                    "valor_label": f"{indicador_snapshot['valor']:.2f}",
                    "meta_label": f"{indicador_snapshot['meta']:.2f}",
                    "cor": "#FF4FD8",
                },
            ],
        }
    )
    return render(request, "monitoramento/dashboard.html", context)


@login_required
def funcionario_metas_view(request):
    context = _worker_context(request, "funcionario-metas")
    funcionario = context["funcionario_atual"]
    if not funcionario:
        messages.error(request, "Nenhum vinculo de funcionario encontrado para essa organizacao.")
        return redirect("dashboard")

    tarefas = (
        Tarefa.objects.filter(funcionario=funcionario)
        .select_related("acao__indicador")
        .prefetch_related("registros")
        .order_by("prazo", "titulo")
    )
    tarefa_alvo = tarefas.filter(pk=request.GET.get("tarefa")).first() or tarefas.first()

    if request.method == "POST":
        tarefa_id = request.POST.get("tarefa_id")
        tarefa_post = get_object_or_404(tarefas, pk=tarefa_id)
        registro_form = RegistroDiarioForm(request.POST, tarefa=tarefa_post)
        if registro_form.is_valid():
            registro = registro_form.save(funcionario=funcionario, tarefa=tarefa_post)
            _sincronizar_indicador_competencia(tarefa_post.acao.indicador, registro.data)
            messages.success(request, "Producao informada com sucesso.")
            return _redirect_with_query("funcionario-metas", {"tarefa": tarefa_post.id})
    else:
        registro_form = RegistroDiarioForm(tarefa=tarefa_alvo)

    context.update(
        {
            "tarefas_funcionario": tarefas,
            "tarefa_alvo": tarefa_alvo,
            "registro_form": registro_form,
            "registros_recentes": RegistroDiario.objects.filter(funcionario=funcionario).select_related("tarefa")[:8],
            "hoje": timezone.localdate(),
        }
    )
    return render(request, "monitoramento/funcionario_metas.html", context)


@login_required
def funcionario_resultados_view(request):
    context = _worker_context(request, "funcionario-resultados")
    funcionario = context["funcionario_atual"]
    if not funcionario:
        messages.error(request, "Nenhum vinculo de funcionario encontrado para essa organizacao.")
        return redirect("dashboard")

    tarefas = Tarefa.objects.filter(funcionario=funcionario).select_related("acao__indicador")
    total_meta = sum(float(t.meta_quantidade or 0) for t in tarefas)
    total_realizado = sum(float(t.realizado_total or 0) for t in tarefas)
    percentual = round((total_realizado / total_meta * 100), 1) if total_meta else 0

    context.update(
        {
            "tarefas_funcionario": tarefas,
            "resultado_percentual": percentual,
            "resultado_meta_total": total_meta,
            "resultado_realizado_total": total_realizado,
        }
    )
    return render(request, "monitoramento/funcionario_resultados.html", context)


@login_required
def funcionario_alertas_view(request):
    context = _worker_context(request, "funcionario-alertas")
    funcionario = context["funcionario_atual"]
    if not funcionario:
        messages.error(request, "Nenhum vinculo de funcionario encontrado para essa organizacao.")
        return redirect("dashboard")

    hoje = timezone.localdate()
    tarefas = Tarefa.objects.filter(funcionario=funcionario).select_related("acao__indicador")
    alertas = []
    for tarefa in tarefas:
        if tarefa.prazo and tarefa.prazo < hoje and not tarefa.concluida:
            alertas.append(("atrasada", tarefa))
        elif tarefa.percentual_realizado < 100:
            alertas.append(("pendente", tarefa))

    context.update({"alertas_tarefas": alertas[:10], "hoje": hoje})
    return render(request, "monitoramento/funcionario_alertas.html", context)


@login_required
def diagnosticos_view(request):
    context = _base_context(request, "diagnosticos")
    cliente = context["cliente_atual"]
    diagnosticos = Diagnostico.objects.filter(cliente=cliente) if cliente else Diagnostico.objects.none()
    if request.method == "POST" and cliente:
        if request.POST.get("form_name") == "editar_diagnostico":
            diagnostico_obj = get_object_or_404(diagnosticos, pk=request.POST.get("diagnostico_id"))
            form = DiagnosticoForm(request.POST, instance=diagnostico_obj)
            if form.is_valid():
                form.save()
                messages.success(request, "Diagnostico atualizado com sucesso.")
                return _redirect_with_query("diagnosticos", {"cliente": cliente.id if context["perfil_tipo"] == "admin" else None})
            context["diagnostico_form"] = DiagnosticoForm()
            context["diagnostico_edicao_form"] = form
            context["diagnostico_alvo_modal"] = diagnostico_obj
        else:
            form = DiagnosticoForm(request.POST)
            if form.is_valid():
                diagnostico = form.save(commit=False)
                diagnostico.cliente = cliente
                diagnostico.save()
                messages.success(request, "Diagnostico cadastrado com sucesso.")
                return _redirect_with_query("diagnosticos", {"cliente": cliente.id if context["perfil_tipo"] == "admin" else None})
            context["diagnostico_form"] = form
    else:
        context["diagnostico_form"] = DiagnosticoForm()
        diagnostico_alvo = diagnosticos.filter(pk=request.GET.get("diagnostico")).first() or diagnosticos.first()
        context["diagnostico_edicao_form"] = DiagnosticoForm(instance=diagnostico_alvo) if diagnostico_alvo else DiagnosticoForm()
        context["diagnostico_alvo_modal"] = diagnostico_alvo
    context["diagnosticos_execucao"] = diagnosticos.filter(status=Diagnostico.Status.EXECUCAO)
    context["diagnosticos_iniciar"] = diagnosticos.filter(status=Diagnostico.Status.INICIAR)
    context["diagnosticos_outros"] = diagnosticos.exclude(status__in=[Diagnostico.Status.EXECUCAO, Diagnostico.Status.INICIAR])
    return render(request, "monitoramento/diagnosticos.html", context)


@login_required
def indicadores_view(request):
    context = _base_context(request, "indicadores")
    cliente = context["cliente_atual"]
    diagnosticos = Diagnostico.objects.filter(cliente=cliente) if cliente else Diagnostico.objects.none()
    diagnostico_id = request.GET.get("diagnostico")
    diagnostico = diagnosticos.filter(pk=diagnostico_id).first() or diagnosticos.first()
    indicadores = (
        Indicador.objects.filter(diagnostico=diagnostico).prefetch_related("acoes", "meta_vigencias")
        if diagnostico
        else Indicador.objects.none()
    )
    if request.method == "POST" and diagnostico:
        if request.POST.get("form_name") == "editar_indicador":
            indicador_obj = get_object_or_404(indicadores, pk=request.POST.get("indicador_id"))
            indicador_edicao_form = IndicadorForm(request.POST, instance=indicador_obj)
            if indicador_edicao_form.is_valid():
                indicador = indicador_edicao_form.save()
                _registrar_meta_vigencia(
                    indicador,
                    indicador_edicao_form.cleaned_data["meta_valor"],
                    indicador_edicao_form.cleaned_data["vigencia_inicio"],
                )
                _sincronizar_indicador_competencia(indicador)
                messages.success(request, "Indicador atualizado com sucesso.")
                return _redirect_with_query(
                    "indicadores",
                    {"cliente": cliente.id if context["perfil_tipo"] == "admin" else None, "diagnostico": diagnostico.id},
                )
            context["indicador_form"] = IndicadorForm()
            context["indicador_edicao_form"] = indicador_edicao_form
            context["indicador_alvo_modal"] = indicador_obj
        else:
            indicador_form = IndicadorForm(request.POST)
            if indicador_form.is_valid():
                indicador = indicador_form.save(commit=False)
                indicador.diagnostico = diagnostico
                indicador.save()
                _registrar_meta_vigencia(
                    indicador,
                    indicador_form.cleaned_data["meta_valor"],
                    indicador_form.cleaned_data["vigencia_inicio"],
                )
                _sincronizar_indicador_competencia(indicador)
                messages.success(request, "Indicador cadastrado com sucesso.")
                return _redirect_with_query(
                    "indicadores",
                    {"cliente": cliente.id if context["perfil_tipo"] == "admin" else None, "diagnostico": diagnostico.id},
                )
            context["indicador_form"] = indicador_form
    else:
        context["indicador_form"] = IndicadorForm()
    indicador_alvo_modal = indicadores.filter(pk=request.GET.get("indicador")).first() or indicadores.first()
    context.update(
        {
            "diagnosticos": diagnosticos,
            "diagnostico_selecionado": diagnostico,
            "indicadores": indicadores,
            "indicador_alvo_modal": indicador_alvo_modal,
            "indicador_edicao_form": IndicadorForm(instance=indicador_alvo_modal) if indicador_alvo_modal else IndicadorForm(),
            "historicos_indicadores": IndicadorHistoricoMensal.objects.filter(indicador__in=indicadores[:8])[:12],
        }
    )
    return render(request, "monitoramento/indicadores.html", context)


@login_required
def acoes_view(request):
    context = _base_context(request, "acoes")
    cliente = context["cliente_atual"]
    competencia = _parse_competencia(request.GET.get("competencia"))
    competencia_final = _proxima_competencia(competencia)
    competencia_anterior = _competencia_anterior(competencia)
    competencia_proxima = _proxima_competencia(competencia)
    diagnosticos = Diagnostico.objects.filter(cliente=cliente) if cliente else Diagnostico.objects.none()
    diagnostico_id = request.GET.get("diagnostico")
    diagnostico = diagnosticos.filter(pk=diagnostico_id).first() or diagnosticos.first()
    indicadores = Indicador.objects.filter(diagnostico=diagnostico) if diagnostico else Indicador.objects.none()
    indicador_id = request.GET.get("indicador")
    indicador = indicadores.filter(pk=indicador_id).first() or indicadores.first()
    acoes = (
        AcaoMelhoria.objects.filter(indicador=indicador)
        .select_related("responsavel")
        .prefetch_related(
            "tarefas__registros",
            "tarefas__funcionario__user",
            "tarefas__funcionario__equipe",
            "atribuicoes__funcionario__user",
            "atribuicoes__equipe",
            "atribuicoes__distribuicoes__funcionario__user",
        )
        if indicador
        else AcaoMelhoria.objects.none()
    )
    if request.method == "POST" and cliente:
        if request.POST.get("form_name") == "nova_acao" and indicador:
            acao_form = AcaoForm(request.POST, cliente=cliente)
            atribuicao_form = AtribuicaoAcaoForm(cliente=cliente)
            if acao_form.is_valid():
                acao = acao_form.save(commit=False)
                acao.indicador = indicador
                acao.save()
                messages.success(request, "Acao cadastrada com sucesso.")
                return _redirect_with_query(
                    "acoes",
                    {
                        "cliente": cliente.id if context["perfil_tipo"] == "admin" else None,
                        "diagnostico": diagnostico.id if diagnostico else None,
                        "indicador": indicador.id,
                        "competencia": competencia.strftime("%Y-%m"),
                    },
                )
        else:
            acao_alvo = get_object_or_404(acoes, pk=request.POST.get("acao_id"))
            acao_form = AcaoForm(cliente=cliente)
            atribuicao_form = AtribuicaoAcaoForm(cliente=cliente)
            salvos, tarefas_criadas, erros = _salvar_atribuicoes_pendentes(cliente, acao_alvo, request.POST.get("pending_assignments"))
            if salvos:
                messages.success(
                    request,
                    f"{salvos} atribuicao(oes) adicionada(s) a acao. {tarefas_criadas} tarefa(s) foram disponibilizadas para os funcionarios."
                )
                return _redirect_with_query(
                    "acoes",
                    {
                        "cliente": cliente.id if context["perfil_tipo"] == "admin" else None,
                        "diagnostico": diagnostico.id if diagnostico else None,
                        "indicador": indicador.id if indicador else None,
                        "competencia": competencia.strftime("%Y-%m"),
                    },
                )
            if erros:
                messages.error(request, " ".join(erros))
        context["acao_form"] = acao_form
        context["atribuicao_form"] = atribuicao_form
    else:
        context["acao_form"] = AcaoForm(cliente=cliente)
        context["atribuicao_form"] = AtribuicaoAcaoForm(cliente=cliente)
    acao_alvo_modal = acoes.filter(pk=request.GET.get("acao")).first() or acoes.first()
    equipes_detalhe_modal = []
    equipes_rateio_data = {}
    if cliente:
        equipes_qs = Equipe.objects.filter(cliente=cliente).prefetch_related("funcionarios__user")
        for equipe in equipes_qs:
            equipes_rateio_data[str(equipe.id)] = [
                {
                    "id": funcionario.id,
                    "nome": str(funcionario),
                }
                for funcionario in equipe.funcionarios.filter(ativo=True).order_by("id")
            ]
    indicador_snapshot = _snapshot_indicador_por_registros(indicador, competencia) if indicador else {"valor": Decimal("0"), "meta": Decimal("0"), "percentual": Decimal("0")}
    acoes_lista = []
    for acao in acoes:
        tarefas_acao = list(acao.tarefas.all())
        registros_competencia = [
            registro
            for tarefa in tarefas_acao
            for registro in tarefa.registros.all()
            if competencia <= registro.data < competencia_final
        ]
        realizado_total = sum((registro.quantidade_realizada for registro in registros_competencia), Decimal("0"))
        percentual_realizado = _percentual(realizado_total, acao.meta_mensal)
        atribuicoes_acao = list(acao.atribuicoes.all())
        atribuicoes_profissionais = [item for item in atribuicoes_acao if item.funcionario_id]
        atribuicoes_equipes = [item for item in atribuicoes_acao if item.equipe_id]
        acoes_lista.append(
            {
                "obj": acao,
                "id": acao.id,
                "nome": acao.nome,
                "meta_mensal": acao.meta_mensal,
                "status": acao.status,
                "status_display": acao.get_status_display(),
                "responsavel": acao.responsavel,
                "realizado_total": realizado_total,
                "percentual_realizado": percentual_realizado,
                "total_atribuicoes_profissionais": len(atribuicoes_profissionais),
                "total_atribuicoes_equipes": len(atribuicoes_equipes),
                "possui_equipes": bool(atribuicoes_equipes),
            }
        )

    if acao_alvo_modal:
        atribuicoes_equipes_modal = [
            atribuicao
            for atribuicao in acao_alvo_modal.atribuicoes.all()
            if atribuicao.equipe_id
        ]
        tarefas_acao_modal = list(acao_alvo_modal.tarefas.all())
        for atribuicao in atribuicoes_equipes_modal:
            membros_ids_manuais = {
                distribuicao.funcionario_id: distribuicao.valor_mensal
                for distribuicao in atribuicao.distribuicoes.all()
            }
            tarefas_equipe = [
                tarefa
                for tarefa in tarefas_acao_modal
                if tarefa.funcionario and tarefa.funcionario.equipe_id == atribuicao.equipe_id
            ]
            membros = []
            for tarefa in tarefas_equipe:
                registros_membro = [
                    registro
                    for registro in tarefa.registros.all()
                    if competencia <= registro.data < competencia_final
                ]
                realizado_membro = sum((registro.quantidade_realizada for registro in registros_membro), Decimal("0"))
                ultima_justificativa = next(
                    (registro.justificativa for registro in registros_membro if registro.justificativa),
                    "",
                )
                meta_oficial_membro = membros_ids_manuais.get(tarefa.funcionario_id, tarefa.meta_quantidade)
                membros.append(
                    {
                        "id": tarefa.funcionario_id,
                        "nome": str(tarefa.funcionario),
                        "funcao": tarefa.funcionario.funcao or "Sem funcao definida",
                        "meta_mensal": meta_oficial_membro,
                        "realizado_total": realizado_membro,
                        "percentual_realizado": _percentual(realizado_membro, meta_oficial_membro),
                        "situacao": tarefa.get_situacao_display(),
                        "ultima_justificativa": ultima_justificativa or "Sem justificativa registrada no mes.",
                    }
                )

            membros.sort(key=lambda item: item["nome"].lower())
            realizado_equipe = sum((membro["realizado_total"] for membro in membros), Decimal("0"))
            equipes_detalhe_modal.append(
                {
                    "id": atribuicao.id,
                    "nome": atribuicao.equipe.nome,
                    "modo_rateio": atribuicao.get_modo_rateio_display(),
                    "meta_mensal": atribuicao.valor_mensal,
                    "realizado_total": realizado_equipe,
                    "percentual_realizado": _percentual(realizado_equipe, atribuicao.valor_mensal),
                    "membros": membros,
                    "total_membros": len(membros),
                }
            )

    context.update(
        {
            "competencia_input": competencia.strftime("%Y-%m"),
            "competencia_label": _formatar_competencia(competencia),
            "competencia_nome": _formatar_competencia(competencia, incluir_ano=False),
            "competencia_anterior_input": competencia_anterior.strftime("%Y-%m"),
            "competencia_proxima_input": competencia_proxima.strftime("%Y-%m"),
            "diagnosticos": diagnosticos,
            "diagnostico_selecionado": diagnostico,
            "indicadores": indicadores,
            "indicador_selecionado": indicador,
            "indicador_valor_competencia": indicador_snapshot["valor"],
            "indicador_meta_competencia": indicador_snapshot["meta"],
            "indicador_percentual_competencia": indicador_snapshot["percentual"],
            "acoes": acoes,
            "acoes_lista": acoes_lista,
            "acao_alvo_modal": acao_alvo_modal,
            "atribuicoes_acao": AcaoAtribuicao.objects.filter(acao=acao_alvo_modal).prefetch_related("distribuicoes__funcionario__user") if acao_alvo_modal else AcaoAtribuicao.objects.none(),
            "equipes_detalhe_modal": equipes_detalhe_modal,
            "equipes_rateio_data": equipes_rateio_data,
        }
    )
    return render(request, "monitoramento/acoes.html", context)


@login_required
def equipes_view(request):
    context = _base_context(request, "equipes")
    cliente = context["cliente_atual"]
    equipes = Equipe.objects.filter(cliente=cliente).annotate(total_funcionarios=Count("funcionarios")) if cliente else Equipe.objects.none()
    equipe_id = request.GET.get("equipe")
    equipe = equipes.filter(pk=equipe_id).first() or equipes.first()
    profissionais = Funcionario.objects.filter(equipe=equipe) if equipe else Funcionario.objects.none()
    if request.method == "POST" and cliente:
        if request.POST.get("form_name") == "nova_equipe":
            equipe_form = EquipeForm(request.POST)
            profissional_form = ProfissionalForm()
            if equipe_form.is_valid():
                nova_equipe = equipe_form.save(commit=False)
                nova_equipe.cliente = cliente
                nova_equipe.save()
                messages.success(request, "Equipe cadastrada com sucesso.")
                return _redirect_with_query(
                    "equipes",
                    {"cliente": cliente.id if context["perfil_tipo"] == "admin" else None, "equipe": nova_equipe.id},
                )
        else:
            equipe_form = EquipeForm()
            profissional_form = ProfissionalForm(request.POST)
            if profissional_form.is_valid() and equipe:
                profissional_form.save(cliente=cliente, equipe=equipe)
                messages.success(request, "Profissional cadastrado com sucesso.")
                return _redirect_with_query(
                    "equipes",
                    {"cliente": cliente.id if context["perfil_tipo"] == "admin" else None, "equipe": equipe.id},
                )
        context["equipe_form"] = equipe_form
        context["profissional_form"] = profissional_form
    else:
        context["equipe_form"] = EquipeForm()
        context["profissional_form"] = ProfissionalForm()
    context.update({"equipes": equipes, "equipe_selecionada": equipe, "profissionais": profissionais})
    return render(request, "monitoramento/equipes.html", context)


@login_required
def profissionais_view(request):
    context = _base_context(request, "profissionais")
    cliente = context["cliente_atual"]
    termo = request.GET.get("q", "").strip()
    profissionais = Funcionario.objects.filter(cliente=cliente) if cliente else Funcionario.objects.none()
    if termo:
        profissionais = profissionais.filter(
            models.Q(user__first_name__icontains=termo)
            | models.Q(user__last_name__icontains=termo)
            | models.Q(user__username__icontains=termo)
        )
    context.update({"profissionais": profissionais, "termo_busca": termo})
    return render(request, "monitoramento/profissionais.html", context)

# Create your views here.
