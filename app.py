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
            filename=session.get("filepath"),
        )
        return render_template("explore.html", cols=cols, info=info)

    # Rotas de geração de imagens (PNG) a partir do DF atual
    def _fig_bytes(fig) -> bytes:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        buf.seek(0)
        return buf.getvalue()

    @app.get("/plot/series")
    def plot_series():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channels = request.args.getlist("ch")
        fig, ax = plt.subplots(figsize=(8, 3), dpi=120)
        configurar_estilo_plot(ax, "Série Temporal")
        plotar_dados_no_canvas(df, channels, None, fig, ax)
        png = _fig_bytes(fig)
        plt.close(fig)
        return Response(png, mimetype="image/png")

    @app.get("/plot/gg")
    def plot_gg():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channel_mapping, _, _ = load_config()
        gg_data, lat_col, lon_col, error = calcular_metricas_gg(df, channel_mapping)
        if error:
            return Response(error, status=400)
        fig, ax = plt.subplots(figsize=(5, 5), dpi=120)
        configurar_estilo_plot(ax, "Diagrama G-G")
        plotar_gg_diagrama_nos_eixos(gg_data, None, fig, ax, lat_col, lon_col)
        png = _fig_bytes(fig)
        plt.close(fig)
        return Response(png, mimetype="image/png")

    @app.get("/plot/map")
    def plot_map():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channel_mapping, _, _ = load_config()
        lat_col = channel_mapping.get("gpslat")
        lon_col = channel_mapping.get("gpslon")
        color_channel = request.args.get("c") or None
        fig, ax = plt.subplots(figsize=(5, 5), dpi=120)
        configurar_estilo_plot(ax, "Mapa da Pista")
        plotar_mapa_pista_nos_eixos(
            df, None, fig, ax, lat_col, lon_col, color_channel
        )
        png = _fig_bytes(fig)
        plt.close(fig)
        return Response(png, mimetype="image/png")

    @app.get("/plot/susp")
    def plot_susp_hist():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channel_mapping, _, _ = load_config()
        susp_internal = ["suspposfl", "suspposfr", "suspposrl", "suspposrr"]
        cols = [
            c
            for c in (channel_mapping.get(n) for n in susp_internal)
            if c and c in df.columns
        ]
        fig, ax = plt.subplots(figsize=(6, 3), dpi=120)
        configurar_estilo_plot(ax, "Histograma Suspensão")
        # a função original espera config_map, aqui passamos lista de colunas já resolvida
        plotar_histograma_suspensao(df, None, fig, ax, channel_mapping)
        png = _fig_bytes(fig)
        plt.close(fig)
        return Response(png, mimetype="image/png")

    @app.get("/plot/accel")
    def plot_accel():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channel_mapping, _, _ = load_config()
        fig, ax = plt.subplots(figsize=(6, 3), dpi=120)
        configurar_estilo_plot(ax, "Aceleração")
        plotar_analise_aceleracao(df, None, fig, ax, channel_mapping)
        png = _fig_bytes(fig)
        plt.close(fig)
        return Response(png, mimetype="image/png")

    @app.get("/plot/skid")
    def plot_skid():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        channel_mapping, _, _ = load_config()
        fig, ax = plt.subplots(figsize=(6, 3), dpi=120)
        configurar_estilo_plot(ax, "Skidpad")
        plotar_analise_skidpad(df, None, fig, ax, channel_mapping)
        png = _fig_bytes(fig)
        plt.close(fig)
        return Response(png, mimetype="image/png")

    @app.get("/plot/delta")
    def plot_delta():
        df = _get_df()
        if df is None:
            return Response("No data", status=400)
        fig, ax = plt.subplots(figsize=(6, 3), dpi=120)
        configurar_estilo_plot(ax, "Delta-Time")
        plotar_delta_time(df, None, fig, ax)
        png = _fig_bytes(fig)
        plt.close(fig)
        return Response(png, mimetype="image/png")

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


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
