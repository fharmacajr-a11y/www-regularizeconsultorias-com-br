# Regularize Consultoria – Site Institucional

Site estático da **Regularize Consultoria**, construído com HTML5 semântico, Tailwind CSS (CDN) e JavaScript puro.

---

## Estrutura de arquivos

```
regularize-consultoria-site/
├── index.html          → Home (hero, diferenciais, serviços em destaque, CTA)
├── sobre.html          → Sobre a empresa (missão, história, público-alvo)
├── servicos.html       → Serviços (6 cards detalhados)
├── contato.html        → Formulário de contato (Formspree + fallback mailto)
├── assets/
│   ├── css/
│   │   └── custom.css  → Variáveis de cor e overrides
│   ├── js/
│   │   └── main.js     → Navbar scroll, menu mobile, link ativo
│   └── img/
│       └── logorc2.png           → Logo oficial aplicada em header e footer
└── README.md           → Este arquivo
```

---

## 1. Testar localmente com Live Server (VS Code)

### 1.1 Instalar a extensão Live Server

1. Abra o **VS Code**.
2. Clique no ícone de **Extensões** na barra lateral (ou `Ctrl+Shift+X`).
3. Pesquise por `Live Server`.
4. Instale a extensão de **Ritwick Dey**.
5. Após instalar, um botão **"Go Live"** aparecerá na barra de status inferior do VS Code.

### 1.2 Abrir o site com Live Server

**Opção A – pelo Explorador de Arquivos:**
1. No painel lateral do VS Code, clique com o botão direito em `index.html`.
2. Selecione **"Open with Live Server"**.
3. O navegador abrirá em `http://127.0.0.1:5500/index.html`.

**Opção B – pelo botão na barra de status:**
1. Abra o arquivo `index.html` no editor.
2. Clique em **"Go Live"** no rodapé do VS Code.

**Dica:** o Live Server recarrega o navegador automaticamente ao salvar qualquer arquivo.

---

## 1.B Testar sem extensão — Python

Se você tem Python 3 instalado:

```powershell
# Na pasta raiz do projeto:
python -m http.server 8000
```

Abra no navegador: **http://127.0.0.1:8000**. Pressione `Ctrl+C` para encerrar.

---

## 2. Deploy no GitHub Pages

### Opção A — Diretamente da branch `main` (mais simples para este projeto)

Como os arquivos estão na raiz do repositório, basta ativar o GitHub Pages:

1. Acesse o repositório no GitHub → **Settings** → **Pages**.
2. Em **Source**, selecione: branch `main`, pasta `/ (root)`.
3. Salve. O site ficará disponível em `https://SEU_USUARIO.github.io/SEU_REPOSITORIO/`.

### Opção B — GitHub Actions

Se quiser publicar automaticamente a cada push na branch `main`, crie o arquivo `.github/workflows/deploy.yml`:

```yaml
name: Deploy para GitHub Pages

on:
  push:
    branches: [main]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/configure-pages@v4
      - uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
      - id: deployment
        uses: actions/deploy-pages@v4
```

---

## 3. Domínio personalizado

1. No painel DNS da registradora, crie os registros A apontando para os IPs do GitHub Pages:
   ```
   185.199.108.153
   185.199.109.153
   185.199.110.153
   185.199.111.153
   ```
2. Crie um registro CNAME para `www` apontando para `SEU_USUARIO.github.io`.
3. Crie um arquivo `CNAME` na raiz do projeto com o seu domínio (ex: `regularizeconsultoria.com.br`).
4. No GitHub: **Settings** → **Pages** → **Custom domain** → insira o domínio → **Save**.
5. Marque **"Enforce HTTPS"** após a propagação do DNS (pode levar até 24h).

---

## 4. Personalização rápida

### Trocar as cores do site
Edite o bloco `:root {}` em [assets/css/custom.css](assets/css/custom.css):
```css
:root {
  --color-brand-dark:  #1a3a5c;
  --color-brand:       #2563eb;
  --color-brand-light: #38bdf8;
}
```

### Configurar o formulário de contato (Formspree)
1. Crie conta em https://formspree.io (plano gratuito: até 50 envios/mês).
2. Crie um novo formulário e copie o ID gerado.
3. Em [contato.html](contato.html), substitua `SEU_ID_AQUI` pelo ID real:
   ```html
   action="https://formspree.io/f/xxxxxxxX"
   ```

---

## 5. Pendências para a próxima fase

- [x] **Logo real** — `assets/img/logorc2.png` aplicada em header e footer de todas as páginas.
- [ ] **Formspree ID** — configurar o endpoint real do formulário de contato em `contato.html`.
- [ ] **Domínio** — definir e apontar o domínio final do site.
- [ ] **Página de obrigado** — criar `obrigado.html` para redirecionamento pós-envio do formulário (opcional).

---

## 6. Tecnologias utilizadas

| Tecnologia | Finalidade |
|---|---|
| HTML5 | Estrutura semântica |
| Tailwind CSS v3 (CDN) | Estilização responsiva |
| Google Fonts (Inter) | Tipografia |
| JavaScript (ES5) puro | Navbar scroll, menu mobile, link ativo |
| Heroicons (inline SVG) | Ícones |

---

© 2026 Regularize Consultoria. Todos os direitos reservados.
