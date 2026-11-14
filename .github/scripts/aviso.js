// Uma issue por assunto de aviso, achada pelo rótulo: abre quando há o que avisar, atualiza
// quando o conteúdo muda (com um comentário, para notificar) e fecha quando tudo volta ao
// normal. Usado por build-deploy.yml (fonte fora do ar) e prazos.yml (releitura vencida).
// Chamado de actions/github-script: require('./.github/scripts/aviso.js')({github, context}, {...}).

const RODAPE = "<!-- rodapé do aviso -->";

module.exports = async ({ github, context }, { rotulo, cor, titulo, corpo, explicacao }) => {
  const { owner, repo } = context.repo;
  const execucao = `${context.serverUrl}/${owner}/${repo}/actions/runs/${context.runId}`;

  try {
    await github.rest.issues.getLabel({ owner, repo, name: rotulo });
  } catch (erro) {
    if (erro.status !== 404) throw erro;
    await github.rest.issues.createLabel({ owner, repo, name: rotulo, color: cor });
  }

  const abertas = await github.paginate(github.rest.issues.listForRepo, {
    owner,
    repo,
    state: "open",
    labels: rotulo,
    per_page: 100,
  });

  if (!corpo.trim()) {
    for (const issue of abertas) {
      await github.rest.issues.createComment({
        owner,
        repo,
        issue_number: issue.number,
        body: `Resolvido: nada a avisar na execução ${execucao}.`,
      });
      await github.rest.issues.update({
        owner,
        repo,
        issue_number: issue.number,
        state: "closed",
        state_reason: "completed",
      });
    }
    return;
  }

  const texto = `${explicacao}\n\n${corpo.trim()}`;
  const completo = `${texto}\n\n${RODAPE}\nÚltima execução que conferiu: ${execucao}`;
  const [atual, ...sobras] = abertas;

  if (!atual) {
    await github.rest.issues.create({ owner, repo, title: titulo, body: completo, labels: [rotulo] });
    return;
  }
  for (const velha of sobras) {
    await github.rest.issues.update({
      owner,
      repo,
      issue_number: velha.number,
      state: "closed",
      state_reason: "not_planned",
    });
  }
  const antes = (atual.body || "").split(RODAPE)[0].trim();
  await github.rest.issues.update({ owner, repo, issue_number: atual.number, title: titulo, body: completo });
  if (antes !== texto.trim()) {
    await github.rest.issues.createComment({
      owner,
      repo,
      issue_number: atual.number,
      body: `Mudou na execução ${execucao}:\n\n${corpo.trim()}`,
    });
  }
};
