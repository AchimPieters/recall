# Dependency Governance

## Policy
- Pin direct dependencies in `recall-server/requirements.txt`.
- Run dependency vulnerability scan on every PR and release.
- Generate SBOM for every release artifact.

## Suggested commands
- Vulnerability scan: `pip-audit -r recall-server/requirements.txt`
- SBOM generation: `cyclonedx-py requirements recall-server/requirements.txt -o sbom.json`

## Exception handling
- Any temporary vulnerability exception must include risk, owner, expiration date, and mitigation.
