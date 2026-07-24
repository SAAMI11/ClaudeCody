# SAAMai 🤖

**SAAMai** ist eine vollständig eigenständige, private KI-Chat-Anwendung. Sie
läuft komplett **lokal auf deinem Rechner** unter Windows, Linux und macOS -
ohne kostenpflichtige Cloud-Dienste, ohne API-Schlüssel, ohne
Internetzwang (nach der einmaligen Installation der Modelle).

SAAMai kombiniert ein modernes Chat-Interface mit lokal laufenden
Open-Source-KI-Modellen (über [Ollama](https://ollama.com)), einer lokalen
Datenbank für den Chatverlauf, Dokumenten- und Bildanalyse, optionaler
Sprachein-/ausgabe, Mehrsprachigkeit, einem Plugin-System und einer
REST-API für eigene Erweiterungen.

---

## Inhaltsverzeichnis

1. [Funktionsübersicht](#funktionsübersicht)
2. [Architektur](#architektur)
3. [Projektstruktur (jede Datei erklärt)](#projektstruktur-jede-datei-erklärt)
4. [Installation](#installation)
5. [Benutzung](#benutzung)
6. [Konfiguration](#konfiguration)
7. [Plugin-System & API für Erweiterungen](#plugin-system--api-für-erweiterungen)
8. [Sicherheit](#sicherheit)
9. [Tests](#tests)
10. [Fehlerbehebung](#fehlerbehebung)

---

## Funktionsübersicht

- 🧠 Eigenständige KI namens **SAAMai**, angetrieben durch lokale
  Open-Source-Modelle (Llama 3, Mistral, Phi, ... - alles, was
  [Ollama](https://ollama.com/library) bereitstellt)
- 💬 Modernes, responsives Chat-Interface (Dark/Light Mode)
- 💾 Lokale SQLite-Datenbank für Chatverläufe, Einstellungen und Konten
- 📄 Dokumente lesen: PDF, Word (.docx), Text/Markdown/CSV
- 🖼️ Bildanalyse über lokale Vision-Modelle (z. B. LLaVA)
- 🎤 Optionale Spracheingabe & 🔊 Sprachausgabe (Browser-native Web
  Speech API - kein zusätzlicher Dienst nötig)
- 🌍 Mehrsprachig (Deutsch, Englisch, beliebig erweiterbar über JSON-Dateien)
- 🔎 Volltextsuche über alle Chats
- ⬇️ Export von Chats (Markdown, Text, JSON)
- 👤 Optionale lokale Benutzerkonten (Mehrbenutzerbetrieb auf einem Gerät)
- 🧩 Plugin-System (eigene .py-Dateien, automatisch geladen)
- 🔌 REST-API für eigene Erweiterungen/Integrationen
- ⚡ Streaming-Antworten (Tokens erscheinen sofort, nicht erst am Ende)
- 🛡️ Sichere Passwort-Hashes (bcrypt), signierte Sessions (JWT), keine
  Cloud-Abhängigkeit

Kein Baustein dieses Projekts erfordert ein kostenpflichtiges Konto, einen
API-Schlüssel oder einen externen Cloud-Dienst.

---

## Architektur

```
┌──────────────────────────┐        HTTP/JSON, Streaming        ┌───────────────────────────┐
│   Frontend (Browser)     │  <──────────────────────────────>  │   Backend (FastAPI)       │
│   HTML/CSS/Vanilla JS    │                                     │   Python                  │
└──────────────────────────┘                                     └────────────┬──────────────┘
                                                                                │
                                     ┌──────────────────────────────────────────┼───────────────────────────┐
                                     │                                          │                           │
                             ┌───────▼────────┐                        ┌───────▼────────┐         ┌────────▼────────┐
                             │  SQLite (lokal) │                        │ Ollama (lokal)  │         │ Dateisystem      │
                             │  Chats/User/    │                        │ Open-Source-LLMs│         │ Uploads/Anhänge  │
                             │  Settings       │                        │ (Text + Vision) │         │                  │
                             └────────────────┘                        └────────────────┘         └──────────────────┘
```

- **Frontend**: reines HTML/CSS/JavaScript ohne Build-Schritt - läuft in
  jedem modernen Browser, wird vom Backend als statische Datei ausgeliefert.
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/) (Python), liefert
  sowohl die REST-API als auch die Frontend-Dateien über einen einzigen
  Prozess/Port aus.
- **KI-Modelle**: [Ollama](https://ollama.com) läuft als separater,
  lokaler Prozess und stellt eine einfache HTTP-API bereit, über die
  SAAMai Text- und Bildanfragen streamt. Ollama ist frei, Open-Source und
  unterstützt u. a. Llama 3, Mistral, Phi-3, Gemma und LLaVA (Vision).
- **Datenbank**: SQLite - eine Datei, kein Serverprozess, keine
  Konfiguration nötig.

---

## Projektstruktur (jede Datei erklärt)

```
SAAMai/
├── requirements.txt          # Alle Python-Abhängigkeiten (ausschließlich Open-Source)
├── .gitignore
├── data/                     # Laufzeitdaten: SQLite-DB & Uploads (nicht versioniert)
│   └── uploads/
│
├── backend/
│   └── app/
│       ├── main.py           # Einstiegspunkt: FastAPI-App, Router, Frontend-Auslieferung
│       ├── config.py         # Zentrale Konfiguration (per Umgebungsvariablen überschreibbar)
│       ├── database.py       # SQLAlchemy-Engine/Session (SQLite)
│       ├── models.py         # ORM-Modelle: User, Chat, Message, Attachment, Setting
│       ├── schemas.py        # Pydantic-Schemas (API-Ein-/Ausgabe)
│       ├── security.py       # Passwort-Hashing, JWT-Tokens, aktueller Benutzer
│       ├── i18n.py           # Lädt Übersetzungsdateien für die API
│       │
│       ├── routers/          # Ein Modul pro Ressource
│       │   ├── auth.py           # Registrierung/Login/„me"
│       │   ├── chats.py          # Chats erstellen/auflisten/suchen/exportieren/löschen
│       │   ├── messages.py       # Nachricht senden + Streaming-Antwort vom Modell
│       │   ├── documents.py      # Datei-Upload (PDF/Word/Text/Bild)
│       │   ├── settings.py       # Einstellungen (Sprache, Theme, ...)
│       │   ├── models.py         # Lokale Modelle auflisten/herunterladen (Ollama)
│       │   ├── plugins.py        # Aktive Plugins auflisten
│       │   └── i18n.py           # Sprachen/Übersetzungen abrufen
│       │
│       ├── services/         # Geschäftslogik, von Routern genutzt
│       │   ├── llm.py            # Ollama-Client (Chat-Streaming, Bildanalyse, Modell-Pull)
│       │   ├── documents.py      # Textextraktion aus PDF/Word/Text
│       │   ├── export.py         # Chat-Export nach Markdown/Text/JSON
│       │   └── plugin_loader.py  # Entdeckt & lädt Plugins automatisch
│       │
│       └── plugins/          # Drop-in-Plugins (eigene .py-Dateien hier ablegen)
│           └── example_plugin.py # Referenzimplementierung eines Plugins
│
│   └── tests/
│       ├── conftest.py       # Testkonfiguration (eigene Test-Datenbank)
│       └── test_api.py       # API-Tests (pytest)
│
├── frontend/
│   ├── index.html            # Einzelseiten-Chat-Oberfläche
│   ├── css/style.css         # Gesamtes Styling inkl. Dark/Light Mode
│   ├── js/
│   │   ├── api.js            # Kapselt alle Backend-Aufrufe
│   │   ├── i18n.js           # Übersetzungen anwenden
│   │   ├── voice.js          # Web-Speech-API (Spracheingabe/-ausgabe)
│   │   ├── chat.js           # Nachrichten rendern & senden (inkl. Streaming)
│   │   ├── settings.js       # Einstellungsdialog (Sprache, Theme, Modelle, Konto)
│   │   └── app.js            # Verbindet alles, initialisiert die App
│   └── locales/
│       ├── de.json           # Deutsche Übersetzungen
│       └── en.json           # Englische Übersetzungen
│
└── scripts/
    ├── setup.py               # Prüft/lädt Ollama-Modelle (plattformunabhängig)
    ├── setup.sh                # Setup + Start für Linux/macOS
    └── setup.bat                # Setup + Start für Windows
```

---

## Installation

### Voraussetzungen

- **Python 3.11+** (getestet mit 3.11/3.12)
- **[Ollama](https://ollama.com/download)** - kostenlos, Open-Source,
  verfügbar für Windows, macOS und Linux. Wird für die eigentliche
  KI-Inferenz benötigt.

### Schnellstart

#### Linux / macOS

```bash
git clone <dein-repo-url> SAAMai
cd SAAMai
./scripts/setup.sh
```

#### Windows

```bat
git clone <dein-repo-url> SAAMai
cd SAAMai
scripts\setup.bat
```

Diese Skripte:

1. erstellen eine virtuelle Python-Umgebung (`.venv`),
2. installieren alle Abhängigkeiten aus `requirements.txt`,
3. prüfen, ob Ollama installiert/gestartet ist, und laden automatisch die
   Standardmodelle (`llama3.1` für Text, `llava` für Bildanalyse) herunter,
4. starten den SAAMai-Server unter **http://127.0.0.1:8000**.

Öffne anschließend `http://127.0.0.1:8000` im Browser - fertig.

### Manuelle Installation

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Ollama separat installieren (https://ollama.com/download), dann:
ollama pull llama3.1
ollama pull llava

uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

---

## Benutzung

- **Neuer Chat**: Button oben links in der Seitenleiste.
- **Nachricht senden**: Text eingeben, `Enter` (bzw. Sende-Button).
  `Shift+Enter` für einen Zeilenumbruch.
- **Datei anhängen**: Büroklammer-Symbol - PDF, Word, Text oder Bild
  auswählen. Der Inhalt wird automatisch extrahiert und der KI als
  Kontext mitgegeben (Bilder gehen an ein Vision-Modell wie LLaVA).
- **Spracheingabe**: Mikrofon-Symbol (falls vom Browser unterstützt,
  z. B. Chrome/Edge).
- **Antwort vorlesen lassen**: „🔊 Vorlesen" unter jeder Antwort.
- **Suche**: Suchfeld in der Seitenleiste durchsucht Titel *und* Inhalt
  aller Chats.
- **Export**: Pfeil-Symbol im Chat-Header, Format wählen (md/txt/json).
- **Anheften**: Pin-Symbol hält wichtige Chats oben in der Liste.
- **Einstellungen**: Zahnrad in der Seitenleiste - Sprache, Theme,
  Modellverwaltung (weitere Modelle herunterladen), Plugin-Übersicht,
  optionales Benutzerkonto.

---

## Konfiguration

Alle Einstellungen lassen sich per Umgebungsvariable überschreiben (Präfix
`SAAMAI_`), z. B. in einer `.env`-Datei im Projektstamm:

| Variable                          | Standardwert                         | Bedeutung                                   |
|-----------------------------------|---------------------------------------|----------------------------------------------|
| `SAAMAI_DATABASE_URL`             | `sqlite:///data/saamai.db`            | Datenbankpfad                                |
| `SAAMAI_LLM_BASE_URL`             | `http://127.0.0.1:11434`              | Ollama- bzw. Modell-Server-Adresse            |
| `SAAMAI_DEFAULT_TEXT_MODEL`       | `llama3.1`                            | Standardmodell für Text-Chats                 |
| `SAAMAI_DEFAULT_VISION_MODEL`     | `llava`                               | Modell für Bildanalyse                        |
| `SAAMAI_SECRET_KEY`               | *(bitte ändern)*                      | Signaturschlüssel für Login-Sessions          |
| `SAAMAI_MAX_UPLOAD_MB`            | `25`                                  | Maximale Dateigröße für Uploads               |
| `SAAMAI_DEFAULT_LANGUAGE`         | `de`                                  | Standardsprache                               |

**Wichtig für den produktiven Einsatz**: Setze `SAAMAI_SECRET_KEY` auf
einen eigenen, zufälligen Wert, bevor du Benutzerkonten verwendest.

Ein anderes lokales, OpenAI-API-kompatibles Modell-Backend (z. B. LM
Studio, llama.cpp-Server) kann über `SAAMAI_LLM_BASE_URL` eingebunden
werden, ohne den Code zu ändern.

---

## Plugin-System & API für Erweiterungen

### Eigene Plugins schreiben

Lege eine neue Datei unter `backend/app/plugins/` an und leite eine
Klasse von `SAAMaiPlugin` ab (siehe
`backend/app/services/plugin_loader.py` und das mitgelieferte Beispiel
`backend/app/plugins/example_plugin.py`):

```python
from ..services.plugin_loader import SAAMaiPlugin, PluginContext

class MyPlugin(SAAMaiPlugin):
    name = "my-plugin"
    description = "Kurzbeschreibung"

    def before_prompt(self, text: str, context: PluginContext) -> str:
        # Nachricht vor dem Senden an das Modell verändern/prüfen
        return text

    def after_response(self, text: str, context: PluginContext) -> str:
        # Antwort des Modells vor dem Speichern verändern
        return text
```

Die Datei wird beim nächsten Serverstart automatisch erkannt und
geladen - keine Registrierung nötig.

### REST-API für externe Erweiterungen

SAAMai bietet eine vollständige, dokumentierte REST-API unter
`http://127.0.0.1:8000/docs` (automatisch generierte OpenAPI/Swagger-UI
von FastAPI). Wichtige Endpunkte:

| Endpunkt                                   | Methode | Zweck                              |
|---------------------------------------------|---------|-------------------------------------|
| `/api/chats`                                | GET/POST| Chats auflisten/erstellen           |
| `/api/chats/{id}`                           | GET     | Chat inkl. Nachrichten abrufen      |
| `/api/chats/{id}/messages/stream`           | POST    | Nachricht senden (Streaming-Antwort)|
| `/api/chats/{id}/export?format=md`          | GET     | Chat exportieren                    |
| `/api/documents/upload`                     | POST    | Datei hochladen & Text extrahieren  |
| `/api/models`                               | GET     | Installierte Modelle auflisten      |
| `/api/models/pull`                          | POST    | Modell herunterladen                |
| `/api/plugins`                              | GET     | Aktive Plugins auflisten            |

---

## Sicherheit

- Passwörter werden ausschließlich als **bcrypt-Hashes** gespeichert,
  niemals im Klartext.
- Sitzungen basieren auf **signierten JWTs** mit Ablaufzeit.
- Benutzerkonten sind **optional**: ohne Login wird ein einzelner
  lokaler Standardbenutzer verwendet, ideal für den Einzelplatzbetrieb.
- Datei-Uploads werden auf Typ und Größe geprüft, bevor sie verarbeitet
  werden.
- Es werden ausschließlich parametrisierte Datenbankabfragen (über
  SQLAlchemy) verwendet - keine manuell zusammengesetzten SQL-Strings.
- Es findet **keine Kommunikation mit externen/kostenpflichtigen
  Diensten** statt; alle Daten bleiben auf dem eigenen Gerät.

---

## Tests

```bash
source .venv/bin/activate
pytest backend/tests -v
```

Die Tests ersetzen den KI-Modell-Aufruf durch eine Fälschung (Mock), sie
benötigen also **keine laufende Ollama-Instanz**.

---

## Fehlerbehebung

**„SAAMai kann das lokale Modell nicht erreichen"**
→ Ollama ist nicht gestartet. Terminal öffnen und `ollama serve`
ausführen, dann die Seite neu laden.

**„Modell ist nicht installiert"**
→ In den Einstellungen unter „Lokale Modelle" den gewünschten
Modellnamen eingeben (z. B. `mistral`) und „Herunterladen" klicken,
oder im Terminal `ollama pull <modell>` ausführen.

**Spracheingabe-Button fehlt**
→ Der Browser unterstützt die Web Speech API nicht (z. B. Firefox).
Chrome, Edge oder ein Chromium-basierter Browser verwenden.

**Datenbank zurücksetzen**
→ SAAMai bei laufendem Server stoppen und `data/saamai.db` löschen; sie
wird beim nächsten Start automatisch neu angelegt.

---

## Lizenz

MIT - siehe [LICENSE](LICENSE). Frei nutzbar, veränderbar und
erweiterbar.
