// Activate a button on a completed tap even when the mobile browser suppresses
// its compatibility click. Leave scrolling, form fields and keyboard clicks native.
function enableButtonTaps(root) {
  let tap;
  root.addEventListener("touchstart", event => {
    const finger = event.changedTouches[0];
    const button = event.target.closest("button");
    tap = event.touches.length === 1 && button
      ? { button, id: finger.identifier, x: finger.clientX, y: finger.clientY } : null;
    if (tap) event.stopPropagation();
  }, { passive: true });
  root.addEventListener("touchmove", event => {
    if (!tap) return;
    const finger = event.touches[0];
    if (event.touches.length !== 1 || Math.hypot(finger.clientX - tap.x, finger.clientY - tap.y) > 12) tap = null;
  }, { passive: true });
  root.addEventListener("touchcancel", () => { tap = null; });
  root.addEventListener("touchend", event => {
    const target = tap;
    tap = null;
    const finger = event.changedTouches[0];
    if (!target || !event.cancelable || finger.identifier !== target.id ||
        !target.button.contains(document.elementFromPoint(finger.clientX, finger.clientY))) return;
    event.preventDefault();
    event.stopPropagation();
    target.button.click();
  }, { passive: false });
}

export function installGarden(module, canvas) {
  const trigger = document.querySelector("#garden-trigger");
  const menu = document.querySelector("#garden-menu");
  const message = menu.querySelector("output");
  const free = menu.querySelector("#garden-free");
  const speed = menu.querySelector("#garden-speed");
  const sun = menu.querySelector("#garden-sun");
  const coins = menu.querySelector("#garden-coins");
  const panel = document.querySelector("#panel");
  const advanced = [[7, "#garden-infinite", "#garden-infinite-row", "Sol infinito"],
                    [8, "#garden-recharge", "#garden-recharge-row", "Recarga instantânea"]];
  const chill = menu.querySelector("#garden-chill");
  function refreshAdvanced() {
    for (const [field, input, row] of advanced) {
      const state = module._gardenState(field);
      menu.querySelector(row).hidden = state < 0;
      menu.querySelector(input).checked = state === 1;
    }
    menu.querySelector("#garden-chill-row").hidden = module._gardenState(9) < 0;
  }
  const editor = menu.querySelector("#garden-editor");
  const editorAvailable = () => typeof module._gardenEditorAvailable === "function" && module._gardenEditorAvailable() === 1;
  function editPlant(remove) {
    if (!editorAvailable()) { message.textContent = "Editor indisponível nesta fase."; return; }
    const col = menu.querySelector("#editor-col").valueAsNumber;
    const row = menu.querySelector("#editor-row").valueAsNumber;
    const seed = Number(menu.querySelector("#editor-seed").value);
    if (!Number.isInteger(col) || col < 1 || col > 9 || !Number.isInteger(row) || row < 1 || row > 6) {
      message.textContent = "Escolha uma coluna de 1 a 9 e uma linha de 1 a 6.";
      return;
    }
    const ok = remove ? module._gardenEditorRemove(col-1,row-1) : module._gardenEditorPlant(col-1,row-1,seed);
    message.textContent = ok ? (remove ? "Planta removida." : "Planta invocada.") :
      "Célula inválida, ocupada ou incompatível com o terreno.";
  }
  menu.querySelector("#editor-plant").onclick = () => editPlant(false);
  menu.querySelector("#editor-remove").onclick = () => editPlant(true);
  const byId = id => menu.querySelector("#" + id);
  const val = id => byId(id).valueAsNumber;
  const cell = () => [val("editor-col") - 1, val("editor-row") - 1];
  const integer = (n, lo, hi) => Number.isInteger(n) && n >= lo && n <= hi;
  function refreshEditor() {
    if (!editorAvailable()) return;
    byId("editor-wave-status").textContent = "Ondas iniciadas: " + module._gardenEditorWave(0,0) + " / " + module._gardenEditorWave(1,0);
    byId("editor-freeze").checked = module._gardenEditorWave(4,0) === 1;
    byId("editor-regen").checked = module._gardenEditorWave(6,0) === 1;
  }
  byId("editor-spawn-zombie").onclick = () => {
    const row = val("editor-row"), count = val("editor-count");
    if (!editorAvailable() || !integer(row,1,6) || !integer(count,1,20)) {
      message.textContent = "Linha ou quantidade inválida."; return;
    }
    const n = module._gardenEditorSpawnZombie(row-1,Number(byId("editor-zombie").value),count);
    message.textContent = n ? n + " zumbi(s) invocado(s)." : "Tipo incompatível com a linha ou limite atingido.";
  };
  function targetChanged() {
    const zombie = byId("editor-target").value === "zombie";
    byId("editor-rate-label").textContent = zombie ? "Velocidade (×1000)" : "Intervalo (ticks)";
    const input = byId("editor-rate");
    input.min = zombie ? "50" : "80";
    input.max = zombie ? "3000" : "10000";
    input.value = zombie ? "300" : "150";
    input.disabled = false;
  }
  byId("editor-target").onchange = targetChanged;
  byId("editor-inspect").onclick = () => {
    if (!editorAvailable()) return;
    const [col,row] = cell(), zombie = byId("editor-target").value === "zombie";
    if (!integer(row,0,5) || (!zombie && !integer(col,0,8))) { message.textContent = "Célula inválida."; return; }
    const read = field => zombie ? module._gardenEditorZombieState(row,field) : module._gardenEditorPlantState(col,row,field);
    const hp = read(1), max = read(2), speed = read(3);
    if (hp < 0) { message.textContent = "Nenhuma entidade encontrada."; return; }
    byId("editor-health").value = max;
    byId("editor-rate").disabled = speed <= 0;
    if (speed > 0) byId("editor-rate").value = speed;
    message.textContent = "Vida atual: " + hp + "/" + max;
  };
  byId("editor-apply").onclick = () => {
    if (!editorAvailable()) return;
    const [col,row] = cell(), zombie = byId("editor-target").value === "zombie";
    const hp = val("editor-health"), rate = val("editor-rate"), editRate = !byId("editor-rate").disabled;
    if (!integer(row,0,5) || (!zombie && !integer(col,0,8)) || !integer(hp,1,100000) ||
      (editRate && !integer(rate,zombie?50:80,zombie?3000:10000))) { message.textContent = "Atributos inválidos."; return; }
    const change = (field,value) => zombie ? module._gardenEditorZombieAttribute(row,field,value) : module._gardenEditorPlantAttribute(col,row,field,value);
    if (!change(1,hp)) { message.textContent = "Nenhuma entidade encontrada."; return; }
    const speedOk = !editRate || change(3,rate);
    message.textContent = speedOk ? "Atributos aplicados." : "Vida aplicada; intervalo não suportado por esta entidade.";
  };
  for (const [id,action] of [["editor-freeze",2],["editor-regen",5]]) byId(id).onchange = () => {
    if (editorAvailable()) module._gardenEditorWave(action,Number(byId(id).checked));
    refreshEditor();
  };
  byId("editor-next-wave").onclick = () => {
    if (!editorAvailable()) return;
    message.textContent = module._gardenEditorWave(3,0) === 1 ? "Próxima onda antecipada ao retomar." : "Não há outra onda.";
    refreshEditor();
  };
  let resume = false;
  const viewport = window.visualViewport;
  function fitMenu() {
    if (!menu.open || !viewport) return;
    menu.style.width = viewport.width + "px";
    menu.style.height = viewport.height + "px";
    menu.style.top = viewport.offsetTop + "px";
    menu.style.left = viewport.offsetLeft + "px";
  }

  function updateAvailability() {
    const available = module._gardenState(0) >= 0;
    const hidden = !available || !panel.hidden;
    if (trigger.hidden !== hidden) trigger.hidden = hidden;
    return available;
  }

  function change(field, value, feedback) {
    if (!module._gardenChange(field, value)) {
      menu.close();
      return;
    }
    message.textContent = feedback;
  }

  enableButtonTaps(trigger);
  enableButtonTaps(menu);
  for (const type of ["pointerdown", "pointerup"]) {
    trigger.addEventListener(type, event => event.stopPropagation());
  }
  trigger.addEventListener("click", () => {
    if (menu.open || !updateAvailability()) return;
    resume = module._gardenState(4) === 0;
    if (resume) module._gardenChange(4, 1);
    sun.value = module._gardenState(0);
    coins.value = module._gardenState(1);
    free.checked = Boolean(module._gardenState(2));
    speed.value = module._gardenState(3);
    message.textContent = "Partida pausada";
    refreshAdvanced();
    editor.hidden = !editorAvailable();
    if (!editor.hidden) refreshEditor();
    menu.showModal();
    fitMenu();
    viewport?.addEventListener("resize", fitMenu);
    viewport?.addEventListener("scroll", fitMenu);
  });

  for (const [input, field, feedback] of [[sun, 0, "Quantidade de sol aplicada."], [coins, 1, "Saldo de moedas aplicado."]]) {
    input.form.addEventListener("submit", event => {
      event.preventDefault();
      change(field, input.valueAsNumber, feedback);
    });
  }
  free.addEventListener("change", () => change(2, Number(free.checked),
    free.checked ? "Plantio grátis ativado." : "Custo normal restaurado."));
  speed.addEventListener("change", () => change(3, Number(speed.value), "Velocidade alterada."));
  menu.querySelector("#garden-heal").onclick = () => change(5, 0, "Plantas curadas.");
  menu.querySelector("#garden-clear").onclick = () => change(6, 0, "Zumbis do gramado removidos.");
  for (const [field, input, , label] of advanced) {
    const toggle = menu.querySelector(input);
    toggle.addEventListener("change", () => {
      change(field, Number(toggle.checked), label + (toggle.checked ? " ativado." : " desativado."));
      sun.value = module._gardenState(0);
    });
  }
  chill.onclick = () => change(9, 0, "Lentidão aplicada aos zumbis elegíveis.");
  // Presets only use commands that the currently shipped native engine exposes.
  function preset(commands, feedback) {
    for (const [field, value] of commands) {
      if (!module._gardenChange(field, value)) { menu.close(); return; }
    }
    sun.value = module._gardenState(0);
    coins.value = module._gardenState(1);
    free.checked = Boolean(module._gardenState(2));
    speed.value = module._gardenState(3);
    refreshAdvanced();
    message.textContent = feedback;
  }
  menu.querySelector("#garden-relaxed").onclick = () => preset([[0,9990],[2,1],[3,1]], "Sol máximo e plantio grátis.");
  menu.querySelector("#garden-normal").onclick = () => {
    const commands = [[2,0],[3,1]];
    for (const [field] of advanced) if (module._gardenState(field) >= 0) commands.push([field,0]);
    preset(commands, "Modificadores contínuos desligados; custo e velocidade normais.");
  };
  menu.querySelector("#garden-back").onclick = () => menu.close();
  menu.addEventListener("close", () => {
    viewport?.removeEventListener("resize", fitMenu);
    viewport?.removeEventListener("scroll", fitMenu);
    if (resume) module._gardenChange(4, 0);
    resume = false;
    canvas.focus({preventScroll: true});
  });
  // SDL also listens on the window. Keep controls and number entry inside the dialog.
  for (const type of ["keydown", "keyup", "keypress", "pointerdown", "pointerup", "touchstart", "touchend"]) {
    menu.addEventListener(type, event => event.stopPropagation());
  }
  const timer = setInterval(updateAvailability, 300);
  return () => {
    clearInterval(timer);
    resume = false;
    if (menu.open) menu.close();
    trigger.hidden = true;
  };
}
