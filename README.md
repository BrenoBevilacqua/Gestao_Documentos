# Gestão de Documentos — Controle de Fichas do Acervo

Aplicação web em **Django** que substitui a planilha *"Caderno de Correspondência Digital — Controle de Fichas do Acervo"*:
controle de **retirada e devolução de fichas de servidores** solicitadas pelo RH.

## Funcionalidades

- **Painel** (equivalente à aba *Painel* da planilha): total de fichas retiradas, emprestadas, devolvidas e em atraso,
  lista das fichas atrasadas e últimas movimentações.
- **CRUD completo** (listar, cadastrar, ver, editar, excluir) de:
  - **Retiradas de fichas** (aba *Controle*);
  - **Servidores** (nome, matrícula, nº da caixa);
  - **Solicitantes (RH)**.
- Tabelas com **busca**, **filtro por situação** e **paginação**.
- **Prazo de devolução automático**: data de retirada + 5 dias corridos (configurável por `PRAZO_DEVOLUCAO_DIAS`).
- **Situação calculada automaticamente**, com as mesmas cores da planilha:
  🟧 *Emprestado* · 🟩 *Devolvido* · 🟥 *Atrasado*.
- Botão **"Registrar devolução"** (preenche a data de hoje).
- **Anexo** opcional em cada retirada (protocolo assinado, digitalização etc.).
- **Admin do Django** em `/admin/`.
- Comando para **importar a planilha Excel** existente.

## Estrutura

```
gestao_documentos/
├── acervo/                    # app principal (models, views, forms, templates, admin)
│   ├── management/commands/importar_planilha.py
│   ├── fixtures/dados_exemplo.json
│   ├── migrations/
│   └── templates/acervo/
├── config/                    # settings, urls, wsgi
├── dados/controle_fichas.xlsx # planilha original (usada pelo importador)
├── templates/base.html        # layout Bootstrap 5 + menu
├── Dockerfile, docker-compose.yml, entrypoint.sh, .dockerignore
├── .env.example
└── requirements.txt
```

## Executar localmente

Requisitos: Python 3.10+.

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser  # usuário para o /admin/
python manage.py importar_planilha   # (opcional) importa dados/controle_fichas.xlsx
python manage.py runserver
```

Acesse <http://127.0.0.1:8000/>.

Outras formas de carregar dados:

```bash
python manage.py importar_planilha caminho/para/outra_planilha.xlsx   # outra planilha (aba "Controle")
python manage.py loaddata dados_exemplo                              # fixture de exemplo
```

O importador ignora linhas vazias e fórmulas, aceita datas como `24.08.2026` ou `24/08/2026`
e não duplica registros se for executado mais de uma vez.

Testes automatizados:

```bash
python manage.py test acervo
```

## Executar com Docker

```bash
cp .env.example .env              # ajuste SECRET_KEY, ALLOWED_HOSTS etc.
docker compose up -d --build
```

Acesse <http://localhost:8000/>. O banco SQLite e os anexos ficam no volume `dados` (`/app/data` no contêiner).

Sem Docker Compose:

```bash
docker build -t gestao-documentos .
docker run -d -p 8000:8000 \
  -e SECRET_KEY="uma-chave-secreta" \
  -e ALLOWED_HOSTS="localhost,127.0.0.1" \
  -e DJANGO_SUPERUSER_USERNAME=admin -e DJANGO_SUPERUSER_PASSWORD=admin123 \
  -v gestao_dados:/app/data \
  gestao-documentos
```

Ao iniciar, o contêiner executa `migrate` automaticamente (`entrypoint.sh`), cria o superusuário se
`DJANGO_SUPERUSER_USERNAME`/`DJANGO_SUPERUSER_PASSWORD` estiverem definidos e, com `IMPORTAR_PLANILHA=1`,
importa a planilha. A aplicação roda com **gunicorn** e os arquivos estáticos são servidos pelo **WhiteNoise**.

## Variáveis de ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | chave insegura de desenvolvimento | **Defina em produção.** |
| `DEBUG` | `1` (local) / `0` (Docker) | Modo de depuração. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` | Hosts permitidos, separados por vírgula. |
| `CSRF_TRUSTED_ORIGINS` | vazio | Ex.: `https://acervo.minhaempresa.gov.br` |
| `SQLITE_PATH` | `db.sqlite3` | Caminho do banco SQLite. |
| `MEDIA_ROOT` | `media/` | Pasta dos anexos enviados. |
| `PRAZO_DEVOLUCAO_DIAS` | `5` | Prazo padrão de devolução (dias corridos). |
| `PAGINATE_BY` | `20` | Registros por página nas tabelas. |
| `TIME_ZONE` | `America/Sao_Paulo` | Fuso horário (define o "hoje" para atrasos). |
| `SERVE_MEDIA` | `1` | Django serve os anexos (adequado para uso interno). |
| `HTTPS` | `0` | `1` quando estiver atrás de HTTPS (cookies seguros). |
| `DJANGO_SUPERUSER_*` | — | Criação automática de superusuário no Docker. |
| `IMPORTAR_PLANILHA` | `0` | `1` importa `dados/controle_fichas.xlsx` ao iniciar o contêiner. |

## Regras herdadas da planilha

| Planilha (aba Controle) | Aplicação |
|---|---|
| Nº | ID da retirada (automático) |
| Nº da Caixa | `Retirada.numero_caixa` (se vazio, usa a caixa do servidor) |
| Nome do Servidor / Matrícula | cadastro de **Servidor** (matrícula opcional) |
| Solicitante (RH) | cadastro de **Solicitante** |
| Data de Retirada | padrão = hoje |
| Prazo de Devolução | `= Data de Retirada + 5` (se não informado) |
| Data de Devolução | preenchida ao devolver |
| Situação | calculada: Devolvido / Atrasado / Emprestado |
| Observações | texto livre |

> Dica da planilha mantida: evite excluir retiradas antigas — elas são o histórico/protocolo de movimentação.
> Servidores e solicitantes com retiradas vinculadas não podem ser excluídos.
