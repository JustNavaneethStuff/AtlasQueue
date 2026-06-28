# Security Policy

## Supported versions

Security fixes are applied to the `main` branch.

## Reporting a vulnerability

Please open a private security advisory on GitHub or email the maintainer with:

- Description of the issue
- Steps to reproduce
- Potential impact

Do not disclose publicly until a fix is available.

## Production checklist

- Change `API_KEY`, `JWT_SECRET`, and `ADMIN_PASSWORD`
- Disable docs in production (`ENABLE_DOCS=false`)
- Protect `/v1/metrics` (`METRICS_REQUIRE_AUTH=true`) or restrict by network policy
- Use TLS termination at ingress/reverse proxy
- Rotate credentials regularly
