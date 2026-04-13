# Backlog do Produto

## Objetivo do app
O sistema existe para ajudar gestores a entender:

- se as metas estao sendo atingidas
- quais unidades, equipes e funcionarios estao ficando abaixo do esperado
- quais acoes de melhoria estao funcionando ou nao
- por que certos resultados nao estao acontecendo

Em outras palavras, o app nao deve ser apenas operacional. Ele precisa virar uma ferramenta de analise gerencial.

## Estado atual
Hoje o sistema ja entrega bem:

- login por codigo da organizacao
- separacao entre acesso gestor e acesso funcionario
- modo hibrido para usuarios que podem atuar como gestor e funcionario
- cadastro de diagnosticos, indicadores, acoes, equipes e profissionais
- atribuicao de acoes para profissionais ou equipes
- geracao automatica de tarefas para funcionarios
- lancamento diario de producao pelos funcionarios
- atualizacao automatica dos indicadores com base nos lancamentos
- dashboard por cliente com leitura mensal

## Validacoes feitas
Ultima validacao executada:

- `.\.venv\Scripts\python manage.py check`
- `.\.venv\Scripts\python manage.py test monitoramento`

Status:

- testes passando
- system check sem problemas

## Perguntas de negocio que o sistema precisa responder
Exemplos reais que o produto deve conseguir responder com seguranca:

1. A meta do municipio e 1000 vacinas no mes. Nos ultimos 3 meses a media foi 800. Por que?
2. Quais UPAs ou unidades nao conseguiram atingir a meta?
3. Nessas unidades, quais gargalos aparecem com mais frequencia?
4. Quais equipes ou funcionarios nao estao conseguindo cumprir as metas?
5. Quais justificativas aparecem com mais frequencia para o nao atingimento?
6. As acoes de melhoria estao gerando impacto real no indicador ou so execucao operacional?

## Furos atuais do sistema

### 1. Falta hierarquia institucional
Hoje o modelo usa `Cliente` como contexto principal, mas nao existe hierarquia entre:

- municipio
- secretaria
- unidade
- UPA
- posto

Impacto:

- nao da para consolidar indicadores de varias unidades dentro do mesmo municipio
- nao da para responder "qual UPA puxou a meta para baixo"

Prioridade: alta

### 2. Calculo mensal inconsistente em acoes
Na pagina de acoes, o percentual realizado ainda pode considerar todo o historico da acao, nao apenas a competencia do mes.

Impacto:

- o numero exibido pode ficar incorreto para leitura mensal
- compromete analise gerencial

Prioridade: alta

### 3. Motivo do nao atingimento ainda e fraco
Hoje existe:

- `causa_gargalo` no diagnostico
- `justificativa` livre no registro diario

Mas o sistema nao exige justificativa estruturada quando o realizado fica abaixo da meta.

Impacto:

- dificulta responder "por que nao bateu a meta"
- nao permite consolidar causas com qualidade

Prioridade: alta

### 4. Regra de equipe ainda pode distorcer a meta
Quando uma acao e atribuida para equipe, o sistema cria tarefa para cada membro usando o mesmo valor mensal da atribuicao.

Impacto:

- risco de multiplicar meta/entrega artificialmente
- fica faltando regra clara de rateio

Prioridade: alta

### 5. Semantica do indicador ainda esta ambigua
O sistema evoluiu para atualizar o indicador automaticamente pelos lancamentos dos funcionarios, mas ainda existe edicao de `valor_atual` na tela de indicadores.

Impacto:

- pode gerar duvida sobre a fonte da verdade
- pode confundir gestor e manutencao futura

Prioridade: media

### 6. Desativacao de atribuicao nao fecha o ciclo operacional
Hoje a tarefa e criada automaticamente quando a atribuicao esta ativa, mas o fluxo de desativacao/remocao ainda precisa revisar o que acontece com as tarefas geradas.

Impacto:

- risco de manter tarefa ativa sem vinculo atual valido

Prioridade: media

### 7. Analise de rede ainda nao existe
O dashboard atual funciona por cliente/unidade e por indicador selecionado, mas nao existe camada de comparacao entre varias unidades ao longo dos meses.

Impacto:

- nao responde bem perguntas de rede, municipio ou secretaria

Prioridade: alta

## Backlog priorizado

### Fase 1. Fechar coerencia do que ja existe

#### Item 1. Tornar calculos mensais consistentes nas acoes
Objetivo:

- garantir que toda leitura de "meta mensal" e "realizado" use a competencia selecionada

Entregas:

- ajustar percentual realizado da pagina de acoes para ler apenas o mes atual/selecionado
- revisar dashboard, resultados do funcionario e tabelas relacionadas
- adicionar testes para competencia mensal

Status: homologado
Prioridade: alta

#### Item 2. Definir e implementar regra de rateio por equipe
Objetivo:

- impedir distorcao quando uma acao e atribuida a uma equipe

Fases decididas:

- Fase 1: dividir a meta igualmente entre os membros ativos da equipe
- Fase 2: permitir distribuicao manual por membro
- Fase 3: permitir que a meta fique na equipe, mas mantendo visibilidade interna do desempenho de cada membro

Status: homologado
Prioridade: alta

Detalhamento das fases:

##### Fase 1. Rateio igual entre membros ativos
Exemplo:

- acao com meta mensal `90`
- equipe com `3` membros ativos
- cada membro recebe tarefa/meta `30`

Vantagens:

- simples de entender
- matematicamente coerente
- boa base para o sistema continuar evoluindo

Status: homologado

##### Fase 2. Distribuicao manual por membro
Exemplo:

- acao com meta mensal `90`
- gestor define:
- membro A = `40`
- membro B = `30`
- membro C = `20`

Vantagens:

- respeita diferenca de carga, funcao e disponibilidade
- melhora a leitura gerencial por pessoa

Status: homologado

##### Fase 3. Meta da equipe com visibilidade interna
Exemplo:

- equipe recebe meta mensal `90`
- a meta oficial fica na equipe
- os membros continuam lancando suas entregas individualmente
- o sistema mostra:
- realizado da equipe
- percentual da equipe
- contribuicao individual de cada membro

Objetivo dessa fase:

- manter a leitura gerencial no nivel da equipe
- sem perder a capacidade de entender quem esta contribuindo e quem esta ficando para tras

Status: homologado

#### Item 3. Fechar semantica do indicador
Objetivo:

- deixar claro que o indicador e derivado dos lancamentos, ou assumir explicitamente que ele pode ser medido externamente

Direcao recomendada hoje:

- indicador derivado automaticamente dos lancamentos
- editar apenas nome, unidade e meta
- nao editar manualmente o valor atual
- metas historicas controladas por vigencia, sem reescrever o passado

Status: homologado
Prioridade: media

### Fase 2. Fortalecer explicacao do nao atingimento

#### Item 4. Exigir justificativa quando o realizado ficar abaixo do previsto
Objetivo:

- melhorar a qualidade da explicacao do nao atingimento

Entregas:

- tornar justificativa obrigatoria em cenarios abaixo da meta
- deixar feedback claro na area do funcionario
- cobrir com teste

Status: homologado
Prioridade: alta

#### Item 5. Estruturar categorias de gargalo/causa
Objetivo:

- transformar justificativas em dados analisaveis

Sugestao inicial de categorias:

- falta de insumo
- falta de pessoal
- problema logistico
- problema no sistema
- demanda abaixo do previsto
- ausencia do profissional
- outro

Entregas:

- criar campo estruturado no `RegistroDiario`
- manter texto livre complementar
- permitir relatorios por causa

Status: homologado
Prioridade: alta

#### Item 6. Criar analise de gargalos por unidade, equipe e funcionario
Objetivo:

- responder "o que esta acontecendo" de forma agregada

Entregas:

- ranking de gargalos por periodo
- ranking de funcionarios/equipes abaixo da meta
- relacao entre acao, indicador e justificativa

Status: homologado
Prioridade: alta

### Fase 3. Estruturar rede e consolidacao institucional

#### Item 7. Criar hierarquia institucional
Objetivo:

- permitir consolidacao por municipio/secretaria e comparacao entre unidades

Direcao sugerida:

- `Organizacao` ou `Rede`
- `Unidade`
- `Equipe`
- `Funcionario`

ou evoluir `Cliente` para suportar `parent`

Status: pendente
Prioridade: alta

#### Item 8. Criar visao consolidada multiunidade
Objetivo:

- responder perguntas do tipo "quais UPAs nao atingiram a meta nos ultimos 3 meses"

Entregas:

- dashboard consolidado por rede
- comparativo entre unidades
- media de 3 meses
- ranking das piores e melhores unidades

Status: pendente
Prioridade: alta

### Fase 4. Maturidade operacional

#### Item 9. Revisar ciclo de vida de atribuicoes e tarefas
Objetivo:

- garantir coerencia quando uma atribuicao e desativada, editada ou removida

Entregas:

- definir o que acontece com tarefa ja criada
- registrar historico de alteracoes
- evitar tarefa "orfã"

Status: pendente
Prioridade: media

#### Item 10. Melhorar trilha de auditoria
Objetivo:

- dar confiabilidade para gestao e consultoria

Entregas:

- saber quem alterou meta, indicador, diagnostico, acao ou atribuicao
- congelar competencias fechadas, se necessario

Status: pendente
Prioridade: media

## Ordem recomendada de execucao
Para termos ganho real de produto rapido, a sequencia sugerida e:

1. tornar calculos mensais consistentes nas acoes
2. definir regra de rateio por equipe
3. fechar semantica do indicador
4. exigir justificativa quando abaixo da meta
5. estruturar categorias de gargalo
6. criar analise de gargalos por unidade/equipe/funcionario
7. criar hierarquia institucional
8. criar visao consolidada multiunidade
9. revisar ciclo de vida de atribuicoes e tarefas
10. melhorar trilha de auditoria

## Convencoes para documentacao daqui pra frente
Quando evoluirmos o sistema, vale manter:

- backlog em `backlog.md`
- decisoes de modelagem em um `docs/arquitetura.md`
- regras de negocio em um `docs/regras-negocio.md`
- changelog de entregas em um `docs/entregas.md`

### Regra de status do backlog
Vamos seguir estes status:

- `pendente`
- `em andamento`
- `concluido tecnicamente`
- `homologado`

Fluxo combinado:

1. implementacao
2. validacao tecnica com testes e check
3. atualizacao do `backlog.md`
4. teste funcional na interface
5. mudanca para `homologado` quando aprovado

## Proximo passo sugerido
Comecar pelo item:

- `Item 1. Tornar calculos mensais consistentes nas acoes`

Esse item corrige a confiabilidade numerica do sistema e prepara o terreno para a parte analitica.
