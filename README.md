# RC Apps – Website Institucional

Site estático da **RC Apps**, gerado com HTML5 semântico, Tailwind CSS (CDN) e JavaScript puro.

---

## Estrutura de arquivos

```
website/
├── index.html          → Home (hero, módulos, CTA)
├── sobre.html          → Sobre a RC Apps (missão, história, público)
├── servicos.html       → Funcionalidades (6 cards detalhados)
├── contato.html        → Formulário de contato (Formspree + fallback mailto)
├── assets/
│   ├── css/
│   │   └── custom.css  → Variáveis de cor e overrides
│   ├── js/
│   │   └── main.js     → Navbar scroll, menu mobile, link ativo
│   └── img/
│       └── logo-placeholder.svg  → Logo SVG (substitua pelo logo real)
└── README.md           → Este arquivo
```

---

## 1. Testar localmente com Live Server (VS Code)

### 1.1 Instalar a extensão Live Server

1. Abra o **VS Code**.
2. Clique no ícone de **Extensões** na barra lateral (ou `Ctrl+Shift+X`).
3. Pesquise: `Live Server`
4. Instale a extensão de **Ritwick Dey** (a mais popular, com mais de 50 milhões de downloads).
5. Após instalar, um botão **"Go Live"** aparecerá na barra de status (rodapé do VS Code).

### 1.2 Abrir o site com Live Server

**Opção A – pelo Explorador de Arquivos:**
1. No painel lateral do VS Code, expanda a pasta `website/`.
2. Clique com o botão direito em `index.html`.
3. Selecione **"Open with Live Server"**.
4. O navegador abrirá automaticamente em `http://127.0.0.1:5500/website/index.html`.

**Opção B – pelo botão na barra de status:**
1. Abra o arquivo `index.html` no editor.
2. Clique em **"Go Live"** no rodapé do VS Code.

**Dicas:**
- O Live Server recarrega o navegador automaticamente ao salvar qualquer arquivo.
- Para navegar entre as páginas do site, use os links do menu — eles funcionam normalmente via Live Server.
- Para parar o servidor, clique em **"Port: 5500"** na barra de status ou feche o VS Code.

---

## 1.B Testar sem extensão — Python (mais simples)

Se você tem Python instalado (qualquer versão 3.x), não precisa de nenhuma extensão:

1. Abra o terminal (**PowerShell** ou **cmd**)
2. Entre na pasta `website/`:
   ```powershell
   cd "caminho\para\v1.6.22 (OK)\website"
   ```
3. Execute o servidor embutido:
   ```powershell
   python -m http.server 8000
   ```
4. Abra no navegador: **http://127.0.0.1:8000**

Para encerrar: pressione `Ctrl+C` no terminal.

---

## 2. Deploy gratuito no GitHub Pages

### Pré-requisitos
- Conta no [GitHub](https://github.com)
- Git instalado na máquina (`git --version` para verificar)
- Repositório criado no GitHub para este projeto

---

### Opção A — GitHub Actions (recomendada)

Esta opção publica **apenas a pasta `/website`** no GitHub Pages de forma automática a cada push na branch `main`.

#### Passo a passo:

1. **Crie o arquivo de workflow** na raiz do repositório (fora da pasta `website/`):

   ```
   .github/
   └── workflows/
       └── deploy-website.yml
   ```

2. **Conteúdo do arquivo `deploy-website.yml`:**

   ```yaml
   name: Deploy Website para GitHub Pages

   on:
     push:
       branches:
         - main          # Dispara no push para a branch main
       paths:
         - 'website/**'  # Somente quando arquivos em /website mudarem

   permissions:
     contents: read
     pages: write
     id-token: write

   concurrency:
     group: "pages"
     cancel-in-progress: false

   jobs:
     deploy:
       runs-on: ubuntu-latest
       environment:
         name: github-pages
         url: ${{ steps.deployment.outputs.page_url }}
       steps:
         - name: Checkout do repositório
           uses: actions/checkout@v4

         - name: Configurar GitHub Pages
           uses: actions/configure-pages@v4

         - name: Fazer upload da pasta /website
           uses: actions/upload-pages-artifact@v3
           with:
             path: './website'   # ← publica apenas esta pasta

         - name: Deploy para GitHub Pages
           id: deployment
           uses: actions/deploy-pages@v4
   ```

3. **Ativar o GitHub Pages no repositório:**
   - Acesse o repositório no GitHub → **Settings** → **Pages**.
   - Em **Source**, selecione: **GitHub Actions**.
   - Salve.

4. **Faça um push** para a branch `main`. O workflow será executado automaticamente.

5. Após o deploy (1–2 minutos), o site estará disponível em:
   ```
   https://SEU_USUARIO.github.io/SEU_REPOSITORIO/
   ```

---

### Opção B — Subtree push para branch `gh-pages`

Use esta opção se preferir não usar GitHub Actions.

#### Passo a passo:

```bash
# 1. Na raiz do repositório, publique apenas a pasta /website
#    na branch gh-pages (cria a branch se não existir)
git subtree push --prefix website origin gh-pages
```

Depois:
1. Acesse **Settings** → **Pages** no GitHub.
2. Em **Source**, selecione: Branch `gh-pages`, pasta `/ (root)`.
3. Salve. O site ficará disponível em `https://SEU_USUARIO.github.io/SEU_REPOSITORIO/`.

> **Para atualizar o site depois:**
> Faça suas alterações nos arquivos em `website/`, commit normalmente na `main`,
> depois execute novamente o comando `git subtree push`.

---

## 3. Domínio personalizado no GitHub Pages

### 3.1 Comprar um domínio

Opções recomendadas (registro nacional e internacional):

| Registradora | URL | Para domínios |
|---|---|---|
| **Registro.br** | https://registro.br | `.com.br`, `.net.br`, `.org.br` |
| **Hostinger** | https://hostinger.com.br | `.com`, `.com.br`, `.net`, etc. |
| **GoDaddy** | https://godaddy.com | `.com`, `.net`, `.io`, etc. |

**Custo médio:** R$ 40–80/ano para `.com.br` | R$ 60–120/ano para `.com`

---

### 3.2 Apontar o domínio para o GitHub Pages

#### Se você tem um domínio apex (ex: `rcapps.com.br`):

1. No painel DNS da registradora, crie 4 registros **A** apontando para os IPs do GitHub:
   ```
   185.199.108.153
   185.199.109.153
   185.199.110.153
   185.199.111.153
   ```
   - Tipo: `A`
   - Host: `@` (representa o domínio raiz)
   - TTL: Automático ou 3600

2. Crie também um registro **CNAME** para `www`:
   ```
   Tipo:  CNAME
   Host:  www
   Valor: SEU_USUARIO.github.io
   TTL:   Automático
   ```

#### Se você tem um subdomínio (ex: `site.rcapps.com.br`):

1. Crie apenas um registro **CNAME**:
   ```
   Tipo:  CNAME
   Host:  site
   Valor: SEU_USUARIO.github.io
   TTL:   Automático
   ```

---

### 3.3 Configurar o domínio no GitHub

1. Crie um arquivo chamado **`CNAME`** dentro da pasta `website/` com o seu domínio:
   ```
   rcapps.com.br
   ```
   (sem `https://`, apenas o domínio)

2. No GitHub: **Settings** → **Pages** → **Custom domain** → insira o domínio → clique **Save**.

3. Marque a opção **"Enforce HTTPS"** (disponível após a propagação do DNS, que pode levar até 24h).

4. Aguarde a propagação DNS (geralmente 30 min a 2 horas, máximo 48h).

---

## 4. Personalização rápida

### Trocar as cores do site inteiro
Edite apenas o bloco `:root {}` em [assets/css/custom.css](assets/css/custom.css):
```css
:root {
  --color-brand-dark:  #1a3a5c;  /* azul escuro principal */
  --color-brand:       #2563eb;  /* azul médio – botões e links */
  --color-brand-light: #38bdf8;  /* azul claro – ícones e destaques */
}
```

### Substituir o logo
Substitua o arquivo [assets/img/logo-placeholder.svg](assets/img/logo-placeholder.svg)
pelo logo real da empresa (PNG, SVG ou outro formato).
Atualize o atributo `src` das tags `<img>` do logo em cada página HTML.

### Atualizar o e-mail de contato
Pesquise `contato@rcapps.com.br` nos arquivos HTML e substitua pelo e-mail real.

### Configurar o formulário de contato (Formspree)
1. Crie conta em https://formspree.io (plano gratuito: até 50 envios/mês)
2. Crie um novo formulário e copie o ID
3. Em [contato.html](contato.html), substitua `SEU_ID_AQUI` pelo ID gerado:
   ```html
   action="https://formspree.io/f/xpzbkqer"
   ```

---

## 5. Tecnologias utilizadas

| Tecnologia | Versão | Finalidade |
|---|---|---|
| HTML5 | — | Estrutura semântica |
| Tailwind CSS | v3 (CDN) | Estilização responsiva |
| Google Fonts (Inter) | — | Tipografia |
| JavaScript (ES5) | — | Interatividade mínima |
| Heroicons | Inline SVG | Ícones |

---

© 2025 RC Apps. Todos os direitos reservados.
