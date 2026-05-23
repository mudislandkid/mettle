# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.9.x   | Yes (latest minor only) |
| < 0.9   | No |

Only the latest 0.9.x release is supported with security fixes during the
pre-1.0 phase.

## Reporting a Vulnerability

Please do not open a public issue for security vulnerabilities.

Use **GitHub Private Vulnerability Reporting**:
<https://github.com/mudislandkid/mettle/security/advisories/new>

We will acknowledge within 72 hours and aim to ship a fix or mitigation
within 14 days for high or critical issues. Lower-severity issues will
roll into the next minor release.

When a fix ships, we will credit reporters in the release notes unless
anonymity is preferred.

## Scope

In scope:
- Authentication or authorisation bypass
- Path traversal / sandbox escapes in the scanner
- Code execution via the API
- Information disclosure via the API or scanner
- Tauri shell vulnerabilities (sidecar process model)

Out of scope:
- Findings from running Mettle against intentionally malicious code
  (it is an analyser; analysing dangerous input is the job)
- Denial of service against a self-hosted instance
- Issues in transitive dependencies without a clear exploit path
  (we monitor via Dependabot and the `dep-audit.yml` workflow)
