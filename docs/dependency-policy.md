# Dependency Policy

## Goals
- Keep dependency graph secure, maintainable, and reproducible.
- Minimize surprise upgrades and supply-chain risk.

## Policy rules
1. Add dependencies only when needed for a documented capability.
2. Prefer actively maintained libraries with clear release cadence.
3. Pin or tightly constrain direct dependencies where practical.
4. Run security scanning for backend and SBOM scanning in CI.
5. Record exceptions with owner, risk, mitigation, and expiry date.

## Required checks
- Python dependency vulnerability scan for backend requirement set.
- SBOM generation and vulnerability scanning in CI.
- Artifact signing for generated SBOM artifacts.

## Frontend governance
- New frontend dependencies must pass:
  - `npm run lint`
  - `npm run test`
  - `npm run build`
- Keep ESLint/Prettier/Vitest toolchain healthy before feature merges.

## Review checklist
- Why is the dependency required?
- Is there an existing in-repo capability that already solves this?
- Security posture reviewed (known CVEs / advisories)?
- Upgrade/removal plan documented?
