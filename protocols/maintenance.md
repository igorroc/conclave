# Manutenção e rastreabilidade

## Gatilhos
Revisar quando houver fonte nova, contradição material, mudança normativa, dado vencido para a decisão, falha observada ou solicitação do usuário. Priorizar risco e volatilidade; não inventar periodicidade como garantia de atualidade. Maestro coordena; especialista pertinente revisa conteúdo, quando disponível; usuário aprova alteração de escopo ou promoção a conhecimento.

## Procedimento de mudança
1. Abrir proposta identificada com projeto, arquivo/seção, problema, impacto, responsável e fonte. Inspecionar conteúdo e limites de escrita antes de editar.
2. Reler fontes específicas; registrar consulta real, data, nível de acesso, edição, independência e pertinência. Não atualizar data externa só por reler registro local.
3. Tratar contradição: explicitar proposições incompatíveis e verificar período, universo, jurisdição, definição e método. Se persistir, conservar ambas com ressalva, reduzir confiança e definir verificação; não apagar evidência inconveniente.
4. Propor correção mínima e justificativa. Revisão de especialista não equivale à aprovação do usuário. Se backend indisponível, declarar revisão independente ausente; não simulá-la.
5. Obter aprovação explícita para promoção de aprendizado e mudanças fora da autorização vigente. Depois editar somente arquivos permitidos, preservando IDs e referências anteriores.
6. Validar links locais, IDs, coerência, contagem/estrutura quando aplicável e escopo do diff. Teste live só se realmente executado; documentar comando, resultado e limite.
7. Registrar no documento afetado ou, para memória de projeto, em `projects/<ID>/memory/history.md`, conforme [project-memory.md](project-memory.md), dentro do escopo autorizado: ID, data, autor, revisor efetivo, aprovação/referência, antes/depois resumido, fontes, motivo, validação, contradições e vínculos às deliberações. Atualizar `projects/<ID>/memory/state.md` e `projects/registry.md` quando necessário; não criar estruturas vazias nem arquivos fora da autorização vigente.

## Promoção a conhecimento
Conversa e parecer são insumos, não fatos. Para promover: formular lição e limites de validade; identificar evidência e contraprova; separar interpretação de fonte; avaliar transferibilidade para outras especialidades/regiões; remover dados privados desnecessários; obter aprovação específica. Um resultado local isolado continua sendo caso, não regra universal. Decisão aprovada pode estar errada e não prova causalidade.

## Preservação e segurança
Todas as memórias ficam em arquivos locais, conforme `project-memory.md`: índice em `projects/registry.md`, estado canônico em `projects/<ID>/memory/state.md` e histórico em `projects/<ID>/memory/history.md`. Decisões, pesquisas, reuniões, ideias e premissas ficam na memória do respectivo projeto, conforme conteúdo real. O perfil transversal fica em `memory/profile-igor-rocha.md`, separado das premissas empresariais. Não criar nem atualizar memórias no canvas, nem sincronizar notas antigas com a fonte local. Preservar o legado migrado e seus vínculos; excluir notas antigas exige autorização explícita. Documentos persistentes ficam segregados por ID. Preservar histórico e indicar substituições, não promover recomendação a aprovado sem usuário.

Nunca alterar GatewayFy, configuração global ou modelos. Não executar transações, assinar, fazer commits, pushes, publicação ou implantação sem autorização específica. Cada demanda define seus arquivos e ações permitidos; este protocolo não amplia a autorização de escrita. Git local e padrões de ignore, inclusive para `.maestri/` e credenciais, não garantem segurança: inspecionar segredos e dados pessoais antes de versionar ou publicar, confirmar destino e visibilidade e nunca registrar tokens, senhas ou chaves nas memórias.
