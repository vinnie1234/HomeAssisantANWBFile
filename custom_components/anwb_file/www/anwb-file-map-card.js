/*
 * ANWB File map card
 *
 * Draws every ANWB File incident on a map: jams as a coloured line along the road
 * (yellow = slow, orange = queueing, red = stationary/closed) plus a marker, and
 * optionally a text list underneath.
 *
 *   type: custom:anwb-file-map-card
 *   show_list: true      # default true
 *   show_map: true       # default true
 *   height: 450          # map height in px, default 450
 */
const SOURCE = "anwb_file";
const CATEGORY_LABEL = { jams: "Files", radars: "Flitsers", roadworks: "Wegwerkzaamheden" };
const CATEGORY_ORDER = ["jams", "radars", "roadworks"];

class AnwbFileMapCard extends HTMLElement {
  setConfig(config) {
    this._config = { show_list: true, show_map: true, height: 450, ...config };
    this._signature = null;
    this._map = null;
    this._built = false;
    if (this.shadowRoot) this.shadowRoot.innerHTML = "";
  }

  getCardSize() {
    return 8;
  }

  static getStubConfig() {
    return {};
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });

    const incidents = Object.values(hass.states)
      .filter((s) => s.entity_id.startsWith("geo_location.") && s.attributes.source === SOURCE)
      .map((s) => ({ entity_id: s.entity_id, ...s.attributes }));

    const signature = incidents.map((i) => `${i.entity_id}:${i.delay_min}:${i.length_km}`).join("|");
    if (this._map) this._map.hass = hass;
    if (signature === this._signature) return;
    this._signature = signature;
    this._render(incidents);
  }

  _render(incidents) {
    if (!this._built) {
      this.shadowRoot.innerHTML = `
        <style>
          .map { width: 100%; }
          .list { padding: 8px 16px 16px; }
          h3 { margin: 12px 0 4px; font-size: 1em; }
          .row { display: flex; gap: 8px; align-items: baseline; padding: 3px 0; line-height: 1.3; }
          .dot { flex: none; width: 10px; height: 10px; border-radius: 50%; }
          .meta { color: var(--secondary-text-color); font-size: .9em; }
          .empty { color: var(--secondary-text-color); padding: 8px 0; }
        </style>
        <ha-card>
          <div class="map"></div>
          <div class="list"></div>
        </ha-card>`;
      this._built = true;
    }
    const mapEl = this.shadowRoot.querySelector(".map");
    mapEl.style.display = this._config.show_map ? "" : "none";
    mapEl.style.height = `${this._config.height}px`;
    if (this._config.show_map) this._renderMap(mapEl, incidents);
    this.shadowRoot.querySelector(".list").innerHTML = this._config.show_list ? this._listHtml(incidents) : "";
  }

  async _renderMap(container, incidents) {
    if (!this._map) {
      // ha-map is lazy loaded by Home Assistant; creating a map card makes it available
      if (!customElements.get("ha-map")) {
        try {
          const helpers = await window.loadCardHelpers();
          await helpers.createCardElement({ type: "map", entities: [] });
        } catch (e) {
          /* fall through to the timeout below */
        }
        await Promise.race([
          customElements.whenDefined("ha-map"),
          new Promise((resolve) => setTimeout(resolve, 5000)),
        ]);
      }
      if (!customElements.get("ha-map")) {
        container.textContent = "Kaart kon niet geladen worden.";
        return;
      }
      if (this._map) return; // another render finished first
      container.textContent = "";
      this._map = document.createElement("ha-map");
      this._map.hass = this._hass;
      this._map.autoFit = true;
      this._map.zoom = 8;
      this._map.style.height = "100%";
      container.appendChild(this._map);
    }
    const now = new Date();
    this._map.entities = incidents.map((i) => ({ entity_id: i.entity_id, color: i.color }));
    this._map.paths = incidents
      .filter((i) => i.path && i.path.length > 1)
      .map((i) => ({
        color: i.color,
        name: `${i.road} ${i.from} - ${i.to}`,
        points: i.path.map((point) => ({ point, timestamp: now })),
      }));
  }

  _listHtml(incidents) {
    const html = [];
    for (const category of CATEGORY_ORDER) {
      const items = incidents
        .filter((i) => i.category === category)
        .sort((a, b) => (b.delay_min || 0) - (a.delay_min || 0) || a.road.localeCompare(b.road));
      if (!items.length) continue;
      html.push(`<h3>${CATEGORY_LABEL[category]} (${items.length})</h3>`);
      for (const i of items) {
        const meta = [
          i.length_km != null ? `${i.length_km} km` : null,
          i.delay_min != null ? `${i.delay_min} min vertraging` : null,
        ].filter(Boolean);
        const where = category === "radars" ? i.from : `${i.from} → ${i.to}`;
        html.push(
          `<div class="row"><span class="dot" style="background:${i.color}"></span>` +
            `<span><b>${this._esc(i.road)}</b> ${this._esc(where)}` +
            (meta.length ? ` <span class="meta">${meta.join(", ")}</span>` : "") +
            `</span></div>`
        );
      }
    }
    return html.length ? html.join("") : `<div class="empty">Geen meldingen</div>`;
  }

  _esc(text) {
    const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" };
    return String(text ?? "").replace(/[&<>"]/g, (c) => map[c]);
  }
}

customElements.define("anwb-file-map-card", AnwbFileMapCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "anwb-file-map-card",
  name: "ANWB File",
  description: "Files, flitsers en werkzaamheden op de kaart, met gekleurde wegen en een tekstlijst.",
});
