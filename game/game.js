"use strict";
/* ============================================================================
   SKYDRIFT
   Ein eigenstaendiges 2D-Arcade-Geschicklichkeitsspiel.

   Spielprinzip: Die Spielfigur (ein kleiner "Gleiter") fliegt automatisch
   nach rechts durch eine Kristallschlucht. Der Spieler steuert nur die
   vertikale Bewegung und muss Barrieren-Paaren ausweichen.

   Der Code ist bewusst in klar getrennte "Module" (Klassen) gegliedert, auch
   wenn alles in einer Datei liegt. Das erlaubt, das Spiel per Doppelklick
   direkt aus dem Dateisystem (file://) zu starten, ohne dass ein Server oder
   ES-Module-Unterstuetzung noetig waeren.

   Module in dieser Datei:
     - Config              zentrale Spielkonstanten
     - StorageManager       persistente Daten (localStorage mit Fallback)
     - AudioManager          synthetisierte Soundeffekte (Web Audio API)
     - InputManager          Tastatur / Maus / Touch, vereinheitlicht
     - ParticleSystem        Partikel-Objekt-Pool
     - BackgroundManager      Parallax-Hintergrund (3 Ebenen)
     - Player                 Spielfigur inkl. Physik
     - Obstacle / ObstacleManager  Hindernis-Erzeugung und -Verwaltung
     - CollisionSystem        Kollisionspruefungen
     - UIManager               DOM-Overlays (Menue, Pause, Game Over, HUD)
     - calculateDifficulty     zentrale Schwierigkeitsfunktion
     - Game                    State-Machine + Game-Loop
   ============================================================================ */

/* ============================================================================
   CONFIG
   ============================================================================ */

const Config = Object.freeze({
  // Feste logische Spielaufloesung. Das Canvas wird per CSS/DPR auf die
  // tatsaechliche Bildschirmgroesse skaliert (Letterboxing), die Spiellogik
  // rechnet aber immer in diesen Einheiten -> Physik fuehlt sich auf jedem
  // Geraet gleich an.
  WIDTH: 480,
  HEIGHT: 800,
  GROUND_HEIGHT: 90,

  // Spielerphysik
  PLAYER_START_X: 140,
  PLAYER_WIDTH: 46,
  PLAYER_HEIGHT: 34,
  PLAYER_HITBOX_INSET_X: 9,
  PLAYER_HITBOX_INSET_Y: 7,
  GRAVITY_UP: 950, // px/s^2 waehrend des Aufstiegs (nach einem "Flap")
  GRAVITY_DOWN: 1500, // px/s^2 waehrend des Falls
  FLAP_STRENGTH: -430, // px/s, Geschwindigkeit unmittelbar nach einem Flap
  MAX_FALL_SPEED: 620, // px/s
  MAX_RISE_SPEED: -560, // px/s
  BOB_AMPLITUDE_X: 5, // kosmetische, leichte horizontale Bewegung
  MAX_ROTATION_UP: -0.5, // Radiant, beim Steigen
  MAX_ROTATION_DOWN: 1.15, // Radiant, beim Fallen
  ROTATION_LERP: 10, // wie schnell sich die Rotation annaehert (pro Sekunde)

  // Hindernisse
  OBSTACLE_WIDTH: 90,
  MIN_BARRIER_HEIGHT: 40,

  // Physik-Update: fester Zeitschritt fuer framerate-unabhaengiges Verhalten
  FIXED_TIMESTEP: 1 / 120,
  MAX_FRAME_TIME: 0.1, // Schutz gegen "Spiral of Death" bei Tab-Wechsel

  // localStorage keys
  STORAGE_PREFIX: "skydrift_",
});

const GameState = Object.freeze({
  MENU: "MENU",
  PLAYING: "PLAYING",
  PAUSED: "PAUSED",
  GAME_OVER: "GAME_OVER",
});

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function rectsOverlap(a, b) {
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}

/* ============================================================================
   calculateDifficulty
   Zentrale Funktion, die anhand des aktuellen Scores alle schwierigkeits-
   relevanten Werte berechnet. Die Werte naehern sich asymptotisch einem
   Maximum an (Deckelung ueber "t"), damit das Spiel niemals unfair wird.
   ============================================================================ */

function calculateDifficulty(score) {
  const t = clamp(score / 40, 0, 1); // Schwierigkeit erreicht bei Score 40 ihr Maximum

  const obstacleSpeed = lerp(220, 340, t); // px/s, Bewegungsgeschwindigkeit der Hindernisse
  const gapSize = lerp(260, 178, t); // px, Groesse der Durchflug-Luecke (nie kleiner als 178)
  const spawnIntervalMs = lerp(1550, 1080, t); // ms zwischen neuen Hindernispaaren
  const gapShiftRange = lerp(85, 165, t); // max. Verschiebung der Luecken-Mitte zum Vorgaenger

  return {
    obstacleSpeed,
    gapSize,
    spawnIntervalMs,
    gapShiftRange,
    difficultyFactor: t,
  };
}

/* ============================================================================
   StorageManager
   Kapselt localStorage-Zugriffe. Faellt bei fehlender Verfuegbarkeit
   (Privatmodus, deaktiviert, o.ae.) auf einen In-Memory-Speicher zurueck,
   damit das Spiel in jedem Fall spielbar bleibt.
   ============================================================================ */

class StorageManager {
  constructor() {
    this.available = this._testAvailability();
    this.memoryFallback = {};
  }

  _testAvailability() {
    try {
      const testKey = Config.STORAGE_PREFIX + "__test__";
      window.localStorage.setItem(testKey, "1");
      window.localStorage.removeItem(testKey);
      return true;
    } catch (err) {
      return false;
    }
  }

  _key(name) {
    return Config.STORAGE_PREFIX + name;
  }

  get(name, fallback) {
    if (!this.available) {
      return name in this.memoryFallback ? this.memoryFallback[name] : fallback;
    }
    try {
      const raw = window.localStorage.getItem(this._key(name));
      if (raw === null) return fallback;
      return JSON.parse(raw);
    } catch (err) {
      return fallback;
    }
  }

  set(name, value) {
    if (!this.available) {
      this.memoryFallback[name] = value;
      return;
    }
    try {
      window.localStorage.setItem(this._key(name), JSON.stringify(value));
    } catch (err) {
      // Speicher voll oder blockiert -> im Speicher weiterlaufen lassen
      this.available = false;
      this.memoryFallback[name] = value;
    }
  }

  getHighScore() {
    return this.get("highScore", 0);
  }

  getRoundsPlayed() {
    return this.get("roundsPlayed", 0);
  }

  getLongestSurvivalMs() {
    return this.get("longestSurvivalMs", 0);
  }

  getMuted() {
    return this.get("muted", false);
  }

  setMuted(muted) {
    this.set("muted", muted);
  }
}

/* ============================================================================
   AudioManager
   Synthetisiert alle Soundeffekte zur Laufzeit ueber die Web Audio API.
   Dadurch werden keinerlei externe Audiodateien benoetigt. Audio wird erst
   nach der ersten Nutzerinteraktion aktiviert (Autoplay-Policy der Browser).
   ============================================================================ */

class AudioManager {
  constructor(storageManager) {
    this.storage = storageManager;
    this.ctx = null;
    this.muted = this.storage.getMuted();
    this.unlocked = false;
  }

  unlock() {
    if (this.unlocked) return;
    this.unlocked = true;
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      this.ctx = new AudioCtx();
      if (this.ctx.state === "suspended") {
        this.ctx.resume().catch(() => {});
      }
    } catch (err) {
      this.ctx = null;
    }
  }

  toggleMute() {
    this.muted = !this.muted;
    this.storage.setMuted(this.muted);
    return this.muted;
  }

  _tone({ freqStart, freqEnd, duration, type = "sine", gainPeak = 0.18, delay = 0 }) {
    if (this.muted || !this.ctx) return;
    try {
      const now = this.ctx.currentTime + delay;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = type;
      osc.frequency.setValueAtTime(freqStart, now);
      if (freqEnd !== undefined) {
        osc.frequency.exponentialRampToValueAtTime(Math.max(freqEnd, 1), now + duration);
      }
      gain.gain.setValueAtTime(0, now);
      gain.gain.linearRampToValueAtTime(gainPeak, now + 0.015);
      gain.gain.exponentialRampToValueAtTime(0.001, now + duration);
      osc.connect(gain).connect(this.ctx.destination);
      osc.start(now);
      osc.stop(now + duration + 0.02);
    } catch (err) {
      // Audio-Fehler duerfen das Spiel niemals unterbrechen
    }
  }

  jump() {
    this._tone({ freqStart: 420, freqEnd: 780, duration: 0.14, type: "triangle", gainPeak: 0.14 });
  }

  score() {
    this._tone({ freqStart: 660, freqEnd: 990, duration: 0.12, type: "sine", gainPeak: 0.16 });
    this._tone({ freqStart: 990, freqEnd: 1320, duration: 0.14, type: "sine", gainPeak: 0.12, delay: 0.07 });
  }

  collision() {
    if (this.muted || !this.ctx) return;
    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "sawtooth";
      osc.frequency.setValueAtTime(220, now);
      osc.frequency.exponentialRampToValueAtTime(40, now + 0.35);
      gain.gain.setValueAtTime(0.22, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      osc.connect(gain).connect(this.ctx.destination);
      osc.start(now);
      osc.stop(now + 0.4);
    } catch (err) {
      /* ignore */
    }
  }

  highscore() {
    [523, 659, 784, 1046].forEach((freq, i) => {
      this._tone({ freqStart: freq, freqEnd: freq, duration: 0.18, type: "square", gainPeak: 0.1, delay: i * 0.09 });
    });
  }

  click() {
    this._tone({ freqStart: 300, freqEnd: 300, duration: 0.05, type: "square", gainPeak: 0.08 });
  }
}

/* ============================================================================
   InputManager
   Vereinheitlicht Tastatur-, Maus- und Touch-Eingaben ueber die Pointer-
   Events-API (verhindert doppelt ausgeloeste Events durch Touch+Mouse).
   Listener werden genau einmal registriert.
   ============================================================================ */

class InputManager {
  constructor(targetElement) {
    this.target = targetElement;
    this.onFlap = null;
    this.onPauseToggle = null;
    this.onDebugToggle = null;
    this._lastPointerTime = 0;

    this._handleKeyDown = this._handleKeyDown.bind(this);
    this._handlePointerDown = this._handlePointerDown.bind(this);

    window.addEventListener("keydown", this._handleKeyDown);
    this.target.addEventListener("pointerdown", this._handlePointerDown, { passive: false });
  }

  _handleKeyDown(e) {
    if (e.code === "Space" || e.code === "ArrowUp") {
      e.preventDefault();
      if (this.onFlap) this.onFlap();
    } else if (e.code === "KeyP" || e.code === "Escape") {
      if (this.onPauseToggle) this.onPauseToggle();
    } else if (e.code === "KeyD") {
      if (this.onDebugToggle) this.onDebugToggle();
    }
  }

  _handlePointerDown(e) {
    // Schutz gegen mehrfach ausgeloeste Events (z.B. schnelle Doppel-Taps)
    const now = performance.now();
    if (now - this._lastPointerTime < 16) return;
    this._lastPointerTime = now;

    e.preventDefault();
    if (this.onFlap) this.onFlap();
  }
}

/* ============================================================================
   ParticleSystem
   Objekt-Pool fuer Partikel (Sprung-Trail, Kollisions-Explosion), um
   Garbage-Collection-Ruckler durch staendig neue Objekte zu vermeiden.
   ============================================================================ */

class ParticleSystem {
  constructor(poolSize = 220) {
    this.pool = new Array(poolSize);
    for (let i = 0; i < poolSize; i++) {
      this.pool[i] = { active: false, x: 0, y: 0, vx: 0, vy: 0, life: 0, maxLife: 1, size: 2, color: "#4fd6ff" };
    }
  }

  _spawnOne(x, y, vx, vy, life, size, color) {
    for (let i = 0; i < this.pool.length; i++) {
      const p = this.pool[i];
      if (!p.active) {
        p.active = true;
        p.x = x;
        p.y = y;
        p.vx = vx;
        p.vy = vy;
        p.life = life;
        p.maxLife = life;
        p.size = size;
        p.color = color;
        return;
      }
    }
    // Pool erschoepft -> Partikel wird einfach ausgelassen (kein unbegrenztes Wachstum)
  }

  burstJump(x, y) {
    for (let i = 0; i < 7; i++) {
      const angle = Math.PI + (Math.random() - 0.5) * 1.2;
      const speed = 60 + Math.random() * 80;
      this._spawnOne(x, y, Math.cos(angle) * speed, Math.sin(angle) * speed - 20, 0.35 + Math.random() * 0.2, 2 + Math.random() * 2, "#4fd6ff");
    }
  }

  burstCollision(x, y) {
    for (let i = 0; i < 34; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = 90 + Math.random() * 220;
      const color = Math.random() > 0.5 ? "#ff5470" : "#ffb545";
      this._spawnOne(x, y, Math.cos(angle) * speed, Math.sin(angle) * speed, 0.4 + Math.random() * 0.5, 2 + Math.random() * 3, color);
    }
  }

  update(dt) {
    for (let i = 0; i < this.pool.length; i++) {
      const p = this.pool[i];
      if (!p.active) continue;
      p.life -= dt;
      if (p.life <= 0) {
        p.active = false;
        continue;
      }
      p.vy += 380 * dt; // leichte Schwerkraft auf Partikel
      p.x += p.vx * dt;
      p.y += p.vy * dt;
    }
  }

  render(ctx) {
    for (let i = 0; i < this.pool.length; i++) {
      const p = this.pool[i];
      if (!p.active) continue;
      const alpha = clamp(p.life / p.maxLife, 0, 1);
      ctx.globalAlpha = alpha;
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  reset() {
    for (let i = 0; i < this.pool.length; i++) this.pool[i].active = false;
  }
}

/* ============================================================================
   BackgroundManager
   Drei Parallax-Ebenen (ferne Wolken, mittlere Landschaft, Vordergrund/Boden)
   mit unterschiedlicher Scrollgeschwindigkeit, nahtlos gekachelt.
   ============================================================================ */

class BackgroundManager {
  constructor() {
    this.scrollFar = 0;
    this.scrollMid = 0;
    this.scrollNear = 0;

    // Deterministische "Zufalls"-Layouts pro Ebene (feste Seeds -> stabile Optik)
    this.cloudTileWidth = 260;
    this.clouds = this._generateClouds();

    this.hillTileWidth = 320;
    this.hills = this._generateHills();
  }

  _generateClouds() {
    const clouds = [];
    for (let i = 0; i < 4; i++) {
      clouds.push({
        offsetX: i * 65 + Math.random() * 20,
        y: 60 + Math.random() * 140,
        scale: 0.6 + Math.random() * 0.8,
      });
    }
    return clouds;
  }

  _generateHills() {
    const hills = [];
    for (let i = 0; i < 3; i++) {
      hills.push({
        offsetX: i * 110,
        height: 70 + Math.random() * 60,
        width: 160 + Math.random() * 80,
      });
    }
    return hills;
  }

  update(dt, speedPxPerSec) {
    this.scrollFar = (this.scrollFar + speedPxPerSec * 0.15 * dt) % this.cloudTileWidth;
    this.scrollMid = (this.scrollMid + speedPxPerSec * 0.42 * dt) % this.hillTileWidth;
    this.scrollNear = (this.scrollNear + speedPxPerSec * 0.9 * dt) % 40;
  }

  render(ctx) {
    const w = Config.WIDTH;
    const h = Config.HEIGHT;
    const groundY = h - Config.GROUND_HEIGHT;

    // Himmel-Gradient
    const sky = ctx.createLinearGradient(0, 0, 0, groundY);
    sky.addColorStop(0, "#0a0e1c");
    sky.addColorStop(0.55, "#141c33");
    sky.addColorStop(1, "#1c2947");
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, w, groundY);

    // Ebene 1: ferne Wolken
    ctx.save();
    ctx.globalAlpha = 0.5;
    ctx.fillStyle = "#3a4a72";
    for (let tile = -1; tile <= Math.ceil(w / this.cloudTileWidth) + 1; tile++) {
      const baseX = tile * this.cloudTileWidth - this.scrollFar;
      for (const cloud of this.clouds) {
        drawCloud(ctx, baseX + cloud.offsetX, cloud.y, cloud.scale);
      }
    }
    ctx.restore();

    // Ebene 2: mittlere Landschaft (Huegel-Silhouette)
    ctx.save();
    ctx.fillStyle = "#202c4a";
    for (let tile = -1; tile <= Math.ceil(w / this.hillTileWidth) + 1; tile++) {
      const baseX = tile * this.hillTileWidth - this.scrollMid;
      for (const hill of this.hills) {
        drawHill(ctx, baseX + hill.offsetX, groundY, hill.width, hill.height);
      }
    }
    ctx.restore();

    // Ebene 3: Vordergrund / Boden
    ctx.fillStyle = "#161d2e";
    ctx.fillRect(0, groundY, w, Config.GROUND_HEIGHT);
    ctx.fillStyle = "#232f4d";
    ctx.fillRect(0, groundY, w, 6);

    // Bodentextur (kleine Kacheln, nahtlos)
    ctx.fillStyle = "#2b3a5e";
    const tileSize = 40;
    for (let x = -tileSize; x <= w + tileSize; x += tileSize) {
      const drawX = x - this.scrollNear;
      ctx.beginPath();
      ctx.moveTo(drawX, groundY + 6);
      ctx.lineTo(drawX + tileSize / 2, groundY + 18);
      ctx.lineTo(drawX + tileSize, groundY + 6);
      ctx.closePath();
      ctx.fill();
    }
  }
}

function drawCloud(ctx, x, y, scale) {
  ctx.beginPath();
  ctx.ellipse(x, y, 34 * scale, 14 * scale, 0, 0, Math.PI * 2);
  ctx.ellipse(x + 20 * scale, y + 4 * scale, 22 * scale, 11 * scale, 0, 0, Math.PI * 2);
  ctx.ellipse(x - 18 * scale, y + 5 * scale, 20 * scale, 10 * scale, 0, 0, Math.PI * 2);
  ctx.fill();
}

function drawHill(ctx, x, groundY, width, height) {
  ctx.beginPath();
  ctx.moveTo(x - width / 2, groundY);
  ctx.quadraticCurveTo(x, groundY - height, x + width / 2, groundY);
  ctx.closePath();
  ctx.fill();
}

/* ============================================================================
   Player
   Die Spielfigur: Ein kleiner, eigens entworfener "Gleiter" ohne jeglichen
   Bezug zu bestehenden Spielfiguren. Enthaelt die vertikale Physik.
   ============================================================================ */

class Player {
  constructor() {
    this.reset();
  }

  reset() {
    this.x = Config.PLAYER_START_X;
    this.y = Config.HEIGHT / 2;
    this.velocityY = 0;
    this.rotation = 0;
    this.bobPhase = Math.random() * Math.PI * 2;
    this.alive = true;
  }

  get drawX() {
    return this.x + Math.sin(this.bobPhase) * Config.BOB_AMPLITUDE_X;
  }

  flap() {
    this.velocityY = Config.FLAP_STRENGTH;
  }

  /** Physik-Update mit festem Zeitschritt (siehe Game._fixedUpdate). */
  updatePhysics(dt) {
    const gravity = this.velocityY < 0 ? Config.GRAVITY_UP : Config.GRAVITY_DOWN;
    this.velocityY += gravity * dt;
    this.velocityY = clamp(this.velocityY, Config.MAX_RISE_SPEED, Config.MAX_FALL_SPEED);
    this.y += this.velocityY * dt;

    this.bobPhase += dt * 2.4;

    const targetRotation =
      this.velocityY < 0
        ? lerp(0, Config.MAX_ROTATION_UP, clamp(this.velocityY / Config.MAX_RISE_SPEED, 0, 1))
        : lerp(0, Config.MAX_ROTATION_DOWN, clamp(this.velocityY / Config.MAX_FALL_SPEED, 0, 1));
    const lerpAmount = clamp(Config.ROTATION_LERP * dt, 0, 1);
    this.rotation = lerp(this.rotation, targetRotation, lerpAmount);
  }

  /** Sanfte Idle-Animation fuer den Menue-Zustand (keine echte Physik). */
  updateIdle(dt, time) {
    this.bobPhase += dt * 2.4;
    this.y = Config.HEIGHT / 2 + Math.sin(time * 1.6) * 22;
    this.rotation = Math.sin(time * 1.6) * 0.18;
  }

  getHitbox() {
    return {
      x: this.drawX - Config.PLAYER_WIDTH / 2 + Config.PLAYER_HITBOX_INSET_X,
      y: this.y - Config.PLAYER_HEIGHT / 2 + Config.PLAYER_HITBOX_INSET_Y,
      w: Config.PLAYER_WIDTH - Config.PLAYER_HITBOX_INSET_X * 2,
      h: Config.PLAYER_HEIGHT - Config.PLAYER_HITBOX_INSET_Y * 2,
    };
  }

  render(ctx, thrusting) {
    ctx.save();
    ctx.translate(this.drawX, this.y);
    ctx.rotate(this.rotation);

    const w = Config.PLAYER_WIDTH;
    const h = Config.PLAYER_HEIGHT;

    // Koerper: stilisierter Gleiter (eigene, geometrische Form)
    const bodyGradient = ctx.createLinearGradient(-w / 2, 0, w / 2, 0);
    bodyGradient.addColorStop(0, "#a855f7");
    bodyGradient.addColorStop(1, "#4fd6ff");
    ctx.fillStyle = bodyGradient;

    ctx.beginPath();
    ctx.moveTo(w / 2, 0);
    ctx.quadraticCurveTo(w / 6, -h / 2, -w / 2, -h / 4);
    ctx.quadraticCurveTo(-w / 3, 0, -w / 2, h / 4);
    ctx.quadraticCurveTo(w / 6, h / 2, w / 2, 0);
    ctx.closePath();
    ctx.fill();

    // Leuchtender Kern
    ctx.fillStyle = "rgba(255,255,255,0.85)";
    ctx.beginPath();
    ctx.arc(2, 0, 4.5, 0, Math.PI * 2);
    ctx.fill();

    // Heckflosse
    ctx.fillStyle = "#22c9ff";
    ctx.beginPath();
    ctx.moveTo(-w / 2, -2);
    ctx.lineTo(-w / 2 - 10, 0);
    ctx.lineTo(-w / 2, 6);
    ctx.closePath();
    ctx.fill();

    // Triebwerksglühen beim Steigen
    if (thrusting) {
      ctx.fillStyle = "rgba(79, 214, 255, 0.55)";
      ctx.beginPath();
      ctx.ellipse(-w / 2 - 6, 2, 8, 4, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.restore();
  }

  renderHitboxDebug(ctx) {
    const box = this.getHitbox();
    ctx.strokeStyle = "#00ff88";
    ctx.lineWidth = 1;
    ctx.strokeRect(box.x, box.y, box.w, box.h);
  }
}

/* ============================================================================
   Obstacle
   Ein Hindernispaar: eine obere und eine untere "Kristallbarriere" mit einer
   Luecke dazwischen.
   ============================================================================ */

class Obstacle {
  constructor(x, gapCenter, gapSize) {
    this.x = x;
    this.gapCenter = gapCenter;
    this.gapSize = gapSize;
    this.passed = false;
  }

  get topHeight() {
    return this.gapCenter - this.gapSize / 2;
  }

  get bottomY() {
    return this.gapCenter + this.gapSize / 2;
  }

  get playableHeight() {
    return Config.HEIGHT - Config.GROUND_HEIGHT;
  }

  getTopRect() {
    return { x: this.x, y: 0, w: Config.OBSTACLE_WIDTH, h: Math.max(this.topHeight, 0) };
  }

  getBottomRect() {
    const bottomY = this.bottomY;
    return { x: this.x, y: bottomY, w: Config.OBSTACLE_WIDTH, h: Math.max(this.playableHeight - bottomY, 0) };
  }

  update(dt, speed) {
    this.x -= speed * dt;
  }

  isOffScreen() {
    return this.x + Config.OBSTACLE_WIDTH < -10;
  }

  render(ctx) {
    const top = this.getTopRect();
    const bottom = this.getBottomRect();

    drawCrystalBarrier(ctx, top.x, top.y, top.w, top.h, true);
    drawCrystalBarrier(ctx, bottom.x, bottom.y, bottom.w, bottom.h, false);
  }

  renderHitboxDebug(ctx) {
    ctx.strokeStyle = "#ff5470";
    ctx.lineWidth = 1;
    const top = this.getTopRect();
    const bottom = this.getBottomRect();
    ctx.strokeRect(top.x, top.y, top.w, top.h);
    ctx.strokeRect(bottom.x, bottom.y, bottom.w, bottom.h);
  }
}

function drawCrystalBarrier(ctx, x, y, w, h, facingDown) {
  if (h <= 0) return;
  const gradient = ctx.createLinearGradient(x, y, x + w, y);
  gradient.addColorStop(0, "#2c3f6b");
  gradient.addColorStop(0.5, "#3f5a94");
  gradient.addColorStop(1, "#2c3f6b");
  ctx.fillStyle = gradient;
  ctx.fillRect(x, y, w, h);

  // Kristallspitze am Luecken-zugewandten Ende
  const capHeight = 18;
  ctx.fillStyle = "#5fd0ff";
  ctx.beginPath();
  if (facingDown) {
    ctx.moveTo(x, y + h);
    ctx.lineTo(x + w / 2, y + h + capHeight);
    ctx.lineTo(x + w, y + h);
  } else {
    ctx.moveTo(x, y);
    ctx.lineTo(x + w / 2, y - capHeight);
    ctx.lineTo(x + w, y);
  }
  ctx.closePath();
  ctx.fill();

  // Dezente Facetten-Linien
  ctx.strokeStyle = "rgba(255,255,255,0.12)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x + w * 0.35, y);
  ctx.lineTo(x + w * 0.35, y + h);
  ctx.stroke();
}

/* ============================================================================
   ObstacleManager
   Erzeugt, bewegt und entfernt Hindernispaare. Sorgt fuer faire, aber
   ansteigende Schwierigkeit ueber calculateDifficulty().
   ============================================================================ */

class ObstacleManager {
  constructor() {
    this.reset();
  }

  reset() {
    this.obstacles = [];
    this.spawnTimerMs = 0;
    this.lastGapCenter = (Config.HEIGHT - Config.GROUND_HEIGHT) / 2;
    // Erstes Hindernis erscheint erst nach einer kurzen "Einlaufzeit"
    this.initialDelayMs = 1100;
  }

  _validGapRange(gapSize) {
    const playableHeight = Config.HEIGHT - Config.GROUND_HEIGHT;
    const min = gapSize / 2 + Config.MIN_BARRIER_HEIGHT;
    const max = playableHeight - gapSize / 2 - Config.MIN_BARRIER_HEIGHT;
    return { min, max: Math.max(max, min) };
  }

  _spawn(score) {
    const difficulty = calculateDifficulty(score);
    const { min, max } = this._validGapRange(difficulty.gapSize);

    // Faire Positionierung: die neue Luecke darf nur begrenzt von der letzten
    // abweichen, damit kein zwangslaeufig unschaffbarer Sprung entsteht.
    const desired = this.lastGapCenter + (Math.random() * 2 - 1) * difficulty.gapShiftRange;
    const gapCenter = clamp(desired, min, max);

    this.lastGapCenter = gapCenter;
    this.obstacles.push(new Obstacle(Config.WIDTH + 20, gapCenter, difficulty.gapSize));
  }

  update(dt, score, onScored) {
    const difficulty = calculateDifficulty(score);

    if (this.initialDelayMs > 0) {
      this.initialDelayMs -= dt * 1000;
    } else {
      this.spawnTimerMs += dt * 1000;
      if (this.spawnTimerMs >= difficulty.spawnIntervalMs) {
        this.spawnTimerMs -= difficulty.spawnIntervalMs;
        this._spawn(score);
      }
    }

    for (const obstacle of this.obstacles) {
      obstacle.update(dt, difficulty.obstacleSpeed);
      if (!obstacle.passed && obstacle.x + Config.OBSTACLE_WIDTH < Config.PLAYER_START_X) {
        obstacle.passed = true;
        if (onScored) onScored();
      }
    }

    this.obstacles = this.obstacles.filter((o) => !o.isOffScreen());
  }

  render(ctx) {
    for (const obstacle of this.obstacles) obstacle.render(ctx);
  }

  renderHitboxDebug(ctx) {
    for (const obstacle of this.obstacles) obstacle.renderHitboxDebug(ctx);
  }
}

/* ============================================================================
   CollisionSystem
   Statische Hilfsfunktionen fuer alle relevanten Kollisionspruefungen.
   ============================================================================ */

class CollisionSystem {
  static checkPlayerVsObstacles(player, obstacleManager) {
    const hitbox = player.getHitbox();
    for (const obstacle of obstacleManager.obstacles) {
      if (rectsOverlap(hitbox, obstacle.getTopRect())) return true;
      if (rectsOverlap(hitbox, obstacle.getBottomRect())) return true;
    }
    return false;
  }

  static checkGround(player) {
    const hitbox = player.getHitbox();
    return hitbox.y + hitbox.h >= Config.HEIGHT - Config.GROUND_HEIGHT;
  }

  static checkCeiling(player) {
    const hitbox = player.getHitbox();
    return hitbox.y <= 0;
  }
}

/* ============================================================================
   UIManager
   Steuert alle DOM-Overlays (Menue, Pause, Game Over, HUD, Debug, Dev-Panel).
   Event-Listener werden ausschliesslich im Konstruktor einmalig registriert.
   ============================================================================ */

class UIManager {
  constructor(devMode) {
    this.devMode = devMode;

    this.el = {
      hud: document.getElementById("hud"),
      score: document.getElementById("score-display"),
      pauseBtn: document.getElementById("pause-btn"),

      menu: document.getElementById("screen-menu"),
      startBtn: document.getElementById("start-btn"),
      menuHighscore: document.getElementById("menu-highscore"),
      menuRounds: document.getElementById("menu-rounds"),
      menuBestTime: document.getElementById("menu-besttime"),
      muteBtnMenu: document.getElementById("mute-btn-menu"),

      pause: document.getElementById("screen-pause"),
      resumeBtn: document.getElementById("resume-btn"),
      restartBtnPause: document.getElementById("restart-btn-pause"),
      menuBtnPause: document.getElementById("menu-btn-pause"),

      gameOver: document.getElementById("screen-gameover"),
      gameOverScore: document.getElementById("gameover-score"),
      gameOverHighscore: document.getElementById("gameover-highscore"),
      newHighscoreBadge: document.getElementById("new-highscore-badge"),
      restartBtnGameOver: document.getElementById("restart-btn-gameover"),
      menuBtnGameOver: document.getElementById("menu-btn-gameover"),

      debugPanel: document.getElementById("debug-panel"),
      devPanel: document.getElementById("dev-panel"),
      wrapper: document.getElementById("game-wrapper"),
    };

    this._screens = [this.el.menu, this.el.pause, this.el.gameOver];
  }

  bindActions(actions) {
    // actions: { onStart, onResume, onRestart, onGoToMenu, onPauseToggle, onMuteToggle }
    this.el.startBtn.addEventListener("click", actions.onStart);
    this.el.resumeBtn.addEventListener("click", actions.onResume);
    this.el.restartBtnPause.addEventListener("click", actions.onRestart);
    this.el.menuBtnPause.addEventListener("click", actions.onGoToMenu);
    this.el.restartBtnGameOver.addEventListener("click", actions.onRestart);
    this.el.menuBtnGameOver.addEventListener("click", actions.onGoToMenu);
    this.el.pauseBtn.addEventListener("click", actions.onPauseToggle);
    this.el.muteBtnMenu.addEventListener("click", actions.onMuteToggle);
  }

  showScreen(name) {
    for (const screen of this._screens) screen.classList.add("hidden");
    if (name === "menu") this.el.menu.classList.remove("hidden");
    if (name === "pause") this.el.pause.classList.remove("hidden");
    if (name === "gameover") this.el.gameOver.classList.remove("hidden");
  }

  setHudVisible(visible) {
    this.el.hud.classList.toggle("hidden", !visible);
  }

  updateScore(score) {
    this.el.score.textContent = String(score);
  }

  updateMuteIcon(muted) {
    this.el.muteBtnMenu.textContent = muted ? "🔇" : "🔊";
  }

  updateMenuStats(highScore, roundsPlayed, longestSurvivalMs) {
    this.el.menuHighscore.textContent = String(highScore);
    this.el.menuRounds.textContent = String(roundsPlayed);
    this.el.menuBestTime.textContent = (longestSurvivalMs / 1000).toFixed(1) + "s";
  }

  updateGameOver(score, highScore, isNewHighscore) {
    this.el.gameOverScore.textContent = String(score);
    this.el.gameOverHighscore.textContent = String(highScore);
    this.el.newHighscoreBadge.classList.toggle("hidden", !isNewHighscore);
  }

  triggerShake() {
    this.el.wrapper.classList.remove("shake");
    // Reflow erzwingen, damit die Animation bei erneutem Trigger neu startet
    void this.el.wrapper.offsetWidth;
    this.el.wrapper.classList.add("shake");
  }

  setDebugVisible(visible) {
    this.el.debugPanel.classList.toggle("hidden", !visible);
  }

  updateDebug(text) {
    this.el.debugPanel.textContent = text;
  }

  setDevPanelVisible(visible) {
    this.el.devPanel.classList.toggle("hidden", !visible);
  }

  buildDevPanel(game) {
    if (!this.devMode) return;
    const panel = this.el.devPanel;
    panel.innerHTML = "";

    const title = document.createElement("h3");
    title.textContent = "Entwickler-Testmodus";
    panel.appendChild(title);

    const invincibleLabel = document.createElement("label");
    const invincibleCheckbox = document.createElement("input");
    invincibleCheckbox.type = "checkbox";
    invincibleCheckbox.addEventListener("change", () => {
      game.devInvincible = invincibleCheckbox.checked;
    });
    invincibleLabel.textContent = "Unverwundbarkeit ";
    invincibleLabel.appendChild(invincibleCheckbox);
    panel.appendChild(invincibleLabel);

    const speedLabel = document.createElement("label");
    const speedText = document.createElement("span");
    speedText.textContent = "Geschwindigkeit x1.0";
    const speedSlider = document.createElement("input");
    speedSlider.type = "range";
    speedSlider.min = "0.2";
    speedSlider.max = "3";
    speedSlider.step = "0.1";
    speedSlider.value = "1";
    speedSlider.addEventListener("input", () => {
      game.devSpeedMultiplier = parseFloat(speedSlider.value);
      speedText.textContent = "Geschwindigkeit x" + speedSlider.value;
    });
    speedLabel.appendChild(speedText);
    speedLabel.appendChild(speedSlider);
    panel.appendChild(speedLabel);

    const addScoreBtn = document.createElement("button");
    addScoreBtn.textContent = "+10 Score";
    addScoreBtn.addEventListener("click", () => game.devAddScore(10));
    panel.appendChild(addScoreBtn);

    const regenBtn = document.createElement("button");
    regenBtn.textContent = "Hindernisse neu generieren";
    regenBtn.addEventListener("click", () => game.devRegenerateObstacles());
    panel.appendChild(regenBtn);

    this.setDevPanelVisible(true);
  }
}

/* ============================================================================
   Game
   Zentrale State-Machine + Game-Loop. Verbindet alle Module.
   ============================================================================ */

class Game {
  constructor() {
    this.canvas = document.getElementById("game-canvas");
    this.ctx = this.canvas.getContext("2d");
    this.wrapper = document.getElementById("game-wrapper");

    this.storage = new StorageManager();
    this.audio = new AudioManager(this.storage);
    this.input = new InputManager(this.canvas);
    this.particles = new ParticleSystem();
    this.background = new BackgroundManager();
    this.player = new Player();
    this.obstacles = new ObstacleManager();

    const devMode = new URLSearchParams(window.location.search).get("dev") === "1";
    this.ui = new UIManager(devMode);

    this.state = GameState.MENU;
    this.score = 0;
    this.survivalMs = 0;
    this.time = 0;
    this.debugEnabled = false;

    // Dev-/Cheat-Werkzeuge: nur relevant, wenn devMode aktiv ist. Standard-
    // Spielverhalten bleibt davon vollstaendig unberuehrt.
    this.devInvincible = false;
    this.devSpeedMultiplier = 1;

    this.shakeFramesLeft = 0;
    this._accumulator = 0;
    this._lastTimestamp = null;
    this._fpsHistory = [];

    this._setupInput();
    this._setupUI();
    this._setupResize();
    this._setupVisibility();

    if (devMode) this.ui.buildDevPanel(this);

    this._refreshMenuStats();
    this.ui.updateMuteIcon(this.audio.muted);

    requestAnimationFrame(this._loop.bind(this));
  }

  /* ---------------- Setup ---------------- */

  _setupInput() {
    this.input.onFlap = () => {
      this.audio.unlock();
      if (this.state === GameState.PLAYING) {
        this.player.flap();
        this.particles.burstJump(this.player.drawX - Config.PLAYER_WIDTH / 2, this.player.y);
        this.audio.jump();
      } else if (this.state === GameState.MENU) {
        this._startGame();
      }
    };
    this.input.onPauseToggle = () => {
      if (this.state === GameState.PLAYING) this._pauseGame();
      else if (this.state === GameState.PAUSED) this._resumeGame();
    };
    this.input.onDebugToggle = () => {
      this.debugEnabled = !this.debugEnabled;
      this.ui.setDebugVisible(this.debugEnabled);
    };
  }

  _setupUI() {
    this.ui.bindActions({
      onStart: () => {
        this.audio.unlock();
        this.audio.click();
        this._startGame();
      },
      onResume: () => {
        this.audio.click();
        this._resumeGame();
      },
      onRestart: () => {
        this.audio.click();
        this._startGame();
      },
      onGoToMenu: () => {
        this.audio.click();
        this._goToMenu();
      },
      onPauseToggle: () => {
        this.audio.click();
        if (this.state === GameState.PLAYING) this._pauseGame();
        else if (this.state === GameState.PAUSED) this._resumeGame();
      },
      onMuteToggle: () => {
        const muted = this.audio.toggleMute();
        this.ui.updateMuteIcon(muted);
      },
    });
  }

  _setupResize() {
    const resize = () => this._resizeCanvas();
    window.addEventListener("resize", resize);
    window.addEventListener("orientationchange", resize);
    resize();
  }

  _setupVisibility() {
    document.addEventListener("visibilitychange", () => {
      if (document.hidden && this.state === GameState.PLAYING) {
        this._pauseGame();
      }
    });
  }

  _resizeCanvas() {
    try {
      const availW = window.innerWidth;
      const availH = window.innerHeight;
      const scale = Math.min(availW / Config.WIDTH, availH / Config.HEIGHT);
      const cssW = Math.max(1, Math.floor(Config.WIDTH * scale));
      const cssH = Math.max(1, Math.floor(Config.HEIGHT * scale));

      this.wrapper.style.width = cssW + "px";
      this.wrapper.style.height = cssH + "px";

      const dpr = Math.min(window.devicePixelRatio || 1, 3);
      this.canvas.width = Math.round(Config.WIDTH * dpr);
      this.canvas.height = Math.round(Config.HEIGHT * dpr);
      this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    } catch (err) {
      // Falls Bildschirmgroesse nicht ermittelbar ist, Canvas unveraendert lassen
    }
  }

  /* ---------------- State transitions ---------------- */

  _startGame() {
    this.state = GameState.PLAYING;
    this.score = 0;
    this.survivalMs = 0;
    this.player.reset();
    this.obstacles.reset();
    this.particles.reset();
    this.shakeFramesLeft = 0;

    const rounds = this.storage.getRoundsPlayed() + 1;
    this.storage.set("roundsPlayed", rounds);

    this.ui.updateScore(0);
    this.ui.setHudVisible(true);
    this.ui.showScreen(null);
    this.ui.el.menu.classList.add("hidden");
    this.ui.el.pause.classList.add("hidden");
    this.ui.el.gameOver.classList.add("hidden");
  }

  _pauseGame() {
    if (this.state !== GameState.PLAYING) return;
    this.state = GameState.PAUSED;
    this.ui.showScreen("pause");
  }

  _resumeGame() {
    if (this.state !== GameState.PAUSED) return;
    this.state = GameState.PLAYING;
    this.ui.el.pause.classList.add("hidden");
  }

  _goToMenu() {
    this.state = GameState.MENU;
    this.ui.setHudVisible(false);
    this._refreshMenuStats();
    this.ui.showScreen("menu");
  }

  _endGame() {
    this.state = GameState.GAME_OVER;
    this.audio.collision();
    this.particles.burstCollision(this.player.drawX, this.player.y);
    this.ui.triggerShake();
    this.shakeFramesLeft = 14;

    const previousHighScore = this.storage.getHighScore();
    const isNewHighscore = this.score > previousHighScore;
    if (isNewHighscore) {
      this.storage.set("highScore", this.score);
      this.audio.highscore();
    }

    const longestSurvivalMs = this.storage.getLongestSurvivalMs();
    if (this.survivalMs > longestSurvivalMs) {
      this.storage.set("longestSurvivalMs", this.survivalMs);
    }

    this.ui.setHudVisible(false);
    this.ui.updateGameOver(this.score, Math.max(this.score, previousHighScore), isNewHighscore);
    this.ui.showScreen("gameover");
  }

  _refreshMenuStats() {
    this.ui.updateMenuStats(this.storage.getHighScore(), this.storage.getRoundsPlayed(), this.storage.getLongestSurvivalMs());
  }

  /* ---------------- Dev / cheat helpers (nur mit ?dev=1) ---------------- */

  devAddScore(amount) {
    if (this.state !== GameState.PLAYING) return;
    this.score += amount;
    this.ui.updateScore(this.score);
  }

  devRegenerateObstacles() {
    if (this.state !== GameState.PLAYING) return;
    this.obstacles.reset();
  }

  /* ---------------- Main loop ---------------- */

  _loop(timestamp) {
    if (this._lastTimestamp === null) this._lastTimestamp = timestamp;
    let frameTime = (timestamp - this._lastTimestamp) / 1000;
    this._lastTimestamp = timestamp;
    frameTime = Math.min(frameTime, Config.MAX_FRAME_TIME);

    this._trackFps(frameTime);

    this.time += frameTime;

    // Fester Zeitschritt fuer die Physik -> framerate-unabhaengiges Gefuehl
    this._accumulator += frameTime;
    let steps = 0;
    while (this._accumulator >= Config.FIXED_TIMESTEP && steps < 8) {
      this._fixedUpdate(Config.FIXED_TIMESTEP);
      this._accumulator -= Config.FIXED_TIMESTEP;
      steps++;
    }

    // Partikel und Hintergrund duerfen mit variablem Zeitschritt laufen,
    // das faellt visuell nicht ins Gewicht.
    this._variableUpdate(frameTime);

    this._render();

    if (this.debugEnabled) this._updateDebugPanel();

    requestAnimationFrame(this._loop.bind(this));
  }

  _trackFps(frameTime) {
    if (frameTime <= 0) return;
    this._fpsHistory.push(1 / frameTime);
    if (this._fpsHistory.length > 30) this._fpsHistory.shift();
  }

  get currentFps() {
    if (this._fpsHistory.length === 0) return 0;
    return this._fpsHistory.reduce((a, b) => a + b, 0) / this._fpsHistory.length;
  }

  _fixedUpdate(dt) {
    if (this.state === GameState.PLAYING) {
      const speedMul = this.devSpeedMultiplier;
      this.player.updatePhysics(dt * speedMul);
      this.survivalMs += dt * 1000 * speedMul;

      this.obstacles.update(dt * speedMul, this.score, () => {
        this.score += 1;
        this.ui.updateScore(this.score);
        this.audio.score();
      });

      if (!this.devInvincible) {
        const hitObstacle = CollisionSystem.checkPlayerVsObstacles(this.player, this.obstacles);
        const hitGround = CollisionSystem.checkGround(this.player);
        const hitCeiling = CollisionSystem.checkCeiling(this.player);
        if (hitObstacle || hitGround) {
          this.player.y = clamp(this.player.y, 0, Config.HEIGHT - Config.GROUND_HEIGHT);
          this._endGame();
        } else if (hitCeiling) {
          this.player.y = 0;
          this.player.velocityY = 0;
        }
      } else {
        // Unverwundbarkeit: Spielfigur bleibt innerhalb des Spielfelds
        this.player.y = clamp(this.player.y, 0, Config.HEIGHT - Config.GROUND_HEIGHT);
      }
    } else if (this.state === GameState.MENU) {
      this.player.updateIdle(dt, this.time);
    }
    // PAUSED und GAME_OVER: keine physikalische Aktualisierung (eingefroren)
  }

  _variableUpdate(dt) {
    if (this.state === GameState.PAUSED) {
      return; // vollstaendig eingefroren
    }

    const difficulty = calculateDifficulty(this.score);
    const bgSpeed = this.state === GameState.MENU ? calculateDifficulty(0).obstacleSpeed * 0.4 : difficulty.obstacleSpeed;

    if (this.state !== GameState.GAME_OVER) {
      this.background.update(dt, bgSpeed);
    }

    this.particles.update(dt);

    if (this.shakeFramesLeft > 0) this.shakeFramesLeft--;
  }

  /* ---------------- Rendering ---------------- */

  _render() {
    const ctx = this.ctx;
    ctx.clearRect(0, 0, Config.WIDTH, Config.HEIGHT);

    this.background.render(ctx);
    this.obstacles.render(ctx);

    const thrusting = this.state === GameState.PLAYING && this.player.velocityY < 0;
    this.player.render(ctx, thrusting);

    this.particles.render(ctx);

    if (this.debugEnabled) {
      this.player.renderHitboxDebug(ctx);
      this.obstacles.renderHitboxDebug(ctx);
    }
  }

  _updateDebugPanel() {
    const difficulty = calculateDifficulty(this.score);
    const lines = [
      `FPS: ${this.currentFps.toFixed(0)}`,
      `State: ${this.state}`,
      `Player: x=${this.player.x.toFixed(0)} y=${this.player.y.toFixed(0)}`,
      `Velocity Y: ${this.player.velocityY.toFixed(0)} px/s`,
      `Rotation: ${this.player.rotation.toFixed(2)} rad`,
      `Score: ${this.score}`,
      `Obstacles: ${this.obstacles.obstacles.length}`,
      `Difficulty: speed=${difficulty.obstacleSpeed.toFixed(0)} gap=${difficulty.gapSize.toFixed(0)}`,
      `  spawn=${difficulty.spawnIntervalMs.toFixed(0)}ms shift=${difficulty.gapShiftRange.toFixed(0)}`,
    ];
    this.ui.updateDebug(lines.join("\n"));
  }
}

/* ============================================================================
   Bootstrap
   ============================================================================ */

window.addEventListener("DOMContentLoaded", () => {
  try {
    const game = new Game();
    // Globaler Zugriff nur im Entwickler-/Debug-Kontext (?dev=1), damit im
    // normalen Spielbetrieb keine unnoetige globale Variable entsteht.
    if (new URLSearchParams(window.location.search).get("dev") === "1") {
      window.__skydriftGame = game;
    }
  } catch (err) {
    // Letzte Verteidigungslinie: Zeige einen einfachen Hinweis statt eines
    // stillen weissen Bildschirms, falls beim Start etwas fehlschlaegt.
    const app = document.getElementById("app");
    if (app) {
      app.innerHTML =
        '<p style="color:#fff;font-family:sans-serif;padding:20px;text-align:center;">' +
        "SKYDRIFT konnte nicht gestartet werden. Bitte Seite neu laden." +
        "</p>";
    }
    // eslint-disable-next-line no-console
    console.error("SKYDRIFT Startfehler:", err);
  }
});
