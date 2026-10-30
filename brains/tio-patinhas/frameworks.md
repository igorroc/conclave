# Frameworks operacionais

Exemplos exclusivamente hipotéticos, em BRL quando indicado; nenhuma cotação ou recomendação de investimento.

## F01 — Caixa de 13 semanas
- **Origem:** Síntese própria de orçamento e liquidez; BCB fornece base de orçamento pessoal, não autoria deste horizonte.
- **Objetivo:** Antecipar falta de liquidez.
- **Quando usar:** Operação com recebimentos e pagamentos identificáveis; atualizar semanalmente.
- **Passos:** 1. Conciliar saldo disponível sem crédito não contratado. 2. Listar entradas por probabilidade e vencimento. 3. Listar folha, tributos, fornecedores, dívida e investimento. 4. Projetar saldo por semana em base e estresse. 5. Definir ação, responsável e data antes do primeiro saldo negativo.
- **Dados e saída:** Extratos, títulos, contratos, folha, impostos, atrasos históricos. Saída: menor saldo, semana crítica e plano de cobertura.
- **Exemplo hipotético:** Em R$ hipotéticos: saldo 20 mil, entradas 8 mil e saídas 12 mil na primeira semana geram 16 mil; repetir o cálculo, sem tratar vendas futuras como dinheiro garantido.
- **Limites:** Treze semanas é convenção desta rotina; volatilidade pode exigir visão diária e horizonte maior.
- **Referências:** P-BCB; P-CVM; P-INT em [sources.md](sources.md).

## F02 — Contribuição e equilíbrio
- **Origem:** Síntese de contabilidade gerencial, relacionada à disciplina de valor de Damodaran; não fórmula atribuída exclusivamente ao autor.
- **Objetivo:** Identificar volume e mix economicamente sustentáveis.
- **Quando usar:** Precificação, canal, promoção ou expansão de capacidade.
- **Passos:** 1. Obter preço líquido de descontos e tributos. 2. Subtrair custos variáveis sem duplicar impostos. 3. Calcular MC unitária e percentual. 4. Dividir fixos pela MC unitária para equilíbrio em produto único. 5. Testar capacidade, mix, perdas e sensibilidade.
- **Dados e saída:** Preço, taxas, frete, insumos, perdas, fixos e capacidade; saída: MC e equilíbrio operacional, separado do equilíbrio de caixa.
- **Exemplo hipotético:** Preço líquido R$20, custo variável R$12: MC=R$8. Fixos de R$4.000 exigem 500 unidades/mês; se capacidade é 400, alterar estrutura, preço ou mix.
- **Limites:** Mix muda o denominador; capital de giro, amortização de dívida e investimento não estão todos no ponto de equilíbrio operacional.
- **Referências:** P-DAM; P-INT em [sources.md](sources.md).

## F03 — Valuation por cenários
- **Origem:** Adaptação operacional de fluxo de caixa descontado de Damodaran e margem de segurança de Graham.
- **Objetivo:** Traduzir narrativa em faixa de valor e preço máximo condicionado.
- **Quando usar:** Aquisição, entrada de sócio ou investimento com dados minimamente defensáveis.
- **Passos:** 1. Definir moeda e data-base. 2. Projetar receita, margem, tributos e reinvestimento. 3. Estimar fluxo livre e taxa coerente com risco/moeda. 4. Descontar cenários, explicitando valor terminal. 5. Fazer ponte de valor da firma para patrimônio e negociar com folga para erro.
- **Dados e saída:** Histórico, capital de giro, capex, dívida líquida, custo de capital; saída: faixa e premissas que a invalidam.
- **Exemplo hipotético:** Perpetuidade meramente hipotética em R$: fluxo anual 100 mil, g=0 e taxa de 20% dão valor da firma de 500 mil; dívida líquida de 80 mil leva a patrimônio de 420 mil antes de outros ajustes.
- **Limites:** Perpetuidade e taxa são hipóteses ilustrativas, não parâmetros de mercado; receita inicial não garante fluxo estabilizado.
- **Referências:** P-DAM; P-GRA em [sources.md](sources.md).

## F04 — Reserva e teste de ruptura
- **Origem:** Síntese própria a partir de educação financeira e falha de liquidez do LTCM.
- **Objetivo:** Definir perda suportável e gatilhos antes de assumir obrigações.
- **Quando usar:** Antes de dívida, contrato longo, contratação ou expansão.
- **Passos:** 1. Fixar caixa mínimo operacional. 2. Modelar choque conjunto em demanda, prazo e custo. 3. Estimar duração e déficit máximo. 4. Verificar covenants, garantias e acesso realmente contratado. 5. Reduzir exposição ou financiar reserva antes de aprovar.
- **Dados e saída:** Cronograma de dívida, garantias, custos incompressíveis e dependências; saída: cenário de quebra e limite aprovado pelo decisor.
- **Exemplo hipotético:** Se o estresse hipotético consome R$15 mil/mês por quatro meses, são R$60 mil de déficit além do piso operacional; limite de crédito revogável não é reserva certa.
- **Limites:** Choques correlacionados e bloqueios podem superar simulação; reserva deve ser revisada, não automatizada.
- **Referências:** P-BCB; P-LTCM em [sources.md](sources.md).

## F05 — Portão de reinvestimento ou distribuição
- **Origem:** Síntese comparando Bazin, Buffett e Damodaran; não método original conjunto desses autores.
- **Objetivo:** Alocar caixa entre manutenção, dívida, crescimento e sócios.
- **Quando usar:** Fechamento trimestral ou decisão de distribuição extraordinária.
- **Passos:** 1. Reconciliar geração operacional recorrente. 2. Reservar tributos, manutenção e capital de giro. 3. Cumprir dívida e piso de segurança. 4. Comparar projetos marginais ao custo de capital e alternativas. 5. Propor distribuição apenas do excedente permitido e registrar critério de revisão.
- **Dados e saída:** Fluxo reconciliado, contratos, restrições legais e retorno esperado; saída: proposta com faixa de distribuição.
- **Exemplo hipotético:** R$100 mil hipotéticos livres antes de manutenção; reservar 20 mil para manutenção, 30 mil para giro e 10 mil para dívida deixa 40 mil a avaliar, não dividendo automaticamente autorizado.
- **Limites:** Resultado contábil distribuível e caixa disponível diferem; validação contábil/jurídica continua necessária.
- **Referências:** P-BAZ; P-BUF; P-DAM em [sources.md](sources.md).
