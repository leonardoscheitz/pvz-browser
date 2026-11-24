import { installGarden } from "./garden.js";
import { mountSaves, reserveProfile, sync } from "./saves.js";

const config = JSON.parse(document.querySelector("#config").textContent);
const canvas = document.querySelector("#canvas");
const splash = document.querySelector("#splash");
const panel = document.querySelector("#panel");
const notice = document.querySelector("#notice");
const retry = document.querySelector("#retry");
const bar = document.querySelector("[role=progressbar]");
const progressText = document.querySelector("#progress-text");
const expectedBytes = config.pak.size + config.wasm.size;
let received = 0;
let lastPercent = -1;
let persistent = false;
let failed = false;
let releaseProfile;
let removeGarden;

function showMessage(text, action = "Tentar novamente") {
  document.querySelector("#message").textContent = text;
  retry.textContent = action;
  panel.hidden = false;
  retry.focus();
}

function notify(text) {
  notice.querySelector("span").textContent = text;
  notice.hidden = false;
}

function fail(error) {
  if (failed) return;
  failed = true;
  removeGarden?.();
  if (!persistent) releaseProfile?.();
  console.error(error);
  showMessage(error.message || "O jogo não conseguiu iniciar.");
}

function countBytes(count) {
  received += count;
  const percent = Math.min(100, Math.floor(received / expectedBytes * 100));
  if (percent === lastPercent) return;
  lastPercent = percent;
  bar.style.setProperty("--fill", percent + "%");
  bar.setAttribute("aria-valuenow", String(percent));
  progressText.textContent = percent < 100 ? "Carregando " + percent + "%" : "Abrindo o jogo…";
}

async function fetchFile(asset, signal) {
  const response = await fetch(asset.url, { cache: "force-cache", signal });
  if (!response.ok) throw new Error("Falha ao carregar os arquivos do jogo (HTTP " + response.status + ").");
  return response;
}

async function decompressed(asset, signal) {
  const response = await fetchFile(asset, signal);
  const counter = new TransformStream({
    transform(chunk, controller) {
      countBytes(chunk.byteLength);
      controller.enqueue(chunk);
    }
  });
  return response.body.pipeThrough(counter).pipeThrough(new DecompressionStream("gzip"));
}

function initializeEngine() {
  return new Promise((resolve, reject) => {
    window.Module = {
      canvas,
      noInitialRun: true,
      onRuntimeInitialized: () => resolve(window.Module),
      onAbort: reason => {
        const error = new Error("O motor do jogo parou: " + reason);
        fail(error);
        reject(error);
      },
      instantiateWasm(imports, ready) {
        (async () => {
          const source = new Response(await decompressed(config.wasm), { headers: { "Content-Type": "application/wasm" } });
          const { instance } = await WebAssembly.instantiateStreaming(source, imports);
          ready(instance);
        })().catch(reject);
        return {};
      }
    };
    const script = document.createElement("script");
    script.src = config.glue.url;
    script.onerror = () => reject(new Error("Falha ao carregar o motor do jogo. Confira sua conexão."));
    document.head.append(script);
  });
}

async function readPakPart(part, destination, signal) {
  const reader = (await decompressed(part, signal)).getReader();
  let written = 0;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    if (written + value.length > destination.length) throw new Error("Parte do pacote de recursos inválida.");
    destination.set(value, written);
    written += value.length;
  }
  if (written !== destination.length) throw new Error("O pacote de recursos do jogo chegou incompleto.");
}

async function loadPak() {
  const data = new Uint8Array(config.pak.rawSize);
  const parts = config.pak.parts.values();
  const downloads = new AbortController();
  async function readParts() {
    for (const part of parts) {
      await readPakPart(part, data.subarray(part.offset, part.offset + part.rawSize), downloads.signal);
    }
  }
  // Small HTTP cache entries, with at most four inflaters writing into one final PAK buffer.
  try {
    await Promise.all(Array.from({ length: Math.min(4, config.pak.parts.length) }, readParts));
  } catch (error) {
    downloads.abort();
    throw error;
  }
  return data;
}

async function gameAssets() {
  const [pak, properties] = await Promise.all([
    loadPak(),
    Promise.all(config.properties.map(async entry => {
      const response = await fetchFile(entry);
      const bytes = new Uint8Array(await response.arrayBuffer());
      if (bytes.byteLength !== entry.size) throw new Error("Arquivo incompleto: " + entry.path);
      return [entry.path, bytes];
    }))
  ]);
  return { pak, properties };
}

async function start() {
  if (!window.WebAssembly || !window.DecompressionStream || !WebAssembly.instantiateStreaming) {
    throw new Error("Abra o jogo em uma versão atual do Chrome, Edge, Firefox ou Safari.");
  }
  releaseProfile = await reserveProfile();
  const [module, resources] = await Promise.all([initializeEngine(), gameAssets()]);
  const fs = module.FS;
  fs.writeFile("/main.pak", resources.pak, { canOwn: true });
  fs.mkdir("/properties");
  for (const [path, bytes] of resources.properties) fs.writeFile("/" + path, bytes, { canOwn: true });
  persistent = await mountSaves(module, notify);
  // Let the browser paint the final loading update before the engine initializes SDL.
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  if (failed) return;
  splash.hidden = true;
  canvas.focus({ preventScroll: true });
  performance.mark("pvz-engine-start");
  module.callMain([]);
  // PvZ-Portable already owns the indexed PAK in its WASM heap after Init.
  // Release the startup copy so it is not kept alongside the decoded textures.
  fs.unlink("/main.pak");
  if (!failed) removeGarden = installGarden(module, canvas);
}

window.onGameExit = async () => {
  removeGarden?.();
  if (persistent) {
    try { await sync(window.Module.FS); }
    catch (error) { notify("O navegador não conseguiu gravar o último progresso."); console.warn(error); }
  }
  releaseProfile?.();
  splash.hidden = false;
  showMessage("Jogo encerrado.", "Jogar novamente");
};
canvas.addEventListener("contextmenu", event => event.preventDefault());
// A tap can move focus back to the canvas. Restore the editor during the
// user gesture so mobile browsers can open or reopen their virtual keyboard.
canvas.addEventListener("pointerup", () => {
  if (window.Module?.wasmSoftKeyboardState?.active) {
    document.querySelector("#pvz-soft-keyboard").focus({ preventScroll: true });
  }
});
canvas.addEventListener("webglcontextcreationerror", () => fail(new Error("O navegador não conseguiu abrir o WebGL. Ative a aceleração gráfica e tente novamente.")));
canvas.addEventListener("webglcontextlost", () => fail(new Error("A conexão com a placa de vídeo foi interrompida. Reabra o jogo.")));
notice.querySelector("button").addEventListener("click", () => { notice.hidden = true; canvas.focus(); });
retry.addEventListener("click", () => location.reload());
start().catch(fail);
