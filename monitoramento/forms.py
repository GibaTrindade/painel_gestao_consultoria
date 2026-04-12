import os
from datetime import date

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from .models import (
    AcaoAtribuicao,
    AcaoMelhoria,
    Diagnostico,
    Equipe,
    Funcionario,
    Indicador,
    IndicadorHistoricoMensal,
    PerfilUsuario,
    Cliente,
    RegistroDiario,
    Tarefa,
    UsuarioCliente,
)


class StyledFormMixin:
    def apply_styling(self):
        for field in self.fields.values():
            css_class = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{css_class} form-control".strip()


class CodigoOrganizacaoForm(StyledFormMixin, forms.Form):
    codigo = forms.CharField(max_length=60, label="Codigo da organizacao")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()

    def clean_codigo(self):
        codigo = self.cleaned_data["codigo"].strip().lower()
        master_code = os.getenv("MASTER_ACCESS_CODE", "smr-admin").lower()
        if codigo == master_code:
            self.cleaned_data["is_master_code"] = True
            return codigo

        cliente = Cliente.objects.filter(codigo_acesso__iexact=codigo, ativo=True).first()
        if not cliente:
            raise forms.ValidationError("Codigo da organizacao invalido.")
        self.cleaned_data["cliente"] = cliente
        self.cleaned_data["is_master_code"] = False
        return codigo


class OrganizacaoLoginForm(StyledFormMixin, forms.Form):
    username = forms.CharField(label="Usuario")
    password = forms.CharField(label="Senha", widget=forms.PasswordInput)

    def __init__(self, *args, cliente=None, allow_master=False, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()
        self.request = request
        self.cliente = cliente
        self.allow_master = allow_master
        self.user = None

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")

        if not username or not password:
            return cleaned_data

        user = authenticate(self.request, username=username, password=password)
        if not user:
            raise forms.ValidationError("Usuario ou senha invalidos.")

        if self.allow_master:
            if not (user.is_superuser or user.is_staff):
                raise forms.ValidationError("Esse acesso mestre e restrito a administradores.")
            self.user = user
            return cleaned_data

        membership = UsuarioCliente.objects.filter(user=user, cliente=self.cliente, ativo=True).first()
        if not membership:
            raise forms.ValidationError("Esse usuario nao possui acesso a organizacao informada.")

        self.cleaned_data["membership"] = membership
        self.user = user
        return cleaned_data


class DiagnosticoForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Diagnostico
        fields = [
            "titulo",
            "status",
            "periodo_inicio",
            "periodo_fim",
            "periodo_melhoria_inicio",
            "periodo_melhoria_fim",
            "descricao",
            "causa_gargalo",
        ]
        widgets = {
            "periodo_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "periodo_fim": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "periodo_melhoria_inicio": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "periodo_melhoria_fim": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "causa_gargalo": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()
        for field_name in ["periodo_inicio", "periodo_fim", "periodo_melhoria_inicio", "periodo_melhoria_fim"]:
            self.fields[field_name].input_formats = ["%Y-%m-%d"]
        self.fields["titulo"].label = "Descricao"
        self.fields["descricao"].label = "Historico"
        self.fields["causa_gargalo"].label = "Gargalo identificado"


class IndicadorForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Indicador
        fields = ["nome", "valor_atual", "meta_valor"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()
        self.fields["nome"].label = "Indicador"
        self.fields["valor_atual"].label = "Valor atual"
        self.fields["meta_valor"].label = "Meta"
        self.fields["valor_atual"].help_text = "Informe o valor medido hoje. Se ainda nao houver medicao, use 0."
        self.fields["meta_valor"].help_text = "Meta mensal esperada para esse indicador."


class AtualizarIndicadorForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = IndicadorHistoricoMensal
        fields = ["competencia", "valor", "meta"]
        widgets = {"competencia": forms.DateInput(attrs={"type": "month"}, format="%Y-%m")}

    def __init__(self, *args, indicador=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()
        self.indicador = indicador
        self.fields["competencia"].label = "Mes"
        self.fields["competencia"].input_formats = ["%Y-%m", "%Y-%m-%d"]
        self.fields["valor"].label = "Valor apurado"
        self.fields["meta"].label = "Meta do mes"
        self.fields["valor"].help_text = "Valor real medido para a competencia selecionada."
        if indicador:
            self.fields["meta"].initial = indicador.meta_valor
            self.fields["valor"].initial = indicador.valor_atual
            self.initial["competencia"] = date.today().replace(day=1).strftime("%Y-%m")

    def clean_competencia(self):
        competencia = self.cleaned_data["competencia"]
        return date(competencia.year, competencia.month, 1)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.indicador:
            instance.indicador = self.indicador
            self.indicador.valor_atual = instance.valor
            self.indicador.meta_valor = instance.meta
            if commit:
                self.indicador.save(update_fields=["valor_atual", "meta_valor", "updated_at"])
        if commit:
            instance.save()
        return instance


class AcaoForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = AcaoMelhoria
        fields = ["nome", "meta_mensal", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()
        self.fields["nome"].label = "Nome da acao"
        self.fields["meta_mensal"].label = "Valor"


class AtribuicaoAcaoForm(StyledFormMixin, forms.Form):
    tipo_destino = forms.ChoiceField(
        choices=[("funcionario", "Profissional"), ("equipe", "Equipes")],
        widget=forms.RadioSelect,
        initial="funcionario",
    )
    profissional = forms.ModelChoiceField(queryset=Funcionario.objects.none(), required=False)
    equipe_destino = forms.ModelChoiceField(queryset=Equipe.objects.none(), required=False, label="Equipe")
    valor_mensal = forms.DecimalField(max_digits=12, decimal_places=2)
    ativo = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, cliente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()
        if cliente:
            self.fields["profissional"].queryset = Funcionario.objects.filter(cliente=cliente)
            self.fields["equipe_destino"].queryset = Equipe.objects.filter(cliente=cliente)
        self.fields["profissional"].label = "Pesquisar"
        self.fields["valor_mensal"].label = "Valor mensal"

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo_destino")
        profissional = cleaned_data.get("profissional")
        equipe = cleaned_data.get("equipe_destino")
        if tipo == "funcionario" and not profissional:
            self.add_error("profissional", "Selecione um profissional.")
        if tipo == "equipe" and not equipe:
            self.add_error("equipe_destino", "Selecione uma equipe.")
        return cleaned_data

    def save(self, commit=True, acao=None):
        instance = AcaoAtribuicao(acao=acao)
        instance.valor_mensal = self.cleaned_data["valor_mensal"]
        instance.ativo = self.cleaned_data["ativo"]
        if self.cleaned_data["tipo_destino"] == "funcionario":
            instance.funcionario = self.cleaned_data["profissional"]
            instance.equipe = None
        else:
            instance.equipe = self.cleaned_data["equipe_destino"]
            instance.funcionario = None
        if commit:
            instance.save()
        return instance


class EquipeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Equipe
        fields = ["nome"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()


class RegistroDiarioForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = RegistroDiario
        fields = ["descricao_atividade", "quantidade_realizada", "justificativa"]
        widgets = {
            "descricao_atividade": forms.Textarea(attrs={"rows": 3}),
            "justificativa": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, tarefa=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()
        self.tarefa = tarefa
        self.fields["descricao_atividade"].label = "Informe o que foi feito"
        self.fields["quantidade_realizada"].label = "Informe o valor alcancado"
        self.fields["justificativa"].label = "Justificativa"

    def save(self, commit=True, funcionario=None, tarefa=None):
        instance = super().save(commit=False)
        tarefa_obj = tarefa or self.tarefa
        instance.tarefa = tarefa_obj
        instance.funcionario = funcionario
        instance.quantidade_prevista = tarefa_obj.meta_quantidade if tarefa_obj else 0
        realizado = instance.quantidade_realizada or 0
        meta = tarefa_obj.meta_quantidade if tarefa_obj else 0

        if realizado >= meta and meta > 0:
            instance.situacao = Tarefa.Situacao.CONCLUIDA
            tarefa_obj.situacao = Tarefa.Situacao.CONCLUIDA
            tarefa_obj.concluida = True
        elif realizado > 0:
            instance.situacao = Tarefa.Situacao.EM_ANDAMENTO
            tarefa_obj.situacao = Tarefa.Situacao.EM_ANDAMENTO
            tarefa_obj.concluida = False
        else:
            instance.situacao = Tarefa.Situacao.PENDENTE

        if commit:
            instance.save()
            if tarefa_obj:
                tarefa_obj.save(update_fields=["situacao", "concluida", "updated_at"])
        return instance


class ProfissionalForm(StyledFormMixin, forms.Form):
    nome = forms.CharField(max_length=150)
    username = forms.CharField(max_length=150)
    cargo = forms.CharField(max_length=120, required=False)
    telefone = forms.CharField(max_length=30, required=False)
    email = forms.EmailField(required=False)
    dias_trabalho = forms.MultipleChoiceField(
        choices=[
            ("Domingo", "Domingo"),
            ("Segunda", "Segunda"),
            ("Terca", "Terca"),
            ("Quarta", "Quarta"),
            ("Quinta", "Quinta"),
            ("Sexta", "Sexta"),
            ("Sabado", "Sabado"),
        ],
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    ativo = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_styling()
        self.fields["nome"].label = "Nome"
        self.fields["username"].label = "Usuario"

    def save(self, cliente, equipe):
        nome = self.cleaned_data["nome"].strip()
        first_name, _, last_name = nome.partition(" ")
        user, created = User.objects.get_or_create(
            username=self.cleaned_data["username"],
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": self.cleaned_data["email"],
            },
        )
        if created:
            user.set_password("func123")
        user.first_name = first_name
        user.last_name = last_name
        user.email = self.cleaned_data["email"]
        user.save()

        PerfilUsuario.objects.update_or_create(
            user=user,
            defaults={
                "tipo": PerfilUsuario.TipoPerfil.FUNCIONARIO,
                "cliente": cliente,
                "cargo": self.cleaned_data["cargo"],
                "telefone": self.cleaned_data["telefone"],
            },
        )

        UsuarioCliente.objects.update_or_create(
            user=user,
            cliente=cliente,
            defaults={"tipo": PerfilUsuario.TipoPerfil.FUNCIONARIO, "ativo": self.cleaned_data["ativo"]},
        )

        funcionario, _ = Funcionario.objects.update_or_create(
            user=user,
            cliente=cliente,
            defaults={
                "equipe": equipe,
                "funcao": self.cleaned_data["cargo"],
                "telefone": self.cleaned_data["telefone"],
                "email": self.cleaned_data["email"],
                "dias_trabalho": " / ".join(self.cleaned_data["dias_trabalho"]),
                "ativo": self.cleaned_data["ativo"],
            },
        )
        return funcionario
