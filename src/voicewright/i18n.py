"""Minimal i18n: English source strings, German translations."""
from __future__ import annotations

import locale
import os

_lang = "en"


def set_language(lang: str) -> None:
    global _lang
    if lang in ("de", "en"):
        _lang = lang
        return
    sys_lang = ""
    try:
        from PySide6.QtCore import QLocale
        sys_lang = QLocale.system().name()
    except Exception:
        sys_lang = os.environ.get("LANG", "") or (locale.getlocale()[0] or "")
    _lang = "de" if sys_lang.lower().startswith("de") else "en"


def current_language() -> str:
    return _lang


def tr(text: str) -> str:
    if _lang == "de":
        return DE.get(text, text)
    return text


DE: dict[str, str] = {
    # --- tabs / general ---------------------------------------------------
    "Settings": "Einstellungen",
    "General": "Allgemein",
    "Speech model": "Sprachmodell",
    "AI cleanup": "KI-Bereinigung",
    "Output": "Ausgabe",
    "History": "Verlauf",
    "About": "Info",
    "Close": "Schließen",
    "Shortcut": "Tastenkürzel",
    "Shortcut:": "Tastenkürzel:",
    "Dictation shortcut:": "Diktier-Tastenkürzel:",
    "Mode:": "Modus:",
    "Mode": "Modus",
    "Toggle – press once to start, press again to finish":
        "Umschalten – einmal drücken zum Starten, erneut drücken zum Beenden",
    "Push-to-talk – hold while speaking, release to finish":
        "Push-to-Talk – gedrückt halten beim Sprechen, loslassen zum Beenden",
    "Toggle (press – press)": "Umschalten (drücken – drücken)",
    "Push-to-talk (hold)": "Push-to-Talk (halten)",
    "Esc cancels a running recording": "Esc bricht eine laufende Aufnahme ab",
    "Hotkey backend:": "Hotkey-Backend:",
    "Automatic": "Automatisch",
    "None – use CLI/desktop shortcut": "Keins – CLI/Desktop-Tastenkürzel verwenden",
    "Wayland detected. Global key listening needs the evdev backend (run "
    "<code>sudo usermod -aG input $USER</code> and log in again). Alternatively bind "
    "<code>voicewright --toggle</code> to a shortcut in your desktop settings.":
        "Wayland erkannt. Globale Tastenkürzel benötigen das evdev-Backend (führe "
        "<code>sudo usermod -aG input $USER</code> aus und melde dich neu an). Alternativ "
        "<code>voicewright --toggle</code> in den Desktop-Einstellungen als Tastenkürzel hinterlegen.",
    "Press shortcut…  (Esc = cancel)": "Tastenkürzel drücken…  (Esc = Abbrechen)",
    "Not set": "Nicht gesetzt",
    "Empty shortcut": "Leeres Tastenkürzel",
    "Use at least two modifiers or a modifier plus a key":
        "Verwende mindestens zwei Modifikatortasten oder eine Modifikatortaste plus eine Taste",
    "Single keys are only allowed for function keys (F1–F24)":
        "Einzelne Tasten sind nur für Funktionstasten (F1–F24) erlaubt",
    "Microphone": "Mikrofon",
    "Refresh": "Aktualisieren",
    "Input device:": "Eingabegerät:",
    "System default": "Systemstandard",
    "Max. recording length:": "Max. Aufnahmedauer:",
    "Play start/stop sounds": "Start-/Stopp-Töne abspielen",
    "Application": "Anwendung",
    "Show recording indicator": "Aufnahme-Anzeige einblenden",
    "Indicator position:": "Position der Anzeige:",
    "Bottom": "Unten",
    "Top": "Oben",
    "Start minimized to tray": "Minimiert im Infobereich starten",
    "Launch at login": "Beim Anmelden starten",
    "Interface language:": "Sprache der Oberfläche:",
    "System": "System",
    "Restart Voicewright to apply the language.": "Starte Voicewright neu, um die Sprache zu übernehmen.",
    # --- models -------------------------------------------------------------
    "All speech recognition runs locally on your computer. Download a model and select it.":
        "Die Spracherkennung läuft vollständig lokal auf deinem Computer. Lade ein Modell herunter und wähle es aus.",
    "NVIDIA GPU detected (CUDA).": "NVIDIA-GPU erkannt (CUDA).",
    "No CUDA GPU detected – CPU mode.": "Keine CUDA-GPU erkannt – CPU-Modus.",
    "Recommended for you:": "Empfohlen für dich:",
    "Model": "Modell",
    "Size": "Größe",
    "Languages": "Sprachen",
    "Speed": "Tempo",
    "Accuracy": "Genauigkeit",
    "Status": "Status",
    "recommended": "empfohlen",
    "recommended for": "empfohlen für",
    "Not downloaded": "Nicht heruntergeladen",
    "Downloaded": "Heruntergeladen",
    "Active": "Aktiv",
    "Multilingual": "Mehrsprachig",
    "English only": "Nur Englisch",
    "Download": "Herunterladen",
    "Use this model": "Dieses Modell verwenden",
    "Delete": "Löschen",
    "Cancel download": "Download abbrechen",
    "Model downloaded:": "Modell heruntergeladen:",
    "Download failed:": "Download fehlgeschlagen:",
    "Delete model?": "Modell löschen?",
    "Recognition": "Erkennung",
    "Spoken language:": "Gesprochene Sprache:",
    "Automatic detection": "Automatische Erkennung",
    "Task:": "Aufgabe:",
    "Transcribe (keep language)": "Transkribieren (Sprache beibehalten)",
    "Translate to English (offline, Whisper)": "Ins Englische übersetzen (offline, Whisper)",
    "Device:": "Gerät:",
    "Precision:": "Genauigkeit (Rechenformat):",
    "Optional: names, jargon, style hints for Whisper": "Optional: Namen, Fachbegriffe, Stilhinweise für Whisper",
    "Vocabulary prompt:": "Vokabular-Hinweis:",
    "Skip silence (VAD filter)": "Stille überspringen (VAD-Filter)",
    "Keep model in memory (faster)": "Modell im Speicher halten (schneller)",
    "Very fast, low accuracy. Good for testing.": "Sehr schnell, geringe Genauigkeit. Gut zum Testen.",
    "Fast, okay for clear speech.": "Schnell, ausreichend bei deutlicher Aussprache.",
    "Best balance for CPUs / laptops without GPU.": "Beste Balance für CPUs / Laptops ohne GPU.",
    "High accuracy, slow on CPU.": "Hohe Genauigkeit, langsam auf der CPU.",
    "Near large-v3 quality, ~6x faster. Best choice with GPU or fast CPU.":
        "Fast large-v3-Qualität, ca. 6x schneller. Beste Wahl mit GPU oder schneller CPU.",
    "Highest accuracy, needs strong hardware.": "Höchste Genauigkeit, braucht starke Hardware.",
    "English only, fast and accurate.": "Nur Englisch, schnell und genau.",
    "English only small model.": "Kleines Modell, nur Englisch.",
    "English only base model.": "Basis-Modell, nur Englisch.",
    # --- cleanup ------------------------------------------------------------
    "After transcription the raw text can be cleaned up (filler words, punctuation, "
    "self-corrections) and optionally translated. Bring your own API key, or use a local "
    "model via Ollama / LM Studio, or the offline rules.":
        "Nach der Transkription wird der Rohtext bereinigt (Füllwörter, Zeichensetzung, "
        "Selbstkorrekturen) und optional übersetzt. Bring deinen eigenen API-Key mit, nutze ein "
        "lokales Modell über Ollama / LM Studio oder die Offline-Regeln.",
    "Enable cleanup": "Bereinigung aktivieren",
    "Provider": "Anbieter",
    "Provider:": "Anbieter:",
    "Offline rules (no AI)": "Offline-Regeln (ohne KI)",
    "Custom OpenAI-compatible": "Eigener OpenAI-kompatibler Server",
    "Paste your API key": "API-Key einfügen",
    "Optional API key": "Optionaler API-Key",
    "Show": "Anzeigen",
    "Get key": "Key holen",
    "API key:": "API-Key:",
    "Server URL:": "Server-URL:",
    "Load models": "Modelle laden",
    "Loading…": "Lade…",
    "Model:": "Modell:",
    "Test connection": "Verbindung testen",
    "Testing…": "Teste…",
    "Found models:": "Gefundene Modelle:",
    "Please enter an API key first.": "Bitte zuerst einen API-Key eingeben.",
    "Free API keys are available in Google AI Studio. Recommended: gemini-2.5-flash or gemini-2.5-flash-lite.":
        "Kostenlose API-Keys gibt es im Google AI Studio. Empfohlen: gemini-2.5-flash oder gemini-2.5-flash-lite.",
    "Runs fully local. Install Ollama, then e.g. <code>ollama pull llama3.2</code>.":
        "Läuft komplett lokal. Installiere Ollama, dann z. B. <code>ollama pull llama3.2</code>.",
    "Start the local server in LM Studio (Developer tab) and load a model.":
        "Starte in LM Studio den lokalen Server (Tab „Developer“) und lade ein Modell.",
    "Any OpenAI-compatible endpoint (vLLM, LocalAI, llama.cpp server, …).":
        "Beliebiger OpenAI-kompatibler Endpunkt (vLLM, LocalAI, llama.cpp-Server, …).",
    "Removes filler words and repetitions without any AI. Works offline, no translation.":
        "Entfernt Füllwörter und Wiederholungen ohne KI. Funktioniert offline, keine Übersetzung.",
    "On Wayland, set a desktop shortcut for voicewright --toggle.": "Lege unter Wayland ein Desktop-Tastenkürzel für voicewright --toggle an.",
    "Global shortcut unavailable. Bind voicewright --toggle in your desktop settings.": "Globales Tastenkürzel nicht verfügbar. Lege in den Desktop-Einstellungen ein Kürzel für voicewright --toggle an.",
    "System keyring unavailable. API key was not saved.": "Der System-Schlüsselbund ist nicht verfügbar. Der API-Schlüssel wurde nicht gespeichert.",
    "Voicewright copies finished dictations to the clipboard.": "Voicewright kopiert fertige Diktate in die Zwischenablage.",
    "Add a space after copied text": "Leerzeichen nach kopiertem Text ergänzen",
    "Your key is stored in the system keychain.": "Dein Key wird im Schlüsselbund des Systems gespeichert.",
    "API key saved": "API-Key gespeichert",
    "system keychain": "System-Schlüsselbund",
    "local file": "lokale Datei",
    "Style and translation": "Stil und Übersetzung",
    "Style:": "Stil:",
    "Clean – remove fillers, fix grammar (recommended)": "Sauber – Füllwörter entfernen, Grammatik korrigieren (empfohlen)",
    "Minimal – punctuation only": "Minimal – nur Zeichensetzung",
    "Formal – professional writing": "Formell – professioneller Schreibstil",
    "Casual – chat style": "Locker – Chat-Stil",
    "Output language:": "Ausgabesprache:",
    "Same as spoken (no translation)": "Wie gesprochen (keine Übersetzung)",
    "e.g. Use British spelling. Write numbers as digits.": "z. B. Zahlen als Ziffern schreiben. Du-Form verwenden.",
    "Custom instructions:": "Eigene Anweisungen:",
    "Comma separated: Voicewright, Kubernetes, Dr. Müller": "Kommagetrennt: Voicewright, Kubernetes, Dr. Müller",
    "Dictionary:": "Wörterbuch:",
    "Fall back to offline rules if the AI request fails": "Bei KI-Fehler auf Offline-Regeln zurückfallen",
    "Timeout:": "Zeitlimit:",
    # --- languages ----------------------------------------------------------
    "German": "Deutsch", "English": "Englisch", "French": "Französisch", "Spanish": "Spanisch",
    "Italian": "Italienisch", "Portuguese": "Portugiesisch", "Dutch": "Niederländisch",
    "Polish": "Polnisch", "Turkish": "Türkisch", "Russian": "Russisch", "Ukrainian": "Ukrainisch",
    "Czech": "Tschechisch", "Swedish": "Schwedisch", "Danish": "Dänisch", "Norwegian": "Norwegisch",
    "Finnish": "Finnisch", "Greek": "Griechisch", "Hungarian": "Ungarisch", "Romanian": "Rumänisch",
    "Arabic": "Arabisch", "Hebrew": "Hebräisch", "Hindi": "Hindi", "Japanese": "Japanisch",
    "Korean": "Koreanisch", "Chinese": "Chinesisch", "Vietnamese": "Vietnamesisch",
    "Indonesian": "Indonesisch", "Thai": "Thailändisch",
    # --- output -------------------------------------------------------------
    "Text insertion": "Texteinfügung",
    "Method:": "Methode:",
    "Paste via clipboard (fast, recommended)": "Über Zwischenablage einfügen (schnell, empfohlen)",
    "Simulate typing (slower, no clipboard)": "Tippen simulieren (langsamer, ohne Zwischenablage)",
    "Copy to clipboard only": "Nur in die Zwischenablage kopieren",
    "Paste shortcut:": "Einfüge-Kürzel:",
    "Automatic (Ctrl+V / ⌘V)": "Automatisch (Strg+V / ⌘V)",
    "Ctrl+Shift+V (terminals)": "Strg+Umschalt+V (Terminals)",
    "Restore previous clipboard content": "Vorherigen Inhalt der Zwischenablage wiederherstellen",
    "Add a space after inserted text": "Leerzeichen nach eingefügtem Text anhängen",
    "Paste delay:": "Einfüge-Verzögerung:",
    "Linux input tool:": "Linux-Eingabewerkzeug:",
    "On Wayland, install <code>wl-clipboard</code> and <code>ydotool</code> "
    "(Fedora: <code>sudo dnf install wl-clipboard ydotool</code> and enable "
    "<code>ydotoold</code>). Without them, text is copied and you paste manually.":
        "Unter Wayland <code>wl-clipboard</code> und <code>ydotool</code> installieren "
        "(Fedora: <code>sudo dnf install wl-clipboard ydotool</code> und <code>ydotoold</code> "
        "aktivieren). Ohne diese wird der Text nur kopiert und du fügst ihn manuell ein.",
    # --- history / about ----------------------------------------------------
    "Save history locally": "Verlauf lokal speichern",
    "Copy": "Kopieren",
    "Copy raw transcript": "Rohtranskript kopieren",
    "Clear history": "Verlauf löschen",
    "Copied to clipboard.": "In die Zwischenablage kopiert.",
    "Delete the entire history?": "Gesamten Verlauf löschen?",
    "Local-first voice dictation. Speech recognition runs offline with faster-whisper; "
    "cleanup uses your own API key or a local model.":
        "Lokales Sprachdiktat. Die Spracherkennung läuft offline mit faster-whisper; die "
        "Bereinigung nutzt deinen eigenen API-Key oder ein lokales Modell.",
    "Open models folder": "Modellordner öffnen",
    "Open logs folder": "Log-Ordner öffnen",
    "Open config folder": "Konfigurationsordner öffnen",
    # --- tray / controller --------------------------------------------------
    "Start dictation": "Diktat starten",
    "Stop dictation": "Diktat beenden",
    "Settings…": "Einstellungen…",
    "Quit": "Beenden",
    "Ready": "Bereit",
    "Recording…": "Aufnahme…",
    "Processing…": "Verarbeite…",
    "Welcome! Download a speech model to get started (recommended model is marked with ★).":
        "Willkommen! Lade ein Sprachmodell herunter, um loszulegen (das empfohlene Modell ist mit ★ markiert).",
    "Voicewright is running in the system tray. Shortcut:": "Voicewright läuft im Infobereich. Tastenkürzel:",
    "Invalid shortcut:": "Ungültiges Tastenkürzel:",
    "Global shortcut unavailable. Bind 'voicewright --toggle' to a desktop shortcut, "
    "or on Linux add yourself to the 'input' group.":
        "Globales Tastenkürzel nicht verfügbar. Lege 'voicewright --toggle' als Desktop-Tastenkürzel "
        "an oder füge dich unter Linux der Gruppe 'input' hinzu.",
    "Wayland: the shortcut only works while an X11/XWayland window is focused. "
    "Use the evdev backend (input group) or bind 'voicewright --toggle' as desktop shortcut.":
        "Wayland: Das Tastenkürzel funktioniert nur, wenn ein X11/XWayland-Fenster fokussiert ist. "
        "Nutze das evdev-Backend (Gruppe input) oder lege 'voicewright --toggle' als Desktop-Tastenkürzel an.",
    "Hold the shortcut while speaking": "Tastenkürzel beim Sprechen gedrückt halten",
    "No speech model downloaded. Please download one in the settings.":
        "Kein Sprachmodell heruntergeladen. Bitte lade eines in den Einstellungen herunter.",
    "Microphone error:": "Mikrofonfehler:",
    "Cancelled": "Abgebrochen",
    "No speech detected": "Keine Sprache erkannt",
    "Transcribing…": "Transkribiere…",
    "No API key set for": "Kein API-Key hinterlegt für",
    "AI cleanup failed": "KI-Bereinigung fehlgeschlagen",
    "Text copied to clipboard – paste it with Ctrl+V.": "Text in die Zwischenablage kopiert – mit Strg+V einfügen.",
    "Copied to clipboard": "In Zwischenablage kopiert",
    "Inserted": "Eingefügt",
    "Insert failed": "Einfügen fehlgeschlagen",
    "Error": "Fehler",
    "Transcription failed:": "Transkription fehlgeschlagen:",
    "Fatal error:": "Schwerer Fehler:",
}
