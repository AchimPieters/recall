# Content Workflow

## States
- `draft`
- `review`
- `approved`
- `published`
- `archived`

## Role responsibilities
- **editor**: mag content naar `review` bewegen.
- **reviewer**: mag content `approved` en `published` maken.
- **admin/superadmin**: mogen alle workflow-transities uitvoeren.

## Pipeline
1. editor uploadt content in `draft`.
2. editor zet item naar `review`.
3. reviewer zet item naar `approved`.
4. reviewer publiceert naar `published`.
5. item kan later naar `archived`.
