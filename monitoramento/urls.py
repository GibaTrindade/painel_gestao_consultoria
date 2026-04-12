from django.urls import path

from . import views


urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("app/metas/", views.funcionario_metas_view, name="funcionario-metas"),
    path("app/resultados/", views.funcionario_resultados_view, name="funcionario-resultados"),
    path("app/alertas/", views.funcionario_alertas_view, name="funcionario-alertas"),
    path("diagnosticos/", views.diagnosticos_view, name="diagnosticos"),
    path("indicadores/", views.indicadores_view, name="indicadores"),
    path("acoes/", views.acoes_view, name="acoes"),
    path("equipes/", views.equipes_view, name="equipes"),
    path("profissionais/", views.profissionais_view, name="profissionais"),
]
