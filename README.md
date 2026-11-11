# Voicewright

Voicewright ist eine freie Desktop-App für lokale Diktate auf Deutsch, Englisch
und in weiteren Whisper-Sprachen. Mikrofon und Spracherkennung arbeiten auf
dem eigenen Gerät. Eine optionale Textkorrektur kann ebenfalls lokal laufen.
Cloud-Dienste sind freiwillig und nur mit eigener Konfiguration aktiv.

**Status:** Entwicklung von 0.1.0-alpha.1. Die Übergabe mit Prüfergebnissen,
bekannten Einschränkungen und offenen Schritten steht in
[docs/PROGRESS.md](docs/PROGRESS.md).

Unter Linux nutzt Voicewright auf X11 globale Tasten und sicheres direktes
Einfügen. Auf Wayland kommen globale Tasten über das XDG-Desktop-Portal,
sofern der Desktop es anbietet und du die Freigabe bestätigst. Automatisches
Einfügen bleibt dort bewusst aus; der erkannte Text bleibt in der App und
lässt sich kopieren.

- [Installation und Entwicklung](docs/INSTALLATION.md)
- [Sprach- und Korrekturmodelle](docs/MODELS.md)
- [Anbieter](docs/PROVIDERS.md)
- [Plattformen](docs/PLATFORM_SUPPORT.md)
- [Datenschutz](PRIVACY.md) und [Sicherheit](SECURITY.md)

Der Anwendungscode steht unter der [MIT-Lizenz](LICENSE). Für Modelle und
Abhängigkeiten gelten [eigene Lizenzen](docs/THIRD_PARTY_LICENSES.md).
