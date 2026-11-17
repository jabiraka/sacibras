// O endereço do site no ar, num lugar só: a imagem de compartilhamento (og:image e og:url no
// index.html), o canônico das páginas de pergunta e o sitemap (`paginas.mjs`) pedem o endereço
// completo. Quando o domínio próprio sair (depende do Caio), muda aqui e em `anterior.SITE`, no
// builder. O robots.txt só vale na raiz do domínio: no GitHub Pages (/sacibras/) o Google não
// o lê, e o sitemap se manda à mão no Search Console; com o domínio próprio, passa a valer.
export const ENDERECO = "https://jabiraka.github.io/sacibras/";
