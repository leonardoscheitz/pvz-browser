// Operate only with the engine closed and with its exclusive Web Lock.
const MOUNT = "/pvz-browser-goty";
const STORE = "FILE_DATA";
const LIMIT = 32 * 1024 * 1024;
const BACKUPS = "pvz-browser-restore-backup-v1";
const status = document.querySelector("#save-status");
const file = document.querySelector("#save-file");
const buttons = [...document.querySelectorAll("#save-export,#save-import,#save-previous")];
let busy = false;
function request(req) {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
function finished(tx) {
  return new Promise((resolve, reject) => {
    tx.oncomplete = resolve;
    tx.onabort = () => reject(tx.error || new Error("Transação cancelada."));
    tx.onerror = () => reject(tx.error || new Error("Erro no armazenamento."));
  });
}
async function openGameDB() {
  const req = indexedDB.open(MOUNT);
  req.onupgradeneeded = () => req.transaction.abort();
  const db = await request(req).catch(() => { throw new Error("Abra o jogo e crie um perfil antes de gerenciar saves."); });
  if (!db.objectStoreNames.contains(STORE)) { db.close(); throw new Error("Banco do jogo não encontrado."); }
  return db;
}
function validPath(path) {
  return typeof path === "string" && path.startsWith(MOUNT + "/") &&
    path.length <= 512 && path.slice(MOUNT.length + 1).split("/").every(part =>
      part && part !== "." && part !== ".." && !/[\\\u0000-\u001f]/.test(part));
}
function encode(bytes) {
  let out = "";
  for (let i = 0; i < bytes.length; i += 16384) out += String.fromCharCode(...bytes.subarray(i, i + 16384));
  return btoa(out);
}
function decode(base64) {
  if (typeof base64 !== "string" || base64.length > LIMIT * 2) throw new Error("Dados inválidos.");
  return Uint8Array.from(atob(base64), c => c.charCodeAt(0));
}
async function snapshot(db) {
  const tx = db.transaction(STORE);
  const done = finished(tx);
  const store = tx.objectStore(STORE);
  const [keys, values] = await Promise.all([request(store.getAllKeys()), request(store.getAll()), done]);
  const records = [];
  for (let i = 0; i < keys.length; i++) {
    const path = keys[i], value = values[i];
    if (!validPath(path)) throw new Error("Registro inesperado no banco. Nenhuma alteração realizada.");
    const type = value.mode & 0xf000;
    if (type !== 0x4000 && type !== 0x8000) throw new Error("Tipo de arquivo inesperado.");
    records.push({path, mode:value.mode, timestamp:new Date(value.timestamp).toISOString(),
      ...(type === 0x8000 ? {data:encode(new Uint8Array(value.contents))} : {})});
  }
  return {format:"pvz-browser-goty-backup", version:1, createdAt:new Date().toISOString(), records};
}
function validate(data) {
  if (data?.format !== "pvz-browser-goty-backup" || data.version !== 1 ||
      !Array.isArray(data.records) || data.records.length > 4096) throw new Error("Formato de backup incompatível.");
  const seen = new Map();
  let total = 0;
  for (const row of data.records) {
    if (!row || !validPath(row.path) || seen.has(row.path) || !Number.isInteger(row.mode) ||
        row.mode < 0 || row.mode > 0xffff || typeof row.timestamp !== "string")
      throw new Error("Registro de backup inválido.");
    const timestamp = new Date(row.timestamp), type = row.mode & 0xf000;
    if (!Number.isFinite(timestamp.getTime()) || ![0x4000,0x8000].includes(type)) throw new Error("Registro de backup inválido.");
    const value = {mode:row.mode,timestamp};
    if (type === 0x8000) {
      value.contents = decode(row.data); total += value.contents.length;
      if (total > LIMIT) throw new Error("Backup muito grande.");
    }
    seen.set(row.path,value);
  }
  for (const path of seen.keys()) {
    const parent = path.slice(0,path.lastIndexOf("/"));
    if (parent !== MOUNT && (seen.get(parent)?.mode & 0xf000) !== 0x4000)
      throw new Error("Pasta ausente no backup.");
  }
  return seen;
}
async function backupDB() {
  const req = indexedDB.open(BACKUPS,1);
  req.onupgradeneeded = () => req.result.createObjectStore("snapshots");
  return request(req);
}
async function keepPrevious(data) {
  const db = await backupDB();
  try { const tx = db.transaction("snapshots","readwrite"), done = finished(tx);
    tx.objectStore("snapshots").put(data,"previous"); await done;
  } finally { db.close(); }
}
async function getPrevious() {
  const db = await backupDB();
  try { return await request(db.transaction("snapshots").objectStore("snapshots").get("previous")); }
  finally { db.close(); }
}
function download(data, name) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data)],{type:"application/json"}));
  const a = document.createElement("a"); a.href = url; a.download = name;
  document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url),60000);
}
async function exclusively(action) {
  if (busy) return;
  busy = true; buttons.forEach(b => b.disabled = true);
  try {
    if (!navigator.locks) throw new Error("Seu navegador não oferece bloqueio seguro de saves. Use um navegador atualizado.");
    await navigator.locks.request("pvz-browser-goty-save",{ifAvailable:true},async lock => {
      if (!lock) throw new Error("Feche as outras abas do jogo e tente novamente.");
      await action();
    });
  } catch(error) { status.textContent = error.message || "Operação não concluída."; console.warn(error); }
  finally { busy = false; buttons.forEach(b => b.disabled = false); buttons[1].disabled = !file.files.length; }
}
file.addEventListener("change",() => { buttons[1].disabled = busy || !file.files.length; });
buttons[0].addEventListener("click",() => exclusively(async () => {
  const db = await openGameDB();
  try { download(await snapshot(db),"pvz-save-"+new Date().toISOString().slice(0,10)+".json"); status.textContent = "Backup exportado."; }
  finally { db.close(); }
}));
buttons[1].addEventListener("click",() => exclusively(async () => {
  const selected = file.files[0];
  if (!selected || selected.size > LIMIT * 2) throw new Error("Selecione um backup válido.");
  const rows = validate(JSON.parse(await selected.text()));
  if (!confirm("Substituir o progresso local pelo backup selecionado? Uma cópia anterior será guardada.")) return;
  const db = await openGameDB();
  try {
    await keepPrevious(await snapshot(db));
    // Clear and replace in one atomic IndexedDB transaction; errors roll back.
    const tx = db.transaction(STORE,"readwrite"), done = finished(tx), store = tx.objectStore(STORE);
    store.clear();
    for (const [path,value] of rows) store.put(value,path);
    await done;
    status.textContent = "Backup restaurado. Volte ao jogo para carregar o progresso.";
  } finally { db.close(); }
}));
buttons[2].addEventListener("click",() => exclusively(async () => {
  const previous = await getPrevious();
  if (!previous) throw new Error("Nenhum backup anterior à restauração.");
  download(previous,"pvz-save-anterior.json"); status.textContent = "Cópia de segurança exportada.";
}));
