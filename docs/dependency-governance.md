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
- Current temporary exception: `CVE-2024-23342` (`ecdsa` transitive dependency from `python-jose`) has no upstream fix release available; track and remove ignore once a patched release is published.
