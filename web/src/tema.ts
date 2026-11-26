// O tema claro ou escuro (Caio, 26/11/2026: "Adicione a opção de tema escuro").
//
// Sem escolha, segue o sistema (`prefers-color-scheme`); com escolha, vale a guardada no
// navegador (`sacibras-tema`: "claro" ou "escuro"). O `data-tema` do <html> é posto por um
// script no <head> do index.html, antes da primeira pintura (sem lampejo claro). Os gráficos
// leem as cores do CSS na hora de desenhar, então trocar de tema recarrega a página (como o
// idioma); o endereço (#...) fica e a pessoa volta ao mesmo lugar.

const GUARDADO = "sacibras-tema";
const OPCOES = [
  ["auto", "Automático"],
  ["claro", "Claro"],
  ["escuro", "Escuro"],
] as const;

function lerEscolha(): string {
  try {
    const v = localStorage.getItem(GUARDADO);
    return v === "claro" || v === "escuro" ? v : "auto";
  } catch {
    return "auto";
  }
}

function guardar(escolha: string): void {
  try {
    if (escolha === "auto") localStorage.removeItem(GUARDADO);
    else localStorage.setItem(GUARDADO, escolha);
  } catch {
    // Sem armazenamento (janela privada): a escolha vale só até recarregar.
  }
}

/** A lista "Tema" no menu, acima do "Idioma". */
export function ligarTema(): void {
  const caixa = document.getElementById("idioma");
  if (!caixa) return;
  const rotulo = document.createElement("label");
  rotulo.className = "idioma-rotulo";
  rotulo.htmlFor = "tema-lista";
  rotulo.textContent = "Tema";
  const lista = document.createElement("select");
  lista.className = "escolha tema-lista";
  lista.id = "tema-lista";
  for (const [valor, nome] of OPCOES) {
    const opcao = document.createElement("option");
    opcao.value = valor;
    opcao.textContent = nome;
    lista.append(opcao);
  }
  lista.value = lerEscolha();
  lista.addEventListener("change", () => {
    guardar(lista.value);
    location.reload();
  });
  caixa.prepend(rotulo, lista);
}
