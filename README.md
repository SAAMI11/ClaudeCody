# Bildgenerator

Eine einfache, handyfreundliche Web-App: Prompt eingeben, Bild generieren.
Nutzt den kostenlosen [Pollinations.ai](https://pollinations.ai)-Dienst direkt im Browser – kein API-Key, kein Server nötig.

## Auf dem Handy öffnen (kostenloses Deploy via Vercel)

1. Auf [vercel.com](https://vercel.com) mit deinem GitHub-Account einloggen.
2. "Add New Project" → dieses Repo auswählen.
3. Als Root Directory einfach `/` lassen, kein Build-Command nötig (reines statisches HTML).
4. Deploy klicken. Nach ein paar Sekunden bekommst du eine URL wie `https://dein-projekt.vercel.app`.
5. Diese URL auf dem Handy öffnen (z.B. zum Home-Bildschirm hinzufügen, dann wirkt's wie eine App).

## Lokal testen

Einfach `index.html` im Browser öffnen, oder z.B. mit:

```bash
python3 -m http.server 8000
```

und dann `http://localhost:8000` öffnen.
