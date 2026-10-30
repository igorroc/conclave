# Conclave

Um conselho de agentes para colocar ideias à prova.

Conclave organiza especialistas de IA para explorar propostas, pesquisar oportunidades, confrontar premissas e apoiar decisões. Em vez de buscar concordância automática, reúne perspectivas diferentes e preserva as objeções que realmente importam. A decisão final continua sendo sua.

O foco atual é um conselho empresarial com contexto brasileiro, mas o processo também serve para amadurecer novas iniciativas e projetos. Não é uma equipe de desenvolvimento por padrão.

## O que este repositório contém

Uma base documental em Markdown: instruções, especialidades, referências e protocolos de colaboração. Ela orienta os agentes, mas **não executa agentes sozinha**.

A operação atual usa o Maestri para coordenar os especialistas. Um clone deste repositório não instala o Maestri, não configura modelos, não cria agentes e não estabelece conexões automaticamente. Não há aplicação de fórum, interface web ou runtime de agentes incluído.

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
| Hater | Crítica, premissas frágeis e riscos | [hater](brains/hater/) |
| Xeroque Rolmes | Pesquisa de mercado e evidências | [xeroque-rolmes](brains/xeroque-rolmes/) |
| Tio Patinhas | Finanças e viabilidade | [tio-patinhas](brains/tio-patinhas/) |
| Pablo Marçal | Marketing e posicionamento | [pablo](brains/pablo/) |
| MVPzinho | Validação de hipóteses e MVP | [mvpzinho](brains/mvpzinho/) |
| Doutor B.O. | Análise jurídica e riscos legais | [doutor-bo](brains/doutor-bo/) |
| Seu Zé | Operações e execução autorizada | [seu-ze](brains/seu-ze/) |
| Tubarão | Vendas e negociação | [tubarao](brains/tubarao/) |

Os nomes identificam papéis de trabalho. As bases representam especialidades e referências, não imitação de pessoas públicas, endosso dos autores citados ou parecer profissional habilitado.

## Como começar

### Na instalação atual com Maestri

1. Leia [AGENTS.md](AGENTS.md) para entender limites, responsabilidades e acesso à base.
2. Confirme os agentes conectados com `maestri list`. Os nomes acima descrevem a configuração atual; não são criados pelo repositório.
3. Forneça ao Maestro o projeto, o estágio e a pergunta que precisa resolver. Se houver memória local, retome pelo registro e pelo estado do projeto.
4. Ao delegar, inclua o contexto, o escopo, o critério de aceite e o caminho absoluto do brain. Não pressuponha que arquivos Markdown foram carregados automaticamente.
5. Peça uma síntese com evidências, divergências, limites e próximo passo. Só autorize execução depois de avaliar a recomendação.

Exemplo de pedido:

> Projeto EXEMPLO-01, estágio de exploração. Quero avaliar uma ideia de serviço para pequenos negócios brasileiros. Selecione as perspectivas necessárias, questione as premissas e recomende um teste barato antes de investir. Não execute ações externas.

### Em outra instalação

Use a estrutura como referência, mas configure explicitamente os agentes e sua ferramenta de orquestração. As instruções locais contêm caminhos absolutos da instalação original (`D:/qg-de-ideias/`); adapte-os antes do uso em outra máquina. O nome da pasta e o ID interno `QG-BRAINS-01` foram preservados para manter referências existentes, apesar da identidade pública Conclave.

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

## Limites e estado atual

- A base e os protocolos estão documentados; sua presença não comprova aplicação pelos agentes nem eficácia das recomendações.
- Consultas pontuais a agentes já foram realizadas na instalação local, mas não equivalem à validação completa do fluxo, da integração ou de todas as especialidades.
- Disponibilidade dos agentes e do backend precisa ser verificada em cada tarefa. Falhas não autorizam inventar pareceres ou alterar configurações para contorná-las.
- Referências têm níveis de acesso e datas próprios. Citações e sínteses não significam leitura integral dos livros, fatos atuais confirmados ou aconselhamento profissional.
- Recomendações não autorizam transações, contratos, mudanças de sistemas, commits, pushes, publicações ou implantações. Essas ações exigem aprovação específica.
- A implementação interna de referência usa o ID `QG-BRAINS-01`; ele não identifica um projeto comercial.

## Origem

A organização foi inspirada em [Roast Room, de nateherkai](https://github.com/nateherkai/roast-room), com adaptação para um conselho de especialidades e contexto brasileiro. A inspiração arquitetural não comprova eficácia empresarial e não implica instalação de componentes daquele projeto.

Conclave era anteriormente chamado QG das Ideias. Referências históricas e identificadores antigos são preservados quando necessários à rastreabilidade.
