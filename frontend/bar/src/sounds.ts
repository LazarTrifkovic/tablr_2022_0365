// Zvučna signalizacija bez audio fajlova (WebAudio).
// Browseri traže korisničku interakciju pre puštanja zvuka — otključavamo na prvi klik.

let ctx: AudioContext | null = null;

function ensureCtx(): AudioContext {
  if (!ctx) ctx = new AudioContext();
  if (ctx.state === "suspended") void ctx.resume();
  return ctx;
}

export function unlockAudio(): void {
  ensureCtx();
}

function tone(freq: number, start: number, duration: number): void {
  const audio = ensureCtx();
  const osc = audio.createOscillator();
  const gain = audio.createGain();
  osc.type = "sine";
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(0.25, audio.currentTime + start);
  gain.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + start + duration);
  osc.connect(gain).connect(audio.destination);
  osc.start(audio.currentTime + start);
  osc.stop(audio.currentTime + start + duration);
}

/** Nova porudžbina: prijatan dvoton ("ding-dong"). */
export function orderSound(): void {
  tone(880, 0, 0.15);
  tone(660, 0.18, 0.25);
}

/** Poziv konobara / račun: uporniji troton — mora da se čuje u gužvi. */
export function requestSound(): void {
  tone(523, 0, 0.12);
  tone(523, 0.2, 0.12);
  tone(784, 0.4, 0.3);
}
