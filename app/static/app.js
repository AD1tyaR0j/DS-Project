// Small progressive enhancements. Everything works without this file.
(() => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Score count-up, synced with the gauge sweep. The final number is already in the HTML.
  document.querySelectorAll("[data-count]").forEach((el) => {
    const target = Number(el.dataset.count);
    if (reduce || !target) return;
    const duration = 1200, delay = 120, start = performance.now() + delay;
    const ease = (t) => 1 - Math.pow(1 - t, 4);
    el.textContent = "0";
    const tick = (now) => {
      const t = Math.min(1, Math.max(0, (now - start) / duration));
      el.textContent = String(Math.round(ease(t) * target));
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });

  // Scanning state while the analysis request is in flight.
  document.querySelectorAll("form.form").forEach((form) => {
    form.addEventListener("submit", () => {
      const btn = form.querySelector("button[type=submit]");
      form.classList.add("scanning");
      if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner" aria-hidden="true"></span> Analysing…';
      }
    });
  });

  // Restore the form if the user comes back with the browser's back button.
  window.addEventListener("pageshow", (e) => {
    if (!e.persisted) return;
    document.querySelectorAll("form.scanning").forEach((f) => f.classList.remove("scanning"));
    document.querySelectorAll("button[data-label]").forEach((b) => { b.disabled = false; b.innerHTML = b.dataset.label; });
  });
  document.querySelectorAll("form.form button[type=submit]").forEach((b) => { b.dataset.label = b.innerHTML; });
})();
