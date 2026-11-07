# Externe Textkorrektur

Die externe Korrektur ist freiwillig. Sie verarbeitet den erkannten Text
und die eingegebene Bearbeitungsanweisung. Lies dazu [PRIVACY.md](../PRIVACY.md).
Die Nutzung externer Dienste kann Kosten verursachen.

Die Anbieter OpenAI, Google Gemini, Anthropic Claude, xAI und OpenRouter haben
je eigene Anmeldedaten. Mistral, Groq, DeepSeek, Together AI, Fireworks AI
und Cerebras sind mit ihrer Dienstadresse hinterlegt. Wähle **Kompatibel**
für eine eigene Basisadresse mit Unterstützung für `chat/completions`.
Dokumentation der direkt angebundenen Anbieter:

- [OpenAI](https://platform.openai.com/docs/api-reference/responses)
- [Google Gemini](https://ai.google.dev/api/generate-content)
- [Anthropic](https://platform.claude.com/docs/en/api/messages)
- [xAI](https://docs.x.ai/docs/api-reference)
- [OpenRouter](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request)

Wähle ein Textmodell aus der Liste des Anbieters oder trage seine Modell-ID
ein. Gib deinen Schlüssel nur in den Einstellungen ein und lösche ihn
dort, wenn du die Verbindung nicht mehr nutzt. Linux benötigt dafür einen
verfügbaren Dienst zur Verwaltung von Zugangsdaten, etwa den GNOME
Schlüsselbund oder eine kompatible Secret-Service-Implementierung.

Ein benutzerdefinierter Dienst im Internet benötigt HTTPS. Lokale Dienste
wie Ollama oder LM Studio können über `localhost`, `127.0.0.1` oder
`[::1]` auch per HTTP angesprochen werden. Gib die Basisadresse inklusive
Port und gegebenenfalls API-Pfad ein. Auf dem eigenen Rechner ist der
Schlüssel optional. Prüfe bei Fehlern zuerst die Dienstadresse, die
Modell-ID, die Berechtigungen deines Schlüssels und das Limit des Anbieters.
