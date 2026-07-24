/**
 * voice.js - optional speech input/output using the browser's built-in
 * Web Speech API (SpeechRecognition + speechSynthesis). This needs no
 * server, no API key and no paid service; it simply isn't available in
 * every browser (e.g. Firefox lacks SpeechRecognition), so every method
 * here degrades gracefully when unsupported.
 */

const SAAMaiVoice = (() => {
  const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognizer = null;
  let listening = false;

  function speechInputSupported() {
    return !!SpeechRecognitionImpl;
  }

  function speechOutputSupported() {
    return "speechSynthesis" in window;
  }

  function startListening({ lang, onResult, onEnd, onError }) {
    if (!speechInputSupported() || listening) return;
    recognizer = new SpeechRecognitionImpl();
    recognizer.lang = lang === "en" ? "en-US" : "de-DE";
    recognizer.interimResults = true;
    recognizer.continuous = false;

    recognizer.onresult = (event) => {
      let transcript = "";
      for (let i = 0; i < event.results.length; i += 1) {
        transcript += event.results[i][0].transcript;
      }
      onResult(transcript, event.results[event.results.length - 1].isFinal);
    };
    recognizer.onerror = (event) => onError && onError(event.error);
    recognizer.onend = () => {
      listening = false;
      onEnd && onEnd();
    };

    recognizer.start();
    listening = true;
  }

  function stopListening() {
    if (recognizer && listening) recognizer.stop();
  }

  function isListening() {
    return listening;
  }

  function speak(text, lang) {
    if (!speechOutputSupported() || !text) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang === "en" ? "en-US" : "de-DE";
    window.speechSynthesis.speak(utterance);
  }

  return { speechInputSupported, speechOutputSupported, startListening, stopListening, isListening, speak };
})();
