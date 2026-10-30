# Memória local por projeto

Política aprovada pelo usuário em 2026-10-29: todas as memórias de ideias e projetos ficam nos arquivos locais, não em notas do Maestri. Raiz: D:/qg-de-ideias.

## Organização e fonte de verdade

```text
memory/
  profile-igor-rocha.md
projects/
  registry.md
  <ID>/
    memory/
      state.md
      history.md
      assumptions.md
      decisions/
      research/
      meetings/
      ideas/
    [documentos e anexos do projeto]
```

`state.md` e `history.md` são o núcleo mínimo. Os demais arquivos e diretórios só devem ser criados quando houver conteúdo real. Não gerar estruturas vazias por projeto.

- `projects/registry.md`: índice de projetos/ideias, estágio e link de entrada. Não copiar detalhes financeiros ou decisões.
- `memory/state.md`: fonte canônica do estado atual; ID, estágio, objetivo, fatos com fonte/data, hipóteses, decisões confirmadas, propostas, divergências, bloqueios, responsáveis e próximos passos. Curto o suficiente para retomada rápida.
- `memory/history.md`: registros cronológicos de mudanças, sessões e migrações, com origem, data, autor e vínculos. Preservar registros antigos; correções explícitas em vez de reescrita silenciosa. Snapshots migrados são históricos, não outra fonte atual.
- `memory/assumptions.md`: catálogo de premissas quando exceder o resumo; ID, enunciado, evidência, status, responsável, teste e critério de revisão. `state.md` aponta aos IDs.
- `memory/decisions/`: deliberações completas com status recomendação ou aprovado usuário, conforme decision-making.md. `state.md` contém somente resultado atual e link.
- `memory/research/`: pesquisas datadas, fontes, nível consultado, recortes, números com moeda/período/universo e limites; não confundir dado externo com hipótese.
- `memory/meetings/`: sínteses materiais de sessões, análises efetivamente recebidas e revisões, sem transcrever automaticamente conversas inteiras ou segredos.
- `memory/ideas/`: hipóteses e alternativas exploradas/descartadas com justificativa. Ideia independente recebe ID no registry; não vinculá-la arbitrariamente a outra empresa.
- `memory/profile-igor-rocha.md` na raiz: contexto pessoal transversal, não premissas financeiras de empresas. Conhecimento geral continua em brains/ e knowledge/.

A antiga pasta decisions/ da raiz deixa de ser destino de novos registros; não mover registros existentes sem inspeção. Nesta migração nenhum registro de decisão preexistente foi identificado ali.

## Retomada e atualização

1. Maestro executa maestri list para conhecer agentes, não para buscar memória. Lê projects/registry.md e apenas o state.md do projeto identificado; consulta perfil quando relevante.
2. Confirma projeto e estágio. Abre histórico, pesquisas e decisões somente conforme links e necessidade.
3. Delega contexto suficiente e caminhos absolutos aos especialistas; não exige leitura de notas do canvas nem de todos os arquivos.
4. Define um responsável por arquivo. Especialistas retornam análises; Maestro integra estado. Escritas paralelas somente em arquivos disjuntos autorizados.
5. Ao concluir etapa material, registra mudança no histórico e atualiza estado/índice se necessário. Inclui origem, limitações e pendências; não marca como validado o que não foi executado.
6. Não promover automaticamente conversa, hipótese ou experiência local a conhecimento dos cérebros. Não aprovar decisões pelo silêncio.

## Migração das notas

Conteúdos de Registro de Projetos, Projeto DRINKS-ILH-01, Projeto QG-BRAINS-01 e Perfil - Igor Rocha foram preservados em arquivos locais com indicação de origem. As notas antigas recebem somente aviso de migração e caminho canônico; não armazenar novas memórias, não sincronizar duas cópias. Não criar notas novas para estado, missão ou passagem de bastão. Excluir notas antigas exige autorização explícita.

## Versionamento e privacidade

Git local inicializado em 2026-10-29, branch main, a pedido do usuário. Na escolha de destino o usuário optou por somente Git local; sem remoto, commit ou push nesta etapa. .maestri/ e padrões comuns de credenciais são ignorados. Isso não substitui inspeção de segredos e dados pessoais antes de git add/commit/publicação. Por autorização do usuário em 2026-10-29 para preparar o repositório público, `projects/`, `memory/` e `decisions/` são integralmente locais e ignorados pelo Git, incluindo registro, estados, históricos, documentos e perfil pessoal. `.idea/`, `.maki/` e `.maestri/` também ficam fora dos commits. Não usar `git add -f` nesses caminhos. Clones públicos não contêm a memória operacional; sua ausência não autoriza reconstruir dados privados a partir de suposições. As exclusões não removem arquivos já rastreados nem histórico publicado; conferir índice e histórico antes da publicação. Nunca registrar tokens, senhas ou chaves nas memórias.
