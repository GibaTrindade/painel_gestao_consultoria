from django.contrib import admin

from .models import (
    AcaoMelhoria,
    AcaoAtribuicao,
    AcaoAtribuicaoDistribuicao,
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


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("user", "tipo", "cliente", "cargo", "telefone")
    list_filter = ("tipo", "cliente")
    search_fields = ("user__username", "user__first_name", "user__last_name", "cargo", "cliente__nome")


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "parent", "codigo_acesso", "tipo", "responsavel", "cidade", "uf", "ativo")
    list_filter = ("tipo", "ativo", "uf", "parent")
    search_fields = ("nome", "codigo_acesso", "responsavel", "cidade", "parent__nome")


@admin.register(UsuarioCliente)
class UsuarioClienteAdmin(admin.ModelAdmin):
    list_display = ("user", "cliente", "tipo", "ativo")
    list_filter = ("tipo", "ativo", "cliente")
    search_fields = ("user__username", "user__first_name", "user__last_name", "cliente__nome", "cliente__codigo_acesso")


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ("nome", "cliente", "lider")
    list_filter = ("cliente",)
    search_fields = ("nome", "cliente__nome")


@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ("user", "cliente", "equipe", "funcao", "telefone", "ativo")
    list_filter = ("cliente", "equipe", "ativo")
    search_fields = ("user__username", "user__first_name", "user__last_name", "funcao")


@admin.register(Diagnostico)
class DiagnosticoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "cliente", "status", "periodo_inicio", "periodo_fim")
    list_filter = ("cliente", "status")
    search_fields = ("titulo", "cliente__nome", "descricao")


@admin.register(Indicador)
class IndicadorAdmin(admin.ModelAdmin):
    list_display = ("nome", "diagnostico", "meta_valor", "valor_atual", "ativo")
    list_filter = ("diagnostico__cliente", "ativo")
    search_fields = ("nome", "codigo", "diagnostico__titulo")


@admin.register(AcaoMelhoria)
class AcaoMelhoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "indicador", "meta_mensal", "status", "responsavel")
    list_filter = ("status", "indicador__diagnostico__cliente")
    search_fields = ("nome", "indicador__nome")


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "acao", "funcionario", "meta_quantidade", "previsto_quantidade", "situacao", "prazo", "concluida")
    list_filter = ("concluida", "prioridade", "situacao", "funcionario__cliente")
    search_fields = ("titulo", "funcionario__user__first_name", "funcionario__user__last_name")


@admin.register(RegistroDiario)
class RegistroDiarioAdmin(admin.ModelAdmin):
    list_display = ("tarefa", "funcionario", "data", "quantidade_prevista", "quantidade_realizada", "situacao")
    list_filter = ("data", "situacao", "funcionario__cliente")
    search_fields = ("tarefa__titulo", "descricao_atividade", "funcionario__user__first_name")


@admin.register(IndicadorHistoricoMensal)
class IndicadorHistoricoMensalAdmin(admin.ModelAdmin):
    list_display = ("indicador", "competencia", "valor", "meta")
    list_filter = ("indicador__diagnostico__cliente",)
    search_fields = ("indicador__nome",)


@admin.register(IndicadorMetaVigencia)
class IndicadorMetaVigenciaAdmin(admin.ModelAdmin):
    list_display = ("indicador", "inicio_vigencia", "fim_vigencia", "valor_meta")
    list_filter = ("indicador__diagnostico__cliente",)
    search_fields = ("indicador__nome",)


@admin.register(AcaoAtribuicao)
class AcaoAtribuicaoAdmin(admin.ModelAdmin):
    list_display = ("acao", "funcionario", "equipe", "modo_rateio", "valor_mensal", "ativo")
    list_filter = ("ativo", "acao__indicador__diagnostico__cliente")
    search_fields = ("acao__nome", "funcionario__user__first_name", "equipe__nome")


@admin.register(AcaoAtribuicaoDistribuicao)
class AcaoAtribuicaoDistribuicaoAdmin(admin.ModelAdmin):
    list_display = ("atribuicao", "funcionario", "valor_mensal")
    list_filter = ("atribuicao__acao__indicador__diagnostico__cliente",)
    search_fields = ("atribuicao__acao__nome", "funcionario__user__first_name", "funcionario__user__last_name")

# Register your models here.
