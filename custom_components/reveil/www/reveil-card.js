/**
 * reveil-card — carte Lovelace pour l'intégration « Réveil ».
 *
 * Configuration minimale :
 *   type: custom:reveil-card
 *   device_id: 0123456789abcdef            # l'appareil « Réveil » (sélecteur dans l'éditeur)
 *   name: Réveil semaine                   # facultatif
 *
 * La carte retrouve toutes les entités de l'appareil via leur clé de traduction
 * (donc quelle que soit la langue). L'ancienne option `entity` (n'importe quelle
 * entité du réveil) reste acceptée.
 * Aucune dépendance : composant web natif.
 */

const CARD_VERSION = "0.1.0";

const DAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
];

const TEXTS = {
  fr: {
    today: "Aujourd'hui",
    tomorrow: "Demain",
    none: "Aucun réveil programmé",
    off: "Réveil désactivé",
    now: "Maintenant",
    lessThanMinute: "dans moins d'une minute",
    rel: (d, h, m) =>
      d
        ? `dans ${d} j ${h} h`
        : h
          ? `dans ${h} h ${String(m).padStart(2, "0")}`
          : `dans ${m} min`,
    lightFrom: (t) => `Lumière dès ${t}`,
    lightRising: "La lumière monte",
    defaultTime: "Heure par défaut",
    dayTime: (d) => `Heure du ${d}`,
    save: "Enregistrer",
    useDefault: "Utiliser l'heure par défaut",
    cancel: "Annuler",
    awake: "Je suis réveillé",
    toggleAlarm: "Activer ou désactiver le réveil",
    toggleDay: (d) => `Activer ou désactiver le ${d}`,
    editTime: (d) => `Modifier l'heure du ${d}`,
    missing: (e) => `Entité introuvable : ${e}`,
    notReveil: "Cet appareil ou cette entité n'appartient pas à l'intégration Réveil.",
    unsupported:
      "Cette version de Home Assistant n'expose pas les clés de traduction des entités. Mettez Home Assistant à jour.",
  },
  en: {
    today: "Today",
    tomorrow: "Tomorrow",
    none: "No alarm scheduled",
    off: "Alarm disabled",
    now: "Now",
    lessThanMinute: "in less than a minute",
    rel: (d, h, m) =>
      d
        ? `in ${d} d ${h} h`
        : h
          ? `in ${h} h ${String(m).padStart(2, "0")} min`
          : `in ${m} min`,
    lightFrom: (t) => `Light from ${t}`,
    lightRising: "Light is rising",
    defaultTime: "Default time",
    dayTime: (d) => `${d} time`,
    save: "Save",
    useDefault: "Use default time",
    cancel: "Cancel",
    awake: "I'm awake",
    toggleAlarm: "Turn the alarm on or off",
    toggleDay: (d) => `Turn ${d} on or off`,
    editTime: (d) => `Edit ${d} time`,
    missing: (e) => `Entity not found: ${e}`,
    notReveil: "This device or entity does not belong to the Réveil integration.",
    unsupported:
      "This Home Assistant version does not expose entity translation keys. Please update Home Assistant.",
  },
};

const esc = (s) =>
  String(s).replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]
  );

const capitalize = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

/** "07:00:00" -> "07:00:00" ; "unknown" / undefined -> null */
const validTime = (state) => (/^\d{2}:\d{2}/.test(state || "") ? state : null);

const STYLE = `
  :host { display: block; }
  ha-card { padding: 16px; }
  button { font: inherit; }
  button:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }
  .msg { color: var(--error-color, #db4437); font-size: 0.9rem; }

  .top { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  .name {
    font-size: 1rem; font-weight: 500; color: var(--primary-text-color);
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }
  .sw {
    position: relative; flex: none; width: 44px; height: 26px; padding: 0;
    border: 0; border-radius: 13px; cursor: pointer;
    background: var(--switch-unchecked-track-color, var(--divider-color));
    transition: background 0.15s;
  }
  .sw::after {
    content: ""; position: absolute; top: 3px; left: 3px;
    width: 20px; height: 20px; border-radius: 50%; background: #fff;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3); transition: transform 0.15s;
  }
  .sw[aria-checked="true"] { background: var(--primary-color); }
  .sw[aria-checked="true"]::after { transform: translateX(18px); }

  .body { transition: opacity 0.2s; }
  .off .body { opacity: 0.5; }

  .next { margin-top: 14px; }
  .when { font-size: 0.875rem; color: var(--secondary-text-color); }
  .nextrow { display: flex; align-items: baseline; flex-wrap: wrap; column-gap: 12px; }
  .time {
    font-size: 3.25rem; font-weight: 300; line-height: 1.05; letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums; color: var(--primary-text-color);
  }
  .rel { font-size: 0.95rem; color: var(--secondary-text-color); }

  .dawn { margin-top: 14px; }
  .track { height: 6px; border-radius: 3px; background: var(--divider-color); overflow: hidden; }
  .fill {
    height: 100%; width: calc(var(--p, 0) * 1%);
    background: linear-gradient(90deg, #35407a, #b86f6a 45%, #e9a95b 75%, #f6d58f);
    background-size: calc(10000% / max(var(--p, 1), 1)) 100%;
  }
  .cap { margin-top: 6px; font-size: 0.8rem; color: var(--secondary-text-color); }

  .days {
    display: grid; grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 6px; margin-top: 18px;
  }
  .day { display: flex; flex-direction: column; align-items: center; gap: 2px; }
  .chip {
    width: 100%; max-width: 48px; height: 40px; border-radius: 20px;
    border: 1px solid var(--divider-color); background: transparent;
    color: var(--secondary-text-color); font-size: 0.85rem; cursor: pointer;
  }
  .day.on .chip {
    background: var(--primary-color); border-color: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }
  .hhmm {
    min-height: 32px; padding: 6px 4px; border: 0; border-radius: 6px; background: none;
    font-size: 0.75rem; color: var(--secondary-text-color); cursor: pointer;
    font-variant-numeric: tabular-nums;
  }
  .day.ovr .hhmm { color: var(--primary-text-color); font-weight: 600; }
  .day:not(.on) .hhmm { opacity: 0.55; }
  .hhmm[aria-expanded="true"] { background: var(--secondary-background-color); }

  .editor {
    margin-top: 10px; padding: 12px; border-radius: 10px;
    background: var(--secondary-background-color); animation: open 0.18s ease-out;
  }
  .editor label { display: block; margin-bottom: 6px; font-size: 0.85rem; color: var(--secondary-text-color); }
  .editor input {
    font: inherit; font-size: 1.25rem; padding: 6px 8px; border-radius: 8px;
    border: 1px solid var(--divider-color); background: var(--card-background-color);
    color: var(--primary-text-color); font-variant-numeric: tabular-nums;
  }
  .actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
  .btn {
    padding: 8px 12px; border-radius: 8px; font-size: 0.85rem; cursor: pointer;
    border: 1px solid var(--divider-color); background: transparent;
    color: var(--primary-text-color);
  }
  .btn.primary {
    background: var(--primary-color); border-color: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }

  .foot {
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 8px; margin-top: 10px;
  }
  .linkbtn {
    padding: 6px 0; border: 0; background: none; cursor: pointer; font-size: 0.85rem;
    color: var(--secondary-text-color); text-decoration: underline dotted;
    text-underline-offset: 3px; font-variant-numeric: tabular-nums;
  }

  @keyframes open { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: reduce) {
    .editor { animation: none; }
    .sw, .sw::after, .body { transition: none; }
  }
`;

class ReveilCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._editing = null; // "default" | "monday" | ... | null
    this._draft = "";
    this._sig = null;
    this._timer = null;
    this._live = null;
    this._focusInput = false;

    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    this.shadowRoot.addEventListener("input", (ev) => {
      if (ev.target.matches && ev.target.matches("input[type=time]")) {
        this._draft = ev.target.value;
      }
    });
  }

  // ---- API Lovelace -------------------------------------------------------
  setConfig(config) {
    if (!config || !(config.device_id || config.entity)) {
      throw new Error("Choisissez l'appareil Réveil (« device_id »).");
    }
    this._config = { ...config };
    this._sig = null;
    this._resolvedFor = null;
    this._resolved = null;
    if (this._hass) this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  getCardSize() {
    return 4;
  }

  getGridOptions() {
    return { columns: 12, min_columns: 6 };
  }

  static getConfigElement() {
    return document.createElement("reveil-card-editor");
  }

  static getStubConfig(hass) {
    const found = Object.values((hass && hass.entities) || {}).find(
      (e) => e.platform === "reveil" && e.device_id
    );
    return { device_id: found ? found.device_id : "" };
  }

  connectedCallback() {
    this._timer = setInterval(() => this._paintLive(), 30000);
    this._paintLive();
  }

  disconnectedCallback() {
    clearInterval(this._timer);
    this._timer = null;
  }

  // ---- Utilitaires --------------------------------------------------------
  _lang() {
    return (this._hass && this._hass.language) || "en";
  }

  _t() {
    return this._lang().toLowerCase().startsWith("fr") ? TEXTS.fr : TEXTS.en;
  }

  _fmt(value) {
    let date = value;
    if (!(value instanceof Date)) {
      const [h, m] = String(value).split(":").map(Number);
      date = new Date(2000, 0, 1, h, m);
    }
    const opts = { hour: "2-digit", minute: "2-digit" };
    const tf = this._hass.locale && this._hass.locale.time_format;
    if (tf === "12") opts.hour12 = true;
    else if (tf === "24") opts.hourCycle = "h23";
    return date.toLocaleTimeString(this._lang(), opts);
  }

  _dayName(index, style) {
    // 2024-01-01 est un lundi ; style "narrow" donne l'initiale (L, M, M, J, V, S, D)
    const name = new Date(2024, 0, 1 + index).toLocaleDateString(this._lang(), {
      weekday: style,
    });
    return capitalize(name.replace(/\.$/, ""));
  }

  _dayLabel(next) {
    const L = this._t();
    const now = new Date();
    const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    if (next.toDateString() === now.toDateString()) return L.today;
    if (next.toDateString() === tomorrow.toDateString()) return L.tomorrow;
    return capitalize(
      next.toLocaleDateString(this._lang(), { weekday: "long", day: "numeric", month: "long" })
    );
  }

  _callService(domain, service, data) {
    Promise.resolve(this._hass.callService(domain, service, data)).catch((err) =>
      console.error(`reveil-card: ${domain}.${service} a échoué`, err)
    );
  }

  // ---- Résolution des entités --------------------------------------------
  _resolve() {
    const hass = this._hass;
    if (this._resolved && this._resolvedFor === hass.entities) return this._resolved;

    const registry = hass.entities || {};
    let deviceId = this._config.device_id;
    let result;

    if (!deviceId) {
      // Compatibilité : n'importe quelle entité du réveil
      const ref = registry[this._config.entity];
      if (!ref) result = { error: "missing" };
      else if ((ref.platform && ref.platform !== "reveil") || !ref.device_id) {
        result = { error: "notReveil" };
      } else deviceId = ref.device_id;
    }

    if (deviceId) {
      const map = {};
      let found = false;
      for (const e of Object.values(registry)) {
        if (e.device_id !== deviceId) continue;
        if (e.platform && e.platform !== "reveil") continue;
        found = true;
        if (e.translation_key) map[e.translation_key] = e.entity_id;
      }
      if (!found) {
        result = { error: "notReveil" };
      } else if (!map.enabled || !map.default_time) {
        result = { error: Object.keys(map).length ? "notReveil" : "unsupported" };
      } else {
        const device = hass.devices && hass.devices[deviceId];
        result = {
          map,
          name:
            this._config.name ||
            (device && (device.name_by_user || device.name)) ||
            "Réveil",
        };
      }
    }

    this._resolvedFor = hass.entities;
    this._resolved = result;
    return result;
  }

  // ---- Rendu --------------------------------------------------------------
  _update() {
    if (!this._hass || !this._config) return;
    const r = this._resolve();
    const sig = r.error
      ? `err:${r.error}`
      : Object.keys(r.map)
          .sort()
          .map((k) => `${k}=${this._hass.states[r.map[k]]?.state}`)
          .join("|") + `|${this._editing}|${this._lang()}`;
    if (sig === this._sig) return;
    this._sig = sig;
    this._render(r);
  }

  _render(r) {
    const root = this.shadowRoot;
    const L = this._t();

    if (r.error) {
      const text =
        r.error === "missing"
          ? L.missing(this._config.entity)
          : r.error === "notReveil"
            ? L.notReveil
            : L.unsupported;
      root.innerHTML = `<style>${STYLE}</style><ha-card><div class="msg">${esc(text)}</div></ha-card>`;
      this._live = null;
      return;
    }

    const hass = this._hass;
    const st = (key) => hass.states[r.map[key]]?.state;
    const enabled = st("enabled") !== "off";
    const defaultTime = validTime(st("default_time")) || "07:00:00";

    const parseDate = (state) => {
      const d = state && !["unknown", "unavailable"].includes(state) ? new Date(state) : null;
      return d && !isNaN(d) ? d : null;
    };
    const next = enabled ? parseDate(st("next_alarm")) : null;
    const start = next ? parseDate(st("pre_ring_start")) : null;
    this._live = { next, start };

    // -- Prochain réveil
    let nextHtml;
    if (next) {
      nextHtml = `
        <div class="next">
          <div class="when">${esc(this._dayLabel(next))}</div>
          <div class="nextrow"><span class="time">${esc(this._fmt(next))}</span><span class="rel"></span></div>
          ${
            start
              ? `<div class="dawn"><div class="track"><div class="fill"></div></div></div>`
              /*? `<div class="dawn"><div class="track"><div class="fill"></div></div><div class="cap"></div></div>`*/
              : ""
          }
        </div>`;
    } else {
      nextHtml = `<div class="next"><div class="when">${esc(enabled ? L.none : L.off)}</div></div>`;
    }

    // -- Jours
    const daysHtml = DAYS.map((day, i) => {
      const active = st(`day_${day}`) === "on";
      const override = validTime(st(`time_${day}`));
      const effective = override || defaultTime;
      const long = this._dayName(i, "long").toLowerCase();
      return `
        <div class="day ${active ? "on" : ""} ${override ? "ovr" : ""}">
          <button class="chip" data-action="toggle-day" data-day="${day}"
            aria-pressed="${active}" aria-label="${esc(L.toggleDay(long))}">${esc(this._dayName(i, "narrow"))}</button>
          <button class="hhmm" data-action="edit-time" data-day="${day}"
            aria-expanded="${this._editing === day}" aria-label="${esc(L.editTime(long))}">${esc(this._fmt(effective))}</button>
        </div>`;
    }).join("");

    // -- Éditeur d'heure
    let editorHtml = "";
    if (this._editing) {
      const e = this._editing;
      const override = e === "default" ? null : validTime(st(`time_${e}`));
      const current = override || defaultTime;
      const title =
        e === "default"
          ? L.defaultTime
          : L.dayTime(this._dayName(DAYS.indexOf(e), "long").toLowerCase());
      const value = this._draft || current.slice(0, 5);
      editorHtml = `
        <div class="editor">
          <label for="edit-time">${esc(title)}</label>
          <input id="edit-time" type="time" value="${esc(value)}" />
          <div class="actions">
            <button class="btn primary" data-action="save-time">${esc(L.save)}</button>
            ${override ? `<button class="btn" data-action="clear-time">${esc(L.useDefault)}</button>` : ""}
            <button class="btn" data-action="cancel-edit">${esc(L.cancel)}</button>
          </div>
        </div>`;
    }

    // -- Pied : heure par défaut + confirmation
    const todayIndex = (new Date().getDay() + 6) % 7;
    const todayTime = validTime(st(`time_${DAYS[todayIndex]}`)) || defaultTime;
    const [th, tm] = todayTime.split(":").map(Number);
    const now = new Date();
    const alarmPassed =
      now.getHours() * 60 + now.getMinutes() >= th * 60 + tm;
    const showDismiss = enabled && st("rings_today") === "on" && alarmPassed;

    root.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        <div class="${enabled ? "" : "off"}">
          <div class="top">
            <div class="name">${esc(r.name)}</div>
            <button class="sw" role="switch" aria-checked="${enabled}"
              aria-label="${esc(L.toggleAlarm)}" data-action="toggle-enabled"></button>
          </div>
          <div class="body">
            ${nextHtml}
            <div class="days">${daysHtml}</div>
            ${editorHtml}
            <div class="foot">
              <button class="linkbtn" data-action="edit-time" data-day="default">${esc(L.defaultTime)} ${esc(this._fmt(defaultTime))}</button>
              ${showDismiss ? `<button class="btn primary" data-action="dismiss">${esc(L.awake)}</button>` : ""}
            </div>
          </div>
        </div>
      </ha-card>`;

    if (this._focusInput) {
      this._focusInput = false;
      const input = root.querySelector("input[type=time]");
      if (input) input.focus();
    }
    this._paintLive();
  }

  /** Met à jour ce qui dépend de l'heure courante, sans reconstruire la carte. */
  _paintLive() {
    if (!this._live || !this._hass) return;
    const { next, start } = this._live;
    if (!next) return;
    const root = this.shadowRoot;
    const L = this._t();
    const now = Date.now();

    const rel = root.querySelector(".rel");
    if (rel) {
      const minutes = Math.floor((next.getTime() - now) / 60000);
      if (minutes < 0) rel.textContent = L.now;
      else if (minutes < 1) rel.textContent = L.lessThanMinute;
      else {
        rel.textContent = L.rel(
          Math.floor(minutes / 1440),
          Math.floor((minutes % 1440) / 60),
          minutes % 60
        );
      }
    }

    const fill = root.querySelector(".fill");
    //const cap = root.querySelector(".cap");
    if (fill /*&& cap*/ && start) {
      const total = next.getTime() - start.getTime();
      const p = total > 0 ? Math.min(1, Math.max(0, (now - start.getTime()) / total)) : 0;
      fill.style.setProperty("--p", (p * 100).toFixed(1));
      //cap.textContent = now >= start.getTime() ? L.lightRising : L.lightFrom(this._fmt(start));
    }
  }

  // ---- Actions ------------------------------------------------------------
  _closeEditor() {
    this._editing = null;
    this._draft = "";
    this._sig = null;
    this._update();
  }

  _onClick(ev) {
    const btn = ev.target.closest && ev.target.closest("[data-action]");
    const r = this._resolved;
    if (!btn || !r || r.error) return;
    const { action, day } = btn.dataset;

    switch (action) {
      case "toggle-enabled":
        this._callService("switch", "toggle", { entity_id: r.map.enabled });
        break;
      case "toggle-day":
        this._callService("switch", "toggle", { entity_id: r.map[`day_${day}`] });
        break;
      case "dismiss":
        this._callService("button", "press", { entity_id: r.map.dismiss });
        break;
      case "edit-time":
        this._editing = this._editing === day ? null : day;
        this._draft = "";
        this._focusInput = Boolean(this._editing);
        this._sig = null;
        this._update();
        break;
      case "cancel-edit":
        this._closeEditor();
        break;
      case "save-time": {
        const input = this.shadowRoot.querySelector("input[type=time]");
        const value = input && input.value;
        if (!value) return;
        const key = this._editing === "default" ? "default_time" : `time_${this._editing}`;
        this._callService("time", "set_value", {
          entity_id: r.map[key],
          time: value.length === 5 ? `${value}:00` : value,
        });
        this._closeEditor();
        break;
      }
      case "clear-time":
        this._callService("reveil", "set_time", {
          entity_id: r.map.default_time,
          day: this._editing,
        });
        this._closeEditor();
        break;
    }
  }
}

/** Éditeur visuel (Modifier la carte). */
class ReveilCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
  }

  _render() {
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) =>
        ({ device_id: "Appareil Réveil", name: "Nom (facultatif)" })[schema.name] || schema.name;
      this._form.addEventListener("value-changed", (ev) => {
        // L'ancienne option `entity` est abandonnée dès qu'un appareil est choisi
        const { entity, ...config } = ev.detail.value;
        this.dispatchEvent(
          new CustomEvent("config-changed", {
            detail: { config: config.device_id ? config : ev.detail.value },
            bubbles: true,
            composed: true,
          })
        );
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = [
      {
        name: "device_id",
        required: true,
        selector: { device: { filter: { integration: "reveil" } } },
      },
      { name: "name", selector: { text: {} } },
    ];
  }
}

customElements.define("reveil-card", ReveilCard);
customElements.define("reveil-card-editor", ReveilCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "reveil-card",
  name: "Carte Réveil",
  description: "Prochain réveil, jours actifs, heure par jour et confirmation du réveil.",
});

console.info(`%c REVEIL-CARD %c ${CARD_VERSION} `, "background:#35407a;color:#fff", "");