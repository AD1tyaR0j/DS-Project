// Visual effects: an interactive "threat network" backdrop plus pointer-driven micro-interactions.
// Purely decorative. Pages work the same without it, and it stands down for reduced-motion users.
(() => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = window.matchMedia("(pointer: fine)").matches;
  document.documentElement.classList.add("fx");

  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  // Shared pointer state (viewport coordinates), smoothed for the aura.
  const pointer = { x: innerWidth / 2, y: innerHeight * 0.3, sx: innerWidth / 2, sy: innerHeight * 0.3, active: false };
  addEventListener("pointermove", (e) => { pointer.x = e.clientX; pointer.y = e.clientY; pointer.active = true; }, { passive: true });
  document.addEventListener("pointerleave", () => { pointer.active = false; });

  /* ------------------------------------------------------------------ backdrop */
  const canvas = document.querySelector("[data-backdrop]");
  const ctx = canvas && canvas.getContext("2d");
  let W = 0, H = 0, dpr = 1, nodes = [], pulses = [], colors = {};
  let risk = Number(document.body.dataset.score || 0) || 0; // 0-100, drives how many nodes get flagged
  let targetRisk = risk;

  function readColors() {
    colors = { accent: css("--accent"), muted: css("--muted"), crit: css("--crit"), high: css("--high"), med: css("--med"), low: css("--low") };
  }
  function riskColor(r) { return r >= 75 ? colors.crit : r >= 50 ? colors.high : r >= 25 ? colors.med : colors.accent; }

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = innerWidth; H = innerHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const want = clamp(Math.round((W * H) / 16000), 28, 95);
    while (nodes.length < want) nodes.push(makeNode());
    nodes.length = want;
  }
  function makeNode() {
    const a = Math.random() * Math.PI * 2, sp = 0.08 + Math.random() * 0.22;
    return { x: Math.random() * W, y: Math.random() * H, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp,
             r: 1 + Math.random() * 1.6, flag: 0, phase: Math.random() * Math.PI * 2 };
  }

  const LINK = 130, REPEL = 150;
  let last = performance.now(), sweep = -0.2, running = false;

  function frame(now) {
    const dt = Math.min(48, now - last) / 16.67; last = now;
    risk += (targetRisk - risk) * 0.04 * dt;
    ctx.clearRect(0, 0, W, H);

    // Radar sweep band travelling down the screen.
    sweep += 0.0016 * dt; if (sweep > 1.25) sweep = -0.25;
    const sy = sweep * H;
    const band = ctx.createLinearGradient(0, sy - 120, 0, sy + 2);
    band.addColorStop(0, "transparent");
    band.addColorStop(1, hexA(riskColor(risk), 0.07));
    ctx.fillStyle = band; ctx.fillRect(0, sy - 120, W, 122);
    ctx.fillStyle = hexA(riskColor(risk), 0.18); ctx.fillRect(0, sy, W, 1);

    // Flag a few nodes as "suspicious"; more of them as the risk climbs.
    const flagChance = 0.0004 + (risk / 100) ** 1.6 * 0.008;
    const mx = pointer.x, my = pointer.y;

    for (const n of nodes) {
      if (!reduce.matches) {
        if (pointer.active && finePointer) {
          const dx = n.x - mx, dy = n.y - my, d2 = dx * dx + dy * dy;
          if (d2 < REPEL * REPEL && d2 > 1) {
            const d = Math.sqrt(d2), f = (1 - d / REPEL) * 0.6;
            n.vx += (dx / d) * f * 0.08 * dt; n.vy += (dy / d) * f * 0.08 * dt;
          }
        }
        n.vx *= 0.985; n.vy *= 0.985;
        const sp = Math.hypot(n.vx, n.vy);
        if (sp < 0.08) { n.vx += (Math.random() - 0.5) * 0.02; n.vy += (Math.random() - 0.5) * 0.02; }
        n.x += n.vx * dt; n.y += n.vy * dt;
        if (n.x < -20) n.x = W + 20; else if (n.x > W + 20) n.x = -20;
        if (n.y < -20) n.y = H + 20; else if (n.y > H + 20) n.y = -20;
        if (n.flag <= 0 && Math.random() < flagChance * dt) n.flag = 1;
        if (n.flag > 0) n.flag -= 0.004 * dt;
      }
    }

    // Links between neighbours.
    ctx.lineWidth = 1;
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j], dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy;
        if (d2 > LINK * LINK) continue;
        const t = 1 - Math.sqrt(d2) / LINK;
        const hot = Math.max(a.flag, b.flag);
        ctx.strokeStyle = hot > 0 ? hexA(riskColor(Math.max(risk, 60)), t * 0.35 * hot + t * 0.08) : hexA(colors.muted, t * 0.16);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }
    }

    // Scanner lines from the cursor to nearby nodes.
    if (pointer.active && finePointer && !reduce.matches) {
      for (const n of nodes) {
        const d = Math.hypot(n.x - mx, n.y - my);
        if (d > REPEL * 1.35) continue;
        const t = 1 - d / (REPEL * 1.35);
        ctx.strokeStyle = hexA(colors.accent, t * 0.45);
        ctx.beginPath(); ctx.moveTo(mx, my); ctx.lineTo(n.x, n.y); ctx.stroke();
      }
      ctx.fillStyle = hexA(colors.accent, 0.5);
      ctx.beginPath(); ctx.arc(mx, my, 2.2, 0, Math.PI * 2); ctx.fill();
    }

    // Nodes, with a pulsing ring on flagged ones and a glint as the sweep passes.
    for (const n of nodes) {
      const near = Math.max(0, 1 - Math.abs(n.y - sy) / 60);
      if (n.flag > 0) {
        const c = riskColor(Math.max(risk, 60));
        const ring = (1 - n.flag) * 14 + 3;
        ctx.strokeStyle = hexA(c, n.flag * 0.55);
        ctx.beginPath(); ctx.arc(n.x, n.y, ring, 0, Math.PI * 2); ctx.stroke();
        ctx.fillStyle = hexA(c, 0.5 + n.flag * 0.5);
        ctx.beginPath(); ctx.arc(n.x, n.y, n.r + 1, 0, Math.PI * 2); ctx.fill();
      } else {
        ctx.fillStyle = near > 0 ? hexA(riskColor(risk), 0.25 + near * 0.6) : hexA(colors.muted, 0.35);
        ctx.beginPath(); ctx.arc(n.x, n.y, n.r + near, 0, Math.PI * 2); ctx.fill();
      }
    }

    // Click shockwaves.
    for (let i = pulses.length - 1; i >= 0; i--) {
      const p = pulses[i];
      p.r += 6 * dt; p.a -= 0.018 * dt;
      if (p.a <= 0) { pulses.splice(i, 1); continue; }
      ctx.strokeStyle = hexA(colors.accent, p.a * 0.6); ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.stroke(); ctx.lineWidth = 1;
      for (const n of nodes) {
        const dx = n.x - p.x, dy = n.y - p.y, d = Math.hypot(dx, dy);
        if (Math.abs(d - p.r) < 18 && d > 1) { n.vx += (dx / d) * 0.35 * p.a; n.vy += (dy / d) * 0.35 * p.a; }
      }
    }

    if (running) requestAnimationFrame(frame);
  }

  // Colour helper: accepts #rrggbb / #rgb and returns rgba() with the given alpha.
  const hexCache = {};
  function hexA(hex, a) {
    a = clamp(a, 0, 1);
    let rgb = hexCache[hex];
    if (!rgb) {
      let h = hex.replace("#", "");
      if (h.length === 3) h = h.split("").map((c) => c + c).join("");
      const n = parseInt(h, 16);
      rgb = hexCache[hex] = Number.isNaN(n) ? [128, 128, 128] : [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    }
    return `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${a.toFixed(3)})`;
  }

  function start() {
    if (running || reduce.matches || document.hidden) return;
    running = true; last = performance.now(); requestAnimationFrame(frame);
  }
  function stop() { running = false; }

  if (ctx) {
    readColors(); resize();
    if (reduce.matches) frame(performance.now()); else start();
    addEventListener("resize", () => { resize(); if (!running) frame(performance.now()); });
    document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { readColors(); if (!running) frame(performance.now()); });
    reduce.addEventListener("change", () => (reduce.matches ? (stop(), frame(performance.now())) : start()));

    // Clicking empty space sends a shockwave through the network.
    addEventListener("pointerdown", (e) => {
      if (reduce.matches || e.button !== 0) return;
      if (e.target.closest("a, button, input, textarea, label, select, .panel, .stat, .kpi, nav, .notice, summary")) return;
      pulses.push({ x: e.clientX, y: e.clientY, r: 4, a: 1 });
    });
  }

  // Other scripts (the live estimate) can steer the backdrop's risk colour.
  window.PhishFX = { setRisk(score) { targetRisk = clamp(Number(score) || 0, 0, 100); } };

  /* ------------------------------------------------------------------ aura */
  const aura = document.querySelector(".aura");
  if (aura && finePointer) {
    const loop = () => {
      pointer.sx += (pointer.x - pointer.sx) * 0.08;
      pointer.sy += (pointer.y - pointer.sy) * 0.08;
      aura.style.setProperty("--ax", pointer.sx.toFixed(1) + "px");
      aura.style.setProperty("--ay", pointer.sy.toFixed(1) + "px");
      aura.classList.toggle("on", pointer.active && !reduce.matches);
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  /* ------------------------------------------------------------------ micro-interactions */
  document.addEventListener("DOMContentLoaded", () => {
    // Cursor spotlight on cards.
    if (finePointer) {
      document.addEventListener("pointermove", (e) => {
        const el = e.target.closest(".panel, .stat, .kpi, .sample-list button");
        if (!el) return;
        const r = el.getBoundingClientRect();
        el.style.setProperty("--sx", (e.clientX - r.left).toFixed(0) + "px");
        el.style.setProperty("--sy", (e.clientY - r.top).toFixed(0) + "px");
      }, { passive: true });
    }

    // Gentle 3D tilt on the verdict card.
    const tilt = document.querySelector(".verdict");
    if (tilt && finePointer) {
      tilt.addEventListener("pointermove", (e) => {
        if (reduce.matches) return;
        const r = tilt.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width - 0.5, py = (e.clientY - r.top) / r.height - 0.5;
        tilt.style.setProperty("--rx", (-py * 6).toFixed(2) + "deg");
        tilt.style.setProperty("--ry", (px * 6).toFixed(2) + "deg");
      });
      tilt.addEventListener("pointerleave", () => { tilt.style.setProperty("--rx", "0deg"); tilt.style.setProperty("--ry", "0deg"); });
    }

    // Magnetic primary buttons.
    if (finePointer) {
      document.querySelectorAll(".btn.primary").forEach((b) => {
        b.addEventListener("pointermove", (e) => {
          if (reduce.matches || b.disabled) return;
          const r = b.getBoundingClientRect();
          b.style.setProperty("--mx", ((e.clientX - r.left - r.width / 2) * 0.18).toFixed(1) + "px");
          b.style.setProperty("--my", ((e.clientY - r.top - r.height / 2) * 0.3).toFixed(1) + "px");
        });
        b.addEventListener("pointerleave", () => { b.style.setProperty("--mx", "0px"); b.style.setProperty("--my", "0px"); });
      });
    }

    // Click ripple on buttons and sample items.
    document.addEventListener("pointerdown", (e) => {
      const el = e.target.closest(".btn, .sample-list button, .segmented a");
      if (!el || reduce.matches) return;
      const r = el.getBoundingClientRect(), size = Math.max(r.width, r.height) * 2;
      const s = document.createElement("span");
      s.className = "ripple";
      s.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX - r.left - size / 2}px;top:${e.clientY - r.top - size / 2}px`;
      el.append(s);
      s.addEventListener("animationend", () => s.remove());
    });

    // Reveal cards as they scroll into view (cards already on screen are left alone).
    if ("IntersectionObserver" in window && !reduce.matches) {
      const io = new IntersectionObserver((entries) => {
        entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
      }, { rootMargin: "0px 0px -8% 0px" });
      document.querySelectorAll(".report-main .panel, .two-col .panel, .side .panel, .ev-group").forEach((el) => {
        if (el.getBoundingClientRect().top > innerHeight) { el.classList.add("reveal"); io.observe(el); }
      });
    }
  });
})();
