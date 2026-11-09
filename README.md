# Conclave

Um conselho de agentes para colocar ideias à prova.

Conclave organiza especialistas de IA para explorar propostas, pesquisar oportunidades, confrontar premissas e apoiar decisões. Em vez de buscar concordância automática, reúne perspectivas diferentes e preserva as objeções que realmente importam. A decisão final continua sendo sua.

O foco atual é um conselho empresarial com contexto brasileiro, mas o processo também serve para amadurecer novas iniciativas e projetos. Não é uma equipe de desenvolvimento por padrão.

## O que este repositório contém

Uma base documental em Markdown — instruções, especialidades, referências e protocolos — e o módulo local de voz em `apps/voice/`. A documentação orienta os agentes, mas **não executa agentes sozinha**.

A via ativa desta instalação é o **Maki com subagentes internos**, coordenados pelo Maestro em um terminal. A mesa web recebe rodadas estruturadas para audição, não é chat web e não inclui microfone/STT. Um clone não instala o Maki, não configura modelos nem ativa a ponte automaticamente. A integração está em implementação e ainda precisa de validação live; as roles antigas do Maestri permanecem como legado, sem alteração.

## Como o conselho trabalha

1. **Definir a questão.** Identificar projeto, estágio, objetivo, restrições e critério de sucesso.
2. **Selecionar perspectivas.** Maestro aciona apenas os especialistas necessários, com contexto e escopo explícitos.
3. **Analisar de forma independente.** Os especialistas separam fatos, estimativas, hipóteses e opiniões, indicando evidências e limites.
4. **Confrontar os argumentos.** Divergências relevantes são examinadas; a síntese não é decidida por maioria nem por autoridade do personagem.
5. **Recomendar um próximo passo.** A entrega apresenta alternativas, riscos, confiança de 0 a 1 e condições que fariam a recomendação mudar.
6. **Decidir e registrar.** O usuário decide. Estado, histórico e decisões ficam em arquivos locais separados por projeto.

Há três modos de atuação:

- **Consultoria:** uma pergunta delimitada, respondida diretamente ou com a especialidade necessária.
- **Conselho:** uma decisão multidisciplinar, com análises independentes e confronto de argumentos.
- **Tribunal:** uma tese colocada à prova por sua melhor defesa e sua objeção mais forte; não é julgamento jurídico nem ataque pessoal.

O processo completo está em [protocols/council.md](protocols/council.md).

## Quem participa

| Agente | Responsabilidade | Base |
| --- | --- | --- |
| Maestro | Coordenação, contexto e síntese | [maestro](brains/maestro/) |
| Professor Pardal | Ideação e exploração técnica | [professor-pardal](brains/professor-pardal/) |
| Dona do Contra | Crítica, premissas frágeis e riscos | [hater](brains/hater/) |
| Sherlocka | Pesquisa de mercado e evidências | [xeroque-rolmes](brains/xeroque-rolmes/) |
| Tio Patinhas | Finanças e viabilidade | [tio-patinhas](brains/tio-patinhas/) |
| Pablo | Marketing e posicionamento | [pablo](brains/pablo/) |
| MVPzinha | Validação de hipóteses e MVP | [mvpzinho](brains/mvpzinho/) |
| Doutora B.O. | Análise jurídica e riscos legais | [doutor-bo](brains/doutor-bo/) |
| Seu Zé | Operações e execução autorizada | [seu-ze](brains/seu-ze/) |
| Tubarão | Vendas e negociação | [tubarao](brains/tubarao/) |

Os nomes identificam papéis de trabalho. As bases representam especialidades e referências, não imitação de pessoas públicas, endosso dos autores citados ou parecer profissional habilitado. Hater, Xeroque Rolmes, MVPzinho e Doutor B.O. permanecem aliases de entrada; IDs e pastas não mudam, nem registros históricos. Dona do Contra, Sherlocka, MVPzinha e Doutora B.O. têm apresentação feminina em português, sem estereótipos ou mudança de especialidade. Dona do Contra pode concordar quando a evidência sustenta a proposta.

## Como começar

### Na instalação atual com Maki

1. Leia [AGENTS.md](AGENTS.md) para entender limites, responsabilidades e acesso seletivo à base em `D:/conclave/`.
2. Prepare o módulo de voz conforme abaixo. O plugin-fonte fica em `apps/voice/maki/`; a partir de `D:/conclave/apps/voice/`, instale a cópia local ao projeto com `uv run python install_plugin.py`. O instalador preserva configurações locais divergentes e recusa destinos fora do projeto.
3. No Maki aberto em `D:/conclave`, **o usuário deve executar `/reload`**. Se o Maki avisar que o projeto ganhou `.maki/init.lua` desde a autorização anterior, inicie `maki --trust` nessa pasta para confiar apenas nessa execução; não use `--yolo`. Criar arquivos ou recarregar não comprova que subagentes e ponte funcionam: é necessário um teste real. Não é preciso executar `maestri list/ask/check` neste fluxo.
4. Forneça ao Maestro ID/empresa, estágio, pergunta, contexto necessário, restrições, perda tolerável e critério de sucesso. Se houver memória local, retome pelo registro e pelo estado somente do projeto identificado.
5. Maestro seleciona especialistas com `council_consult`, pede `council_counterpoint` quando há divergência material e conclui com sua síntese. A delegação inclui escopo, exclusões, aceite, validações e caminho absoluto `D:/conclave/brains/<slug>/`, começando por `_hot.md` e `voice.md`; não carregar toda a memória.
6. Ao concluir, Maestro deve chamar `council_publish` automaticamente para enviar a rodada à API local, sem novo pedido de envio. Isso não autoriza publicação externa. `/conclave-status` mostra pendências e `/conclave-retry` reenvia rodadas concluídas sem repetir análises. Se o serviço falhar, os retornos textuais continuam no Maki; pendências em memória podem se perder no cancelamento ou `/reload`.
7. Na web, selecione “Debate + síntese” ou “Somente síntese do Maestro” e clique para ouvir. Nenhum modo inicia áudio pela chegada da rodada ou pela simples seleção. Avalie evidências, divergências e limites antes de autorizar qualquer execução.

Exemplo de pedido:

> Projeto EXEMPLO-01, estágio de exploração. Quero avaliar uma ideia de serviço para pequenos negócios brasileiros. Selecione as perspectivas necessárias, questione as premissas e recomende um teste barato antes de investir. Não execute ações externas.

### Em outra instalação

Use a estrutura como referência, mas configure explicitamente os agentes e sua ferramenta de orquestração. As instruções ativas usam a raiz absoluta `D:/conclave/`; adapte-a antes do uso em outra máquina. O ID interno `QG-BRAINS-01` e os slugs foram preservados para manter referências existentes. Caminhos ou nomes antigos em registros históricos e roles Maestri não são instruções de instalação atuais.

## Como os brains são consultados

Cada pasta em `brains/` tem oito arquivos:

| Arquivo | Conteúdo |
| --- | --- |
| `_hot.md` | Mapa rápido e pontos de entrada |
| `voice.md` | Identidade, tom e protocolo de atuação |
| `principles.md` | Princípios de julgamento |
| `frameworks.md` | Roteiros e ferramentas de análise |
| `books.md` | Referências bibliográficas e limites de acesso |
| `positions.md` | Teses revisáveis e contrapontos |
| `stories.md` | Casos, exemplos e seus limites |
| `sources.md` | Fontes e nível de evidência |

O acesso é seletivo: começar por `_hot.md`, ler `voice.md` na primeira atuação da sessão e consultar no máximo dois arquivos temáticos adicionais por demanda. As entradas de `sources.md` que sustentam as afirmações utilizadas também devem ser consultadas. Não carregar todos os brains nem todo o acervo por padrão.

## Estrutura da base pública

```text
AGENTS.md
brains/
  <especialista>/
knowledge/
  references/core.md
  shared/brazil.md
protocols/
  council.md
  decision-making.md
  maintenance.md
  project-memory.md
  research.md
```

- [AGENTS.md](AGENTS.md): instruções locais, responsabilidades e limites de autorização.
- [Referências comuns](knowledge/references/core.md): repertório compartilhado e interpretações por especialidade.
- [Contexto brasileiro](knowledge/shared/brazil.md): checklist para não transplantar premissas de outros mercados sem revisão.
- [Decisões](protocols/decision-making.md): diferença entre recomendação e aprovação do usuário.
- [Pesquisa](protocols/research.md): fontes, evidências, atualidade e incerteza.
- [Manutenção](protocols/maintenance.md): revisão e promoção controlada de conhecimento.
- [Memória por projeto](protocols/project-memory.md): organização, retomada e preservação de histórico.

## Memória local e privacidade

A base reutilizável é pública; o trabalho de cada projeto permanece local. Os caminhos abaixo não acompanham um clone e devem ser mantidos conforme a necessidade real:

```text
projects/registry.md
projects/<ID>/memory/state.md
projects/<ID>/memory/history.md
projects/<ID>/memory/decisions/
projects/<ID>/memory/research/
projects/<ID>/memory/ideas/
memory/
```

`state.md` é o estado atual; `history.md` preserva a cronologia. Premissas, decisões, pesquisas, reuniões e ideias ficam na memória do respectivo projeto, sem estruturas vazias ou mistura de informações entre empresas. Documentos e anexos também permanecem separados por projeto.

Memória operacional não é mantida em notas do canvas. Notas antigas são legado e não devem virar uma segunda fonte atual.

O `.gitignore` exclui `projects/`, `memory/`, `decisions/`, `.maestri/`, `.maki/`, `.idea/` e padrões comuns de credenciais. Isso **não garante ausência de dados privados nos arquivos permitidos**, não remove arquivos já rastreados e não apaga publicações anteriores. Revise o conteúdo antes de cada commit ou publicação e não force a inclusão de caminhos privados.

## Laboratório de voz local

O módulo [`apps/voice/`](apps/voice/) usa kokoro-onnx para TTS pt-BR local, preservando entrada manual e amostras. A ponte Maki → API local → mesa web está em implementação; **não há comprovação live da integração nesta etapa documental**. O usuário relatou geração normal com as três vozes e aprovou a distribuição inicial, mas isso não equivale a aprovação detalhada de pronúncia ou naturalidade.

**Local não significa deliberação offline:** prompts, contexto delegado e respostas dos subagentes passam pelo provedor de modelo configurado no Maki. Somente o TTS permanece local. Envie apenas o contexto necessário e autorizado.

Requisitos: Windows, Python 3.12 e `uv`. No terminal, a partir de `apps/voice/`:

```console
uv sync --locked --python 3.12
uv run python -X utf8 assets.py
uv run python -X utf8 server.py
```

Abra `http://127.0.0.1:8765`. O download explícito obtém aproximadamente 354 MB de modelo e vozes oficiais, com SHA256 fixados em `assets.py`. O servidor não baixa arquivos ao iniciar. O ambiente Python e o runtime ocupam espaço adicional. Não use múltiplos workers nem exponha o serviço à rede.

O catálogo `apps/voice/catalog.json` mantém IDs, aliases e defaults dos dez perfis, com três vozes nativas (`pf_dora`, `pm_alex`, `pm_santa`). Defaults iniciais aprovados: Maestro `pm_santa/0.95`; Professor Pardal `pm_alex/1.05`; Dona do Contra `pf_dora/1.00`; Sherlocka `pf_dora/0.95`; Tio Patinhas `pm_santa/0.90`; Pablo `pm_alex/1.05`; MVPzinha `pf_dora/1.05`; Doutora B.O. `pf_dora/0.90`; Seu Zé `pm_santa/1.00`; Tubarão `pm_alex/1.00`. São ajustes iniciais, não dez identidades vocais distintas garantidas nem características psicológicas derivadas de gênero/timbre.

Os perfis de voz/velocidade são persistidos em `apps/voice/data/profiles.json`, ignorado pelo Git, com escrita atômica. `GET/PUT /api/profiles` usa `schema_version: 1` e os dez IDs canônicos; aceita apenas vozes do catálogo e velocidade de 0,8 a 1,2. Arquivo ilegível/corrompido é preservado e exige recuperação explícita, não sobrescrita silenciosa. Salvar/restaurar defaults deve ter confirmação visual; sem override, a geração resolve o perfil salvo no servidor.

A geração ocorre em CPU, um trabalho por vez, com até três solicitações admitidas (uma ativa e duas em espera), limite de 6.000 caracteres e tempo máximo de espera/geração de 180 segundos. A mesa mantém reprodução serializada, pausa/continuação e parada; textos longos são segmentados sem remover ressalvas, números ou a ordem original. O texto original continua disponível. Parar descarta a síntese em curso e impede os próximos trechos; o trecho ativo pode terminar internamente.

### Contrato e retenção de rodadas

- `POST /api/rounds` publica texto, sem gerar áudio; exige autenticação local com token efêmero em `apps/voice/data/bridge-token`, renovado a cada partida e nunca enviado aos modelos ou logs. O serviço permanece em loopback com validação de Host/Origin, sem CORS aberto. Não exponha a credencial nem o serviço à rede.
- Envelope versão 1: `round_id`, `project_id`, `title`, `session_id`, `status` (`complete`/`partial`), `interventions`, `synthesis` e `failures`. Cada intervenção contém `intervention_id`, `specialist_id` canônico, `phase`, `text`, `reply_to` e `order` contígua desde zero. A síntese tem campo próprio, fase `synthesis` e autoria `maestro`; falhas são metadados, não falas atribuídas.
- Até nove análises independentes, três em paralelo, e uma etapa de até dois contrapontos dirigidos. Contraponto exige análise da própria especialista e vínculo anterior explícito. Sem divergência material, não fabricar discordância nem chamar simples análises de debate com contraponto. Síntese preserva convergências, divergências, evidências, limites e próximo passo, sem votação.
- Limites: 6.000 caracteres por intervenção e 128 KiB por envelope; rejeição explícita, sem truncamento silencioso. Repetir `round_id` com conteúdo igual não duplica a rodada; conteúdo diferente gera conflito enquanto o ID estiver retido.
- `GET /api/rounds` lista metadados; `GET /api/rounds/{id}` entrega o texto; `DELETE /api/rounds/{id}` remove a rodada. Retenção **somente em memória**: máximo de 20 rodadas, TTL de duas horas desde publicação (polling não renova) e máximo de **2,5 MiB** de envelopes serializados. Limites removem as mais antigas; reiniciar descarta todas. Exclusão/expiração impede novas gerações daquela rodada.
- Rodada recebida não inicia áudio nem interrompe a fala em andamento. Os dois modos exigem clique e usam os perfis salvos, uma fala por vez. “Debate + síntese” toca análises, contrapontos existentes e síntese; “Somente síntese do Maestro” toca apenas a síntese.

Textos e áudios de rodadas não são gravados em disco ou logs da ponte/API; apenas perfis de voz são persistidos pelo fluxo, além da credencial efêmera privada. Isso não elimina políticas de retenção do Maki/provedor nem substitui a memória documental do projeto. Download manual pelo navegador é ação explícita. O benchmark é separado e grava áudios/métricas em `apps/voice/output/`, ignorado pelo Git, assim como modelos e ambiente virtual.

Para preparar as nove amostras disponíveis na página e medir o desempenho:

```console
uv run python -X utf8 benchmark.py --offline
uv run pytest -q
uv run ruff check .
```

O benchmark bloqueia conexões por sockets Python durante a carga e síntese; não é uma auditoria de tráfego de código nativo ou do sistema. Ele grava métricas locais e mantém a aprovação auditiva como pendente. Para o teste opcional de interface real, é necessário Microsoft Edge instalado e `VOICE_BROWSER_TEST=1` no ambiente antes de executar `uv run pytest tests/test_browser.py -q`. Esse teste inicia e encerra seu próprio servidor e se recusa a usar uma porta já ocupada.

Biblioteca upstream: MIT; modelo: Apache-2.0 conforme o README/model card upstream. Os pesos não são redistribuídos por este repositório. Antes de qualquer redistribuição, confira licenças, atribuições e eventuais avisos dos artefatos e dependências. Não há clonagem nem imitação de pessoas reais.

## Limites e estado atual

- A base e os protocolos estão documentados; sua presença não comprova aplicação pelos agentes nem eficácia das recomendações.
- Consultas pontuais anteriores não comprovam o novo fluxo. Plugin/subagentes Maki, ponte autenticada e reprodução de rodadas ainda exigem teste live; instalação, lint ou testes simulados não bastam para declarar integração ativa.
- Disponibilidade dos agentes e do backend precisa ser verificada em cada tarefa. Falhas não autorizam inventar pareceres ou alterar configurações para contorná-las.
- Referências têm níveis de acesso e datas próprios. Citações e sínteses não significam leitura integral dos livros, fatos atuais confirmados ou aconselhamento profissional.
- Recomendações não autorizam transações, contratos, mudanças de sistemas, commits, pushes, publicações ou implantações. Essas ações exigem aprovação específica.
- A implementação interna de referência usa o ID `QG-BRAINS-01`; ele não identifica um projeto comercial.

## Origem

A organização foi inspirada em [Roast Room, de nateherkai](https://github.com/nateherkai/roast-room), com adaptação para um conselho de especialidades e contexto brasileiro. A inspiração arquitetural não comprova eficácia empresarial e não implica instalação de componentes daquele projeto.

Conclave era anteriormente chamado QG das Ideias. Referências históricas e identificadores antigos são preservados quando necessários à rastreabilidade.
