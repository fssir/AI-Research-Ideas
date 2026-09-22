# Security

Never submit tokens, credentials, personal/confidential data without authorization, or malware disguised as research. Raise security-sensitive problems privately with the repository owner through a private contact channel; do not publish secrets or exploit payloads in Issues.

The trusted publisher runs only code from the default branch. It inspects PR Git blobs through the API without checking them out, importing them, installing dependencies, executing notebooks or running submitted programs. Contributors cannot grant themselves permissions by changing the registry, workflow, labels or commit authorship.

Only the machine-owned `automation/ori-platform` branch may be regenerated; user branches and `main` are never force-pushed by this automation. Protected PRs are merged only after explicit validation of their immutable candidate and an up-to-date base check. Maintainers must independently review platform-code changes and must not treat an arbitrary green PR workflow as proof of safety.

This is risk reduction, not a guarantee that all uploaded files or scientific claims are safe. Use an isolated environment before manually running any research code. Keep account two-factor authentication enabled. Do not grant repository-wide write access to unknown contributors.
