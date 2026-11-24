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

  trigger.addEventListener("click", () => {
    if (!updateAvailability()) return;
    resume = module._gardenState(4) === 0;
    if (resume) module._gardenChange(4, 1);
    sun.value = module._gardenState(0);
    coins.value = module._gardenState(1);
    free.checked = Boolean(module._gardenState(2));
    speed.value = module._gardenState(3);
    message.textContent = "Partida pausada";
    menu.showModal();
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
  menu.querySelector("#garden-back").onclick = () => menu.close();
  menu.addEventListener("close", () => {
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
