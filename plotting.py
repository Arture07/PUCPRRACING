import customtkinter as ctk
import tkinter as tk
import pandas as pd
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from typing import List, Optional, Dict
from config_manager import get_channel_name

# Importa cores (ou define aqui)
COLOR_PRIMARY_BG = "#2B2B2B"; COLOR_SECONDARY_BG = "#1E1E1E"; COLOR_RED = "#E53935"; COLOR_GOLD = "#FFA000"; COLOR_TEXT = "#E0E0E0"

# ==============================================================================
# MÓDULO: plotting.py
# ==============================================================================

def configurar_estilo_plot(ax: plt.Axes, title: str = "Gráfico"):
    """Configura estilo visual padrão para um eixo Matplotlib."""
    ax.clear(); ax.set_aspect('auto'); ax.autoscale(enable=True, axis='both')
    ax.set_xlabel(""); ax.set_ylabel("")
    ax.set_facecolor(COLOR_PRIMARY_BG)
    ax.tick_params(axis='x', colors=COLOR_TEXT, labelsize=9); ax.tick_params(axis='y', colors=COLOR_TEXT, labelsize=9)
    ax.xaxis.label.set_color(COLOR_TEXT); ax.yaxis.label.set_color(COLOR_TEXT)
    ax.title.set_color(COLOR_TEXT); ax.grid(True, linestyle='--', alpha=0.4, color=COLOR_TEXT)
    ax.set_title(title, color=COLOR_TEXT)

def plotar_dados_no_canvas(df: Optional[pd.DataFrame], channels: List[str], canvas_widget: FigureCanvasTkAgg, fig: Figure, ax: plt.Axes):
    """Desenha gráficos de séries temporais no canvas da GUI."""
    configurar_estilo_plot(ax, "Dados da Série Temporal")
    if df is not None and not df.empty and channels:
        valid_channels = [ch for ch in channels if ch in df.columns]
        if valid_channels:
            for channel in valid_channels:
                try:
                    label_prefix = "[C]" if channel == 'LapNumber' else ""
                    ax.plot(df.index, df[channel], label=f"{label_prefix}{channel}", linewidth=1.5)
                except Exception as e: print(f"Erro plot {channel}: {e}"); ax.text(0.5, 0.5, f"Erro {channel}", ha='center', color=COLOR_RED); break
            else:
                 ax.legend(fontsize='small', labelcolor=COLOR_TEXT); ax.set_xlabel("Tempo"); ax.set_ylabel("Valor")
                 if isinstance(df.index, pd.DatetimeIndex): plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
                 ax.relim(); ax.autoscale_view()
        else: ax.text(0.5, 0.5, "Nenhum canal válido selecionado", ha='center', color=COLOR_TEXT)
    else: ax.text(0.5, 0.5, "Carregue dados e selecione canais", ha='center', color=COLOR_TEXT)
    try: fig.tight_layout()
    except ValueError: print("Aviso: Erro no fig.tight_layout().")
    canvas_widget.draw()

def plotar_gg_diagrama_nos_eixos(gg_data: pd.DataFrame, canvas_widget: FigureCanvasTkAgg, fig: Figure, ax: plt.Axes, lat_accel_col: Optional[str], lon_accel_col: Optional[str]):
    """Desenha o diagrama G-G no canvas da GUI."""
    configurar_estilo_plot(ax, "Diagrama G-G")
    if not gg_data.empty and lat_accel_col and lon_accel_col:
        try:
            ax.scatter(gg_data[lat_accel_col], gg_data[lon_accel_col], alpha=0.4, s=5, color=COLOR_GOLD)
            ax.set_xlabel(f"{lat_accel_col} (G)"); ax.set_ylabel(f"{lon_accel_col} (G)")
            ax.axhline(0, color=COLOR_TEXT, linewidth=0.5); ax.axvline(0, color=COLOR_TEXT, linewidth=0.5)
            ax.axis('equal')
            x_max = gg_data[lat_accel_col].abs().max() * 1.1; y_max = gg_data[lon_accel_col].abs().max() * 1.1
            lim = max(x_max, y_max, 0.1); ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
        except Exception as e: ax.text(0.5, 0.5, f"Erro ao plotar G-G:\n{e}", ha='center', va='center', color=COLOR_RED)
    else: ax.text(0.5, 0.5, "Dados G-G indisponíveis", ha='center', va='center', color=COLOR_TEXT)
    try: fig.tight_layout()
    except ValueError: pass
    canvas_widget.draw()

def plotar_mapa_pista_nos_eixos(df: Optional[pd.DataFrame], canvas_widget: FigureCanvasTkAgg, fig: Figure, ax: plt.Axes, lat_col: Optional[str], lon_col: Optional[str], color_channel: Optional[str] = None, config_map: Optional[Dict[str, str]] = None):
    """Desenha o mapa da pista no canvas da GUI."""
    configurar_estilo_plot(ax, f"Mapa da Pista {('- Cor: ' + color_channel) if color_channel else ''}")
    if df is not None and lat_col and lat_col in df.columns and lon_col and lon_col in df.columns:
        try:
            lat_data = df[lat_col].dropna(); lon_data = df[lon_col].dropna()
            common_index = lat_data.index.intersection(lon_data.index)
            lat_data = lat_data.loc[common_index]; lon_data = lon_data.loc[common_index]
            if not lat_data.empty:
                scatter_color = COLOR_GOLD; c_data = None; cmap = 'plasma'
                color_col_real = color_channel # Usa direto o nome da coluna selecionado no combo
                if color_col_real and color_col_real in df.columns:
                     c_data_series = df[color_col_real].loc[common_index].dropna()
                     final_index = lat_data.index.intersection(c_data_series.index)
                     if not final_index.empty:
                         lat_data = lat_data.loc[final_index]; lon_data = lon_data.loc[final_index]
                         c_data = c_data_series.loc[final_index]; scatter_color = c_data
                     else: print(f"Aviso: Sem dados válidos para colorir com {color_col_real}"); color_channel = None
                sc = ax.scatter(lon_data, lat_data, c=scatter_color, cmap=cmap, s=5, marker='.')
                ax.set_xlabel(f"{lon_col} (Longitude)"); ax.set_ylabel(f"{lat_col} (Latitude)")
                ax.axis('equal')
                if color_channel and c_data is not None:
                     cbar = fig.colorbar(sc, ax=ax, fraction=0.046, pad=0.04)
                     cbar_label = color_channel
                     cbar.set_label(cbar_label, color=COLOR_TEXT); cbar.ax.yaxis.set_tick_params(color=COLOR_TEXT)
                     cbar.outline.set_edgecolor(COLOR_TEXT); plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color=COLOR_TEXT)
            else: ax.text(0.5, 0.5, "Dados GPS insuficientes", ha='center', color=COLOR_TEXT)
        except Exception as e: ax.text(0.5, 0.5, f"Erro ao plotar Mapa:\n{e}", ha='center', color=COLOR_RED)
    else: ax.text(0.5, 0.5, f"Colunas GPS ('{lat_col}', '{lon_col}') não encontradas", ha='center', color=COLOR_TEXT)
    try: fig.tight_layout()
    except ValueError: pass
    canvas_widget.draw()

def plotar_analise_skidpad(df: Optional[pd.DataFrame], canvas_widget: FigureCanvasTkAgg, fig: Figure, ax: plt.Axes, config_map: Dict[str, str]):
    """Plota gráfico básico para análise do Skid Pad."""
    lat_col = get_channel_name(config_map, 'lataccel', df.columns if df is not None else None)
    configurar_estilo_plot(ax, "Análise Skid Pad (Placeholder)")
    if df is not None and lat_col:
        try:
            ax.plot(df.index, df[lat_col], label=f"{lat_col} (Lat Accel)", color=COLOR_GOLD)
            ax.set_xlabel("Tempo"); ax.set_ylabel("Aceleração Lateral (G)")
            ax.legend(labelcolor=COLOR_TEXT)
            if isinstance(df.index, pd.DatetimeIndex): plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
            ax.text(0.05, 0.95, "Plot básico.\nAnálise real precisa\ndetectar fase do Skid Pad.", transform=ax.transAxes, fontsize=9, verticalalignment='top', color=COLOR_TEXT)
            ax.relim(); ax.autoscale_view()
        except Exception as e: ax.text(0.5, 0.5, f"Erro ao plotar:\n{e}", ha='center', color=COLOR_RED)
    else: ax.text(0.5, 0.5, f"Coluna LatAccel não encontrada/mapeada.", ha='center', color=COLOR_TEXT)
    try: fig.tight_layout()
    except ValueError: pass
    canvas_widget.draw()

def plotar_analise_aceleracao(df: Optional[pd.DataFrame], canvas_widget: FigureCanvasTkAgg, fig: Figure, ax: plt.Axes, config_map: Dict[str, str]):
    """Plota gráfico básico para análise de Aceleração."""
    speed_col = None; speed_data_to_plot = None; speed_col_name = "Velocidade"
    if df is not None:
        ws_fl = get_channel_name(config_map, 'wheelspeedfl', df.columns)
        ws_fr = get_channel_name(config_map, 'wheelspeedfr', df.columns)
        gps_speed = get_channel_name(config_map, 'gpsspeed', df.columns)
        vehicle_speed = get_channel_name(config_map, 'vehiclespeed', df.columns)
        if vehicle_speed and vehicle_speed in df.columns:
            speed_col = vehicle_speed; speed_data_to_plot = df[speed_col]; speed_col_name = f"{speed_col} (mapeada)"
        elif ws_fl and ws_fr:
            try: speed_data_to_plot = df[[ws_fl, ws_fr]].mean(axis=1); speed_col = f"Média Rodas ({ws_fl}, {ws_fr})"; speed_col_name = speed_col
            except Exception: pass
        elif gps_speed and gps_speed in df.columns:
            speed_col = gps_speed; speed_data_to_plot = df[speed_col]; speed_col_name = f"{speed_col} (GPS)"

    configurar_estilo_plot(ax, "Análise Aceleração (Placeholder)")
    if df is not None and speed_data_to_plot is not None:
        try:
            ax.plot(df.index, speed_data_to_plot, label=f"{speed_col_name}", color=COLOR_GOLD)
            ax.set_xlabel("Tempo"); ax.set_ylabel("Velocidade (m/s)")
            ax.legend(labelcolor=COLOR_TEXT)
            if isinstance(df.index, pd.DatetimeIndex): plt.setp(ax.get_xticklabels(), rotation=30, ha='right')
            ax.text(0.05, 0.95, "Plot básico.\nAnálise real precisa\ndetectar fase da Aceleração.", transform=ax.transAxes, fontsize=9, verticalalignment='top', color=COLOR_TEXT)
            ax.relim(); ax.autoscale_view()
        except Exception as e: ax.text(0.5, 0.5, f"Erro ao plotar:\n{e}", ha='center', color=COLOR_RED)
    else: ax.text(0.5, 0.5, "Nenhuma coluna de velocidade encontrada.", ha='center', color=COLOR_TEXT)
    try: fig.tight_layout()
    except ValueError: pass
    canvas_widget.draw()

def plotar_histograma_suspensao(df: Optional[pd.DataFrame], canvas_widget: FigureCanvasTkAgg, fig: Figure, ax: plt.Axes, config_map: Dict[str, str]):
    """Desenha histograma de posição da suspensão."""
    susp_internal = ['suspposfl', 'suspposfr', 'suspposrl', 'suspposrr']
    susp_cols_real = []
    if df is not None:
        susp_cols_real = [get_channel_name(config_map, n, df.columns) for n in susp_internal]
        susp_cols_real = [c for c in susp_cols_real if c is not None and c in df.columns]

    configurar_estilo_plot(ax, "Histograma Posição Suspensão")
    if df is not None and susp_cols_real:
        plotted = False
        try:
            for col in susp_cols_real: ax.hist(df[col].dropna(), bins=30, alpha=0.7, label=col); plotted = True
            if plotted: ax.legend(labelcolor=COLOR_TEXT); ax.set_xlabel("Deslocamento (mm)"); ax.set_ylabel("Frequência")
            else: ax.text(0.5, 0.5, "Colunas de suspensão não encontradas", ha='center', color=COLOR_TEXT)
            ax.relim(); ax.autoscale_view()
        except Exception as e: ax.text(0.5, 0.5, f"Erro ao plotar Histograma:\n{e}", ha='center', color=COLOR_RED)
    else: ax.text(0.5, 0.5, "Carregue dados/mapeie colunas", ha='center', color=COLOR_TEXT)
    try: fig.tight_layout()
    except ValueError: pass
    canvas_widget.draw()

def plotar_delta_time(df: Optional[pd.DataFrame], canvas_widget: FigureCanvasTkAgg, fig: Figure, ax: plt.Axes):
    """Desenha gráfico de Delta-Time (Placeholder)."""
    configurar_estilo_plot(ax, "Delta-Time (Não Implementado)")
    # TODO: Implementar cálculo e plotagem de delta-time
    ax.text(0.5, 0.5, "Cálculo e Plotagem de Delta-Time\nAinda Não Implementado", ha='center', va='center', color=COLOR_TEXT)
    try: fig.tight_layout()
    except ValueError: pass
    canvas_widget.draw()