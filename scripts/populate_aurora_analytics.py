from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User

from monitoramento.models import (
    AcaoAtribuicao,
    AcaoMelhoria,
    Cliente,
    Diagnostico,
    Equipe,
    Funcionario,
    Indicador,
    IndicadorMetaVigencia,
    JustificativaNaoAtingimentoMensal,
    PerfilUsuario,
    RegistroDiario,
    Tarefa,
    UsuarioCliente,
)


cliente = Cliente.objects.get(codigo_acesso="aurora-saude")

categoria_cycle = [
    "falta_insumo",
    "falta_pessoal",
    "problema_logistico",
    "problema_sistema",
    "demanda_abaixo",
    "ausencia_profissional",
    "outro",
]

months = [
    (date(2026, 1, 1), date(2026, 1, 18)),
    (date(2026, 2, 1), date(2026, 2, 18)),
    (date(2026, 3, 1), date(2026, 3, 18)),
    (date(2026, 4, 1), date(2026, 4, 10)),
]


def ensure_user(
    username,
    password,
    first_name,
    last_name,
    email,
    tipo,
    cargo,
    telefone,
    equipe=None,
    funcao=None,
    dias="Segunda / Terca / Quarta / Quinta / Sexta",
):
    user, _ = User.objects.get_or_create(
        username=username,
        defaults={"first_name": first_name, "last_name": last_name, "email": email},
    )
    user.first_name = first_name
    user.last_name = last_name
    user.email = email
    user.set_password(password)
    user.save()

    PerfilUsuario.objects.update_or_create(
        user=user,
        defaults={"tipo": tipo, "cliente": cliente, "cargo": cargo, "telefone": telefone},
    )
    UsuarioCliente.objects.update_or_create(
        user=user,
        cliente=cliente,
        defaults={"tipo": tipo, "ativo": True},
    )

    funcionario = None
    if equipe is not None:
        funcionario, _ = Funcionario.objects.update_or_create(
            user=user,
            cliente=cliente,
            defaults={
                "equipe": equipe,
                "funcao": funcao or cargo,
                "telefone": telefone,
                "email": email,
                "dias_trabalho": dias,
                "ativo": True,
            },
        )
    return user, funcionario


equipes_config = [
    {
        "nome": "UPA Centro",
        "descricao": "Urgencia e acolhimento da regiao central",
        "lider": (
            "caio.lider",
            "lider123",
            "Caio",
            "Nogueira",
            "caio@aurora.local",
            "Coordenador UPA Centro",
            "85990000002",
        ),
        "membros": [
            ("ana.upa", "func123", "Ana", "Silva", "ana.upa@aurora.local", "Enfermeira", "85990000011"),
            (
                "bruno.upa",
                "func123",
                "Bruno",
                "Pires",
                "bruno.upa@aurora.local",
                "Tecnico de enfermagem",
                "85990000012",
            ),
            ("rita.upa", "func123", "Rita", "Morais", "rita.upa@aurora.local", "Recepcionista", "85990000015"),
            ("joel.upa", "func123", "Joel", "Barros", "joel.upa@aurora.local", "Maqueiro", "85990000016"),
        ],
    },
    {
        "nome": "Imunizacao",
        "descricao": "Campanhas, busca ativa e salas de vacina",
        "lider": (
            "marina.lider",
            "lider123",
            "Marina",
            "Alves",
            "marina@aurora.local",
            "Coordenadora Imunizacao",
            "85990000003",
        ),
        "membros": [
            ("luana.vac", "func123", "Luana", "Rocha", "luana.vac@aurora.local", "Vacinadora", "85990000013"),
            (
                "igor.vac",
                "func123",
                "Igor",
                "Melo",
                "igor.vac@aurora.local",
                "Apoio de campanha",
                "85990000014",
            ),
            (
                "tania.vac",
                "func123",
                "Tania",
                "Lopes",
                "tania.vac@aurora.local",
                "Tecnica de imunizacao",
                "85990000017",
            ),
            ("davi.vac", "func123", "Davi", "Campos", "davi.vac@aurora.local", "Motorista de apoio", "85990000018"),
        ],
    },
    {
        "nome": "Saude da Familia Norte",
        "descricao": "Cobertura territorial e visitas domiciliares",
        "lider": (
            "paula.esf",
            "lider123",
            "Paula",
            "Mendes",
            "paula.esf@aurora.local",
            "Coordenadora ESF Norte",
            "85990000019",
        ),
        "membros": [
            ("lucas.esf", "func123", "Lucas", "Freitas", "lucas.esf@aurora.local", "ACS", "85990000020"),
            (
                "bia.esf",
                "func123",
                "Beatriz",
                "Souza",
                "bia.esf@aurora.local",
                "Enfermeira ESF",
                "85990000021",
            ),
            ("otavio.esf", "func123", "Otavio", "Lima", "otavio.esf@aurora.local", "Tecnico ESF", "85990000022"),
        ],
    },
    {
        "nome": "Farmacia Central",
        "descricao": "Dispensacao e reposicao de medicamentos",
        "lider": (
            "sergio.farm",
            "lider123",
            "Sergio",
            "Araujo",
            "sergio.farm@aurora.local",
            "Coordenador Farmacia",
            "85990000023",
        ),
        "membros": [
            ("nina.farm", "func123", "Nina", "Ramos", "nina.farm@aurora.local", "Farmaceutica", "85990000024"),
            (
                "vitor.farm",
                "func123",
                "Vitor",
                "Sales",
                "vitor.farm@aurora.local",
                "Auxiliar de farmacia",
                "85990000025",
            ),
            (
                "karla.farm",
                "func123",
                "Karla",
                "Rezende",
                "karla.farm@aurora.local",
                "Atendente de farmacia",
                "85990000026",
            ),
        ],
    },
]

funcionarios = {}

for equipe_cfg in equipes_config:
    lider_username, lider_password, lider_first, lider_last, lider_email, lider_cargo, lider_tel = equipe_cfg["lider"]
    lider_user, _ = ensure_user(
        lider_username,
        lider_password,
        lider_first,
        lider_last,
        lider_email,
        PerfilUsuario.TipoPerfil.CLIENTE,
        lider_cargo,
        lider_tel,
    )
    equipe, _ = Equipe.objects.update_or_create(
        cliente=cliente,
        nome=equipe_cfg["nome"],
        defaults={"descricao": equipe_cfg["descricao"], "lider": lider_user},
    )
    _, lider_func = ensure_user(
        lider_username,
        lider_password,
        lider_first,
        lider_last,
        lider_email,
        PerfilUsuario.TipoPerfil.CLIENTE,
        lider_cargo,
        lider_tel,
        equipe=equipe,
        funcao="Lider de equipe",
    )
    funcionarios[lider_username] = lider_func

    for username, password, first, last, email, funcao, tel in equipe_cfg["membros"]:
        _, funcionario = ensure_user(
            username,
            password,
            first,
            last,
            email,
            PerfilUsuario.TipoPerfil.FUNCIONARIO,
            funcao,
            tel,
            equipe=equipe,
            funcao=funcao,
        )
        funcionarios[username] = funcionario

ensure_user(
    "helena.gestor",
    "gestor123",
    "Helena",
    "Castro",
    "helena@aurora.local",
    PerfilUsuario.TipoPerfil.CLIENTE,
    "Secretaria de Saude",
    "85990000001",
)

config = [
    {
        "titulo": "Reduzir tempo de espera na UPA Centro",
        "descricao": "Plano para agilizar triagem, acolhimento e classificacao de risco.",
        "gargalo": "Picos de demanda, escalas incompletas e lentidao em registro.",
        "indicadores": [
            {
                "nome": "Pacientes triados em ate 10 minutos",
                "meta": Decimal("120"),
                "unidade": "pacientes/mes",
                "acoes": [
                    ("Reforcar triagem nos horarios de pico", Decimal("80"), ["caio.lider", "ana.upa", "bruno.upa", "rita.upa"]),
                    ("Padronizar acolhimento na recepcao", Decimal("40"), ["rita.upa", "joel.upa"]),
                ],
            },
            {
                "nome": "Cadastros concluidos sem retrabalho",
                "meta": Decimal("200"),
                "unidade": "cadastros/mes",
                "acoes": [
                    ("Revisar cadastro antes do fechamento", Decimal("90"), ["rita.upa", "joel.upa"]),
                    ("Treinar equipe para registro rapido", Decimal("60"), ["caio.lider", "ana.upa"]),
                ],
            },
        ],
    },
    {
        "titulo": "Dobrar vacinacao infantil",
        "descricao": "Fortalecer cobertura vacinal com busca ativa e campanhas locais.",
        "gargalo": "Oscilacao de insumos, adesao irregular e dificuldade de mobilizacao.",
        "indicadores": [
            {
                "nome": "Doses aplicadas em criancas",
                "meta": Decimal("300"),
                "unidade": "doses/mes",
                "acoes": [
                    ("Buscar faltosos da vacinacao infantil", Decimal("150"), ["marina.lider", "luana.vac", "igor.vac", "tania.vac"]),
                    ("Ampliar salas volantes de vacina", Decimal("90"), ["davi.vac", "luana.vac", "tania.vac"]),
                ],
            },
            {
                "nome": "Contatos efetivos com responsaveis",
                "meta": Decimal("240"),
                "unidade": "contatos/mes",
                "acoes": [
                    ("Ligar para familias com atraso vacinal", Decimal("120"), ["igor.vac", "davi.vac"]),
                    ("Fazer busca escolar com agenda semanal", Decimal("100"), ["marina.lider", "luana.vac"]),
                ],
            },
        ],
    },
    {
        "titulo": "Aumentar cobertura de visitas domiciliares",
        "descricao": "Expandir visitas prioritarias e reconectar familias ao cuidado basico.",
        "gargalo": "Territorio amplo, ausencias, chuva e falhas de rota.",
        "indicadores": [
            {
                "nome": "Visitas domiciliares realizadas",
                "meta": Decimal("260"),
                "unidade": "visitas/mes",
                "acoes": [
                    ("Reorganizar microareas prioritarias", Decimal("110"), ["paula.esf", "lucas.esf", "bia.esf"]),
                    ("Executar mutirao de visitas atrasadas", Decimal("100"), ["otavio.esf", "lucas.esf"]),
                ],
            },
            {
                "nome": "Familias reengajadas no acompanhamento",
                "meta": Decimal("160"),
                "unidade": "familias/mes",
                "acoes": [
                    ("Ativar retorno das familias vulneraveis", Decimal("80"), ["paula.esf", "bia.esf"]),
                    ("Atualizar cadastros territoriais", Decimal("60"), ["lucas.esf", "otavio.esf"]),
                ],
            },
        ],
    },
    {
        "titulo": "Melhorar disponibilidade de medicamentos",
        "descricao": "Reduzir ruptura e agilizar dispensacao para os itens mais sensiveis.",
        "gargalo": "Reposicao lenta, erro de pedido e demanda irregular.",
        "indicadores": [
            {
                "nome": "Itens dispensados sem ruptura",
                "meta": Decimal("420"),
                "unidade": "itens/mes",
                "acoes": [
                    ("Monitorar ruptura semanal da farmacia", Decimal("140"), ["sergio.farm", "nina.farm", "vitor.farm"]),
                    ("Priorizar reposicao dos itens criticos", Decimal("120"), ["karla.farm", "nina.farm"]),
                ],
            },
            {
                "nome": "Pedidos internos atendidos no prazo",
                "meta": Decimal("180"),
                "unidade": "pedidos/mes",
                "acoes": [
                    ("Padronizar conferencia dos pedidos", Decimal("90"), ["sergio.farm", "karla.farm"]),
                    ("Separar kits de alta rotacao", Decimal("70"), ["vitor.farm", "karla.farm"]),
                ],
            },
        ],
    },
]

just_idx = 0

for diag_cfg in config:
    diagnostico, _ = Diagnostico.objects.update_or_create(
        cliente=cliente,
        titulo=diag_cfg["titulo"],
        defaults={
            "descricao": diag_cfg["descricao"],
            "periodo_inicio": date(2026, 1, 1),
            "periodo_fim": date(2026, 12, 31),
            "periodo_melhoria_inicio": date(2026, 1, 1),
            "periodo_melhoria_fim": date(2026, 12, 31),
            "status": Diagnostico.Status.EXECUCAO,
            "causa_gargalo": diag_cfg["gargalo"],
        },
    )

    for indicador_cfg in diag_cfg["indicadores"]:
        indicador, _ = Indicador.objects.update_or_create(
            diagnostico=diagnostico,
            nome=indicador_cfg["nome"],
            defaults={
                "meta_valor": indicador_cfg["meta"],
                "valor_atual": Decimal("0"),
                "unidade": indicador_cfg["unidade"],
                "ativo": True,
            },
        )
        IndicadorMetaVigencia.objects.update_or_create(
            indicador=indicador,
            inicio_vigencia=date(2026, 1, 1),
            defaults={"valor_meta": indicador_cfg["meta"], "fim_vigencia": None},
        )

        for action_index, (acao_nome, meta_mensal, owners) in enumerate(indicador_cfg["acoes"], start=1):
            responsavel_user = funcionarios[owners[0]].user
            acao, _ = AcaoMelhoria.objects.update_or_create(
                indicador=indicador,
                nome=acao_nome,
                defaults={
                    "descricao": f"Rotina operacional da acao {acao_nome.lower()}.",
                    "meta_mensal": meta_mensal,
                    "status": AcaoMelhoria.Status.ATIVA,
                    "responsavel": responsavel_user,
                },
            )

            per_person = (meta_mensal / Decimal(str(len(owners)))).quantize(Decimal("0.01"))
            valores = [per_person for _ in owners]
            if sum(valores) != meta_mensal:
                valores[-1] += meta_mensal - sum(valores)

            for owner_idx, username in enumerate(owners):
                funcionario = funcionarios[username]
                valor = valores[owner_idx]
                AcaoAtribuicao.objects.update_or_create(
                    acao=acao,
                    funcionario=funcionario,
                    defaults={"valor_mensal": valor, "ativo": True},
                )
                tarefa, _ = Tarefa.objects.update_or_create(
                    acao=acao,
                    funcionario=funcionario,
                    defaults={
                        "titulo": acao.nome,
                        "descricao": acao.descricao,
                        "meta_quantidade": valor,
                        "previsto_quantidade": valor,
                        "situacao": "pendente",
                        "concluida": False,
                    },
                )

                for month_idx, (competencia, data_registro) in enumerate(months):
                    meta = tarefa.meta_quantidade
                    base_factor = Decimal(str(0.55 + (((owner_idx + action_index + month_idx) % 7) * 0.08)))
                    realizado = (meta * base_factor).quantize(Decimal("0.01"))
                    if month_idx == 3:
                        realizado = (meta * Decimal(str(0.40 + (((owner_idx + action_index) % 5) * 0.09)))).quantize(
                            Decimal("0.01")
                        )
                    if ((owner_idx + action_index + month_idx) % 4) == 0:
                        realizado = meta
                    if realizado > meta:
                        realizado = meta
                    situacao = "concluida" if realizado >= meta else "em_andamento"

                    RegistroDiario.objects.update_or_create(
                        tarefa=tarefa,
                        funcionario=funcionario,
                        data=data_registro,
                        defaults={
                            "descricao_atividade": f"OBS {competencia.strftime('%m/%Y')}: execucao de {acao.nome.lower()}.",
                            "quantidade_prevista": meta,
                            "quantidade_realizada": realizado,
                            "justificativa": "",
                            "situacao": situacao,
                        },
                    )

                    if competencia.month <= 3 and realizado < meta:
                        categoria = categoria_cycle[just_idx % len(categoria_cycle)]
                        detalhe_outro = ""
                        obs = f"Fechamento {competencia.strftime('%m/%Y')}: equipe reportou ajuste operacional."
                        if categoria == "outro":
                            detalhe_outro = "Oscilacao local nao prevista no planejamento da semana."
                        JustificativaNaoAtingimentoMensal.objects.update_or_create(
                            tarefa=tarefa,
                            competencia=competencia,
                            defaults={
                                "funcionario": funcionario,
                                "categoria": categoria,
                                "justificativa": obs,
                                "detalhe_outro": detalhe_outro,
                            },
                        )
                        just_idx += 1
                    elif competencia.month <= 3:
                        JustificativaNaoAtingimentoMensal.objects.filter(
                            tarefa=tarefa,
                            competencia=competencia,
                        ).delete()

for indicador in Indicador.objects.filter(diagnostico__cliente=cliente):
    total = Decimal("0")
    for tarefa in Tarefa.objects.filter(acao__indicador=indicador):
        total += sum(
            (
                r.quantidade_realizada
                for r in tarefa.registros.filter(data__gte=date(2026, 4, 1), data__lt=date(2026, 5, 1))
            ),
            Decimal("0"),
        )
    indicador.valor_atual = total
    indicador.save(update_fields=["valor_atual", "updated_at"])

print("Base analitica expandida com sucesso.")
print("Resumo:")
print("equipes=", Equipe.objects.filter(cliente=cliente).count())
print("funcionarios=", Funcionario.objects.filter(cliente=cliente).count())
print("diagnosticos=", Diagnostico.objects.filter(cliente=cliente).count())
print("indicadores=", Indicador.objects.filter(diagnostico__cliente=cliente).count())
print("acoes=", AcaoMelhoria.objects.filter(indicador__diagnostico__cliente=cliente).count())
print("tarefas=", Tarefa.objects.filter(funcionario__cliente=cliente).count())
print("registros=", RegistroDiario.objects.filter(funcionario__cliente=cliente).count())
print("justificativas=", JustificativaNaoAtingimentoMensal.objects.filter(funcionario__cliente=cliente).count())
print("novos acessos uteis:")
for row in [
    ("paula.esf", "lider123", "lider ESF Norte"),
    ("sergio.farm", "lider123", "lider Farmacia Central"),
    ("rita.upa", "func123", "UPA Centro"),
    ("tania.vac", "func123", "Imunizacao"),
    ("bia.esf", "func123", "ESF Norte"),
    ("nina.farm", "func123", "Farmacia Central"),
]:
    print(f"- {row[0]} / {row[1]} :: {row[2]}")
