# QG das Ideias

Base documental do conselho empresarial brasileiro. **QG-BRAINS-01 — implementação interna**, não autorização de investimento ou execução comercial.

## Mapa
| Caminho | Uso |
| --- | --- |
| [AGENTS.md](AGENTS.md) | Limites, nomes, acesso absoluto seletivo e integração explícita com roles |
| `brains/<slug>/` | Dez brains existentes; oito arquivos por especialista |
| [protocols/council.md](protocols/council.md) | Consultoria, conselho e tribunal |
| [protocols/research.md](protocols/research.md) | Evidências, IDs, fontes e atualidade |
| [protocols/decision-making.md](protocols/decision-making.md) | Recomendação, aprovação e deliberações |
| [protocols/maintenance.md](protocols/maintenance.md) | Revisão, contradições e rastreabilidade |
| [knowledge/references/core.md](knowledge/references/core.md) | Referências comuns e interpretações por especialidade |
| [knowledge/shared/brazil.md](knowledge/shared/brazil.md) | Checklist de aplicação brasileira |
| [projects/registry.md](projects/registry.md) | Índice local de projetos e ideias, com estágio e entrada para retomada |
| [protocols/project-memory.md](protocols/project-memory.md) | Fonte de verdade local, organização, retomada e migração das memórias |
| [memory/profile-igor-rocha.md](memory/profile-igor-rocha.md) | Perfil pessoal transversal, separado das premissas das empresas |
| `projects/<ID>/memory/` | `state.md` canônico, `history.md` cronológico e, conforme necessidade, premissas, decisões, pesquisas, reuniões e ideias |
| `projects/<ID>/` | Documentos e anexos persistentes segregados por projeto |
| `projects/<ID>/memory/decisions/` | Deliberações do projeto; `decisions/` na raiz é legado, não destino de novos registros |

Cada brain contém `_hot.md`, `voice.md`, `principles.md`, `frameworks.md`, `books.md`, `positions.md`, `stories.md` e `sources.md`. Começar por `_hot.md`, ler `voice.md` na primeira atuação e até dois arquivos temáticos relevantes, além das fontes específicas. Não há autoload.

## Origem e operação
Organização inspirada em [Roast Room, de nateherkai](https://github.com/nateherkai/roast-room). Proveniência e componentes consultados estão no documento já existente [projects/QG-BRAINS-01/reference-architecture.md](projects/QG-BRAINS-01/reference-architecture.md), preservado nesta entrega. A referência arquitetural não prova eficácia empresarial; nenhum runtime externo é instalado por estes documentos.

Todas as memórias são mantidas em arquivos locais, não em notas Maestri. Para retomar, ler `projects/registry.md` e `projects/<ID>/memory/state.md`; abrir histórico, decisões, pesquisas, ideias e perfil somente quando pertinentes, conforme o protocolo de memória. As notas antigas são legado migrado: não criar ou atualizar memórias no canvas nem sincronizar duas fontes atuais. Preservar histórico e não excluir notas antigas sem autorização. A integração CLI/role requer instrução explícita de leitura; arquivos não mudam configuração, modelos ou GatewayFy.

O repositório público contém a base reutilizável (`brains/`, `knowledge/`, `protocols/` e instruções). `projects/`, `memory/` e `decisions/` são privados e locais, excluídos integralmente pelo `.gitignore`, incluindo o índice de projetos, documentos, anexos e perfil pessoal. Os caminhos acima que apontam para essas pastas só estarão disponíveis na instalação local; não acompanham um clone público. `.maestri/`, `.maki/`, `.idea/` e padrões comuns de secrets/credenciais também são ignorados.

As exclusões não apagam arquivos locais nem removem arquivos já rastreados ou publicados do histórico. Não usar `git add -f` nesses caminhos. Inspecionar o conteúdo e o diff preparado antes de cada commit/publicação: o `.gitignore` **não garante ausência de segredos ou dados pessoais** nos demais arquivos. A preparação para uso público não autoriza commit, push ou publicação.

## Limites da entrega
Registro histórico da entrega documental anterior (não diagnóstico permanente de disponibilidade): inspeção local da estrutura, fontes dos brains e notas; criação de instruções e protocolos. Fontes externas citadas foram herdadas dos registros locais, não reconsultadas nesta etapa. Nenhum livro integralmente lido ou atualidade jurídica certificada. Backend de agentes indisponível conforme contexto informado; **não há teste live nem parecer independente de agentes nesta entrega**. Revisão documental não equivale a teste de integração.
