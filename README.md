# 🎬 videopipe — Ein-Prompt-KI-Videopipeline (kostenlos)

Ein Prompt rein → fertiges kurzes Video raus. Die App zerlegt deinen Satz in
ein Storyboard, erzeugt Bilder, animiert sie, legt Untertitel und einen
lizenzfreien Musik-Bett darüber, fügt alles mit Übergängen zusammen und
speichert eine fertige `.mp4` — **ohne kostenpflichtige APIs**.

```bash
python run.py "Erstelle ein 20-sekündiges Werbevideo für eine Pizzeria im modernen, cineastischen Stil."
```

Ergebnis: `output/…​.mp4` + passende `.srt` (Untertitel) + `.json` (Metadaten),
und am Ende ein anklickbarer `file://`-Link.

---

## 1. Ist das technisch machbar? — Ja.

Der komplette Ablauf ist realisierbar. Der Trick ist eine **Provider-Architektur**:
jeder Schritt ist austauschbar. So läuft dieselbe Pipeline

* **komplett offline** (prozedurales Rendern, keine Internet­verbindung nötig) — genau
  so ist dieser Prototyp gebaut, damit er überall sofort läuft; **und**
* **mit kostenlosen Web-/Open-Source-Diensten** auf deinem eigenen PC, wenn du
  fotorealistische Bilder und echte Sprecherstimmen willst.

## 2. Kostenlose Tools pro Schritt (lokal vs. Web)

| Schritt | In diesem Prototyp (offline, 100 % gratis) | Kostenlose Upgrade-Option auf deinem PC |
|---|---|---|
| **Prompt → Storyboard** | Regel-/Template-Logik (`brain.py`) | Lokales LLM via **Ollama** (Llama 3, Mistral) · **Pollinations Text** (gratis, ohne Key) |
| **Bilder** | Prozedural mit **Pillow/numpy** (Verläufe, Glow, Grain, Motive) | **Pollinations** (`--images pollinations`, gratis ohne Key) · lokal **Stable Diffusion** (AUTOMATIC1111/ComfyUI, braucht GPU) |
| **Bild → Videoclip** | **Ken-Burns**-Effekt (Zoom/Schwenk) — voll lokal | **Stable Video Diffusion / AnimateDiff / CogVideoX** (lokal, GPU) |
| **Sprecherstimme (TTS)** | — (Prototyp nutzt Musik + Untertitel) | **Piper** (offline, sehr gut, `--tts piper`) · **gTTS** (gratis, online, `--tts gtts`) · **Coqui TTS** |
| **Untertitel** | Aus dem bekannten Skript erzeugt → echte `.srt` | **openai-whisper / faster-whisper** (Auto-Transkript, lokal) |
| **Musik** | Prozedural erzeugt → **per Konstruktion lizenzfrei** | **Free Music Archive**, **Pixabay Music**, **Incompetech** (CC) |
| **Zusammenschnitt** | **PyAV** (gebündeltes ffmpeg), H.264 + AAC, Crossfades | dasselbe — läuft überall gleich |

Alle Web-Optionen sind kostenlos/ohne Pflicht-Key nutzbar. **Wichtig:** Prüfe vor
kommerzieller Nutzung immer die AGB des jeweiligen Dienstes und die Lizenz der
Musik.

## 3. Was läuft wo?

* **Lokal (dein PC, keine Kosten):** die ganze Pipeline. Für Fotorealismus/echte
  Stimmen ideal: Stable Diffusion + Piper lokal → nichts verlässt deinen Rechner.
* **Kostenlose Webdienste:** Pollinations (Bild/Text) und gTTS (Stimme) — nur ein
  Flag umlegen, kein Account, kein Key.

## 4. Wie ist es automatisiert?

`run.py` → `videopipe/render.py` orchestriert die 6 Stufen vollautomatisch:

```
prompt ─▶ brain (Storyboard) ─▶ images (1 Still/Szene) ─▶ motion (Ken Burns)
       ─▶ subtitles (Overlay + .srt) ─▶ audio (Musik + optional TTS)
       ─▶ assemble (Crossfades + H.264/AAC-Mux) ─▶ fertige .mp4
```

Nur der eine Prompt ist Eingabe; alles andere läuft im Hintergrund.

## 5. Der Link / auf dem Handy öffnen

Nach jedem Lauf bekommst du:

* einen `file://`-Link im Terminal (sofort am PC anklickbar),
* die Datei in `output/` (leicht zugänglicher Ordner),
* eine `.json` mit dem absoluten Pfad (für Weiterverarbeitung/Automatisierung).

**Handy:** Da das Ergebnis eine Standard-`.mp4` (H.264/AAC, `+faststart`) ist,
lässt sie sich überall abspielen. Optionen, um sie aufs Handy zu bekommen:
lokalen Mini-Webserver starten (`python -m http.server` im `output/`-Ordner und
per WLAN-IP am Handy öffnen), in einen Cloud-Ordner (Drive/Nextcloud) legen, oder
in Claude Code direkt teilen. In dieser Umgebung wird die fertige Datei dir
direkt in der Oberfläche zum Öffnen/Download bereitgestellt.

## 6. Setup

```bash
pip install -r requirements.txt          # av, numpy, Pillow (Kern, offline)
python run.py "dein Prompt hier"
```

Optionen:

```bash
python run.py "…" --images pollinations   # fotorealistische Bilder (Internet)
python run.py "…" --tts gtts              # echte Sprecherstimme (Internet, gratis)
python run.py "…" --tts piper             # offline-Stimme (Piper-Binary + Modell)
python run.py "…" --no-music --seconds 15 # ohne Musik, 15s Ziel-Länge
```

## 7. Grenzen dieses MVP & Ausblick

* **Sandbox ohne Internet + ohne GPU** → Bilder sind bewusst *stilisiert*
  (kein Fotorealismus) und es gibt keine Sprecherstimme. Beides schaltest du auf
  deinem PC per Flag/Modell frei — die Pipeline bleibt identisch.
* Roadmap: echtes LLM-Storyboard, SVD-Animation, Whisper-Untertitel,
  Web-Oberfläche, Auto-Upload mit Sharing-Link.

## Projektstruktur

```
run.py                 # CLI-Einstieg
videopipe/
  config.py            # Einstellungen, Provider-Auswahl
  brain.py             # Prompt → Storyboard
  images.py            # Bilder: local (offline) / pollinations (online)
  motion.py            # Ken-Burns-Animation
  subtitles.py         # Text-Overlay + .srt
  audio.py             # Musik-Bett + TTS-Hook
  assemble.py          # PyAV: Crossfades + H.264/AAC-Mux
  render.py            # Orchestrator
docs/demo/             # Beispiel-Ausgabe
```
