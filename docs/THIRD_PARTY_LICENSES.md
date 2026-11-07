# Fremdsoftware und Modelle

Die MIT-Lizenz in [LICENSE](../LICENSE) gilt für den VoxTakt-Code. Für
Fremdsoftware gelten jeweils die Lizenztexte und Hinweise der Urheber.

| Projekt | Rolle | Lizenz laut Projekt |
| --- | --- | --- |
| [Tauri](https://github.com/tauri-apps/tauri) | Desktop-Rahmen und Paketbau | MIT oder Apache-2.0 |
| [React](https://github.com/facebook/react) | Oberfläche | MIT |
| [Vite](https://github.com/vitejs/vite) | Erstellung der Oberfläche | MIT |
| [CPAL](https://github.com/RustAudio/cpal) | Mikrofonzugriff | Apache-2.0 |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp/blob/master/LICENSE) | Lokale Spracherkennung | MIT |
| [llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/LICENSE) | Lokale Textkorrektur | MIT |
| [whisper-rs](https://codeberg.org/tazz4843/whisper-rs) | Rust-Anbindung an whisper.cpp | Unlicense |
| [llama-cpp-rs](https://github.com/utilityai/llama-cpp-rs) | Rust-Anbindung an llama.cpp | MIT oder Apache-2.0 |
| [Enigo](https://github.com/enigo-rs/enigo) | Direkte Texteingabe | MIT |
| [arboard](https://github.com/1Password/arboard) | Zwischenablage | MIT oder Apache-2.0 |
| [keyring-rs](https://github.com/hwchen/keyring-rs) | Zugangsdaten-Speicher | MIT oder Apache-2.0 |

Diese indirekten Rust-Abhängigkeiten verwenden MPL-2.0. Ihr Quellcode ist
über die exakten Versionen auf crates.io verfügbar:

- [cssparser 0.37.0](https://crates.io/crates/cssparser/0.37.0)
- [cssparser-macros 0.7.1](https://crates.io/crates/cssparser-macros/0.7.1)
- [dtoa-short 0.3.5](https://crates.io/crates/dtoa-short/0.3.5)
- [option-ext 0.2.0](https://crates.io/crates/option-ext/0.2.0)
- [selectors 0.38.0](https://crates.io/crates/selectors/0.38.0)

Die Zertifikatsliste [webpki-roots 1.0.11](https://crates.io/crates/webpki-roots/1.0.11)
verwendet CDLA-Permissive-2.0.

Für die vollständige Liste der Versionen siehe `package-lock.json`,
`src-tauri/Cargo.lock` und `engines/cleanup/Cargo.lock`. Für eine
Veröffentlichung sind auch indirekte Abhängigkeiten, eingebundene
C/C++-Bibliotheken, alle mitgelieferten Laufzeiten und nötige Lizenzhinweise
zu prüfen. Ein Sicherheitscheck der Abhängigkeiten ersetzt diese Prüfung
nicht.

Modelle werden separat bezogen. Ihre Lizenzbedingungen stammen aus den
jeweiligen Modellkarten und stehen unabhängig von den Lizenzen der
Ausführungssoftware. Siehe [MODELS.md](MODELS.md).
