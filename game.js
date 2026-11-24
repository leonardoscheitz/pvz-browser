import { mountSaves, sync } from "./saves.js";

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

async function fetchFile(asset) {
  const response = await fetch(asset.url, { cache: "force-cache" });
  if (!response.ok) throw new Error("Falha ao carregar os arquivos do jogo (HTTP " + response.status + ").");
  return response;
}

async function decompressed(asset) {
  const response = await fetchFile(asset);
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

async function loadPak() {
  const reader = (await decompressed(config.pak)).getReader();
  const data = new Uint8Array(config.pak.rawSize);
  let offset = 0;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    data.set(value, offset);
    offset += value.length;
  }
  if (offset !== data.length) throw new Error("O pacote de recursos do jogo chegou incompleto.");
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
}

window.onGameExit = async () => {
  if (persistent) {
    try { await sync(window.Module.FS); }
    catch (error) { notify("O navegador não conseguiu gravar o último progresso."); console.warn(error); }
  }
  splash.hidden = false;
  showMessage("Jogo encerrado.", "Jogar novamente");
};
canvas.addEventListener("contextmenu", event => event.preventDefault());
canvas.addEventListener("webglcontextcreationerror", () => fail(new Error("O navegador não conseguiu abrir o WebGL. Ative a aceleração gráfica e tente novamente.")));
canvas.addEventListener("webglcontextlost", () => fail(new Error("A conexão com a placa de vídeo foi interrompida. Reabra o jogo.")));
notice.querySelector("button").addEventListener("click", () => { notice.hidden = true; canvas.focus(); });
retry.addEventListener("click", () => location.reload());
start().catch(fail);
