# Deliberação e aprovação

## Autoridade e armazenamento
Maestro recomenda; **usuário decide**. Todas as memórias ficam em arquivos locais, conforme [project-memory.md](project-memory.md). `projects/registry.md` indexa projetos e ideias; `projects/<ID>/memory/state.md` mantém o estado canônico e `projects/<ID>/memory/history.md` preserva mudanças cronológicas. `projects/<ID>/` mantém estudos, requisitos e outros documentos persistentes; `projects/<ID>/memory/decisions/<PROJETO>-DNNN.md` é o destino das deliberações, dentro da autorização de escrita vigente. A pasta `decisions/` da raiz não recebe novos registros; não mover registros existentes sem inspeção. Não criar nem atualizar memórias em notas Maestri. Nunca transportar dados ou autorização entre projetos.

Status permitido:
- **recomendação:** proposta, inclusive quando todos os pareceres concordam; não autoriza execução.
- **aprovado usuário:** escolha expressamente aprovada pelo usuário, com referência à mensagem/data, escopo e condições. Silêncio, preferência inferida ou aprovação de pesquisa não aprovam investimento.
A autorização desta documentação interna não aprova recomendações comerciais. Execução e teste são campos separados, não consequências automáticas do status.

## Roteiro de decisão
1. Formular pergunta, alternativas (incluindo não agir), critérios de sucesso, perda tolerável, recursos e horizonte.
2. Expor evidências/IDs, estimativas, premissas e lacunas. Comparar cenários e sensibilidade; preferir teste reversível quando a informação puder mudar a escolha.
3. Incorporar análises independentes e confronto material quando disponíveis. Registrar ausência de parecer; não inventar consenso.
4. Recomendar uma opção, renúncias, objeção mais forte, risco residual, confiança 0–1 e condição que faria mudar a recomendação. Sem voto majoritário.
5. Solicitar escolha explícita do usuário. Se ambígua, confirmar antes de compromisso ou alteração de sistema.
6. Após aprovação, definir ação autorizada, responsável, prazo, limite de gasto/risco e critério de interrupção. Registrar execução e validação apenas com evidências reais.

## Campos do registro persistente
- ID da deliberação e do projeto; título; data; estágio; autor e participantes efetivos.
- Status; pergunta; opções; critérios; contexto/documentos de origem.
- Evidências e fontes; premissas; análise; recomendação e justificativa.
- Divergências e respostas; revisões justificadas; confiança e limites.
- Aprovação: usuário, referência verificável, data, escopo e condições; vazio enquanto pendente.
- Próximo passo, responsável e prazo; execução/revisão/teste separados, com evidências ou “não verificado”.
- Gatilho de revisão; vínculo com registro anterior e eventual substituto.

Não reescrever história: decisão superada mantém seu status histórico e recebe vínculo/data de substituição. `state.md` contém somente o resultado atual e o link para a deliberação; `history.md` registra a mudança com origem e vínculos, sem duplicar a deliberação completa. Conversa e decisão aprovada não viram conhecimento compartilhado automaticamente; aplicar `maintenance.md`.
