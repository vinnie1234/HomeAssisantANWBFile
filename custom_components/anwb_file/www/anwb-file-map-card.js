/*
 * ANWB File card
 *
 * Traffic information like anwb.nl/verkeer: a list grouped by road (with search and
 * filters) next to a map. "Bekijk op kaart" zooms to the incident, and jams are drawn
 * as coloured lines along the road (yellow = slow, orange = queueing, red = stationary).
 *
 *   type: custom:anwb-file-map-card
 *   radius_km: 20     # initial map view: your home location + this radius
 *   height: 640       # card height in px on wide screens
 *
 * Data comes from the ANWB File integration over a websocket subscription.
 */

const BASE = "/anwb_file/";
const NETHERLANDS = [[50.75, 3.3], [53.55, 7.25]];
const WIDE_BREAKPOINT = 860;

// Material Design Icons (24x24), used inside the map markers
const MDI = {
  jams: "M8,11L9.5,6.5H18.5L20,11M18.5,16A1.5,1.5 0 0,1 17,14.5A1.5,1.5 0 0,1 18.5,13A1.5,1.5 0 0,1 20,14.5A1.5,1.5 0 0,1 18.5,16M9.5,16A1.5,1.5 0 0,1 8,14.5A1.5,1.5 0 0,1 9.5,13A1.5,1.5 0 0,1 11,14.5A1.5,1.5 0 0,1 9.5,16M19.92,6C19.71,5.4 19.14,5 18.5,5H9.5C8.86,5 8.29,5.4 8.08,6L6,12V20A1,1 0 0,0 7,21H8A1,1 0 0,0 9,20V19H19V20A1,1 0 0,0 20,21H21A1,1 0 0,0 22,20V12L19.92,6M14.92,3C14.71,2.4 14.14,2 13.5,2H4.5C3.86,2 3.29,2.4 3.08,3L1,9V17A1,1 0 0,0 2,18H3A1,1 0 0,0 4,17V12.91C3.22,12.63 2.82,11.77 3.1,11C3.32,10.4 3.87,10 4.5,10H4.57L5.27,8H3L4.5,3.5H15.09L14.92,3Z",
  radars: "M12,10.8A3.2,3.2 0 0,1 15.2,14A3.2,3.2 0 0,1 12,17.2A3.2,3.2 0 0,1 8.8,14A3.2,3.2 0 0,1 12,10.8M16,3.33V2A6,6 0 0,1 22,8H20.67C20.67,5.42 18.58,3.33 16,3.33M16,6V4.67C17.84,4.67 19.33,6.16 19.33,8H18C18,6.89 17.11,6 16,6M17,9H22V20A2,2 0 0,1 20,22H4A2,2 0 0,1 2,20V8A2,2 0 0,1 4,6H7.17L9,4H15V7C16.11,7 17,7.89 17,9M12,19A5,5 0 0,0 17,14A5,5 0 0,0 12,9A5,5 0 0,0 7,14A5,5 0 0,0 12,19Z",
  roadworks: "M12,15C7.58,15 4,16.79 4,19V21H20V19C20,16.79 16.42,15 12,15M8,9A4,4 0 0,0 12,13A4,4 0 0,0 16,9M11.5,2C11.2,2 11,2.21 11,2.5V5.5H10V3C10,3 7.75,3.86 7.75,6.75C7.75,6.75 7,6.89 7,8H17C16.95,6.89 16.25,6.75 16.25,6.75C16.25,3.86 14,3 14,3V5.5H13V2.5C13,2.21 12.81,2 12.5,2H11.5Z",
};

const CATEGORIES = {
  jams: { label: "Files", icon: "mdi:car-multiple", one: "file", many: "files" },
  roadworks: { label: "Werkzaamheden", icon: "mdi:account-hard-hat", one: "werkzaamheid", many: "werkzaamheden" },
  radars: { label: "Flitsers", icon: "mdi:camera-wireless", one: "flitser", many: "flitsers" },
};
const CATEGORY_ORDER = ["jams", "roadworks", "radars"];

const TYPE_LABEL = {
  "slow-traffic": "Langzaam verkeer",
  "queing-traffic": "Stagnerend verkeer",
  "stationary-traffic": "Stilstaand verkeer",
  "road-closed": "Dicht",
  roadworks: "Werkzaamheden",
  radar: "Flitser",
};

const STYLE = `
  :host { display: block; color: var(--primary-text-color); }
  * { box-sizing: border-box; }
  ha-card { overflow: hidden; }
  .wrap { display: grid; grid-template-columns: 1fr; position: relative; }
  .wrap.wide { grid-template-columns: minmax(360px, 460px) 1fr; height: var(--card-height, 640px); }
  .panel { display: flex; flex-direction: column; min-height: 0; min-width: 0; }
  .wrap:not(.wide) .panel { order: 2; }
  .wrap:not(.wide) .list { max-height: 560px; }
  .wide .panel { border-right: 1px solid var(--divider-color); }
  .wrap.nomap { grid-template-columns: 1fr; height: auto; }
  .nomap .panel { border-right: 0; }
  .nomap .list { max-height: var(--card-height, 640px); }
  .nomap .mapbox, .nomap .show-map, .nomap .route-show { display: none; }
  .section-title { padding: 14px 16px 6px; font-size: 12px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase;
    color: var(--secondary-text-color); }
  .route { margin: 0 12px 10px; padding: 12px 14px; border-radius: 12px; border: 1px solid var(--divider-color);
    background: var(--card-background-color); }
  .route.selected { border-color: var(--primary-color); box-shadow: 0 0 0 1px var(--primary-color) inset; }
  .route-head { display: flex; align-items: center; gap: 10px; }
  .route-name { flex: 1; min-width: 0; font-weight: 600; font-size: 15px; }
  .person { display: inline-flex; align-items: center; gap: 5px; margin-left: 10px; padding: 2px 9px 2px 3px; border-radius: 12px;
    background: var(--secondary-background-color); font-size: 12px; font-weight: 500; vertical-align: middle; --mdc-icon-size: 16px; }
  .person img { width: 18px; height: 18px; border-radius: 50%; object-fit: cover; }
  .person ha-icon { margin-left: 3px; }
  .route-show { flex: none; cursor: pointer; padding: 6px 12px; border-radius: 6px; font: inherit; font-size: 13px; font-weight: 600;
    background: var(--card-background-color); color: var(--primary-text-color); border: 1px solid var(--divider-color); }
  .route-show:hover, .route.selected .route-show { border-color: var(--primary-color); color: var(--primary-color); }
  .route-stats { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 14px; margin-top: 8px; }
  .route-time { font-size: 26px; font-weight: 700; line-height: 1.1; }
  .delay-tag { padding: 2px 10px; border-radius: 12px; font-size: 12.5px; font-weight: 700; color: #fff; background: #2e7d32; }
  .delay-tag.warn { background: #f57c00; }
  .delay-tag.bad { background: #d32f2f; }
  .route-sub { margin-top: 4px; font-size: 13px; color: var(--secondary-text-color); display: flex; flex-wrap: wrap; gap: 2px 12px; }
  .route-alts { margin-top: 10px; border-top: 1px solid var(--divider-color); }
  .route-alts-title { padding: 8px 0 2px; font-size: 12px; font-weight: 700; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: .4px; }
  .route-alt { display: flex; flex-wrap: wrap; gap: 2px 12px; align-items: baseline; padding: 7px 8px; margin: 0 -8px; border-radius: 8px; cursor: pointer; font-size: 13.5px; }
  .route-alt:hover { background: var(--secondary-background-color); }
  .route-alt.active { background: color-mix(in srgb, var(--primary-color) 12%, transparent); font-weight: 600; }
  .route-alt .diff { color: var(--secondary-text-color); }
  .endpoint { width: 26px; height: 26px; border-radius: 50%; border: 2px solid #fff; color: #fff; font-weight: 700; font-size: 13px;
    display: flex; align-items: center; justify-content: center; box-shadow: 0 1px 5px rgba(0,0,0,.5); }

  .toolbar { padding: 14px 16px 10px; display: flex; flex-direction: column; gap: 10px;
    border-bottom: 1px solid var(--divider-color); background: var(--card-background-color); }
  .search { display: flex; align-items: center; gap: 8px; padding: 0 12px; height: 42px; border-radius: 21px;
    background: var(--secondary-background-color); border: 1px solid transparent; color: var(--secondary-text-color); }
  .search:focus-within { border-color: var(--primary-color); }
  .search input { flex: 1; min-width: 0; border: 0; outline: 0; background: transparent; font: inherit;
    color: var(--primary-text-color); font-size: 15px; }
  .search .clear { cursor: pointer; display: none; --mdc-icon-size: 18px; }
  .search.has-value .clear { display: inline-flex; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px 6px 8px; border-radius: 18px; cursor: pointer;
    border: 1px solid var(--divider-color); background: transparent; color: var(--primary-text-color); font: inherit;
    font-size: 13px; font-weight: 500; --mdc-icon-size: 18px; transition: background .15s, border-color .15s; }
  .chip:hover { background: var(--secondary-background-color); }
  .chip.active { background: color-mix(in srgb, var(--chip-color) 16%, transparent); border-color: var(--chip-color); }
  .chip .dot { width: 22px; height: 22px; border-radius: 50%; background: var(--chip-color); color: #fff;
    display: inline-flex; align-items: center; justify-content: center; --mdc-icon-size: 14px; }
  .chip .count { color: var(--secondary-text-color); font-weight: 400; }
  .summary { font-size: 12.5px; color: var(--secondary-text-color); }

  .list { flex: 1; overflow-y: auto; min-height: 0; }
  .group { border-bottom: 1px solid var(--divider-color); }
  .group-head { display: flex; align-items: center; gap: 12px; padding: 12px 16px; cursor: pointer; user-select: none;
    background: var(--secondary-background-color); transition: filter .15s; }
  .group-head:hover { filter: brightness(.97); }
  .badge { flex: none; min-width: 48px; padding: 5px 8px; border-radius: 4px; text-align: center; font-weight: 700;
    font-size: 13px; color: #fff; background: #d32f2f; letter-spacing: .3px; }
  .badge.n { background: #ffc107; color: #1b1b1b; }
  .badge.o { background: #607d8b; }
  .group-title { flex: 1; min-width: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 4px 12px;
    font-weight: 600; color: var(--primary-color); font-size: 14.5px; }
  .pill { display: inline-flex; align-items: center; gap: 5px; --mdc-icon-size: 18px; }
  .group-stats { flex: none; text-align: right; font-size: 13px; font-weight: 500; white-space: nowrap; }
  .group-stats span + span { margin-left: 10px; }
  .chev { flex: none; color: var(--primary-color); transition: transform .2s; --mdc-icon-size: 22px; }
  .group.open .chev { transform: rotate(180deg); }
  .group-body { display: none; background: var(--card-background-color); }
  .group.open .group-body { display: block; }
  .direction { padding: 14px 16px 2px; font-weight: 600; color: var(--primary-color); font-size: 13.5px; }
  .item { display: flex; gap: 12px; align-items: flex-start; padding: 12px 16px 14px; border-top: 1px solid var(--divider-color);
    transition: background .2s; }
  .direction + .item { border-top: 0; }
  .item.selected { background: color-mix(in srgb, var(--primary-color) 10%, transparent); }
  .item-icon { flex: none; width: 38px; height: 38px; border-radius: 50%; display: flex; align-items: center;
    justify-content: center; color: #fff; --mdc-icon-size: 21px; }
  .item-main { flex: 1; min-width: 0; }
  .item-title { font-weight: 600; font-size: 14.5px; }
  .item-meta { display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: 2px; font-size: 13px; color: var(--secondary-text-color); }
  .tag { display: inline-block; margin-top: 8px; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; color: #fff; }
  .reason-label { margin-top: 8px; font-size: 12px; font-weight: 700; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: .4px; }
  .reason { font-size: 14px; line-height: 1.4; }
  .when { margin-top: 6px; font-size: 12.5px; color: var(--secondary-text-color); }
  .show-map { flex: none; cursor: pointer; padding: 7px 12px; border-radius: 6px; font: inherit; font-size: 13px; font-weight: 600;
    background: var(--card-background-color); color: var(--primary-text-color); border: 1px solid var(--divider-color);
    display: inline-flex; align-items: center; gap: 6px; --mdc-icon-size: 16px; }
  .show-map:hover { border-color: var(--primary-color); color: var(--primary-color); }
  .empty { padding: 40px 16px; text-align: center; color: var(--secondary-text-color); }
  .empty ha-icon { --mdc-icon-size: 40px; opacity: .6; display: block; margin: 0 auto 8px; }

  .mapbox { position: relative; isolation: isolate; z-index: 0; height: 380px; background: var(--secondary-background-color); }
  .wide .mapbox { height: auto; }
  .map { position: absolute; inset: 0; }
  .map-actions { position: absolute; top: 10px; right: 10px; z-index: 500; display: flex; flex-direction: column; gap: 6px; }
  .map-actions button { cursor: pointer; display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; border-radius: 18px;
    border: 0; font: inherit; font-size: 12.5px; font-weight: 600; color: #1b1b1b; background: rgba(255,255,255,.95);
    box-shadow: 0 1px 4px rgba(0,0,0,.35); --mdc-icon-size: 16px; }
  .map-actions button:hover { background: #fff; }
  .legend { position: absolute; left: 10px; bottom: 22px; z-index: 500; display: flex; gap: 10px; padding: 6px 10px; border-radius: 14px;
    background: rgba(255,255,255,.92); font-size: 11.5px; color: #222; box-shadow: 0 1px 4px rgba(0,0,0,.3); }
  .legend i { display: inline-block; width: 18px; height: 5px; border-radius: 3px; margin-right: 5px; vertical-align: middle; }
  .status { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; text-align: center;
    padding: 20px; color: var(--secondary-text-color); background: var(--card-background-color); z-index: 600; }
  .status[hidden] { display: none; }

  .pin { width: 30px; height: 30px; border-radius: 50%; border: 2px solid #fff; box-shadow: 0 1px 5px rgba(0,0,0,.5);
    display: flex; align-items: center; justify-content: center; transition: transform .15s; }
  .pin svg { width: 18px; height: 18px; fill: #fff; }
  .pin.selected { transform: scale(1.35); box-shadow: 0 0 0 4px rgba(255,255,255,.55), 0 2px 8px rgba(0,0,0,.6); }
  .home-dot { width: 16px; height: 16px; border-radius: 50%; background: #1976d2; border: 3px solid #fff; box-shadow: 0 0 0 4px rgba(25,118,210,.3); }
  .popup b { display: block; margin-bottom: 2px; }
  .popup .sub { color: #555; font-size: 12px; }
  .leaflet-container { font: inherit; background: var(--secondary-background-color); }
`;

let leafletPromise = null;
function loadLeaflet() {
  if (!leafletPromise) {
    leafletPromise = (async () => {
      const css = await (await fetch(`${BASE}leaflet.css`)).text();
      if (!window.L) {
        await new Promise((resolve, reject) => {
          const script = document.createElement("script");
          script.src = `${BASE}leaflet.js`;
          script.onload = resolve;
          script.onerror = () => reject(new Error("leaflet.js kon niet geladen worden"));
          document.head.appendChild(script);
        });
      }
      return { L: window.L, css };
    })().catch((err) => {
      leafletPromise = null;
      throw err;
    });
  }
  return leafletPromise;
}

const esc = (text) =>
  String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function roadKey(road) {
  const [, letters = "", number = "0"] = /^([A-Z]*)(\d*)/.exec(road) || [];
  const rank = letters === "A" ? 0 : letters === "N" ? 1 : 2;
  return [rank, letters, parseInt(number, 10) || 0];
}
function compareRoads(a, b) {
  const [ra, la, na] = roadKey(a);
  const [rb, lb, nb] = roadKey(b);
  return ra - rb || la.localeCompare(lb) || na - nb || a.localeCompare(b);
}
const roadClass = (road) => (road.startsWith("A") ? "a" : road.startsWith("N") ? "n" : "o");
const plural = (n, category) => `${n} ${n === 1 ? CATEGORIES[category].one : CATEGORIES[category].many}`;
const direction = (text) => esc(String(text ?? "").replace(/ - /g, " → "));
const title = (i) => (i.category === "radars" ? i.from : `${i.from} → ${i.to}`);

function formatWhen(i) {
  const fmt = (iso) =>
    new Date(iso).toLocaleString("nl-NL", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  if (i.start && i.stop) return `${fmt(i.start)} t/m ${fmt(i.stop)}`;
  if (i.start && i.category !== "radars") return `Sinds ${fmt(i.start)}`;
  return "";
}

class AnwbFileCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._incidents = [];
    this._categories = Object.keys(CATEGORIES);
    this._mapCategories = new Set();
    this._filters = new Set();
    this._query = "";
    this._selectedId = null;
    this._expanded = new Set();
    this._loaded = false;
    this._routes = [];
    this._selectedRoute = null;
    this._selectedAlt = -1;
  }

  setConfig(config) {
    this._config = { show_map: true, my_routes_only: false, radius_km: 20, height: 640, ...config };
    this.style.setProperty("--card-height", `${this._config.height}px`);
    this._build();
  }

  getCardSize() {
    return 10;
  }

  static getStubConfig() {
    return { show_map: true };
  }

  static getConfigElement() {
    return document.createElement("anwb-file-map-card-editor");
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._subscribe();
    const dark = !!hass.themes?.darkMode;
    if (dark !== this._dark) {
      this._dark = dark;
      this._applyTiles();
    }
    if (first && this._fitted) this._fitHome();
  }

  connectedCallback() {
    if (this._hass && !this._unsub) this._subscribe();
    this._resizeObserver = new ResizeObserver(() => {
      const wide = this.clientWidth >= WIDE_BREAKPOINT;
      this._root?.classList.toggle("wide", wide);
      this._map?.invalidateSize();
    });
    this._resizeObserver.observe(this);
  }

  disconnectedCallback() {
    this._resizeObserver?.disconnect();
    this._unsubscribe();
  }

  /* ---------- data ---------- */

  async _subscribe() {
    if (this._subscribing || this._unsub || !this.isConnected) return;
    this._subscribing = true;
    try {
      this._unsub = await this._hass.connection.subscribeMessage((data) => this._onData(data), {
        type: "anwb_file/subscribe",
      });
    } catch (err) {
      this._showStatus("ANWB File is niet geladen. Is de integratie toegevoegd?");
    } finally {
      this._subscribing = false;
    }
  }

  _unsubscribe() {
    if (this._unsub) this._unsub();
    this._unsub = null;
  }

  _onData(data) {
    this._incidents = data.incidents || [];
    this._categories = CATEGORY_ORDER.filter((c) => (data.categories || []).includes(c));
    this._mapCategories = new Set(data.map_categories || []);
    this._routes = data.routes || [];
    if (this._selectedRoute && !this._routes.some((r) => r.id === this._selectedRoute)) this._selectedRoute = null;
    if (!this._loaded) {
      this._loaded = true;
      this._filters = new Set(this._categories);
    }
    this._showStatus(null);
    this._renderToolbar();
    this._renderList();
    this._updateMap();
    this._drawRoute();
  }

  _visible() {
    const query = this._query.trim().toLowerCase();
    return this._incidents.filter((i) => {
      if (!this._filters.has(i.category)) return false;
      if (!query) return true;
      return [i.road, i.from, i.to, i.reason, i.direction, TYPE_LABEL[i.incident_type]]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(query));
    });
  }

  /* ---------- skeleton ---------- */

  _build() {
    // setConfig can run again on an existing card (editor, card picker): start clean
    this._mapObserver?.disconnect();
    this._map?.remove();
    this._map = null;
    this._tiles = this._labels = null;
    this._fitted = false;
    this.shadowRoot.innerHTML = `
      <style>${STYLE}</style>
      <ha-card>
        <div class="wrap">
          <div class="panel">
            <div class="toolbar">
              <label class="search">
                <ha-icon icon="mdi:magnify"></ha-icon>
                <input type="search" placeholder="Zoek op weg, plaats of situatie" autocomplete="off" />
                <ha-icon class="clear" icon="mdi:close-circle"></ha-icon>
              </label>
              <div class="chips"></div>
              <div class="summary"></div>
            </div>
            <div class="list"></div>
          </div>
          <div class="mapbox">
            <div class="map"></div>
            <div class="map-actions">
              <button class="home"><ha-icon icon="mdi:crosshairs-gps"></ha-icon>Mijn omgeving</button>
              <button class="nl"><ha-icon icon="mdi:map-outline"></ha-icon>Heel Nederland</button>
            </div>
            <div class="legend">
              <span><i style="background:#fbc02d"></i>Langzaam</span>
              <span><i style="background:#f57c00"></i>Stagnerend</span>
              <span><i style="background:#d32f2f"></i>Stilstaand</span>
            </div>
            <div class="status" hidden></div>
          </div>
        </div>
      </ha-card>`;
    const $ = (selector) => this.shadowRoot.querySelector(selector);
    this._root = $(".wrap");
    this._root.classList.toggle("nomap", !this._config.show_map);
    this._root.classList.toggle("wide", this.clientWidth >= WIDE_BREAKPOINT);

    const input = $(".search input");
    input.addEventListener("input", () => {
      this._query = input.value;
      $(".search").classList.toggle("has-value", !!input.value);
      this._renderList();
      this._updateMap();
    });
    $(".search .clear").addEventListener("click", () => {
      input.value = "";
      input.dispatchEvent(new Event("input"));
      input.focus();
    });
    $(".chips").addEventListener("click", (event) => {
      const chip = event.target.closest(".chip");
      if (!chip) return;
      const category = chip.dataset.category;
      if (this._filters.has(category)) this._filters.delete(category);
      else this._filters.add(category);
      this._renderToolbar();
      this._renderList();
      this._updateMap();
    });
    $(".list").addEventListener("click", (event) => {
      const routeButton = event.target.closest(".route-show");
      if (routeButton) return this._toggleRoute(routeButton.dataset.route);
      const alternative = event.target.closest(".route-alt");
      if (alternative) return this._pickAlternative(alternative.dataset.route, Number(alternative.dataset.alt));
      const button = event.target.closest(".show-map");
      if (button) return this._select(button.dataset.id, { zoom: true });
      const head = event.target.closest(".group-head");
      if (head) {
        const road = head.parentElement.dataset.road;
        if (this._expanded.has(road)) this._expanded.delete(road);
        else this._expanded.add(road);
        head.parentElement.classList.toggle("open");
      }
    });
    $(".home").addEventListener("click", () => this._fitHome());
    $(".nl").addEventListener("click", () => this._map?.fitBounds(NETHERLANDS));

    this._renderToolbar();
    this._renderList();
    if (this._config.show_map) this._initMap();
  }

  _showStatus(message) {
    const status = this.shadowRoot.querySelector(".status");
    if (!status) return;
    status.hidden = !message;
    status.textContent = message || "";
  }

  /* ---------- toolbar + list ---------- */

  _renderToolbar() {
    const chips = this.shadowRoot.querySelector(".chips");
    chips.innerHTML = this._categories
      .map((category) => {
        const count = this._incidents.filter((i) => i.category === category).length;
        const color = { jams: "#f57c00", roadworks: "#607d8b", radars: "#1976d2" }[category];
        return `<button class="chip ${this._filters.has(category) ? "active" : ""}" data-category="${category}" style="--chip-color:${color}">
          <span class="dot"><ha-icon icon="${CATEGORIES[category].icon}"></ha-icon></span>
          ${CATEGORIES[category].label} <span class="count">${count}</span></button>`;
      })
      .join("");
  }

  _renderList() {
    const list = this.shadowRoot.querySelector(".list");
    const visible = this._visible();

    const jams = visible.filter((i) => i.category === "jams");
    const delay = jams.reduce((sum, i) => sum + (i.delay_min || 0), 0);
    const length = jams.reduce((sum, i) => sum + (i.length_km || 0), 0);
    this.shadowRoot.querySelector(".summary").textContent = this._loaded
      ? `${visible.length} ${visible.length === 1 ? "melding" : "meldingen"}` +
        (jams.length ? ` · ${Math.round(length)} km file, ${delay} min vertraging` : "")
      : "Laden…";

    if (!visible.length) {
      list.innerHTML =
        this._routesHtml() +
        (this._loaded
          ? `<div class="empty"><ha-icon icon="mdi:check-circle-outline"></ha-icon>Geen meldingen gevonden</div>`
          : "");
      return;
    }

    const byRoad = new Map();
    for (const incident of visible) {
      if (!byRoad.has(incident.road)) byRoad.set(incident.road, []);
      byRoad.get(incident.road).push(incident);
    }
    // While searching, show matches expanded so nothing is hidden behind a click
    const searching = !!this._query.trim();
    const autoOpen = searching && byRoad.size <= 8;

    list.innerHTML =
      this._routesHtml() +
      (this._visibleRoutes().length ? '<div class="section-title">Meldingen</div>' : "") +
      [...byRoad.keys()]
      .sort(compareRoads)
      .map((road) => this._groupHtml(road, byRoad.get(road), autoOpen || this._expanded.has(road)))
      .join("");

    if (this._selectedId) {
      list.querySelector(`.item[data-id="${CSS.escape(this._selectedId)}"]`)?.classList.add("selected");
    }
  }

  _groupHtml(road, items, open) {
    const counts = CATEGORY_ORDER.map((category) => [category, items.filter((i) => i.category === category).length]).filter(
      ([, n]) => n
    );
    const single = items.length === 1 ? items[0] : null;
    const titleHtml = single
      ? `<span>${esc(title(single))}</span>`
      : counts
          .map(([category, n]) => `<span class="pill"><ha-icon icon="${CATEGORIES[category].icon}"></ha-icon>${plural(n, category)}</span>`)
          .join("");

    const jams = items.filter((i) => i.category === "jams");
    const delay = jams.reduce((sum, i) => sum + (i.delay_min || 0), 0);
    const length = jams.reduce((sum, i) => sum + (i.length_km || 0), 0);
    const stats = jams.length
      ? `<span>+ ${delay} min</span><span>${Math.round(length)} km</span>`
      : "";

    const directions = new Map();
    for (const item of items) {
      const key = item.direction || "";
      if (!directions.has(key)) directions.set(key, []);
      directions.get(key).push(item);
    }
    const body = [...directions.entries()]
      .map(
        ([dir, group]) =>
          `<div class="direction">${direction(dir)}</div>` +
          group
            .sort((a, b) => (b.delay_min || 0) - (a.delay_min || 0))
            .map((item) => this._itemHtml(item))
            .join("")
      )
      .join("");

    return `<div class="group ${open ? "open" : ""}" data-road="${esc(road)}">
      <div class="group-head">
        <span class="badge ${roadClass(road)}">${esc(road)}</span>
        <span class="group-title">${titleHtml}</span>
        <span class="group-stats">${stats}</span>
        <ha-icon class="chev" icon="mdi:chevron-down"></ha-icon>
      </div>
      <div class="group-body">${body}</div>
    </div>`;
  }

  _itemHtml(i) {
    const meta = [];
    if (i.delay_min != null) meta.push(`<span>+ ${i.delay_min} min</span>`);
    if (i.length_km != null) meta.push(`<span>${i.length_km} km</span>`);
    const when = formatWhen(i);
    const label = TYPE_LABEL[i.incident_type];
    const heading = i.category === "radars" ? `Flitser ${esc(i.from)}` : esc(`${i.from} - ${i.to}`);
    return `<div class="item" data-id="${esc(i.id)}">
      <div class="item-icon" style="background:${i.color}"><ha-icon icon="${CATEGORIES[i.category].icon}"></ha-icon></div>
      <div class="item-main">
        <div class="item-title">${heading}</div>
        ${meta.length ? `<div class="item-meta">${meta.join("")}</div>` : ""}
        ${label ? `<span class="tag" style="background:${i.color}">${esc(label)}</span>` : ""}
        ${i.reason ? `<div class="reason-label">Situatie</div><div class="reason">${esc(i.reason)}</div>` : ""}
        ${when ? `<div class="when">${esc(when)}</div>` : ""}
      </div>
      <button class="show-map" data-id="${esc(i.id)}"><ha-icon icon="mdi:map-marker"></ha-icon>Bekijk op kaart</button>
    </div>`;
  }

  /* ---------- routes ---------- */

  /** Routes to show: all, those of one person, or those of the logged-in user's person. */
  _visibleRoutes() {
    let wanted = this._config.person || null;
    if (this._config.my_routes_only) {
      const userId = this._hass?.user?.id;
      const mine = Object.values(this._hass?.states || {}).find(
        (s) => s.entity_id.startsWith("person.") && userId && s.attributes.user_id === userId
      );
      wanted = mine ? mine.entity_id : "none";
    }
    return wanted ? this._routes.filter((route) => route.person === wanted) : this._routes;
  }

  _personHtml(entityId) {
    const state = entityId && this._hass?.states[entityId];
    if (!state) return "";
    const name = state.attributes.friendly_name || entityId;
    const picture = state.attributes.entity_picture;
    return `<span class="person">${picture ? `<img src="${esc(picture)}" alt="" />` : "<ha-icon icon=\"mdi:account\"></ha-icon>"}${esc(name)}</span>`;
  }

  _routesHtml() {
    const routes = this._visibleRoutes();
    if (!routes.length) return "";
    const time = (iso) => new Date(iso).toLocaleTimeString("nl-NL", { hour: "2-digit", minute: "2-digit" });
    const min = (value) => `${Math.round(value)} min`;
    const rows = routes.map((route) => {
      const selected = route.id === this._selectedRoute;
      if (route.error || !route.best) {
        return `<div class="route"><div class="route-head"><span class="route-name">${esc(route.name)}</span></div>
          <div class="route-sub">Route niet beschikbaar: de locatie of de ANWB-gegevens ontbreken.</div></div>`;
      }
      const best = route.best;
      const level = best.delay_min >= 10 ? "bad" : best.delay_min >= 1 ? "warn" : "";
      const jams = best.incidents.length;
      const alternatives =
        selected && route.alternatives.length
          ? `<div class="route-alts"><div class="route-alts-title">Routes</div>` +
            [best, ...route.alternatives]
              .map((alt, index) => {
                const diff = index === 0 ? "snelste" : `${alt.difference_min > 0 ? "+" : ""}${Math.round(alt.difference_min)} min`;
                const altIndex = index === 0 ? -1 : index - 1;
                return `<div class="route-alt ${altIndex === this._selectedAlt ? "active" : ""}" data-route="${esc(route.id)}" data-alt="${altIndex}">
                  <span>${esc(alt.via.join(" · ") || "Route")}</span><span>${min(alt.duration_min)}</span>
                  <span class="diff">${diff}</span><span class="diff">${Math.round(alt.distance_km)} km</span></div>`;
              })
              .join("") +
            `</div>`
          : "";
      return `<div class="route ${selected ? "selected" : ""}" data-route="${esc(route.id)}">
        <div class="route-head"><span class="route-name">${esc(route.name)}${this._personHtml(route.person)}</span>
          <button class="route-show" data-route="${esc(route.id)}">${selected ? "Verberg route" : "Bekijk op kaart"}</button></div>
        <div class="route-stats">
          <span class="route-time">${min(best.duration_min)}</span>
          <span class="delay-tag ${level}">${best.delay_min >= 1 ? `+ ${min(best.delay_min)} vertraging` : "Geen vertraging"}</span>
          <span>Aankomst ${time(best.arrival)}</span>
        </div>
        <div class="route-sub">
          <span>${esc(best.via.join(" · "))}</span><span>${Math.round(best.distance_km)} km</span>
          ${jams ? `<span>${jams} ${jams === 1 ? "file" : "files"} op de route</span>` : ""}
          ${best.toll ? "<span>Tol</span>" : ""}
        </div>
        ${alternatives}
      </div>`;
    });
    return `<div class="section-title">Mijn routes</div>${rows.join("")}`;
  }

  _toggleRoute(id) {
    this._selectedRoute = this._selectedRoute === id ? null : id;
    this._selectedAlt = -1;
    this._renderList();
    this._drawRoute({ fit: true });
    if (this._selectedRoute && !this._root.classList.contains("wide")) {
      this.shadowRoot.querySelector(".mapbox").scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }

  _pickAlternative(id, index) {
    this._selectedAlt = index;
    this._renderList();
    this._drawRoute({ fit: true });
  }

  _drawRoute({ fit = false } = {}) {
    if (!this._map || !this._L) return;
    const L = this._L;
    this._routeLayer.clearLayers();
    const route = this._routes.find((r) => r.id === this._selectedRoute);
    if (!route || !route.best) return;

    const all = [route.best, ...route.alternatives];
    const chosen = all[this._selectedAlt + 1] || route.best;
    const line = (path, color, weight, opacity) => {
      if (path.length < 2) return;
      L.polyline(path, { color: "#fff", weight: weight + 4, opacity: 0.9, lineCap: "round", interactive: false }).addTo(this._routeLayer);
      L.polyline(path, { color, weight, opacity, lineCap: "round", interactive: false }).addTo(this._routeLayer);
    };
    for (const alt of all) if (alt !== chosen) line(alt.path, "#78909c", 5, 0.8);
    line(chosen.path, "#1976d2", 7, 1);
    // Delays on the route itself, on top of the blue line
    for (const incident of chosen.incidents) line(incident.path, incident.delay_min >= 5 ? "#d32f2f" : "#f57c00", 7, 1);

    const endpoint = (point, letter, color) =>
      L.marker(point, {
        icon: L.divIcon({ className: "", html: `<div class="endpoint" style="background:${color}">${letter}</div>`, iconSize: [26, 26], iconAnchor: [13, 13] }),
        interactive: false,
        keyboard: false,
        zIndexOffset: 500,
      }).addTo(this._routeLayer);
    endpoint(route.origin, "A", "#2e7d32");
    endpoint(route.destination, "B", "#c62828");

    if (fit && chosen.path.length > 1) this._map.flyToBounds(L.latLngBounds(chosen.path), { padding: [50, 50], duration: 0.7 });
  }

  /* ---------- selection ---------- */

  _select(id, { zoom = false, scrollList = false } = {}) {
    const incident = this._incidents.find((i) => i.id === id);
    if (!incident) return;
    this._selectedId = id;
    this._expanded.add(incident.road);

    // Make sure the incident is visible in the list (a filter could hide it)
    if (!this._filters.has(incident.category)) {
      this._filters.add(incident.category);
      this._renderToolbar();
    }
    this._renderList();
    if (scrollList) {
      this.shadowRoot.querySelector(`.item[data-id="${CSS.escape(id)}"]`)?.scrollIntoView({ block: "center", behavior: "smooth" });
    }

    this._updateMap();
    this._markers.get(id)?.openPopup();
    if (zoom) this._focus(incident);
    if (zoom && !this._root.classList.contains("wide")) {
      this.shadowRoot.querySelector(".mapbox").scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }

  _focus(incident) {
    if (!this._map || !this._L) return;
    const L = this._L;
    const points = incident.path?.length > 1 ? incident.path : null;
    if (points) this._map.flyToBounds(L.latLngBounds(points), { padding: [60, 60], maxZoom: 14, duration: 0.7 });
    else if (incident.latitude != null) this._map.flyTo([incident.latitude, incident.longitude], 15, { duration: 0.7 });
  }

  /* ---------- map ---------- */

  async _initMap() {
    const container = this.shadowRoot.querySelector(".map");
    try {
      const { L, css } = await loadLeaflet();
      if (!container.isConnected) return; // card was rebuilt meanwhile
      this._L = L;
      const style = document.createElement("style");
      style.textContent = css;
      this.shadowRoot.appendChild(style);

      this._map = L.map(container, { zoomControl: true, attributionControl: true, preferCanvas: false });
      this._map.attributionControl.setPrefix(false);
      this._routeLayer = L.layerGroup().addTo(this._map);
      this._lines = L.layerGroup().addTo(this._map);
      this._pins = L.layerGroup().addTo(this._map);
      this._markers = new Map();
      this._applyTiles();
      L.marker(this._home(), {
        icon: L.divIcon({ className: "", html: '<div class="home-dot"></div>', iconSize: [16, 16] }),
        interactive: false,
        keyboard: false,
      }).addTo(this._map);
      // Fit once the container has a real size, otherwise Leaflet picks a wrong zoom
      this._mapObserver = new ResizeObserver(() => {
        this._map.invalidateSize();
        if (!this._fitted && container.clientWidth > 0) {
          this._fitted = true;
          this._fitHome();
        }
      });
      this._mapObserver.observe(container);
      this._updateMap();
      this._drawRoute();
    } catch (err) {
      this._showStatus("De kaart kon niet geladen worden.");
    }
  }

  _home() {
    const config = this._hass?.config;
    return config ? [config.latitude, config.longitude] : [52.09, 5.12];
  }

  _fitHome() {
    if (!this._map || !this._L) return;
    const [lat, lon] = this._home();
    const dLat = (Number(this._config.radius_km) || 20) / 111.32;
    const dLon = dLat / Math.cos((lat * Math.PI) / 180);
    this._map.fitBounds([[lat - dLat, lon - dLon], [lat + dLat, lon + dLon]]);
  }

  _applyTiles() {
    if (!this._map || !this._L) return;
    this._tiles?.remove();
    this._labels?.remove();
    // Esri basemaps need no API key and no referrer (OpenStreetMap blocks the Home Assistant app)
    const esri = (path) => `https://server.arcgisonline.com/ArcGIS/rest/services/${path}/MapServer/tile/{z}/{y}/{x}`;
    const options = { maxZoom: 19, maxNativeZoom: this._dark ? 16 : 19, attribution: "Tiles © Esri" };
    this._tiles = this._L
      .tileLayer(esri(this._dark ? "Canvas/World_Dark_Gray_Base" : "World_Street_Map"), options)
      .addTo(this._map);
    this._tiles.bringToBack();
    if (this._dark) {
      this._labels = this._L
        .tileLayer(esri("Canvas/World_Dark_Gray_Reference"), { ...options, pane: "shadowPane" })
        .addTo(this._map);
    }
  }

  _updateMap() {
    if (!this._map || !this._L) return;
    const L = this._L;
    this._lines.clearLayers();
    this._pins.clearLayers();
    this._markers = new Map();

    // The map shows what the list shows, limited to the categories chosen for the map
    const shown = this._visible().filter((i) => this._mapCategories.has(i.category));
    const selected = this._incidents.find((i) => i.id === this._selectedId);
    if (selected && !shown.includes(selected)) shown.push(selected);

    // Draw the selected incident last so it ends up on top
    shown.sort((a, b) => (a.id === this._selectedId) - (b.id === this._selectedId));
    for (const incident of shown) this._draw(L, incident, incident.id === this._selectedId);
  }

  _draw(L, incident, selected) {
    if (incident.path?.length > 1) {
      const latlngs = incident.path;
      const dashArray = incident.category === "roadworks" ? "2 10" : null;
      L.polyline(latlngs, { color: "#fff", weight: selected ? 12 : 9, opacity: 0.9, lineCap: "round", interactive: false }).addTo(this._lines);
      L.polyline(latlngs, { color: incident.color, weight: selected ? 8 : 5, opacity: 1, lineCap: "round", dashArray })
        .on("click", () => this._select(incident.id, { scrollList: true }))
        .addTo(this._lines);
    }
    if (incident.latitude == null) return;
    const marker = L.marker([incident.latitude, incident.longitude], {
      icon: L.divIcon({
        className: "",
        html: `<div class="pin ${selected ? "selected" : ""}" style="background:${incident.color}"><svg viewBox="0 0 24 24"><path d="${MDI[incident.category]}"/></svg></div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15],
      }),
      zIndexOffset: selected ? 1000 : 0,
      riseOnHover: true,
    });
    marker.bindPopup(this._popupHtml(incident), { maxWidth: 260, closeButton: false, autoPan: false });
    marker.on("click", () => this._select(incident.id, { scrollList: true }));
    marker.addTo(this._pins);
    this._markers.set(incident.id, marker);
  }

  _popupHtml(i) {
    const meta = [i.delay_min != null ? `+ ${i.delay_min} min` : null, i.length_km != null ? `${i.length_km} km` : null]
      .filter(Boolean)
      .join(" · ");
    return `<div class="popup"><b>${esc(i.road)} ${esc(i.category === "radars" ? i.from : title(i))}</b>
      <div class="sub">${esc(TYPE_LABEL[i.incident_type] || "")}${meta ? " · " + esc(meta) : ""}</div>
      ${i.reason ? `<div>${esc(i.reason)}</div>` : ""}</div>`;
  }
}

const EDITOR_SCHEMA = [
  { name: "show_map", selector: { boolean: {} } },
  { name: "my_routes_only", selector: { boolean: {} } },
  { name: "person", selector: { entity: { domain: "person" } } },
  { name: "radius_km", selector: { number: { min: 1, max: 100, step: 1, mode: "slider", unit_of_measurement: "km" } } },
  { name: "height", selector: { number: { min: 300, max: 1400, step: 10, mode: "slider", unit_of_measurement: "px" } } },
];
const EDITOR_LABELS = {
  show_map: "Kaart tonen (uit = alleen de lijst)",
  my_routes_only: "Alleen mijn routes (de persoon die bij jouw gebruiker hoort)",
  person: "Alleen routes van deze persoon (leeg = alle routes)",
  radius_km: "Beginzoom: straal rond je thuislocatie",
  height: "Hoogte van de kaart op brede schermen",
};

const EDITOR_DEFAULTS = { show_map: true, my_routes_only: false, radius_km: 20, height: 640 };

class AnwbFileCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = config;
    // Home Assistant hands back what we just emitted: keep the form as it is then, otherwise
    // clearing a field (to type a new number) would snap back to the default straight away.
    if (JSON.stringify(config) !== this._emitted) this._data = { ...EDITOR_DEFAULTS, ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._form) this._form.hass = hass;
  }

  _render() {
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.schema = EDITOR_SCHEMA;
      this._form.computeLabel = (schema) => EDITOR_LABELS[schema.name] || schema.name;
      this._form.addEventListener("value-changed", (event) => {
        this._data = event.detail.value;
        this._emitted = JSON.stringify(this._data);
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._data }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._data;
  }
}

customElements.define("anwb-file-map-card", AnwbFileCard);
customElements.define("anwb-file-map-card-editor", AnwbFileCardEditor);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "anwb-file-map-card",
  name: "ANWB File",
  description: "Files, flitsers en werkzaamheden: lijst met zoeken en filters naast een kaart, zoals op anwb.nl.",
  preview: false,
  documentationURL: "https://github.com/vinnie1234/HomeAssisantANWBFile",
});
