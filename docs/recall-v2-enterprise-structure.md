# Recall v2 Enterprise Directory Structuur

Onderstaande structuur is de **target state** voor Recall v2. Deze is bedoeld als implementatiecontract voor engineering.

## Target tree (samengevat)

```text
recall/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   ├── core/
│   │   ├── db/migrations/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── workers/
│   │   ├── integrations/
│   │   └── utils/
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/{app,components,features,hooks,lib,routes,services,store,styles,types}
│   ├── public/
│   ├── package.json
│   └── Dockerfile
├── agent/
│   ├── recall_agent/
│   ├── tests/
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── recall-agent.service
├── deploy/
│   ├── docker/
│   ├── k8s/
│   ├── scripts/
│   └── traefik/
├── observability/
│   ├── prometheus/
│   ├── grafana/
│   └── loki/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── security.md
│   ├── deployment.md
│   ├── device_protocol.md
│   ├── ota-updates.md
│   ├── development.md
│   └── runbooks/
└── .github/
    ├── workflows/
    ├── CODEOWNERS
    └── pull_request_template.md
```

## Migratie-aanpak
- Huidige code in `recall-server/` blijft tijdelijk bestaan als compatibiliteitslaag.
- Nieuwe features worden eerst in v2-structuur gebouwd, daarna worden legacy modules uitgefaseerd.
- Gebruik adapter-routes waar nodig zodat bestaande agents niet direct breken.

## Definition of done voor structuur
- Elke map heeft een duidelijke eigenaar en teststrategie.
- Geen businesslogica meer in route handlers.
- Geen in-memory persistence voor domeinobjecten.
- CI valideert backend, frontend en security als gescheiden pipelines.
