# Frameworks operacionais

Todos os exemplos são hipotéticos, não dados de projetos nem reprodução de experimentos reais.

## F01 — Premortem com responsáveis
- **Origem:** Gary Klein, Performing a Project Premortem (2007); operacionalização adaptada, não autoria de Kahneman.
- **Objetivo:** Descobrir falhas plausíveis antes de comprometer recursos.
- **Quando usar:** Projeto com plano preliminar e pessoas que conheçam a execução.
- **Passos:** 1. Fixar objetivo e horizonte. 2. Supor que fracassou. 3. Cada participante escreve causas independentemente. 4. Agrupar sem eliminar dissenso; priorizar por impacto, plausibilidade e detectabilidade. 5. Atribuir prevenção, sinal de alerta, responsável e prazo. 6. Reavaliar risco residual e decidir.
- **Dados e saída:** Plano, dependências, orçamento e incidentes anteriores; saída: lista de riscos com mitigação e dono.
- **Exemplo hipotético:** Piloto hipotético falhou em 60 dias por atraso de licença; exigir verificação documental antes de contratar local, com responsável e data definidos.
- **Limites:** Imaginação não estima frequência; não somar medos como se fossem probabilidades. Roteiro é adaptação de resumo acessível, não transcrição do artigo integral.
- **Referências:** H-KLEIN; H-INT em [sources.md](sources.md).

## F02 — Registro e calibração de previsões
- **Origem:** Adaptação dos temas de Tetlock e Gardner; cálculo Brier como ferramenta estatística, não invenção desses autores.
- **Objetivo:** Tornar confiança auditável e melhorar atualização.
- **Quando usar:** Eventos binários repetidos com data e resultado verificável.
- **Passos:** 1. Formular evento e critério de resolução. 2. Buscar classe-base. 3. Registrar p entre 0 e 1 e razões contrárias. 4. Atualizar com data sem apagar previsão anterior. 5. Resolver y=0 ou 1. 6. Calcular média de (p−y)² e examinar calibração por faixas.
- **Dados e saída:** Histórico datado, fontes de resolução e resultados; saída: diário e escore da série, com política fixa para previsões canceladas.
- **Exemplo hipotético:** Previsão hipotética de p=0,70 para dez contratos até 30/11; resultado não atingido, y=0: escore 0,49. Uma observação não demonstra descalibração.
- **Limites:** Brier depende da dificuldade e taxa-base; comparar com benchmark equivalente. Confiança de recomendação não é automaticamente previsão binária.
- **Referências:** H-TET; H-IBGE; H-INT em [sources.md](sources.md).

## F03 — Visão externa com ajuste explícito
- **Origem:** Síntese de taxa-base e classe de referência associadas a Kahneman; IBGE como fonte de população brasileira.
- **Objetivo:** Evitar previsão construída só de detalhes favoráveis.
- **Quando usar:** Estimativa de sobrevivência, prazo ou custo com comparáveis.
- **Passos:** 1. Definir evento e unidade. 2. Escolher classe antes de olhar desfechos convenientes. 3. Extrair frequência e incerteza. 4. Verificar população, coorte e mudanças de método. 5. Ajustar somente por evidência documentada. 6. Mostrar base, ajuste e intervalo separadamente.
- **Dados e saída:** Metadados, denominadores, período e diferenças do projeto; saída: estimativa-base e cenários de ajuste.
- **Exemplo hipotético:** Em amostra hipotética de 100 projetos comparáveis, 40 atrasam; ponto inicial 40%, não estatística IBGE. Evidência de fornecedor contratado pode mudar avaliação, sem redução arbitrária automática.
- **Limites:** Classe mal escolhida gera precisão falsa; amostras pequenas e exclusão de fracassos distorcem. Nenhuma taxa real foi extraída aqui.
- **Referências:** H-KAH; H-IBGE em [sources.md](sources.md).

## F04 — Portão causal para experimentos
- **Origem:** Síntese própria apoiada na introdução metodológica de Flavio Carneiro/Ipea.
- **Objetivo:** Distinguir efeito do teste de sazonalidade e seleção.
- **Quando usar:** Preço, canal ou processo em que seja possível comparar intervenção e alternativa.
- **Passos:** 1. Definir tratamento, população, métrica e hipótese causal. 2. Desenhar contrafactual e, se possível, randomizar. 3. Fixar duração, tamanho e regra de análise antes de coletar. 4. Auditar atrito, contaminação e adesão. 5. Estimar diferença com incerteza e custos. 6. Reportar validade externa e decidir.
- **Dados e saída:** Logs, atribuição dos grupos, linha de base e eventos externos; saída: efeito estimado ou associação explicitamente rotulada.
- **Exemplo hipotético:** Dois grupos aleatórios hipotéticos de 200 visitantes convertem 20 e 30 pedidos: 10% e 15%, diferença de 5 pontos percentuais; sem intervalo e análise de desenho não declarar vencedor causal definitivo.
- **Limites:** Randomização não resolve interferência ou baixa potência; não usar significância como substituto de importância econômica ou ética.
- **Referências:** H-IPEA; H-INT em [sources.md](sources.md).

## F05 — Red team com portão de decisão
- **Origem:** Síntese própria: crítica independente, incentivos de Franco, escolhas temporais de Giannetti e perdas assimétricas de Taleb.
- **Objetivo:** Escolher agir, testar, adiar ou abandonar com critérios proporcionais.
- **Quando usar:** Decisão importante com proposta já formulada, sem provocar oposição por teatro.
- **Passos:** 1. Registrar melhor argumento a favor. 2. Produzir crítica independente sobre três premissas decisivas. 3. Distinguir dano intolerável de incerteza testável. 4. Comparar quatro alternativas e custo de esperar. 5. Fixar perda máxima e condições de aprovação. 6. Decisor registra escolha e gatilho de revisão.
- **Dados e saída:** Objetivo, restrições, incentivos, alternativas e evidência pró/contra; saída: recomendação com confiança, divergências e próximo passo.
- **Exemplo hipotético:** Para contrato hipotético anual de R$120 mil versus piloto de R$8 mil, propor piloto se resolve a incerteza principal sem assumir obrigação anual; não afirmar que piloto sempre é melhor.
- **Limites:** Revisão pode atrasar oportunidade; timebox e responsável evitam paralisia. Sem fatos novos, discordância não vale mais que concordância.
- **Referências:** H-FRA; H-GIA; H-TAL; H-INT em [sources.md](sources.md).
