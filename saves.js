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

async function oldProfiles() {
  if (!indexedDB.databases) return [];
  const existing = new Set((await indexedDB.databases()).map(db => db.name));
  let newest = -1;
  let profile = [];
  for (const name of legacyStores.filter(name => existing.has(name))) {
    const db = await result(indexedDB.open(name));
    try {
      if (!db.objectStoreNames.contains("FILE_DATA")) continue;
      const store = db.transaction("FILE_DATA").objectStore("FILE_DATA");
      const keys = (await result(store.getAllKeys())).filter(key =>
        typeof key === "string" && /\/userdata\/user(?:s|\d+)\.dat$/i.test(key));
      // Read only profile records. The same old database may also contain an entire Wine prefix.
      const records = await Promise.all(keys.map(async key => [key, await result(store.get(key))]));
      for (const [key, value] of records) {
        if (!/\/users\.dat$/i.test(key) || !value.contents?.length) continue;
        const date = Number(value.timestamp);
        if (date <= newest) continue;
        const folder = key.slice(0, key.lastIndexOf("/") + 1);
        profile = records.filter(([path, item]) => path.startsWith(folder) && item.contents?.length)
          .map(([path, item]) => [path.slice(folder.length).toLowerCase(), item.contents]);
        newest = date;
      }
    } finally {
      db.close();
    }
  }
  return profile;
}

// An IDBFS instance syncs a whole directory snapshot. Two writers could drop each other's progress.
async function reserveProfile() {
  if (!navigator.locks) return;
  await new Promise((resolve, reject) => {
    navigator.locks.request("pvz-browser-goty-save", { ifAvailable: true }, lock => {
      if (!lock) return reject(new Error("O jogo já está aberto em outra aba. Feche essa aba para continuar aqui."));
      resolve();
      return new Promise(() => {}); // The browser releases the lock when the document closes.
    }).catch(reject);
  });
}

export async function mountSaves(module, notify) {
  await reserveProfile();
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
      if (files.length) {
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
