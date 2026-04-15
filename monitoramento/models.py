from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils.text import slugify
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PerfilUsuario(models.Model):
    class TipoPerfil(models.TextChoices):
        ADMIN = "admin", "Admin da Consultoria"
        CLIENTE = "cliente", "Gestor do Cliente"
        FUNCIONARIO = "funcionario", "Funcionário"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    cliente = models.ForeignKey(
        "Cliente",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfis",
    )
    tipo = models.CharField(max_length=20, choices=TipoPerfil.choices, default=TipoPerfil.FUNCIONARIO)
    cargo = models.CharField(max_length=120, blank=True)
    telefone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_tipo_display()})"


class Cliente(TimeStampedModel):
    nome = models.CharField(max_length=200)
    codigo_acesso = models.SlugField(max_length=60, unique=True, blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    tipo = models.CharField(
        max_length=30,
        choices=[
            ("rede", "Rede"),
            ("empresa", "Empresa"),
            ("secretaria", "Secretaria"),
            ("prefeitura", "Prefeitura"),
            ("unidade", "Unidade"),
            ("upa", "UPA"),
            ("posto", "Posto"),
        ],
        default="empresa",
    )
    responsavel = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    cidade = models.CharField(max_length=120, blank=True)
    uf = models.CharField(max_length=2, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        if not self.parent_id:
            return
        if self.parent_id == self.id:
            raise ValidationError({"parent": "Um cliente nao pode ser pai dele mesmo."})

        atual = self.parent
        while atual:
            if atual.id == self.id:
                raise ValidationError({"parent": "Nao e permitido criar ciclo na hierarquia de clientes."})
            atual = atual.parent

    def get_ancestors(self, include_self=False):
        ancestors = []
        atual = self if include_self else self.parent
        while atual:
            ancestors.append(atual)
            atual = atual.parent
        return list(reversed(ancestors))

    def get_descendant_ids(self, include_self=True):
        ids = [self.id] if include_self and self.id else []
        frontier = [self.id] if self.id else []
        while frontier:
            filhos = list(Cliente.objects.filter(parent_id__in=frontier).values_list("id", flat=True))
            ids.extend(filhos)
            frontier = filhos
        return ids

    @property
    def nome_hierarquico(self):
        return " > ".join(item.nome for item in self.get_ancestors(include_self=True))

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.codigo_acesso:
            base = slugify(self.nome)[:50] or "organizacao"
            codigo = base
            counter = 1
            while Cliente.objects.exclude(pk=self.pk).filter(codigo_acesso=codigo).exists():
                counter += 1
                codigo = f"{base[:45]}-{counter}"
            self.codigo_acesso = codigo
        super().save(*args, **kwargs)


class UsuarioCliente(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clientes_acesso")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="usuarios_acesso")
    tipo = models.CharField(max_length=20, choices=PerfilUsuario.TipoPerfil.choices, default=PerfilUsuario.TipoPerfil.FUNCIONARIO)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["cliente__nome", "user__username"]
        unique_together = ("user", "cliente")

    def __str__(self):
        return f"{self.user.username} -> {self.cliente.nome}"


class Equipe(TimeStampedModel):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="equipes")
    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    lider = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipes_lideradas",
    )

    class Meta:
        unique_together = ("cliente", "nome")
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} - {self.cliente.nome}"


class Funcionario(TimeStampedModel):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="funcionarios")
    equipe = models.ForeignKey(Equipe, on_delete=models.SET_NULL, null=True, blank=True, related_name="funcionarios")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="vinculos_funcionario")
    funcao = models.CharField(max_length=120, blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    dias_trabalho = models.CharField(max_length=120, blank=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["user__first_name", "user__username"]

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Diagnostico(TimeStampedModel):
    class Status(models.TextChoices):
        INICIAR = "iniciar", "A iniciar"
        EXECUCAO = "execucao", "Em execução"
        CONCLUIDO = "concluido", "Concluído"
        PAUSADO = "pausado", "Pausado"

    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="diagnosticos")
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    periodo_inicio = models.DateField()
    periodo_fim = models.DateField()
    periodo_melhoria_inicio = models.DateField(null=True, blank=True)
    periodo_melhoria_fim = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.INICIAR)
    causa_gargalo = models.TextField(blank=True)

    class Meta:
        ordering = ["-periodo_inicio", "titulo"]

    def __str__(self):
        return self.titulo


class Indicador(TimeStampedModel):
    diagnostico = models.ForeignKey(Diagnostico, on_delete=models.CASCADE, related_name="indicadores")
    codigo = models.CharField(max_length=30, blank=True)
    nome = models.CharField(max_length=160)
    descricao = models.TextField(blank=True)
    unidade = models.CharField(max_length=30, default="un")
    meta_valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    valor_atual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.codigo:
            prefixo = "IND"
            ultimo = (
                Indicador.objects.filter(diagnostico=self.diagnostico, codigo__startswith=f"{prefixo}-")
                .exclude(pk=self.pk)
                .order_by("-id")
                .first()
            )
            proximo_numero = 1
            if ultimo and ultimo.codigo:
                try:
                    proximo_numero = int(ultimo.codigo.split("-")[-1]) + 1
                except (ValueError, TypeError):
                    proximo_numero = Indicador.objects.filter(diagnostico=self.diagnostico).exclude(pk=self.pk).count() + 1
            self.codigo = f"{prefixo}-{proximo_numero:03d}"
        super().save(*args, **kwargs)

    @property
    def percentual(self):
        if not self.meta_valor:
            return Decimal("0")
        return min((self.valor_atual / self.meta_valor) * 100, Decimal("999.99"))

    @property
    def status_resumo(self):
        if self.meta_valor <= 0:
            return "Sem meta"
        if self.valor_atual >= self.meta_valor:
            return "Meta atingida"
        if self.valor_atual > 0:
            return "Em andamento"
        return "Sem produção"


class IndicadorMetaVigencia(TimeStampedModel):
    indicador = models.ForeignKey(Indicador, on_delete=models.CASCADE, related_name="meta_vigencias")
    inicio_vigencia = models.DateField(help_text="Use o primeiro dia do mes como inicio da vigencia.")
    fim_vigencia = models.DateField(null=True, blank=True)
    valor_meta = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["-inicio_vigencia"]
        unique_together = ("indicador", "inicio_vigencia")

    def __str__(self):
        return f"{self.indicador.nome} - {self.inicio_vigencia:%m/%Y} ({self.valor_meta})"


class AcaoMelhoria(TimeStampedModel):
    class Status(models.TextChoices):
        ATIVA = "ativa", "Ativa"
        INATIVA = "inativa", "Inativa"
        CONCLUIDA = "concluida", "Concluída"

    indicador = models.ForeignKey(Indicador, on_delete=models.CASCADE, related_name="acoes")
    nome = models.CharField(max_length=180)
    descricao = models.TextField(blank=True)
    meta_mensal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ATIVA)
    responsavel = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acoes_responsavel",
    )

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def realizado_total(self):
        total = self.tarefas.aggregate(total=Sum("registros__quantidade_realizada"))["total"]
        return total or Decimal("0")

    @property
    def percentual_realizado(self):
        if not self.meta_mensal:
            return Decimal("0")
        return min((self.realizado_total / self.meta_mensal) * 100, Decimal("999.99"))


class Tarefa(TimeStampedModel):
    class Situacao(models.TextChoices):
        PENDENTE = "pendente", "Pendente"
        ATRASADA = "atrasada", "Atrasada"
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        CONCLUIDA = "concluida", "Concluida"
        CANCELADA = "cancelada", "Cancelada"

    class Prioridade(models.TextChoices):
        BAIXA = "baixa", "Baixa"
        MEDIA = "media", "Média"
        ALTA = "alta", "Alta"

    acao = models.ForeignKey(AcaoMelhoria, on_delete=models.CASCADE, related_name="tarefas")
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name="tarefas")
    titulo = models.CharField(max_length=180)
    descricao = models.TextField(blank=True)
    meta_quantidade = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    previsto_quantidade = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    prazo = models.DateField(null=True, blank=True)
    prioridade = models.CharField(max_length=10, choices=Prioridade.choices, default=Prioridade.MEDIA)
    situacao = models.CharField(max_length=20, choices=Situacao.choices, default=Situacao.PENDENTE)
    concluida = models.BooleanField(default=False)

    class Meta:
        ordering = ["prazo", "titulo"]

    def __str__(self):
        return self.titulo

    @property
    def realizado_total(self):
        total = self.registros.aggregate(total=Sum("quantidade_realizada"))["total"]
        return total or Decimal("0")

    @property
    def percentual_realizado(self):
        if not self.meta_quantidade:
            return Decimal("0")
        return min((self.realizado_total / self.meta_quantidade) * 100, Decimal("999.99"))


class RegistroDiario(TimeStampedModel):
    tarefa = models.ForeignKey(Tarefa, on_delete=models.CASCADE, related_name="registros")
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name="registros")
    data = models.DateField(default=timezone.localdate)
    descricao_atividade = models.TextField(blank=True)
    quantidade_prevista = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantidade_realizada = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    situacao = models.CharField(max_length=20, choices=Tarefa.Situacao.choices, default=Tarefa.Situacao.PENDENTE)
    justificativa = models.TextField(blank=True)

    class Meta:
        ordering = ["-data", "-created_at"]

    def __str__(self):
        return f"{self.funcionario} - {self.data}"


class JustificativaNaoAtingimentoMensal(TimeStampedModel):
    class CategoriaGargalo(models.TextChoices):
        FALTA_INSUMO = "falta_insumo", "Falta de insumo"
        FALTA_PESSOAL = "falta_pessoal", "Falta de pessoal"
        PROBLEMA_LOGISTICO = "problema_logistico", "Problema logistico"
        PROBLEMA_SISTEMA = "problema_sistema", "Problema no sistema"
        DEMANDA_ABAIXO = "demanda_abaixo", "Demanda abaixo do previsto"
        AUSENCIA_PROFISSIONAL = "ausencia_profissional", "Ausencia do profissional"
        OUTRO = "outro", "Outro"

    tarefa = models.ForeignKey(Tarefa, on_delete=models.CASCADE, related_name="justificativas_mensais")
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name="justificativas_mensais")
    competencia = models.DateField(help_text="Use o primeiro dia do mes como referencia.")
    categoria = models.CharField(max_length=40, choices=CategoriaGargalo.choices)
    justificativa = models.TextField(blank=True)
    detalhe_outro = models.TextField(blank=True)

    class Meta:
        ordering = ["-competencia", "-updated_at"]
        unique_together = ("tarefa", "competencia")

    def __str__(self):
        return f"{self.tarefa} - {self.competencia:%m/%Y}"


class IndicadorHistoricoMensal(TimeStampedModel):
    indicador = models.ForeignKey(Indicador, on_delete=models.CASCADE, related_name="historicos")
    competencia = models.DateField(help_text="Use o primeiro dia do mes como referencia.")
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    meta = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["-competencia"]
        unique_together = ("indicador", "competencia")

    def __str__(self):
        return f"{self.indicador.nome} - {self.competencia:%m/%Y}"


class AcaoAtribuicao(TimeStampedModel):
    class ModoRateio(models.TextChoices):
        AUTOMATICO = "automatico", "Automatico"
        MANUAL = "manual", "Manual"

    acao = models.ForeignKey(AcaoMelhoria, on_delete=models.CASCADE, related_name="atribuicoes")
    funcionario = models.ForeignKey(
        Funcionario,
        on_delete=models.CASCADE,
        related_name="atribuicoes_acao",
        null=True,
        blank=True,
    )
    equipe = models.ForeignKey(
        Equipe,
        on_delete=models.CASCADE,
        related_name="atribuicoes_acao",
        null=True,
        blank=True,
    )
    valor_mensal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    modo_rateio = models.CharField(max_length=20, choices=ModoRateio.choices, default=ModoRateio.AUTOMATICO)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["-ativo", "id"]

    def __str__(self):
        destino = self.funcionario or self.equipe
        return f"{self.acao.nome} -> {destino}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if bool(self.funcionario) == bool(self.equipe):
            raise ValidationError("Informe apenas um destino: funcionario ou equipe.")


class AcaoAtribuicaoDistribuicao(TimeStampedModel):
    atribuicao = models.ForeignKey(AcaoAtribuicao, on_delete=models.CASCADE, related_name="distribuicoes")
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE, related_name="distribuicoes_acao")
    valor_mensal = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["funcionario__user__first_name", "funcionario__user__username"]
        unique_together = ("atribuicao", "funcionario")

    def __str__(self):
        return f"{self.atribuicao} -> {self.funcionario} ({self.valor_mensal})"
