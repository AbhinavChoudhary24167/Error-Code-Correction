# Security policy

GREEN is research software for reliability and sustainability analysis. ECC here concerns data integrity; it does not provide confidentiality, authentication, tamper resistance, or cryptographic security.

## Supported code

The repository does not currently publish a versioned backport schedule. Security and integrity fixes target the current default branch. Historical campaign packages are immutable evidence: a correction is added as a new record or documented migration rather than silently rewriting the original.

## Report a vulnerability

Use GitHub's private vulnerability-reporting or security-advisory interface for this repository when available. If it is unavailable, contact a repository maintainer privately through the hosting platform before filing a public issue. Do not include credentials, private data, exploit payloads, or sensitive system paths in a public report.

Include the affected commit, platform, minimal reproducer, expected/observed behavior, and potential impact. Relevant issues include arbitrary code execution, unsafe path handling, dependency compromise, denial of service on ordinary inputs, or an integrity defect that silently changes ECC/research results.

No response deadline is promised. Maintainers will assess reproducibility, impact, affected results, disclosure needs, and whether an additive correction or migration is required.

## Trust boundary

Treat configuration, CSV/JSON, telemetry, RTL, campaign scripts, and external EDA reports as untrusted until reviewed. Some historical campaigns contain exact commands and absolute paths; they are provenance, not commands for automatic execution. The repository does not automatically install physical-design tools or execute frozen campaigns during ordinary tests.

Scientific overclaiming or a reproducibility discrepancy may be important without being a software vulnerability. Report non-sensitive research-integrity problems in the normal issue tracker, preserving the failing artifact and evidence boundary.
