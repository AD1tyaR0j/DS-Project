// Progressive enhancements. Every page still works without this file.
(() => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  // Score count-up, synced with the dial sweep. The final number is already in the HTML.
  $$("[data-count]").forEach((el) => {
    const target = Number(el.dataset.count);
    if (reduce || !target) return;
    const duration = 1200, start = performance.now() + 100;
    const ease = (t) => 1 - Math.pow(1 - t, 4);
    el.textContent = "0";
    const tick = (now) => {
      const t = Math.min(1, Math.max(0, (now - start) / duration));
      el.textContent = String(Math.round(ease(t) * target));
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });

  const form = $("[data-composer]");
  if (!form) return;

  // Example messages (all fictitious) so the scoring can be explored without real data.
  const SAMPLES = [
    { kind: "phish", channel: "email", name: "Account suspended (PayPal look-alike)",
      fields: { sender: "PayPal Security <alert@paypa1-verify.xyz>", subject: "URGENT: Your account has been suspended",
        body: "Dear customer,\n\nWe noticed unusual activity and your account will be suspended within 24 hours.\nVerify your identity now at http://paypa1-verify.xyz/login and confirm your card number and CVV.\n\nPayPal Security Team" } },
    { kind: "phish", channel: "email", name: "CEO gift-card request",
      fields: { sender: "Rahul Mehta (CEO) <rahul.mehta.ceo@gmail.com>", reply_to: "ceo.office.private@outlook.com", subject: "Quick favour - confidential",
        body: "Are you at your desk? I need you to buy 5 Amazon gift cards of Rs 10,000 each for a client today. Keep this confidential and send me the codes as soon as possible. I'm in a meeting so can't take calls." } },
    { kind: "safe", channel: "email", name: "Team lunch invite",
      fields: { sender: "Priya Sharma <priya@company.com>", subject: "Lunch on Friday?",
        body: "Hi all,\n\nShall we do team lunch this Friday at 1pm? Reply with your preference: Italian or Thai.\n\nThanks,\nPriya" } },
    { kind: "phish", channel: "sms", name: "Parcel redelivery fee",
      fields: { sender: "+91 98765 43210", body: "India Post: Your parcel is on hold due to incomplete address. Pay Rs 25 redelivery fee within 12 hours: http://indiapost-help.top/pay" } },
    { kind: "phish", channel: "sms", name: "KYC update / OTP request",
      fields: { sender: "+91 70123 45678", body: "Dear SBI user, your account will be blocked today. Update KYC immediately at http://bit.ly/sbi-kyc-upd and share the OTP sent to you with our executive." } },
    { kind: "safe", channel: "sms", name: "Bank OTP (legitimate)",
      fields: { sender: "VM-HDFCBK", body: "123456 is your OTP for a transaction of Rs 1,250 at AMAZON. Valid for 10 minutes. Do not share this OTP with anyone. -HDFC Bank" } },
    { kind: "phish", channel: "url", name: "Raw IP login page", fields: { url: "http://192.168.10.24/secure/account/login.php" } },
    { kind: "phish", channel: "url", name: "Brand in the wrong domain", fields: { url: "https://microsoft-account-verify.support-login.top/signin" } },
    { kind: "safe", channel: "url", name: "Official site", fields: { url: "https://www.github.com/login" } },
  ];
  const CHANNEL_LABEL = { email: "Email", sms: "SMS", url: "Link" };

  const channelInput = $("[data-channel-input]", form);
  const panels = $$("[data-panel]", form);
  const tabs = $$("[data-tab]", form);

  function setChannel(channel, focus = false) {
    channelInput.value = channel;
    tabs.forEach((t) => {
      const on = t.dataset.tab === channel;
      t.classList.toggle("on", on);
      t.setAttribute("aria-selected", String(on));
    });
    panels.forEach((p) => {
      const on = p.dataset.panel === channel;
      p.hidden = !on;
      p.disabled = !on; // disabled fieldsets are not submitted, so duplicate field names never clash
    });
    const url = new URL(location.href);
    url.searchParams.set("channel", channel);
    history.replaceState(null, "", url);
    if (focus) $("[data-panel='" + channel + "'] textarea, [data-panel='" + channel + "'] input:not([type=file])", form)?.focus();
  }

  tabs.forEach((t) => t.addEventListener("click", (e) => {
    if (e.metaKey || e.ctrlKey || e.shiftKey) return;
    e.preventDefault();
    setChannel(t.dataset.tab, true);
  }));

  // Sample list
  const sampleBox = $("[data-samples]");
  const sampleList = $("[data-sample-list]");
  if (sampleBox && sampleList) {
    SAMPLES.forEach((s) => {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.type = "button";
      b.innerHTML = `<span class="s-kind ${s.kind === "safe" ? "safe" : ""}">${s.kind === "safe" ? "Safe" : "Scam"}</span>` +
        `<span class="s-name"></span><span class="s-ch">${CHANNEL_LABEL[s.channel]}</span>`;
      b.querySelector(".s-name").textContent = s.name;
      b.addEventListener("click", () => loadSample(s));
      li.append(b);
      sampleList.append(li);
    });
    sampleBox.hidden = false;
  }

  function clearPanel(panel) {
    $$("input:not([type=file]), textarea", panel).forEach((el) => { el.value = ""; });
    const file = $("input[type=file]", panel);
    if (file) { file.value = ""; file.dispatchEvent(new Event("change")); }
  }

  function loadSample(s) {
    setChannel(s.channel);
    const panel = $(`[data-panel='${s.channel}']`, form);
    clearPanel(panel);
    Object.entries(s.fields).forEach(([name, value]) => {
      const el = $(`[name='${name}']`, panel);
      if (el) el.value = value;
    });
    $("button[type=submit]", form).focus({ preventScroll: true });
    if (window.innerWidth < 980) form.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  }

  $("[data-clear]", form)?.addEventListener("click", () => {
    clearPanel($(`[data-panel='${channelInput.value}']`, form));
  });

  // .eml dropzone: show the chosen file and accept drag-and-drop.
  const zone = $("[data-dropzone]", form);
  if (zone) {
    const input = $("input[type=file]", zone);
    const text = $("[data-dropzone-text]", zone);
    const original = text.innerHTML;
    input.addEventListener("change", () => {
      const f = input.files && input.files[0];
      zone.classList.toggle("has-file", Boolean(f));
      if (f) {
        text.innerHTML = "<b></b> will be analysed instead of the fields above";
        text.querySelector("b").textContent = f.name;
      } else {
        text.innerHTML = original;
      }
    });
    ["dragenter", "dragover"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => zone.addEventListener(ev, () => zone.classList.remove("over")));
    zone.addEventListener("drop", (e) => {
      e.preventDefault();
      if (e.dataTransfer?.files?.length) {
        input.files = e.dataTransfer.files;
        input.dispatchEvent(new Event("change"));
      }
    });
  }

  // Ctrl/Cmd + Enter submits.
  form.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); form.requestSubmit(); }
  });

  // Scanning state while the request is in flight.
  const submit = $("button[type=submit]", form);
  const label = submit.innerHTML;
  form.addEventListener("submit", () => {
    form.classList.add("scanning");
    submit.disabled = true;
    submit.innerHTML = '<span class="spinner" aria-hidden="true"></span> Analysing…';
  });
  // Restore the form when the user comes back with the browser's back button.
  window.addEventListener("pageshow", (e) => {
    if (!e.persisted) return;
    form.classList.remove("scanning");
    submit.disabled = false;
    submit.innerHTML = label;
  });
})();
