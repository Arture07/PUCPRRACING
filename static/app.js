// Toolbar interativa para imagens de gráficos (pan/zoom, back/forward, reset, salvar, configurar subplots)

(function () {
  const TOOLTIP = {
    home: 'Reset original view',
    back: 'Back to previous view',
    forward: 'Forward to next view',
    pan: 'Left button pans, Right button zooms\n x/y fixes axis, CTRL fixes aspect',
    zoom: 'Zoom to rectangle\n x/y fixes axis',
    config: 'Configure subplots',
    save: 'Save the figure',
  };

  function parseUrl(src) {
    try { return new URL(src, window.location.origin); } catch { return null; }
  }

  function setSearchParams(url, params) {
    const u = new URL(url, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
      if (v === undefined || v === null || v === '') u.searchParams.delete(k);
      else u.searchParams.set(k, v);
    });
    return u.toString();
  }

  class History {
    constructor() {
      this.stack = [];
      this.index = -1;
    }
    push(state) {
      this.stack = this.stack.slice(0, this.index + 1);
      this.stack.push(JSON.parse(JSON.stringify(state)));
      this.index = this.stack.length - 1;
    }
    back() { if (this.index > 0) { this.index--; return this.stack[this.index]; } return null; }
    forward() { if (this.index < this.stack.length - 1) { this.index++; return this.stack[this.index]; } return null; }
    current() { return this.index >= 0 ? this.stack[this.index] : null; }
    reset(state) { this.stack = []; this.index = -1; this.push(state); }
  }

  async function fetchPlotJson(url) {
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error('Falha ao obter gráfico');
    return await res.json();
  }

  // Renderiza figura Plotly em um container
  async function renderPlot(divId, url) {
    const data = await fetchPlotJson(url);
    const fig = JSON.parse(JSON.stringify(data));
    await Plotly.react(divId, fig.data, fig.layout, { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['toImage'] });
    const el = document.getElementById(divId);
    if (el) el.dispatchEvent(new Event('plot-rendered'));
  }
  window.renderPlot = renderPlot;

  class PlotToolbar {
    constructor(container) {
      this.box = container;
      // Para Plotly usamos o primeiro filho com class plot (div)
      this.plotDiv = container.querySelector('.plot');
      this.overlay = container.querySelector('.plot-rect');
      this.mode = 'none'; // none|pan|zoom
      this.hist = new History();
      this._buildButtons();
      this._bind();
    }
    _buildButtons() {
      const bar = this.box.querySelector('.plot-toolbar');
      bar.innerHTML = '';
      const mk = (key, label) => {
        const b = document.createElement('button');
        b.className = 'plot-btn';
        b.title = TOOLTIP[key];
        b.dataset.key = key;
        b.textContent = label;
        return b;
      };
      const btns = [
        mk('home', '🏠'),
        mk('back', '⬅️'),
        mk('forward', '➡️'),
        mk('pan', '🖱️'),
        mk('zoom', '🔍'),
        mk('config', '⚙️'),
        mk('save', '💾'),
      ];
      btns.forEach(b => bar.appendChild(b));
    }
    _bind() {
      // init after first render
      this.plotDiv.addEventListener('plot-rendered', () => this._onRendered());
      this.box.querySelector('.plot-toolbar').addEventListener('click', (e) => {
        if (!(e.target instanceof HTMLElement)) return;
        const key = e.target.dataset.key;
        if (!key) return;
        e.stopPropagation();
        this._onBtn(key);
      });
    }
    _onRendered() {
      this.resetView();
      // registrar eventos de navegação (ranges)
      if (typeof this.plotDiv.on === 'function') {
        this.plotDiv.on('plotly_relayout', (ev) => {
          const s = this._snapshot();
          if (s) this.hist.push(s);
        });
      }
    }
    _onBtn(key) {
      switch (key) {
        case 'home': this.resetView(); break;
        case 'back': {
          const s = this.hist.back(); if (s) this._applyState(s);
          break;
        }
        case 'forward': {
          const s = this.hist.forward(); if (s) this._applyState(s);
          break;
        }
        case 'pan': this.mode = (this.mode === 'pan' ? 'none' : 'pan'); this._updateActive(); Plotly.relayout(this.plotDiv, { dragmode: (this.mode === 'pan' ? 'pan' : false) }); break;
        case 'zoom': this.mode = (this.mode === 'zoom' ? 'none' : 'zoom'); this._updateActive(); Plotly.relayout(this.plotDiv, { dragmode: (this.mode === 'zoom' ? 'zoom' : false) }); break;
        case 'config': this.openConfig(); break;
        case 'save': this.save(); break;
      }
    }
    _updateActive() {
      this.box.querySelectorAll('.plot-btn').forEach(b => b.classList.remove('active'));
      const btn = this.box.querySelector(`.plot-btn[data-key="${this.mode}"]`);
      if (btn) btn.classList.add('active');
      if (this.overlay) this.overlay.style.display = 'none';
      this.box.classList.remove('pan','zoom');
      if (this.mode === 'pan') this.box.classList.add('pan');
      if (this.mode === 'zoom') this.box.classList.add('zoom');
    }
    resetView() {
      // autorange para ambos os eixos
      Plotly.relayout(this.plotDiv, { 'xaxis.autorange': true, 'yaxis.autorange': true }).then(() => {
        const s = this._snapshot();
        if (s) this.hist.reset(s);
      });
    }
    _applyState(s) {
      if (!s) return;
      const rel = {};
      if (s.xr) rel['xaxis.range'] = s.xr;
      else rel['xaxis.autorange'] = true;
      if (s.yr) rel['yaxis.range'] = s.yr;
      else rel['yaxis.autorange'] = true;
      Plotly.relayout(this.plotDiv, rel);
    }
    _snapshot() {
      const l = this.plotDiv.layout || {};
      const xr = (l.xaxis && l.xaxis.range) ? [l.xaxis.range[0], l.xaxis.range[1]] : null;
      const yr = (l.yaxis && l.yaxis.range) ? [l.yaxis.range[0], l.yaxis.range[1]] : null;
      return { xr, yr };
    }

    openConfig() {
      const modal = document.getElementById('subplot-modal');
      if (!modal) return;
      modal.style.display = 'block';
      const sliders = modal.querySelectorAll('input[type="range"]');
      // set from current URL if exists
      // para Plotly via JSON, mantemos os sliders como controladores de margens do layout
      const params = new URLSearchParams();
      sliders.forEach(sl => {
        const key = sl.name;
        sl.oninput = () => {
          const layout = this._getPlotLayout();
          const obj = {}; sliders.forEach(s2 => obj[s2.name] = parseFloat(s2.value));
          // mapeia para margens aproximadas
          layout.margin = layout.margin || {};
          layout.margin.l = Math.floor(40 + obj.left * 200);
          layout.margin.b = Math.floor(30 + obj.bottom * 200);
          layout.margin.r = Math.floor(10 + (1 - obj.right) * 200);
          layout.margin.t = Math.floor(40 + (1 - obj.top) * 200);
          Plotly.relayout(this.plotDiv, layout);
        };
      });
      modal.querySelector('.close-btn').onclick = () => modal.style.display = 'none';
      modal.querySelector('.reset-btn').onclick = () => {
        sliders.forEach(s => s.value = s.dataset.def || s.min);
        Plotly.relayout(this.plotDiv, { margin: { l: 40, r: 10, t: 40, b: 30 } });
      };
    }

    save() {
      Plotly.downloadImage(this.plotDiv, { format: 'png', filename: 'figure' });
    }

    _getPlotLayout() {
      const gd = this.plotDiv;
      return gd && gd.layout ? JSON.parse(JSON.stringify(gd.layout)) : {};
    }
  }

  function initPlotToolbars(root = document) {
    root.querySelectorAll('.plot-box').forEach((box) => {
      if (!box._plotToolbar) box._plotToolbar = new PlotToolbar(box);
    });
  }

  // Expose globally
  window.initPlotToolbars = initPlotToolbars;
})();
