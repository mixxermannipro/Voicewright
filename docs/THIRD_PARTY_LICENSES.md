# Fremdsoftware und Modelle

Die MIT-Lizenz in [LICENSE](../LICENSE) gilt für den Voicewright-Code. Für
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
| [ashpd](https://github.com/bilelmoussaoui/ashpd) | XDG-Desktop-Portale für Wayland-Tastenkürzel | MIT |
| [futures-util](https://github.com/rust-lang/futures-rs) | Asynchrone Stream-Helfer für das Portal | MIT oder Apache-2.0 |
| [unicode-segmentation](https://github.com/unicode-rs/unicode-segmentation) | Graphem-sicheres Einfügen von Unicode | MIT oder Apache-2.0 |
| [x11rb](https://github.com/psychon/x11rb) | X11-Verbindung und Fokusprüfung | MIT oder Apache-2.0 |

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

## Mitgelieferte native Engines / Bundled native engines

Diese Hinweise stammen aus den Quellen der gesperrten Crates
`whisper-rs-sys 0.15.0` und `llama-cpp-sys-2 0.1.161`.
These notices cover the bundled whisper.cpp and llama.cpp sources.

whisper.cpp: Copyright (c) 2023-2024 The ggml authors

llama.cpp: Copyright (c) 2023-2026 The ggml authors

MIT License (applies to each engine separately):

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
