const status = document.querySelector("#offline-status");
const button = document.querySelector("#offline-prepare");
if ("serviceWorker" in navigator && "caches" in window) {
  button.hidden = false;
  status.hidden = false;
  status.textContent = "Modo offline opcional";
  let pending = false;
  async function prepare() {
    if (pending) return;
    pending = true;
    button.disabled = true;
    status.textContent = "Preparando arquivos offline…";
    try {
      const registration = await navigator.serviceWorker.register("./sw.js", {updateViaCache: "none"});
      const worker = registration.installing || registration.waiting;
      if (worker && worker.state !== "installed" && worker.state !== "activated") {
        await new Promise((resolve, reject) => {
          function changed() {
            if (worker.state === "installed" || worker.state === "activated") {
              worker.removeEventListener("statechange", changed); resolve();
            } else if (worker.state === "redundant") {
              worker.removeEventListener("statechange", changed); reject(new Error("Cache offline incompleto"));
            }
          }
          worker.addEventListener("statechange", changed);
          changed();
        });
      }
      await navigator.serviceWorker.ready;
      status.textContent = "Offline preparado. Abra novamente sem internet após fechar as abas antigas.";
      button.textContent = "Atualizar offline";
    } catch (error) {
      console.warn("PVZ offline", error);
      status.textContent = "Não foi possível preparar o modo offline. Tente novamente.";
    } finally { pending = false; button.disabled = false; }
  }
  button.addEventListener("click", prepare);
  navigator.serviceWorker.getRegistration("./").then(registration => {
    if (registration?.active) {
      button.textContent = "Atualizar offline";
      status.textContent = "Modo offline preparado";
    }
  }).catch(console.warn);
}
