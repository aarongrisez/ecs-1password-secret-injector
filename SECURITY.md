# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please email the maintainer directly at **aaron@aarongrisez.com** with:

1. A description of the vulnerability.
2. Steps to reproduce the issue.
3. The potential impact.
4. Any suggested mitigations.

You will receive a response within 5 business days.  Once the vulnerability is
confirmed and a fix is available, a security advisory will be published and the
patch will be released.

## Security Considerations

This service handles **sensitive credentials** (1Password tokens, AWS credentials).
Please ensure:

- Environment variables are passed securely (not logged, not stored in plain text).
- AWS and 1Password credentials are scoped with least-privilege policies.
- Network access to your 1Password Connect server is restricted appropriately.
