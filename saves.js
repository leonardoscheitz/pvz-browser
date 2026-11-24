// IDBFS keys databases by mount point. Use a name unique to this game on the Pages origin.
const mount = "/pvz-browser-goty";
const legacyStores = ["/root/key/pvz-goty", "/d_drive/key/pvz-goty"];

function result(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export function sync(fs, populate = false) {
  return new Promise((resolve, reject) => fs.syncfs(populate, error => error ? reject(error) : resolve()));
}

async function readLegacyStore(name) {
  // Opening without a version works even on browsers without databases().
  // Abort creation when this installation of BoxedWine never existed.
  const request = indexedDB.open(name);
  let missing = false;
  request.onupgradeneeded = () => { missing = true; request.transaction.abort(); };
  let db;
  try {
    db = await result(request);
  } catch (error) {
    if (missing && error.name === "AbortError") return [];
    throw error;
  }
  try {
    if (!db.objectStoreNames.contains("FILE_DATA")) return [];
    const files = () => db.transaction("FILE_DATA").objectStore("FILE_DATA");
    const keys = (await result(files().getAllKeys())).filter(key =>
      typeof key === "string" && /\/userdata\/user(?:s|\d+)\.dat$/i.test(key));
    if (!keys.length) return [];
    // Queue all reads on a fresh transaction before yielding. Never load Wine's other files.
    const store = files();
    return await Promise.all(keys.map(async key => [key, await result(store.get(key))]));
  } finally {
    db.close();
  }
}

async function oldProfiles() {
  let latest;
  for (const name of legacyStores) {
    const folders = new Map();
    for (const [path, file] of await readLegacyStore(name)) {
      if (!file?.contents?.length) continue;
      const slash = path.lastIndexOf("/");
      const folder = path.slice(0, slash).toLowerCase();
      if (!folders.has(folder)) folders.set(folder, { files: new Map(), time: 0 });
      const group = folders.get(folder);
      group.files.set(path.slice(slash + 1).toLowerCase(), file.contents);
      group.time = Math.max(group.time, Number(file.timestamp) || 0);
    }
    for (const group of folders.values()) {
      if (group.files.has("users.dat") && (!latest || group.time > latest.time)) latest = group;
    }
  }
  return latest?.files ?? new Map();
}

// An IDBFS instance syncs a whole directory snapshot. Two writers could drop each other's progress.
export async function reserveProfile() {
  if (!navigator.locks) return;
  return new Promise((resolve, reject) => {
    // A just-closed tab can keep its lock briefly while its document is torn down.
    const waiting = new AbortController();
    const timeout = setTimeout(() => waiting.abort(), 1000);
    navigator.locks.request("pvz-browser-goty-save", { signal: waiting.signal }, () => {
      clearTimeout(timeout);
      return new Promise(release => resolve(release));
    }).catch(error => {
      clearTimeout(timeout);
      reject(error.name === "AbortError"
        ? new Error("O jogo já está aberto em outra aba. Feche essa aba para continuar aqui.")
        : error);
    });
  });
}

export async function mountSaves(module, notify) {
  const fs = module.FS;
  fs.mkdir(mount);
  fs.symlink(mount, "/saves");
  let mounted = false;
  try {
    fs.mount(module.IDBFS, { autoPersist: true }, mount);
    mounted = true;
    await sync(fs, true);
  } catch (error) {
    if (mounted) fs.unmount(mount);
    console.warn("Armazenamento local indisponível", error);
    notify("O navegador bloqueou o armazenamento. O progresso desta sessão é temporário.");
    return false;
  }

  if (!fs.analyzePath("/saves/userdata/users.dat").exists) {
    try {
      const files = await oldProfiles();
      if (files.size) {
        fs.mkdirTree("/saves/userdata");
        for (const [name, bytes] of files) fs.writeFile("/saves/userdata/" + name, bytes);
        await sync(fs);
        notify("Seu perfil da versão emulada foi recuperado.");
      }
    } catch (error) {
      console.warn("Leitura do perfil anterior indisponível", error);
    }
  }
  return true;
}
