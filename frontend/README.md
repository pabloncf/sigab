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
