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
  // Presets only use commands that the currently shipped native engine exposes.
  function preset(commands, feedback) {
    for (const [field, value] of commands) {
      if (!module._gardenChange(field, value)) { menu.close(); return; }
    }
    sun.value = module._gardenState(0);
    coins.value = module._gardenState(1);
    free.checked = Boolean(module._gardenState(2));
    speed.value = module._gardenState(3);
    message.textContent = feedback;
  }
  menu.querySelector("#garden-relaxed").onclick = () => preset([[0,9990],[2,1],[3,1]], "Sol máximo e plantio grátis.");
  menu.querySelector("#garden-normal").onclick = () => preset([[2,0],[3,1]], "Custo e velocidade normais.");
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
