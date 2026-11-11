# GitHub Actions aktivieren

**Aktueller Stand (11. November 2026):** Die aktiven und maßgeblichen Abläufe
liegen bereits unter `.github/workflows/`. Insbesondere ruft `ci.yml` jetzt
`linux-package.yml` für AppImage/DEB auf. Die folgenden Vorlagen und die
damalige Aktivierungsanleitung sind historisch; nicht über aktive Workflows
kopieren oder erneut verschieben.

Die beiden YAML-Dateien in diesem Ordner sind die vollständigen Vorlagen
für Prüfungen und Vorabversionen. GitHub hat das Schreiben nach
`.github/workflows/` für die Anmeldedaten dieser Sitzung abgelehnt.
Der verwendeten Anmeldung fehlt die Berechtigung `workflow`.

Mit einer GitHub-Anmeldung, die Workflows schreiben darf, führe auf dem
Arbeitszweig aus:

```sh
mkdir -p .github/workflows
git mv docs/github-workflows/ci.yml .github/workflows/ci.yml
git mv docs/github-workflows/release.yml .github/workflows/release.yml
git diff --cached --check
git commit -m 'ci: activate validation and prerelease workflows'
git push
```

Der Ablauf zur Veröffentlichung braucht zusätzlich einen passenden Tag auf
einem geprüften Stand von `main`. Siehe [RELEASE.md](../RELEASE.md).
