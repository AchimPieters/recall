# Dependency Governance

## Policy
- Pin direct dependencies in `backend/requirements.txt`.
- Run dependency vulnerability scan on every PR and release.
- Generate SBOM for every release artifact.

## Suggested commands
- Vulnerability scan: `pip-audit -r backend/requirements.txt`
- SBOM generation: `cyclonedx-py requirements backend/requirements.txt -o sbom.json`

## Exception handling
- Any temporary vulnerability exception must include risk, owner, expiration date, and mitigation.
- Current temporary exception: `CVE-2024-23342` (`ecdsa` transitive dependency from `python-jose`) has no upstream fix release available; track and remove ignore once a patched release is published.


## Supply chain security gates
- SBOM generation: `syft dir:. -o cyclonedx-json=sbom.cdx.json`
- Vulnerability scan on SBOM: `grype sbom:sbom.cdx.json --fail-on high`
- Artifact signing: `cosign sign-blob sbom.cdx.json --output-signature sbom.cdx.json.sig --output-certificate sbom.cdx.json.pem`
- CI workflow: `.github/workflows/supply-chain-security.yml`
