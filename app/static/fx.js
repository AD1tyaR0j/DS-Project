// Visual effects for PhishGuard. A live "threat globe" backdrop (rotating particle sphere, attack arcs,
// drifting dust), pointer-driven micro-interactions and text effects. Purely decorative: pages work the
// same without it, and it stands down for reduced-motion users.
(() => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = window.matchMedia("(pointer: fine)").matches;
  document.documentElement.classList.add("fx");

  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const TAU = Math.PI * 2;

  const pointer = { x: innerWidth * 0.7, y: innerHeight * 0.35, sx: innerWidth * 0.7, sy: innerHeight * 0.35, active: false, down: false, lastX: 0 };
  addEventListener("pointermove", (e) => { pointer.x = e.clientX; pointer.y = e.clientY; pointer.active = true; }, { passive: true });
  document.addEventListener("pointerleave", () => { pointer.active = false; });

  /* ------------------------------------------------------------------ palette */
  const PAL = { accent: [34, 211, 238], violet: [167, 139, 250], blue: [96, 165, 250], low: [52, 211, 153], med: [251, 191, 36], high: [251, 146, 60], crit: [251, 59, 100], white: [234, 240, 253] };
  const rgba = (c, a) => `rgba(${c[0]},${c[1]},${c[2]},${clamp(a, 0, 1).toFixed(3)})`;
  const mix = (a, b, t) => [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)].map(Math.round);
  function riskColor(r) {
    if (r >= 75) return PAL.crit;
    if (r >= 50) return mix(PAL.high, PAL.crit, (r - 50) / 25);
    if (r >= 25) return mix(PAL.med, PAL.high, (r - 25) / 25);
    return mix(PAL.accent, PAL.med, r / 25 * 0.4);
  }

  /* ------------------------------------------------------------------ globe backdrop */
  const canvas = document.querySelector("[data-backdrop]");
  const ctx = canvas && canvas.getContext("2d");
  const mode = document.body.dataset.globe || "ambient";
  let risk = Number(document.body.dataset.score || 0) || 0, targetRisk = risk;
  let W = 0, H = 0, dpr = 1, R = 200, cx = 0, cy = 0, fade = 1;
  let sphere = [], dust = [], arcs = [], bursts = [], rings = [];
  let rotY = 0, rotX = -0.35, tiltX = 0, tiltY = 0, spin = 0.0022, dragV = 0;

  function buildSphere() {
    const n = W < 700 ? 520 : 900;
    sphere = [];
    const golden = Math.PI * (3 - Math.sqrt(5));
    for (let i = 0; i < n; i++) {
      const y = 1 - (i / (n - 1)) * 2, r = Math.sqrt(1 - y * y), th = golden * i;
      sphere.push({ x: Math.cos(th) * r, y, z: Math.sin(th) * r, tw: Math.random() * TAU });
    }
  }
  function layout() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = innerWidth; H = innerHeight;
    canvas.width = W * dpr; canvas.height = H * dpr;
    canvas.style.width = W + "px"; canvas.style.height = H + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const wide = W >= 1020;
    if (mode === "hero") {
      R = wide ? Math.min(W * 0.24, H * 0.42, 330) : Math.min(W * 0.42, 240);
      cx = wide ? Math.min(W * 0.76, W / 2 + 400) : W * 0.5;
      cy = wide ? 330 : 280;
      fade = wide ? 1 : 0.45;
    } else {
      R = wide ? Math.min(W * 0.2, 300) : Math.min(W * 0.45, 220);
      cx = wide ? W * 0.86 : W * 0.6;
      cy = H * 0.62;
      fade = 0.55;
    }
    if (!sphere.length || (W < 700) !== (sphere.length < 900)) buildSphere();
    const want = clamp(Math.round((W * H) / 14000), 40, 120);
    while (dust.length < want) dust.push(makeDust(true));
    dust.length = want;
  }
  function makeDust(anywhere) {
    return { x: Math.random() * W, y: anywhere ? Math.random() * H : H + 10, z: 0.2 + Math.random() * 0.8, vy: 0.1 + Math.random() * 0.35, tw: Math.random() * TAU };
  }

  // Rotate a unit-sphere point and project it.
  function project(p, scale = 1) {
    let { x, y, z } = p;
    const ry = rotY + tiltY, rx = rotX + tiltX;
    const cosY = Math.cos(ry), sinY = Math.sin(ry);
    let x1 = x * cosY - z * sinY, z1 = x * sinY + z * cosY;
    const cosX = Math.cos(rx), sinX = Math.sin(rx);
    let y1 = y * cosX - z1 * sinX, z2 = y * sinX + z1 * cosX;
    x1 *= scale; y1 *= scale; z2 *= scale;
    const persp = 2.6 / (2.6 + z2);
    return { x: cx + x1 * R * persp, y: cy + y1 * R * persp, z: z2, s: persp };
  }
  function slerp(a, b, t) {
    const dot = clamp(a.x * b.x + a.y * b.y + a.z * b.z, -1, 1), om = Math.acos(dot);
    if (om < 1e-4) return a;
    const s = Math.sin(om), k1 = Math.sin((1 - t) * om) / s, k2 = Math.sin(t * om) / s;
    return { x: a.x * k1 + b.x * k2, y: a.y * k1 + b.y * k2, z: a.z * k1 + b.z * k2 };
  }
  function spawnArc(from) {
    const a = from || sphere[(Math.random() * sphere.length) | 0];
    let b = sphere[(Math.random() * sphere.length) | 0], tries = 0;
    while (tries++ < 8 && a.x * b.x + a.y * b.y + a.z * b.z > 0.6) b = sphere[(Math.random() * sphere.length) | 0];
    const threat = Math.random() < 0.18 + (risk / 100) * 0.75;
    arcs.push({ a, b, t: 0, speed: 0.006 + Math.random() * 0.006, threat, lift: 0.18 + Math.random() * 0.3 });
  }

  let last = performance.now(), arcTimer = 0, running = false, scrollY0 = scrollY;
  addEventListener("scroll", () => { scrollY0 = scrollY; }, { passive: true });

  function frame(now) {
    const dt = Math.min(50, now - last) / 16.67; last = now;
    const still = reduce.matches;
    risk += (targetRisk - risk) * 0.05 * dt;
    const rc = riskColor(risk);
    ctx.clearRect(0, 0, W, H);

    // Interaction: tilt toward pointer, drag to spin.
    if (!still) {
      const tx = finePointer && pointer.active ? (pointer.y / H - 0.5) * 0.5 : 0;
      const ty = finePointer && pointer.active ? (pointer.x / W - 0.5) * 0.9 : 0;
      tiltX += (tx - tiltX) * 0.04 * dt; tiltY += (ty - tiltY) * 0.04 * dt;
      dragV *= Math.pow(0.95, dt);
      rotY += (spin + dragV) * dt;
    }
    const gy = cy - (mode === "hero" ? scrollY0 * 0.35 : 0);
    const savedCy = cy; cy = gy;

    // Dust (parallax with pointer).
    const px = finePointer && pointer.active ? (pointer.x / W - 0.5) : 0, py = finePointer && pointer.active ? (pointer.y / H - 0.5) : 0;
    for (const d of dust) {
      if (!still) { d.y -= d.vy * d.z * dt; d.tw += 0.03 * dt; if (d.y < -10) Object.assign(d, makeDust(false)); }
      const x = d.x - px * 30 * d.z, y = d.y - py * 30 * d.z;
      ctx.fillStyle = rgba(d.z > 0.7 ? PAL.white : mix(PAL.accent, rc, 0.5), (0.15 + 0.35 * d.z) * (0.6 + 0.4 * Math.sin(d.tw)));
      ctx.beginPath(); ctx.arc(x, y, 0.5 + d.z * 1.3, 0, TAU); ctx.fill();
    }

    // Halo behind the globe.
    const halo = ctx.createRadialGradient(cx, cy, R * 0.6, cx, cy, R * 1.7);
    halo.addColorStop(0, rgba(rc, 0.16 * fade)); halo.addColorStop(0.5, rgba(PAL.violet, 0.06 * fade)); halo.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = halo; ctx.beginPath(); ctx.arc(cx, cy, R * 1.7, 0, TAU); ctx.fill();
    // Atmosphere rim.
    ctx.strokeStyle = rgba(rc, 0.22 * fade); ctx.lineWidth = 1.2;
    ctx.beginPath(); ctx.arc(cx, cy, R * 1.0, 0, TAU); ctx.stroke(); ctx.lineWidth = 1;

    // Orbit rings with satellites.
    for (let k = 0; k < 2; k++) {
      const tilt = k ? 1.15 : -0.5, rad = k ? 1.35 : 1.18, sp = k ? -0.6 : 1;
      ctx.strokeStyle = rgba(k ? PAL.violet : PAL.accent, 0.18 * fade);
      ctx.setLineDash([2, 6]); ctx.beginPath();
      for (let i = 0; i <= 64; i++) {
        const t = (i / 64) * TAU;
        const p = project({ x: Math.cos(t), y: Math.sin(t) * Math.sin(tilt), z: Math.sin(t) * Math.cos(tilt) }, rad);
        i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y);
      }
      ctx.stroke(); ctx.setLineDash([]);
      const st = (now / 1000) * 0.5 * sp + k * 2;
      const sat = project({ x: Math.cos(st), y: Math.sin(st) * Math.sin(tilt), z: Math.sin(st) * Math.cos(tilt) }, rad);
      ctx.fillStyle = rgba(k ? PAL.violet : PAL.accent, (sat.z < 0 ? 0.95 : 0.35) * fade);
      ctx.shadowColor = rgba(k ? PAL.violet : PAL.accent, 1); ctx.shadowBlur = 12;
      ctx.beginPath(); ctx.arc(sat.x, sat.y, 2.6 * sat.s, 0, TAU); ctx.fill(); ctx.shadowBlur = 0;
    }

    // Sphere points: front brighter, back faint. Pointer proximity lights them up.
    const pr = pointer.active && finePointer ? 110 : 0;
    for (const p of sphere) {
      const q = project(p);
      const front = q.z < 0;
      p.tw += 0.02 * dt;
      let a = front ? 0.7 + 0.3 * Math.sin(p.tw) * 0.4 : 0.12;
      let col = front ? mix(PAL.accent, rc, 0.55) : PAL.blue;
      if (pr) {
        const d = Math.hypot(q.x - pointer.x, q.y - pointer.y);
        if (d < pr && front) { const k = 1 - d / pr; a = Math.min(1, a + k); col = mix(col, PAL.white, k * 0.7); }
      }
      ctx.fillStyle = rgba(col, a * fade);
      const sz = front ? 2.1 * q.s : 1.4 * q.s;
      ctx.fillRect(q.x - sz / 2, q.y - sz / 2, sz, sz);
    }

    // Attack arcs.
    if (!still) {
      arcTimer -= dt;
      if (arcTimer <= 0) { spawnArc(); arcTimer = 26 - (risk / 100) * 16 + Math.random() * 10; }
    }
    for (let i = arcs.length - 1; i >= 0; i--) {
      const A = arcs[i];
      if (!still) A.t += A.speed * dt;
      const head = Math.min(1, A.t), tail = clamp(A.t - 0.35, 0, 1);
      const col = A.threat ? riskColor(Math.max(risk, 80)) : PAL.accent;
      const steps = 26;
      let prev = null;
      for (let s = 0; s <= steps; s++) {
        const t = tail + (head - tail) * (s / steps);
        const p = slerp(A.a, A.b, t);
        const q = project(p, 1 + Math.sin(Math.PI * t) * A.lift);
        if (prev) {
          const alpha = (s / steps) * (q.z < 0.15 ? 0.95 : 0.25) * fade;
          ctx.strokeStyle = rgba(col, alpha); ctx.lineWidth = 1.6 * q.s;
          ctx.beginPath(); ctx.moveTo(prev.x, prev.y); ctx.lineTo(q.x, q.y); ctx.stroke();
        }
        prev = q;
      }
      ctx.lineWidth = 1;
      if (A.t < 1 && prev) {
        ctx.fillStyle = rgba(PAL.white, 0.95 * fade); ctx.shadowColor = rgba(col, 1); ctx.shadowBlur = 14;
        ctx.beginPath(); ctx.arc(prev.x, prev.y, 2.2 * prev.s, 0, TAU); ctx.fill(); ctx.shadowBlur = 0;
      }
      if (A.t >= 1 && !A.hit) { A.hit = true; rings.push({ p: A.b, r: 0, a: 1, col }); }
      if (A.t > 1.35) arcs.splice(i, 1);
    }
    // Impact rings on the surface.
    for (let i = rings.length - 1; i >= 0; i--) {
      const g = rings[i];
      if (!still) { g.r += 0.9 * dt; g.a -= 0.025 * dt; }
      if (g.a <= 0) { rings.splice(i, 1); continue; }
      const q = project(g.p);
      if (q.z > 0.1) continue;
      ctx.strokeStyle = rgba(g.col, g.a * fade); ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.ellipse(q.x, q.y, g.r * q.s, g.r * 0.55 * q.s, 0, 0, TAU); ctx.stroke(); ctx.lineWidth = 1;
    }
    cy = savedCy;

    // Particle bursts (clicks, verdict reveal).
    for (let i = bursts.length - 1; i >= 0; i--) {
      const b = bursts[i];
      b.life -= 0.016 * dt;
      if (b.life <= 0) { bursts.splice(i, 1); continue; }
      if (b.ring) {
        b.r += 7 * dt;
        ctx.strokeStyle = rgba(b.col, b.life * 0.8); ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(b.x, b.y, b.r, 0, TAU); ctx.stroke(); ctx.lineWidth = 1;
        continue;
      }
      b.vx *= 0.97; b.vy = b.vy * 0.97 + 0.04; b.x += b.vx * dt; b.y += b.vy * dt;
      ctx.fillStyle = rgba(b.col, b.life);
      ctx.beginPath(); ctx.arc(b.x, b.y, b.size * b.life + 0.4, 0, TAU); ctx.fill();
    }

    if (running) requestAnimationFrame(frame);
  }

  function burst(x, y, col = PAL.accent, n = 36, power = 6) {
    if (reduce.matches) return;
    bursts.push({ ring: true, x, y, r: 6, life: 1, col });
    for (let i = 0; i < n; i++) {
      const a = Math.random() * TAU, sp = (0.4 + Math.random()) * power;
      bursts.push({ x, y, vx: Math.cos(a) * sp, vy: Math.sin(a) * sp - 1, life: 0.7 + Math.random() * 0.5, size: 1 + Math.random() * 2.2, col: Math.random() < 0.3 ? PAL.white : col });
    }
    if (!running) start();
  }

  function start() {
    if (running || reduce.matches || document.hidden) return;
    running = true; last = performance.now(); requestAnimationFrame(frame);
  }
  function stop() { running = false; }

  if (ctx) {
    layout();
    for (let i = 0; i < 4; i++) { spawnArc(); arcs[i].t = Math.random() * 0.8; }
    if (reduce.matches) frame(performance.now()); else start();
    addEventListener("resize", () => { layout(); if (!running) frame(performance.now()); });
    document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
    reduce.addEventListener("change", () => (reduce.matches ? (stop(), frame(performance.now())) : start()));

    // Clicking empty space fires a burst and a salvo of arcs; dragging spins the globe.
    const isUI = (t) => t.closest("a, button, input, textarea, label, select, .panel, .stat, .kpi, nav, .notice, .hero-stats, .badge");
    addEventListener("pointerdown", (e) => {
      if (reduce.matches || e.button !== 0 || isUI(e.target)) return;
      pointer.down = true; pointer.lastX = e.clientX;
      burst(e.clientX, e.clientY, riskColor(risk), 24, 5);
      for (let i = 0; i < 3; i++) spawnArc();
    });
    addEventListener("pointermove", (e) => {
      if (!pointer.down) return;
      dragV = clamp((e.clientX - pointer.lastX) * 0.0012, -0.08, 0.08); pointer.lastX = e.clientX;
    }, { passive: true });
    addEventListener("pointerup", () => { pointer.down = false; });
  }

  window.PhishFX = {
    setRisk(score) { targetRisk = clamp(Number(score) || 0, 0, 100); document.body.style.setProperty("--live-risk", targetRisk); },
    burst(x, y, score) { burst(x, y, riskColor(score ?? risk), 60, 7); },
  };

  /* ------------------------------------------------------------------ aura */
  const aura = document.querySelector(".aura");
  if (aura && finePointer) {
    const loop = () => {
      pointer.sx += (pointer.x - pointer.sx) * 0.08; pointer.sy += (pointer.y - pointer.sy) * 0.08;
      aura.style.setProperty("--ax", pointer.sx.toFixed(1) + "px"); aura.style.setProperty("--ay", pointer.sy.toFixed(1) + "px");
      aura.classList.toggle("on", pointer.active && !reduce.matches);
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  /* ------------------------------------------------------------------ DOM effects */
  document.addEventListener("DOMContentLoaded", () => {
    const motion = !reduce.matches;

    // Headline: split into words that rise in one after another.
    document.querySelectorAll("[data-split]").forEach((h) => {
      if (!motion) return;
      let i = 0;
      const walk = (node) => {
        [...node.childNodes].forEach((ch) => {
          if (ch.nodeType === 3) {
            const frag = document.createDocumentFragment();
            ch.textContent.split(/(\s+)/).forEach((part) => {
              if (!part) return;
              if (/^\s+$/.test(part)) { frag.append(part); return; }
              const s = document.createElement("span"); s.className = "w"; s.style.setProperty("--wi", i++); s.textContent = part; frag.append(s);
            });
            ch.replaceWith(frag);
          } else if (ch.nodeType === 1) walk(ch);
        });
      };
      walk(h);
    });

    // Eyebrow: decode/scramble effect.
    document.querySelectorAll("[data-scramble]").forEach((el) => {
      if (!motion) return;
      const final = el.textContent, glyphs = "!<>-_\\/[]{}=+*^?#01";
      let f = 0; const total = 28;
      const tick = () => {
        el.textContent = final.split("").map((c, k) => (c === " " || k < (f / total) * final.length ? c : glyphs[(Math.random() * glyphs.length) | 0])).join("");
        if (++f <= total) requestAnimationFrame(tick); else el.textContent = final;
      };
      setTimeout(tick, 150);
    });

    // Count-up numbers.
    const countUp = (el, target, dec) => {
      if (!motion || !isFinite(target)) return;
      const t0 = performance.now(), dur = 1400;
      const step = (now) => {
        const t = Math.min(1, (now - t0) / dur), v = target * (1 - Math.pow(1 - t, 4));
        el.firstChild.nodeValue = v.toFixed(dec);
        if (t < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    };
    document.querySelectorAll("[data-countup], .stat-num, .kpi-num, .cm b").forEach((el) => {
      const node = el.firstChild;
      if (!node || node.nodeType !== 3) return;
      const raw = node.nodeValue.trim(), n = parseFloat(raw);
      if (!isNaN(n) && n > 0) countUp(el, n, (raw.split(".")[1] || "").length);
    });

    // Verdict reveal: particle burst from the dial in the risk colour.
    const dial = document.querySelector(".verdict .dial");
    if (dial && motion) {
      setTimeout(() => {
        const r = dial.getBoundingClientRect();
        window.PhishFX.burst(r.left + r.width / 2, r.top + r.height / 2, Number(document.body.dataset.score || 0));
      }, 1350);
    }

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

    // 3D tilt on the verdict card.
    const tilt = document.querySelector(".verdict");
    if (tilt && finePointer) {
      tilt.addEventListener("pointermove", (e) => {
        if (reduce.matches) return;
        const r = tilt.getBoundingClientRect();
        tilt.style.setProperty("--rx", (-((e.clientY - r.top) / r.height - 0.5) * 10).toFixed(2) + "deg");
        tilt.style.setProperty("--ry", (((e.clientX - r.left) / r.width - 0.5) * 10).toFixed(2) + "deg");
      });
      tilt.addEventListener("pointerleave", () => { tilt.style.setProperty("--rx", "0deg"); tilt.style.setProperty("--ry", "0deg"); });
    }

    // Magnetic primary buttons.
    if (finePointer) {
      document.querySelectorAll(".btn.primary").forEach((b) => {
        b.addEventListener("pointermove", (e) => {
          if (reduce.matches || b.disabled) return;
          const r = b.getBoundingClientRect();
          b.style.setProperty("--mx", ((e.clientX - r.left - r.width / 2) * 0.25).toFixed(1) + "px");
          b.style.setProperty("--my", ((e.clientY - r.top - r.height / 2) * 0.35).toFixed(1) + "px");
        });
        b.addEventListener("pointerleave", () => { b.style.setProperty("--mx", "0px"); b.style.setProperty("--my", "0px"); });
      });
    }

    // Ripple on buttons, tabs and samples; a small burst for the primary action.
    document.addEventListener("pointerdown", (e) => {
      const el = e.target.closest(".btn, .sample-list button, .segmented a");
      if (!el || reduce.matches) return;
      const r = el.getBoundingClientRect(), size = Math.max(r.width, r.height) * 2.2;
      const s = document.createElement("span");
      s.className = "ripple";
      s.style.cssText = `width:${size}px;height:${size}px;left:${e.clientX - r.left - size / 2}px;top:${e.clientY - r.top - size / 2}px`;
      el.append(s);
      s.addEventListener("animationend", () => s.remove());
      if (el.matches(".btn.primary, .sample-list button")) burst(e.clientX, e.clientY, PAL.accent, 18, 4);
    });

    // Reveal cards below the fold as they scroll in (cards already on screen are left alone).
    if ("IntersectionObserver" in window && motion) {
      const io = new IntersectionObserver((entries) => {
        entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
      }, { rootMargin: "0px 0px -6% 0px" });
      document.querySelectorAll(".report-main .panel, .two-col .panel, .side .panel, .ev-group, .panel.flush").forEach((el) => {
        if (el.getBoundingClientRect().top > innerHeight) { el.classList.add("reveal"); io.observe(el); }
      });
    }
  });
})();
