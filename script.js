const promptEl = document.getElementById("prompt");
const styleChipsEl = document.getElementById("styleChips");
const generateBtn = document.getElementById("generateBtn");
const surpriseBtn = document.getElementById("surpriseBtn");
const statusEl = document.getElementById("status");
const resultEl = document.getElementById("result");
const resultImage = document.getElementById("resultImage");
const regenerateBtn = document.getElementById("regenerateBtn");
const downloadBtn = document.getElementById("downloadBtn");
const shareBtn = document.getElementById("shareBtn");

const EXAMPLE_PROMPTS = [
  "Ein Leuchtturm bei Sonnenuntergang, Wellen brechen an Felsen",
  "Eine futuristische Stadt bei Nacht mit fliegenden Autos",
  "Ein Astronaut reitet auf einem Pferd auf dem Mond",
  "Eine gemütliche Kaffeebar in einem verwunschenen Wald",
  "Ein Drache schläft auf einem Berg aus Gold",
  "Ein Katzen-Astronaut schwebt zwischen den Sternen",
  "Ein verlassenes Schloss im Nebel, mystische Stimmung",
  "Ein Roboter gärtnert in einem Zukunftsgarten",
];

let selectedStyle = "";
let currentBasePrompt = "";

styleChipsEl.addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  styleChipsEl.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
  chip.classList.add("active");
  selectedStyle = chip.dataset.style;
});

generateBtn.addEventListener("click", () => {
  const text = promptEl.value.trim();
  if (!text) {
    showStatus("Bitte gib zuerst eine Beschreibung ein.", true);
    return;
  }
  generateImage(text);
});

surpriseBtn.addEventListener("click", () => {
  const random = EXAMPLE_PROMPTS[Math.floor(Math.random() * EXAMPLE_PROMPTS.length)];
  promptEl.value = random;
  generateImage(random);
});

regenerateBtn.addEventListener("click", () => {
  if (currentBasePrompt) generateImage(currentBasePrompt);
});

downloadBtn.addEventListener("click", () => {
  downloadImage(resultImage.src);
});

if (navigator.share) {
  shareBtn.hidden = false;
  shareBtn.addEventListener("click", async () => {
    try {
      const res = await fetch(resultImage.src);
      const blob = await res.blob();
      const file = new File([blob], "bild.jpg", { type: blob.type || "image/jpeg" });
      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({ files: [file], title: "Mein generiertes Bild" });
      } else {
        await navigator.share({ url: resultImage.src, title: "Mein generiertes Bild" });
      }
    } catch (err) {
      // user cancelled or share failed silently
    }
  });
}

function buildFullPrompt(basePrompt) {
  return selectedStyle ? `${basePrompt}, ${selectedStyle}` : basePrompt;
}

function showStatus(text, isError = false) {
  statusEl.hidden = false;
  statusEl.classList.toggle("error", isError);
  statusEl.innerHTML = isError ? "" : '<span class="spinner"></span>';
  statusEl.append(text);
}

function hideStatus() {
  statusEl.hidden = true;
}

function generateImage(basePrompt) {
  currentBasePrompt = basePrompt;
  const fullPrompt = buildFullPrompt(basePrompt);
  const seed = Math.floor(Math.random() * 1_000_000);
  const url = `https://image.pollinations.ai/prompt/${encodeURIComponent(
    fullPrompt
  )}?width=1024&height=1024&seed=${seed}&nologo=true`;

  generateBtn.disabled = true;
  resultEl.hidden = true;
  showStatus("Bild wird erstellt...");

  const img = new Image();
  img.onload = () => {
    resultImage.src = url;
    resultEl.hidden = false;
    hideStatus();
    generateBtn.disabled = false;
    resultEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
  };
  img.onerror = () => {
    showStatus("Bild konnte nicht erstellt werden. Bitte versuch es erneut.", true);
    generateBtn.disabled = false;
  };
  img.src = url;
}

async function downloadImage(url) {
  try {
    const res = await fetch(url);
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = "bild.jpg";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objectUrl);
  } catch (err) {
    window.open(url, "_blank");
  }
}
