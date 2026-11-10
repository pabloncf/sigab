# Frontend React do SIGAB

SPA operacional em React + TypeScript. Regras de domínio, autorização, tenant, sessão, CSRF e idempotência permanecem no backend Django.

## Desenvolvimento

Em um terminal, inicie o backend em seu diretório próprio:

```bash
cd backend
uv run python manage.py runserver
```

Em outro terminal:

```bash
cd frontend
bun install
bun run dev
```

Acesse `http://localhost:5173`. O Vite encaminha `/api`, `/entrar`, `/sair` e `/admin` ao Django em `127.0.0.1:8000` preservando o cabeçalho `Host` (`changeOrigin: false`), o que mantém sessão e verificação de origem do CSRF em mesma origem para o navegador.

## Produção

```bash
bun install --frozen-lockfile
bun run build
```

Sirva `frontend/dist/` e encaminhe `/api/`, `/entrar/`, `/sair/` e `/admin/` ao Django no mesmo domínio. Esta base não habilita CORS; separar os domínios exige uma decisão adicional sobre origens confiáveis, cookies e CSRF.

## Identidade visual por instalação

O SIGAB é single-tenant (ADR 0007): cada cliente tem sua instalação, então a personalização visual é feita por instalação, sem rebuild.

1. Copie `public/brand.example.json` para `brand.json` na raiz servida (em desenvolvimento, `public/brand.json`; em produção, ao lado do `index.html` em `dist/`).
2. Ajuste os campos desejados. Campos ausentes ou inválidos mantêm o padrão de `src/theme/brand.ts`.
3. Logotipos ficam na própria instalação (`logoUrl` aceita só caminhos locais, como `/brand/logo.svg`).

| Campo | Efeito |
| --- | --- |
| `name`, `tagline`, `monogram`, `logoUrl` | Marca na navegação e título da aba |
| `colors.primary` | Cor institucional; fundos, bordas, estados e modo escuro são derivados dela |
| `colors.accent` | Foco de teclado e indicador do item ativo |
| `colors.sidebar` | Fundo da navegação (opcional; derivado da primária) |
| `radius` | Raio base dos componentes (0–20 px) |
| `density` | `comfortable` ou `compact` (balcão com muitos itens na tela) |
| `modules.<id>.label` / `hidden` | Renomeia ou oculta áreas da navegação |

Ocultar um módulo é apenas apresentação: permissões continuam decididas pela API. O acervo não pode ser ocultado, pois é a página inicial.

`brand.json` e `public/brand/` não são versionados.

## Estrutura de tema e navegação

- `src/theme/` — configuração da marca, carregamento de `brand.json` e preferência claro/escuro/sistema do usuário.
- `src/styles/` — CSS em camadas (`tokens` → `base` → `layout` → `components` → `utilities`). Componentes usam apenas tokens semânticos (`--color-*`, `--space-*`), nunca cores literais.
- `src/app/modules.tsx` — registro único de módulos: rota, rótulo, ícone, grupo e permissão. Nova área = nova entrada aqui; navegação e roteamento passam a reconhecê-la.
