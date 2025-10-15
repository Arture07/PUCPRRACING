from __future__ import annotations

import io
import os
from datetime import datetime
from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from flask import (Flask, Response, flash, redirect, render_template, request,
                   send_file, session, url_for)
import plotly.graph_objects as go
import plotly.io as pio

from calculations import (
    calcular_metricas_aceleracao,
    calcular_metricas_gg,
    calcular_metricas_skidpad,
    calcular_tempos_volta,
)
from config_manager import CONFIG_FILE, load_config
from data_loader import carregar_log_csv_web as carregar_log_csv
from plotting import (
    configurar_estilo_plot,
    plotar_analise_aceleracao,
    plotar_analise_skidpad,
    plotar_dados_no_canvas,
    plotar_delta_time,
    plotar_gg_diagrama_nos_eixos,
    plotar_histograma_suspensao,
    plotar_mapa_pista_nos_eixos,
)

# Use backend sem GUI
matplotlib.use("Agg")
# Ajuste de estilo global similar ao main_gui.py
plt.style.use("dark_background")
plt.rc(
    "axes",
    facecolor="#2B2B2B",
    edgecolor="#424242",
    labelcolor="#BDBDBD",
    titlecolor="#F5F5F5",
)
plt.rc("figure", facecolor="#1F1F1F")
plt.rc("xtick", color="#BDBDBD")
plt.rc("ytick", color="#BDBDBD")
plt.rc("grid", color="#424242", linestyle="--", alpha=0.7)
plt.rc("text", color="#F5F5F5")
plt.rc(
    "legend",
    facecolor="#1F1F1F",
    edgecolor="#424242",
    labelcolor="#F5F5F5",
)


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

    # Estado simples em memória (para demo). Em produção, usar storage (S3, disco, DB)
    DATA_CACHE: dict[str, pd.DataFrame] = {}

    @app.context_processor
    def inject_globals():
        channel_mapping, track_config, analysis_config = load_config()
        return dict(
            CONFIG_FILE=CONFIG_FILE,
            channel_mapping=channel_mapping,
            track_config=track_config,
            analysis_config=analysis_config,
        )

    @app.route("/")
    def index():
        filepath = session.get("filepath")
        df_info = None
        if filepath and filepath in DATA_CACHE:
            df = DATA_CACHE[filepath]
            df_info = dict(
                filepath=filepath,
                basename=os.path.basename(filepath),
                rows=len(df),
                cols=list(df.columns),
                has_laps=("LapNumber" in df.columns),
            )
        return render_template("index.html", df_info=df_info)

    @app.post("/upload")
    def upload():
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("Nenhum arquivo selecionado", "warning")
            return redirect(url_for("index"))
        # Salva em um path temporário
        upload_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        filepath = os.path.join(upload_dir, safe_name)
        file.save(filepath)

        # Carrega com util do projeto (config mapping é carregado no template)
        channel_mapping, _, _ = load_config()
        df = carregar_log_csv(filepath, channel_mapping)
        if df is None:
            flash("Falha ao carregar CSV. Verifique o formato/colunas.", "danger")
            return redirect(url_for("index"))

        DATA_CACHE[filepath] = df
        session["filepath"] = filepath
        flash("Log carregado com sucesso.", "success")
        return redirect(url_for("explore"))

    def _get_df() -> Optional[pd.DataFrame]:
        filepath = session.get("filepath")
        if not filepath:
            return None
        return DATA_CACHE.get(filepath)

    @app.get("/explore")
    def explore():
        df = _get_df()
        if df is None:
            flash("Nenhum log carregado.", "warning")
            return redirect(url_for("index"))
        cols = list(df.columns)
        info = dict(
            rows=len(df),
            cols=len(cols),
            filename=os.path.basename(session.get("filepath") or ""),
        )
        return render_template("explore.html", cols=cols, info=info)

    # Rotas de geração de imagens (PNG) a partir do DF atual
    def _fig_bytes(fig) -> bytes:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        return buf.getvalue()

    def _apply_subplot_params(fig: plt.Figure):
        try:
            kw = {}
            for k in ["left", "right", "top", "bottom", "wspace", "hspace"]:
                v = request.args.get(k)
                if v is not None:
                    kw[k] = float(v)
            if kw:
                fig.subplots_adjust(**kw)
        except Exception:
            pass

    @app.get("/plot/series")
    def plot_series():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channels = request.args.getlist("ch")
        # Plotly: série temporal interativa
        fig = go.Figure()
        if isinstance(df.index, pd.DatetimeIndex):
            x = df.index
        else:
            x = list(range(len(df)))
        for ch in channels:
            if ch in df.columns:
                fig.add_trace(go.Scatter(x=x, y=df[ch], mode='lines', name=ch))
        fig.update_layout(
            template='plotly_dark',
            title='Dados da Série Temporal',
            xaxis_title='Tempo',
            yaxis_title='Valor',
            margin=dict(l=40, r=10, t=40, b=30),
            height=420,
        )
        return Response(pio.to_json(fig), mimetype='application/json')

    @app.get("/plot/gg")
    def plot_gg():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channel_mapping, _, _ = load_config()
        gg_data, lat_col, lon_col, error = calcular_metricas_gg(df, channel_mapping)
        if error:
            return Response(error, status=400)
        fig = go.Figure()
        if not gg_data.empty and lat_col and lon_col:
            fig.add_trace(go.Scattergl(
                x=gg_data[lat_col], y=gg_data[lon_col], mode='markers',
                marker=dict(size=3, color='#FBC02D'), name='G-G'
            ))
            lim = max(gg_data[lat_col].abs().max(), gg_data[lon_col].abs().max()) * 1.1
            fig.update_xaxes(range=[-lim, lim], zeroline=True)
            fig.update_yaxes(range=[-lim, lim], zeroline=True, scaleanchor="x", scaleratio=1)
        fig.update_layout(template='plotly_dark', title='Diagrama G-G', xaxis_title=f'{lat_col} (G)', yaxis_title=f'{lon_col} (G)', height=480)
        return Response(pio.to_json(fig), mimetype='application/json')

    @app.get("/plot/map")
    def plot_map():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channel_mapping, _, _ = load_config()
        lat_col = channel_mapping.get("gpslat")
        lon_col = channel_mapping.get("gpslon")
        color_channel = request.args.get("c") or None
        fig = go.Figure()
        if lat_col in df.columns and lon_col in df.columns:
            lat = df[lat_col]
            lon = df[lon_col]
            if color_channel and color_channel in df.columns:
                fig.add_trace(go.Scattergl(x=lon, y=lat, mode='markers', marker=dict(size=3, color=df[color_channel], colorscale='Plasma', colorbar=dict(title=color_channel)), name='GPS'))
            else:
                fig.add_trace(go.Scattergl(x=lon, y=lat, mode='markers', marker=dict(size=3, color='#FBC02D'), name='GPS'))
            fig.update_yaxes(scaleanchor="x", scaleratio=1)
            fig.update_layout(template='plotly_dark', title='Mapa da Pista', xaxis_title=f'{lon_col} (Longitude)', yaxis_title=f'{lat_col} (Latitude)', height=520, margin=dict(l=40,r=10,t=40,b=30))
        return Response(pio.to_json(fig), mimetype='application/json')

    @app.get("/plot/susp")
    def plot_susp_hist():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channel_mapping, _, _ = load_config()
        import numpy as np
        from config_manager import get_channel_name
        susp_internal = ["suspposfl", "suspposfr", "suspposrl", "suspposrr"]
        cols = [get_channel_name(channel_mapping, n, df.columns) for n in susp_internal]
        cols = [c for c in cols if c and c in df.columns]
        fig = go.Figure()
        for c in cols:
            fig.add_trace(go.Histogram(x=df[c].dropna(), nbinsx=30, name=c, opacity=0.75))
        fig.update_layout(template='plotly_dark', barmode='overlay', title='Histograma Posição Suspensão', xaxis_title='Deslocamento (mm)', yaxis_title='Frequência', height=420)
        return Response(pio.to_json(fig), mimetype='application/json')

    @app.get("/plot/accel")
    def plot_accel():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channel_mapping, _, _ = load_config()
        # lógica similar à de plotting.plotar_analise_aceleracao
        from config_manager import get_channel_name
        ws_fl = get_channel_name(channel_mapping, "wheelspeedfl", df.columns)
        ws_fr = get_channel_name(channel_mapping, "wheelspeedfr", df.columns)
        gps_speed = get_channel_name(channel_mapping, "gpsspeed", df.columns)
        vehicle_speed = get_channel_name(channel_mapping, "vehiclespeed", df.columns)
        speed = None; label = ''
        if vehicle_speed and vehicle_speed in df.columns:
            speed = df[vehicle_speed]; label = f"{vehicle_speed} (mapeada)"
        elif ws_fl and ws_fr and ws_fl in df.columns and ws_fr in df.columns:
            speed = df[[ws_fl, ws_fr]].mean(axis=1); label = f"Média Rodas ({ws_fl}, {ws_fr})"
        elif gps_speed and gps_speed in df.columns:
            speed = df[gps_speed]; label = f"{gps_speed} (GPS)"
        fig = go.Figure()
        if speed is not None:
            x = df.index if isinstance(df.index, pd.DatetimeIndex) else list(range(len(df)))
            fig.add_trace(go.Scatter(x=x, y=speed, mode='lines', name=label))
        fig.update_layout(template='plotly_dark', title='Análise Aceleração', xaxis_title='Tempo', yaxis_title='Velocidade (m/s)', height=420)
        return Response(pio.to_json(fig), mimetype='application/json')

    @app.get("/plot/skid")
    def plot_skid():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        # simplificado: usa aceleração lateral ao longo do tempo
        channel_mapping, _, _ = load_config()
        from config_manager import get_channel_name
        lat_col = get_channel_name(channel_mapping, 'lataccel', df.columns)
        fig = go.Figure()
        if lat_col and lat_col in df.columns:
            x = df.index if isinstance(df.index, pd.DatetimeIndex) else list(range(len(df)))
            fig.add_trace(go.Scatter(x=x, y=df[lat_col], mode='lines', name=lat_col))
        fig.update_layout(template='plotly_dark', title='Skid Pad', xaxis_title='Tempo', yaxis_title='Aceleração Lateral (G)', height=420)
        return Response(pio.to_json(fig), mimetype='application/json')

    @app.get("/plot/delta")
    def plot_delta():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        fig = go.Figure()
        fig.add_annotation(text='Delta-Time (Não Implementado)', x=0.5, y=0.5, showarrow=False)
        fig.update_layout(template='plotly_dark', title='Delta-Time', height=360)
        return Response(pio.to_json(fig), mimetype='application/json')

    @app.get("/metrics/laps")
    def metrics_laps():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channel_mapping, track_config, analysis_config = load_config()
        lap_numbers, summary = calcular_tempos_volta(
            df, channel_mapping, track_config, analysis_config
        )
        if lap_numbers is not None:
            df["LapNumber"] = lap_numbers
        return Response(summary, mimetype="text/plain; charset=utf-8")

    @app.get("/metrics/skid")
    def metrics_skid():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channel_mapping, _, _ = load_config()
        text = calcular_metricas_skidpad(df, channel_mapping)
        return Response(text, mimetype="text/plain; charset=utf-8")

    @app.get("/metrics/accel")
    def metrics_accel():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channel_mapping, _, _ = load_config()
        text = calcular_metricas_aceleracao(df, channel_mapping)
        return Response(text, mimetype="text/plain; charset=utf-8")

    @app.get("/download")
    def download_csv():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        # Exporta CSV em memória
        buf = io.StringIO()
        save_index = isinstance(df.index, pd.DatetimeIndex)
        df.to_csv(buf, index=save_index)
        buf.seek(0)
        return send_file(
            io.BytesIO(buf.read().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name="dados_processados.csv",
        )

    return app

# Expor o app para servidores WSGI (ex.: gunicorn app:app)
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
