# pip install customtkinter pandas numpy matplotlib pillow

import os
import platform
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from typing import Any, Dict, List, Optional  # Para type hinting

import customtkinter as ctk
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from calculations import (
    calcular_metricas_aceleracao,
    calcular_metricas_gg,
    calcular_metricas_skidpad,
    calcular_tempos_volta,
)

# Importa funções dos outros módulos
from config_manager import CONFIG_FILE, get_channel_name, load_config
from data_loader import carregar_log_csv
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

# --- Configurações Globais de Aparência (Exceto Fontes) ---
ctk.set_appearance_mode("dark")  # Define o tema escuro
# Paleta de cores refinada
COLOR_BG_PRIMARY = "#242424"  # Fundo principal um pouco mais escuro
COLOR_BG_SECONDARY = "#1F1F1F"  # Fundo secundário (sidebar, tabs)
COLOR_BG_TERTIARY = "#2B2B2B"  # Fundo para elementos internos (scrollframe, plot)
COLOR_ACCENT_RED = "#D32F2F"  # Vermelho um pouco menos saturado
COLOR_ACCENT_GOLD = "#FBC02D"  # Dourado/Amarelo para destaque secundário
COLOR_TEXT_PRIMARY = "#F5F5F5"  # Texto principal (quase branco)
COLOR_TEXT_SECONDARY = "#BDBDBD"  # Texto secundário (cinza claro)
COLOR_BORDER = "#424242"  # Cor para bordas sutis

# Estilo Matplotlib (Pode ser definido globalmente)
plt.style.use("dark_background")
plt.rc(
    "axes",
    facecolor=COLOR_BG_TERTIARY,
    edgecolor=COLOR_BORDER,
    labelcolor=COLOR_TEXT_SECONDARY,
    titlecolor=COLOR_TEXT_PRIMARY,
)
plt.rc("figure", facecolor=COLOR_BG_SECONDARY)
plt.rc("xtick", color=COLOR_TEXT_SECONDARY)
plt.rc("ytick", color=COLOR_TEXT_SECONDARY)
plt.rc("grid", color=COLOR_BORDER, linestyle="--", alpha=0.7)
plt.rc("text", color=COLOR_TEXT_PRIMARY)
plt.rc(
    "legend",
    facecolor=COLOR_BG_SECONDARY,
    edgecolor=COLOR_BORDER,
    labelcolor=COLOR_TEXT_PRIMARY,
)


frequency = 50  # Hz - Frequência padrão (usada se timestamp falhar)


# ==============================================================================
# Classe Principal da Aplicação
# ==============================================================================
class AppAnalisePUCPR(ctk.CTk):
    """Classe principal da aplicação de análise de dados PUCPR Racing."""

    def __init__(self):
        """Inicializa a janela principal e seus componentes."""
        super().__init__()  # Cria a janela raiz primeiro!

        # --- Definição das Fontes---
        self.DEFAULT_FONT_FAMILY = (
            "Segoe UI" if platform.system() == "Windows" else "Roboto"
        )  # Tenta usar fontes comuns
        try:
            # Fontes são atributos da instância (self.)
            self.DEFAULT_FONT = ctk.CTkFont(family=self.DEFAULT_FONT_FAMILY, size=12)
            self.DEFAULT_FONT_BOLD = ctk.CTkFont(
                family=self.DEFAULT_FONT_FAMILY, size=12, weight="bold"
            )
            self.SMALL_FONT = ctk.CTkFont(family=self.DEFAULT_FONT_FAMILY, size=10)
            self.LARGE_FONT_BOLD = ctk.CTkFont(
                family=self.DEFAULT_FONT_FAMILY, size=14, weight="bold"
            )
            self.MENU_FONT = ctk.CTkFont(
                family=self.DEFAULT_FONT_FAMILY, size=10
            )  # Fonte específica para menu
        except Exception as e:  # Fallback se a fonte não for encontrada
            print(
                f"Aviso: Fonte '{self.DEFAULT_FONT_FAMILY}' não encontrada, usando fallback. Erro: {e}"
            )
            # Fallback também usa self.
            self.DEFAULT_FONT_FAMILY = tk.font.nametofont("TkDefaultFont").actual()[
                "family"
            ]  # Pega a fonte padrão do sistema
            self.DEFAULT_FONT = ctk.CTkFont(size=12)
            self.DEFAULT_FONT_BOLD = ctk.CTkFont(size=12, weight="bold")
            self.SMALL_FONT = ctk.CTkFont(size=10)
            self.LARGE_FONT_BOLD = ctk.CTkFont(size=14, weight="bold")
            self.MENU_FONT = ctk.CTkFont(size=10)  # Fallback para menu
        # --- Fim da Definição das Fontes ---

        self.title("PUCPR Racing Ferramenta de Análise v1.0")  # Versão
        self.geometry("1300x800")  # Tamanho inicial da janela
        self.configure(fg_color=COLOR_BG_PRIMARY)  # Cor de fundo da janela
        # Define o tamanho mínimo da janela para evitar problemas de layout
        self.minsize(900, 650)  # Aumentado ligeiramente

        # Carrega config ao iniciar
        self.channel_mapping: Dict[str, str]
        self.track_config: Dict[str, str]
        self.analysis_config: Dict[str, str]
        # Tenta carregar a configuração, tratando possíveis erros
        try:
            self.channel_mapping, self.track_config, self.analysis_config = (
                load_config()
            )
        except FileNotFoundError:
            messagebox.showerror(
                "Erro de Configuração",
                f"Arquivo '{CONFIG_FILE}' não encontrado. Verifique se ele existe no mesmo diretório ou crie um.",
            )
            # Define dicionários vazios para evitar erros posteriores
            self.channel_mapping, self.track_config, self.analysis_config = {}, {}, {}
        except Exception as e:
            messagebox.showerror(
                "Erro de Configuração", f"Erro ao ler '{CONFIG_FILE}':\n{e}"
            )
            # Define dicionários vazios para evitar erros posteriores
            self.channel_mapping, self.track_config, self.analysis_config = {}, {}, {}

        # Variáveis de estado
        self.data_frame: Optional[pd.DataFrame] = None  # DataFrame com os dados do log
        self.current_filepath: str = ""  # Caminho do arquivo carregado
        self.lap_numbers_series: Optional[pd.Series] = None  # Guarda voltas calculadas

        # --- Barra de Menu ---
        self._criar_menu()

        # --- Layout Principal (Grid) ---
        # Configura a expansão das colunas e linhas da janela principal
        self.grid_columnconfigure(
            1, weight=1
        )  # Coluna 1 (direita, tabs) expande horizontalmente
        self.grid_rowconfigure(0, weight=1)  # Linha 0 (principal) expande verticalmente
        self.grid_rowconfigure(
            1, weight=0
        )  # Linha 1 (status bar) não expande verticalmente

        # --- Painel de Controle Lateral (Esquerda) ---
        self._criar_painel_controle()  # Cria o frame da sidebar

        # --- Área Principal com Tabs (Direita) ---
        self._criar_area_tabs()  # Cria a área com abas

        # --- Barra de Status ---
        self._criar_status_bar()  # Cria a barra inferior

        # Atualiza estado inicial dos botões (desabilitados até carregar log)
        self.habilitar_botoes_pos_carga(False)

    def _criar_menu(self):
        """Cria a barra de menus da aplicação."""
        self.menu_bar = tk.Menu(self)  # Usa tk.Menu para compatibilidade
        self.configure(menu=self.menu_bar)  # Associa o menu à janela principal

        # Define estilo do menu
        # Usa self.MENU_FONT definido no __init__
        menu_bg = COLOR_BG_SECONDARY
        menu_fg = COLOR_TEXT_PRIMARY
        menu_active_bg = COLOR_ACCENT_RED
        menu_active_fg = COLOR_TEXT_PRIMARY

        # Menu Arquivo
        self.file_menu = tk.Menu(
            self.menu_bar,
            tearoff=0,
            background=menu_bg,
            foreground=menu_fg,
            activebackground=menu_active_bg,
            activeforeground=menu_active_fg,
            font=self.MENU_FONT,
            borderwidth=0,
        )  # Usa self.MENU_FONT
        self.menu_bar.add_cascade(
            label="Arquivo", menu=self.file_menu
        )  # Adiciona o menu "Arquivo"
        self.file_menu.add_command(
            label="Abrir Log (.csv)...", command=self.abrir_arquivo_log
        )  # Opção para abrir log
        self.file_menu.add_command(
            label="Exportar Log Atual (.csv)...",
            command=self.exportar_dados_csv,
            state="disabled",
        )  # Opção para exportar (começa desabilitada)
        self.file_menu.add_separator()  # Linha separadora
        self.file_menu.add_command(
            label=f"Ver/Editar Configuração ({CONFIG_FILE})...",
            command=self.editar_arquivo_config,
        )  # Opção para editar config
        self.file_menu.add_separator()  # Linha separadora
        self.file_menu.add_command(label="Sair", command=self.quit)  # Opção para sair

        # Menu Ajuda
        self.help_menu = tk.Menu(
            self.menu_bar,
            tearoff=0,
            background=menu_bg,
            foreground=menu_fg,
            activebackground=menu_active_bg,
            activeforeground=menu_active_fg,
            font=self.MENU_FONT,
            borderwidth=0,
        )  # Usa self.MENU_FONT
        self.menu_bar.add_cascade(
            label="Ajuda", menu=self.help_menu
        )  # Adiciona o menu "Ajuda"
        self.help_menu.add_command(
            label="Sobre...", command=self.mostrar_sobre
        )  # Opção "Sobre"

    def _criar_painel_controle(self):
        """Cria o painel lateral (sidebar) com controles."""
        # Cria o frame da sidebar
        self.painel_controle = ctk.CTkFrame(
            self, width=300, corner_radius=10, fg_color=COLOR_BG_SECONDARY
        )
        # Posiciona o frame na grade da janela principal (linha 0, coluna 0)
        self.painel_controle.grid(
            row=0, column=0, padx=(10, 5), pady=10, sticky="nsew"
        )  # Diminui padx direito
        self.painel_controle.grid_propagate(
            False
        )  # Impede que o frame ajuste seu tamanho aos widgets internos

        # Botão Abrir Log (com ícone Unicode)
        self.btn_abrir_log = ctk.CTkButton(
            self.painel_controle,
            text="📁 Abrir Log (.csv)",
            command=self.abrir_arquivo_log,
            fg_color=COLOR_ACCENT_RED,
            hover_color="#A00000",
            text_color=COLOR_TEXT_PRIMARY,
            font=self.DEFAULT_FONT_BOLD,
        )  # Usa self.
        self.btn_abrir_log.pack(
            pady=(15, 10), padx=15, fill="x"
        )  # Aumenta padx interno

        # Label para nome do arquivo
        self.lbl_nome_arquivo = ctk.CTkLabel(
            self.painel_controle,
            text="Nenhum log carregado",
            text_color=COLOR_TEXT_SECONDARY,
            wraplength=270,
            anchor="w",
            justify="left",
            font=self.SMALL_FONT,
        )  # Usa self.
        self.lbl_nome_arquivo.pack(pady=5, padx=15, fill="x")

        # Separador visual
        ctk.CTkFrame(self.painel_controle, height=1, fg_color=COLOR_BORDER).pack(
            pady=15, padx=15, fill="x"
        )  # Mais sutil

        # Frame para lista de canais e botões Marcar/Desmarcar
        frame_lista_canais = ctk.CTkFrame(self.painel_controle, fg_color="transparent")
        frame_lista_canais.pack(
            pady=5, padx=15, fill="both", expand=True
        )  # Aumenta padx interno

        # Label "Canais Disponíveis"
        lbl_lista_canais = ctk.CTkLabel(
            frame_lista_canais,
            text="Canais Disponíveis",
            text_color=COLOR_ACCENT_GOLD,
            anchor="w",
            font=self.DEFAULT_FONT_BOLD,
        )  # Usa self.
        lbl_lista_canais.pack(fill="x", pady=(0, 5))

        # Frame para os botões Marcar/Desmarcar Todos
        frame_botoes_selecao = ctk.CTkFrame(frame_lista_canais, fg_color="transparent")
        frame_botoes_selecao.pack(fill="x", pady=(2, 8))
        self.btn_marcar_todos = ctk.CTkButton(
            frame_botoes_selecao,
            text="✔️ Marcar",
            command=self.marcar_todos_canais,
            fg_color=COLOR_ACCENT_GOLD,
            text_color="#000000",
            height=24,
            font=self.SMALL_FONT,
            state="disabled",
            width=100,
        )  # Usa self.
        self.btn_marcar_todos.pack(side=tk.LEFT, padx=(0, 5))
        self.btn_desmarcar_todos = ctk.CTkButton(
            frame_botoes_selecao,
            text="❌ Desmarcar",
            command=self.desmarcar_todos_canais,
            fg_color=COLOR_ACCENT_GOLD,
            text_color="#000000",
            height=24,
            font=self.SMALL_FONT,
            state="disabled",
            width=100,
        )  # Usa self.
        self.btn_desmarcar_todos.pack(side=tk.LEFT, padx=(5, 0))

        # Frame rolável para as checkboxes dos canais
        self.frame_scroll_canais = ctk.CTkScrollableFrame(
            frame_lista_canais,
            fg_color=COLOR_BG_TERTIARY,
            border_width=1,
            border_color=COLOR_BORDER,
            corner_radius=5,
        )
        self.frame_scroll_canais.pack(fill="both", expand=True)
        self.checkboxes_canais: Dict[str, tk.StringVar] = (
            {}
        )  # Dicionário para guardar as checkboxes e suas variáveis

    def _criar_area_tabs(self):
        """Cria a área principal com as abas de análise."""
        # Cria o widget de abas (TabView)
        self.tabs_view = ctk.CTkTabview(
            self,
            corner_radius=10,
            fg_color=COLOR_BG_SECONDARY,
            border_width=1,
            border_color=COLOR_BORDER,
            segmented_button_selected_color=COLOR_ACCENT_RED,
            segmented_button_selected_hover_color="#A00000",
            segmented_button_unselected_color=COLOR_BG_SECONDARY,
            text_color=COLOR_TEXT_PRIMARY,
            segmented_button_fg_color=COLOR_BG_SECONDARY,
        )
        # Posiciona o TabView na grade da janela principal (linha 0, coluna 1)
        self.tabs_view.grid(
            row=0, column=1, padx=(5, 10), pady=10, sticky="nsew"
        )  # Diminui padx esquerdo
        # Adiciona as abas
        self.tabs_view.add("📊 Geral / Plotagem")
        self.tabs_view.add("↔️ Skid Pad")
        self.tabs_view.add("🏁 Aceleração")
        self.tabs_view.add("🏎️ Autocross / Endurance")  # Adiciona ícones

        # --- Conteúdo da Tab "Geral / Plotagem" ---
        tab_geral = self.tabs_view.tab(
            "📊 Geral / Plotagem"
        )  # Obtém a referência da aba
        # Configura a expansão da linha e coluna interna da aba
        tab_geral.grid_columnconfigure(0, weight=1)
        tab_geral.grid_rowconfigure(1, weight=1)

        # Frame para os botões de controle dentro da aba Geral
        frame_controles_geral = ctk.CTkFrame(tab_geral, fg_color="transparent")
        frame_controles_geral.grid(
            row=0, column=0, padx=10, pady=(10, 5), sticky="ew"
        )  # Aumenta pady superior

        # Botões de plotagem (com ícones)
        self.btn_plotar_selecionados = ctk.CTkButton(
            frame_controles_geral,
            text="📈 Plotar Selecionados",
            command=self.plotar_dados_selecionados_gui,
            fg_color=COLOR_ACCENT_RED,
            hover_color="#A00000",
            text_color=COLOR_TEXT_PRIMARY,
            font=self.DEFAULT_FONT,
        )  # Usa self.
        self.btn_plotar_selecionados.pack(side=tk.LEFT, padx=(0, 10))
        self.btn_plotar_gg = ctk.CTkButton(
            frame_controles_geral,
            text="🎯 Plotar G-G",
            command=self.plotar_gg_diagrama_gui,
            fg_color=COLOR_ACCENT_RED,
            hover_color="#A00000",
            text_color=COLOR_TEXT_PRIMARY,
            font=self.DEFAULT_FONT,
        )  # Usa self.
        self.btn_plotar_gg.pack(side=tk.LEFT, padx=(0, 10))
        self.btn_plotar_mapa = ctk.CTkButton(
            frame_controles_geral,
            text="🗺️ Plotar Mapa",
            command=self.plotar_mapa_pista_gui,
            fg_color=COLOR_ACCENT_RED,
            hover_color="#A00000",
            text_color=COLOR_TEXT_PRIMARY,
            font=self.DEFAULT_FONT,
        )  # Usa self.
        self.btn_plotar_mapa.pack(side=tk.LEFT, padx=(0, 10))

        # Combobox para selecionar canal de cor do mapa
        ctk.CTkLabel(
            frame_controles_geral,
            text="Cor Mapa:",
            font=self.SMALL_FONT,
            text_color=COLOR_TEXT_SECONDARY,
        ).pack(
            side=tk.LEFT, padx=(10, 5)
        )  # Usa self.
        self.var_cor_mapa = ctk.StringVar(value="(Nenhuma Cor)")
        self.combo_cor_mapa = ctk.CTkComboBox(
            frame_controles_geral,
            variable=self.var_cor_mapa,
            values=["(Nenhuma Cor)"],
            state="disabled",
            width=180,
            font=self.DEFAULT_FONT,
            text_color=COLOR_TEXT_PRIMARY,
            fg_color=COLOR_BG_TERTIARY,
            button_color=COLOR_ACCENT_GOLD,  # Usa self.
            dropdown_fg_color=COLOR_BG_SECONDARY,
            dropdown_hover_color=COLOR_BG_PRIMARY,
            border_color=COLOR_BORDER,
            corner_radius=5,
        )
        self.combo_cor_mapa.pack(side=tk.LEFT, padx=(0, 10))

        # Frame para a área do gráfico Matplotlib
        self.frame_area_plot = ctk.CTkFrame(
            tab_geral, fg_color=COLOR_BG_TERTIARY, corner_radius=5
        )  # Cor de fundo e borda
        self.frame_area_plot.grid(
            row=1, column=0, padx=10, pady=(5, 10), sticky="nswe"
        )  # Aumenta pady inferior

        # Cria a figura e o canvas do Matplotlib
        self.figura_plot = Figure(
            figsize=(5, 4), dpi=100, facecolor=COLOR_BG_TERTIARY
        )  # Usa cor do frame
        self.eixo_plot = self.figura_plot.add_subplot(111)  # Adiciona eixos ao gráfico
        self.canvas_plot = FigureCanvasTkAgg(
            self.figura_plot, master=self.frame_area_plot
        )  # Cria o canvas Tkinter
        self.widget_canvas = (
            self.canvas_plot.get_tk_widget()
        )  # Obtém o widget Tkinter do canvas
        self.widget_canvas.configure(bg=COLOR_BG_TERTIARY)  # Garante bg do widget tk
        # Posiciona o canvas dentro do frame_area_plot usando pack
        self.widget_canvas.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True, padx=1, pady=1
        )  # Padding mínimo interno

        # Cria a barra de ferramentas do Matplotlib
        self.toolbar_plot = NavigationToolbar2Tk(
            self.canvas_plot, self.frame_area_plot, pack_toolbar=False
        )  # pack_toolbar=False importante!
        self.toolbar_plot.configure(
            background=COLOR_BG_TERTIARY
        )  # Configura cor de fundo da toolbar

        # Estiliza apenas os botões e checkboxes da toolbar
        for widget in self.toolbar_plot.winfo_children():
            if isinstance(
                widget, (tk.Button, tk.Checkbutton)
            ):  # Verifica se é botão ou checkbox
                try:
                    # Aplica configuração de cores e estilo
                    widget.configure(
                        background=COLOR_BG_TERTIARY,
                        foreground=COLOR_TEXT_SECONDARY,
                        relief=tk.FLAT,
                        borderwidth=0,
                    )
                except tk.TclError as e:
                    # Ignora erro se alguma opção específica não for suportada (menos provável agora)
                    print(
                        f"Aviso: Não foi possível configurar completamente o widget da toolbar: {e}"
                    )

        # Posiciona a toolbar usando pack
        self.toolbar_plot.pack(side=tk.BOTTOM, fill=tk.X, padx=1, pady=(0, 1))
        # Atualiza o plot inicial com uma mensagem
        self.atualizar_area_plot(title="Carregue um arquivo de log")

        # --- Conteúdo das Outras Tabs ---
        # Lista para guardar referências aos botões das abas específicas
        self.botoes_analise_especifica: List[ctk.CTkButton] = []
        # Chama a função para configurar cada aba específica
        self.configurar_aba_especifica(
            "↔️ Skid Pad",
            [
                ("⚙️ Calcular Métricas", self.analisar_skidpad),
                ("📊 Plot Análise", self.plotar_skidpad),
            ],
        )
        self.configurar_aba_especifica(
            "🏁 Aceleração",
            [
                ("⚙️ Calcular Métricas", self.analisar_aceleracao),
                ("📊 Plot Análise", self.plotar_aceleracao),
            ],
        )
        self.configurar_aba_especifica(
            "🏎️ Autocross / Endurance",
            [
                ("⏱️ Calcular Voltas", self.analisar_tempos_volta),
                ("📈 Plot Hist. Susp.", self.plotar_histograma_suspensao),
                ("📉 Plot Delta-Time", self.plotar_delta_time_gui),
            ],
        )

    def _criar_status_bar(self):
        """Cria a barra de status na parte inferior."""
        self.status_bar = ctk.CTkLabel(
            self,
            text="Pronto.",
            anchor="w",
            justify="left",
            fg_color=COLOR_BG_SECONDARY,
            text_color=COLOR_TEXT_SECONDARY,
            height=24,
            font=self.SMALL_FONT,
        )  # Usa self.
        # Posiciona a barra de status na grade da janela principal (linha 1, ocupando 2 colunas)
        self.status_bar.grid(
            row=1, column=0, columnspan=2, padx=0, pady=0, sticky="ew"
        )  # Sem padx/pady externos

    def atualizar_status(self, mensagem: str):
        """Atualiza o texto na barra de status."""
        self.status_bar.configure(
            text=f"  {mensagem}"
        )  # Adiciona um pequeno espaço inicial
        self.update_idletasks()  # Força atualização da GUI para mostrar a mensagem imediatamente

    def configurar_aba_especifica(
        self, nome_tab: str, acoes_botoes: List[tuple[str, callable]]
    ):
        """Configura o conteúdo básico de uma aba de análise específica (Skidpad, Aceleração, etc.)."""
        tab = self.tabs_view.tab(nome_tab)  # Obtém a referência da aba pelo nome
        tab.grid_columnconfigure(
            0, weight=1
        )  # Configura a coluna interna para expandir

        # Frame para título e descrição da aba
        frame_titulo = ctk.CTkFrame(tab, fg_color="transparent")
        frame_titulo.grid(
            row=0, column=0, padx=20, pady=(15, 5), sticky="ew"
        )  # Aumenta pady
        # Extrai o ícone e o texto do nome da aba
        icon = nome_tab.split(" ")[0]
        text_titulo = " ".join(nome_tab.split(" ")[1:])
        lbl_titulo = ctk.CTkLabel(
            frame_titulo,
            text=f"{icon} Análises Específicas - {text_titulo}",
            font=self.LARGE_FONT_BOLD,
            text_color=COLOR_ACCENT_GOLD,
        )  # Usa self.
        lbl_titulo.pack(side=tk.LEFT)
        # Adiciona descrição específica para Skid Pad
        if "Skid Pad" in nome_tab:
            lbl_desc = ctk.CTkLabel(
                frame_titulo,
                text="(Prova em '8' para medir G lateral máx.)",
                font=self.SMALL_FONT,
                text_color=COLOR_TEXT_SECONDARY,
            )  # Usa self.
            lbl_desc.pack(side=tk.LEFT, padx=10)

        # Frame para os botões de ação da aba
        frame_botoes = ctk.CTkFrame(tab, fg_color="transparent")
        frame_botoes.grid(row=1, column=0, padx=20, pady=10, sticky="ew")

        # Frame e Textbox para exibir resultados textuais da análise
        frame_resultados = ctk.CTkFrame(
            tab,
            fg_color=COLOR_BG_TERTIARY,
            corner_radius=5,
            border_width=1,
            border_color=COLOR_BORDER,
        )  # Adiciona borda
        frame_resultados.grid(
            row=2, column=0, padx=20, pady=(5, 15), sticky="nsew"
        )  # Aumenta pady
        tab.grid_rowconfigure(
            2, weight=1
        )  # Faz o frame de resultados expandir verticalmente

        # Cria o Textbox para os resultados
        textbox_resultados = ctk.CTkTextbox(
            frame_resultados,
            wrap="word",
            activate_scrollbars=True,
            text_color=COLOR_TEXT_PRIMARY,
            fg_color=COLOR_BG_TERTIARY,
            border_width=0,  # Borda já está no frame
            font=ctk.CTkFont(family=self.DEFAULT_FONT_FAMILY, size=11),
        )  # Usa self.DEFAULT_FONT_FAMILY
        textbox_resultados.pack(
            padx=10, pady=10, fill="both", expand=True
        )  # Padding interno
        textbox_resultados.insert("1.0", f"Resultados - {text_titulo}")  # Texto inicial
        textbox_resultados.configure(
            state="disabled"
        )  # Começa desabilitado para edição
        # Guarda referência ao textbox usando um nome dinâmico baseado no nome da aba (sem ícone)
        chave_widget = (
            f"textbox_resultados_{text_titulo.replace(' / ', '_').replace(' ', '_')}"
        )
        setattr(self, chave_widget, textbox_resultados)

        # Cria os botões de ação definidos para esta aba
        for i, (texto, comando) in enumerate(acoes_botoes):
            btn = ctk.CTkButton(
                frame_botoes,
                text=texto,
                fg_color=COLOR_ACCENT_RED,
                hover_color="#A00000",
                command=comando,
                state="disabled",
                font=self.DEFAULT_FONT,
            )  # Usa self.
            btn.grid(row=0, column=i, padx=5, pady=5)  # Posiciona os botões lado a lado
            self.botoes_analise_especifica.append(
                btn
            )  # Adiciona à lista para controle de estado global

    # --- Funções de Callback e Lógica Principal ---
    def abrir_arquivo_log(self):
        """Abre diálogo para selecionar arquivo de log (.csv) e o carrega."""
        self.atualizar_status("Abrindo seletor de arquivo...")
        filepath = filedialog.askopenfilename(
            title="Selecionar Arquivo de Log (.csv)",
            filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*")),
        )
        if filepath:
            self.atualizar_status(f"Carregando log: {os.path.basename(filepath)}...")
            # Chama a função de carregamento do data_loader, passando o mapeamento de canais
            self.data_frame = carregar_log_csv(filepath, self.channel_mapping)
            if self.data_frame is not None:
                self.current_filepath = filepath
                filename = os.path.basename(filepath)
                # Atualiza label com nome do arquivo (mostra apenas o final se for muito longo)
                self.lbl_nome_arquivo.configure(
                    text=(
                        f"Log: ...{filename[-35:]}"
                        if len(filename) > 35
                        else f"Log: {filename}"
                    )
                )

                # Limpa estado anterior (número de voltas)
                if "LapNumber" in self.data_frame.columns:
                    self.data_frame = self.data_frame.drop(columns=["LapNumber"])
                self.lap_numbers_series = None

                # Atualiza a interface gráfica
                self.atualizar_lista_canais()  # Popula a lista de checkboxes
                self.atualizar_area_plot(
                    title="Log carregado. Selecione canais para plotar."
                )  # Limpa plot
                self.habilitar_botoes_pos_carga(True)  # Habilita botões de análise
                self.limpar_labels_resultados()  # Limpa textboxes de resultados anteriores
                self.atualizar_status(
                    f"Log '{filename}' carregado com sucesso ({len(self.data_frame)} linhas)."
                )
            else:  # Falha no carregamento (carregar_log_csv retornou None)
                self.current_filepath = ""
                self.lbl_nome_arquivo.configure(text="Falha ao carregar log.")
                self.data_frame = None
                self.lap_numbers_series = None
                self.atualizar_lista_canais()
                self.atualizar_area_plot(title="Falha ao carregar log.")
                self.habilitar_botoes_pos_carga(False)
                self.limpar_labels_resultados()
                # Mensagem de erro já deve ter sido mostrada por carregar_log_csv
                self.atualizar_status("Falha ao carregar o arquivo de log.")
        else:
            self.atualizar_status("Seleção de arquivo cancelada.")

    def limpar_labels_resultados(self):
        """Limpa o texto de todos os textboxes de resultado nas abas específicas."""
        # Usa os nomes das abas como configurados (com ícones)
        for nome_tab_completo in [
            "↔️ Skid Pad",
            "🏁 Aceleração",
            "🏎️ Autocross / Endurance",
        ]:
            # Extrai o nome base para a chave do widget
            nome_base = " ".join(nome_tab_completo.split(" ")[1:])
            chave_widget = (
                f"textbox_resultados_{nome_base.replace(' / ', '_').replace(' ', '_')}"
            )
            if hasattr(self, chave_widget):
                try:
                    textbox = getattr(self, chave_widget)
                    textbox.configure(state="normal")  # Habilita para edição
                    textbox.delete("1.0", tk.END)  # Apaga todo o conteúdo
                    textbox.insert(
                        "1.0", f"Resultados - {nome_base}"
                    )  # Insere texto padrão
                    textbox.configure(state="disabled")  # Desabilita novamente
                except Exception as e:
                    print(
                        f"Erro ao limpar textbox para {nome_base}: {e}"
                    )  # Loga erro no console

    def atualizar_lista_canais(self):
        """Atualiza a lista de checkboxes de canais no painel de controle."""
        # Limpa checkboxes antigas
        for widget in self.frame_scroll_canais.winfo_children():
            widget.destroy()
        self.checkboxes_canais = {}
        nomes_canais_combo = [
            "(Nenhuma Cor)"
        ]  # Opção padrão para combobox de cor do mapa

        if self.data_frame is not None:
            colunas_ordenadas = sorted(self.data_frame.columns.tolist())
            for nome_canal in colunas_ordenadas:
                # Adiciona ao combobox de cor (exceto LapNumber)
                if nome_canal != "LapNumber":
                    nomes_canais_combo.append(nome_canal)
                # Cria a checkbox para o canal
                var_checkbox = tk.StringVar(
                    value="off"
                )  # Usa tk.StringVar compatível com ctk.CTkCheckBox
                cb = ctk.CTkCheckBox(
                    self.frame_scroll_canais,
                    text=nome_canal,
                    variable=var_checkbox,
                    onvalue=nome_canal,
                    offvalue="off",
                    text_color=COLOR_TEXT_PRIMARY,  # Cor primária para texto do canal
                    fg_color=COLOR_ACCENT_RED,
                    hover_color=COLOR_ACCENT_GOLD,
                    font=self.SMALL_FONT,  # Usa self.
                    command=self.checkbox_alterada,
                )  # Chama função ao alterar estado
                cb.pack(
                    anchor="w", padx=5, pady=2
                )  # Adiciona checkbox ao frame rolável com pady=2
                self.checkboxes_canais[nome_canal] = var_checkbox  # Guarda referência

        # Atualiza o combobox de cor do mapa
        self.combo_cor_mapa.configure(values=nomes_canais_combo)
        # Mantém a seleção atual se ainda for válida
        selecao_cor_atual = self.var_cor_mapa.get()
        if selecao_cor_atual not in nomes_canais_combo:
            self.combo_cor_mapa.set("(Nenhuma Cor)")
        # Habilita/desabilita combobox
        estado_combo = "readonly" if len(nomes_canais_combo) > 1 else "disabled"
        self.combo_cor_mapa.configure(state=estado_combo)
        # Habilita/desabilita botões Marcar/Desmarcar Todos
        estado_botoes_selecao = "normal" if self.checkboxes_canais else "disabled"
        self.btn_marcar_todos.configure(state=estado_botoes_selecao)
        self.btn_desmarcar_todos.configure(state=estado_botoes_selecao)

    def checkbox_alterada(self):
        """Chamada quando uma checkbox de canal é marcada/desmarcada."""
        # Atualiza o gráfico principal para refletir a nova seleção
        self.plotar_dados_selecionados_gui()

    def obter_canais_selecionados(self) -> List[str]:
        """Retorna uma lista com os nomes dos canais selecionados."""
        return [
            nome for nome, var in self.checkboxes_canais.items() if var.get() == nome
        ]

    def atualizar_texto_resultado(self, chave_tab_base: str, texto: str):
        """Atualiza o textbox de resultados de uma aba específica."""
        # Chave sem ícone e espaços
        chave_widget = (
            f"textbox_resultados_{chave_tab_base.replace(' / ', '_').replace(' ', '_')}"
        )
        if hasattr(self, chave_widget):
            try:
                textbox = getattr(self, chave_widget)
                textbox.configure(state="normal")  # Habilita para edição
                textbox.delete("1.0", tk.END)  # Limpa conteúdo antigo
                # Insere o novo texto formatado
                textbox.insert(
                    "1.0",
                    f"Resultados - {chave_tab_base.replace('_', ' ')}\n{'-'*30}\n{texto}",
                )  # Adiciona separador
                textbox.configure(state="disabled")  # Desabilita novamente
            except Exception as e:
                print(f"Erro ao atualizar textbox {chave_widget}: {e}")  # Loga erro
        else:
            print(f"Erro: Textbox para {chave_tab_base} não encontrado.")  # Loga erro

    def atualizar_area_plot(self, title: str = "Gráfico"):
        """Limpa e prepara a área de plotagem principal com um título."""
        # Define título padrão se nenhum log estiver carregado
        if self.data_frame is None and "Carregue" not in title:
            title = "Nenhum log carregado"
        # Configura estilo e título dos eixos (usando função de plotting)
        configurar_estilo_plot(
            self.eixo_plot, title
        )  # Assume que essa função usa as cores/fontes certas
        # Redesenha o canvas para mostrar as alterações
        self.canvas_plot.draw()

    # --- Callbacks Aba Geral ---
    def plotar_dados_selecionados_gui(self):
        """Plota os canais selecionados na área principal."""
        if self.data_frame is None:
            return  # Não faz nada se não houver dados
        selecionados = self.obter_canais_selecionados()
        if not selecionados:  # Se nada selecionado, limpa o plot
            self.atualizar_area_plot(title="Selecione canais para plotar")
            self.atualizar_status("Nenhum canal selecionado.")
            return
        self.atualizar_status(f"Plotando {len(selecionados)} canais selecionados...")
        # Chama a função de plotagem do módulo plotting
        plotar_dados_no_canvas(
            self.data_frame,
            selecionados,
            self.canvas_plot,
            self.figura_plot,
            self.eixo_plot,
        )
        self.atualizar_status("Pronto.")

    def plotar_gg_diagrama_gui(self):
        """Plota o diagrama G-G."""
        if self.data_frame is None:
            return messagebox.showwarning("Aviso", "Carregue um log primeiro.")
        self.atualizar_status("Calculando e plotando G-G...")
        # Calcula métricas G-G usando a função do módulo calculations
        gg_data, lat_col, lon_col, error = calcular_metricas_gg(
            self.data_frame, self.channel_mapping
        )
        if error:
            self.atualizar_status(f"Erro G-G: {error}")
            return messagebox.showerror("Erro G-G", error)
        # Plota o diagrama usando a função do módulo plotting
        plotar_gg_diagrama_nos_eixos(
            gg_data,
            self.canvas_plot,
            self.figura_plot,
            self.eixo_plot,
            lat_col,
            lon_col,
        )
        self.atualizar_status("Diagrama G-G plotado.")

    def plotar_mapa_pista_gui(self):
        """Plota o mapa da pista usando coordenadas GPS."""
        if self.data_frame is None:
            return messagebox.showwarning("Aviso", "Carregue um log primeiro.")
        self.atualizar_status("Plotando mapa da pista...")
        # Obtém nomes das colunas GPS do mapeamento
        lat_col = get_channel_name(
            self.channel_mapping, "gpslat", self.data_frame.columns
        )
        lon_col = get_channel_name(
            self.channel_mapping, "gpslon", self.data_frame.columns
        )
        if not lat_col or not lon_col:
            self.atualizar_status("Erro: Colunas GPS não encontradas/mapeadas.")
            return messagebox.showerror(
                "Erro",
                "Colunas GPS (latitude/longitude) não encontradas ou não mapeadas no arquivo de configuração.",
            )

        # Verifica qual canal usar para colorir o mapa
        canal_cor_selecionado = self.var_cor_mapa.get()
        canal_cor_usar = None
        if canal_cor_selecionado != "(Nenhuma Cor)":
            if canal_cor_selecionado in self.data_frame.columns:
                canal_cor_usar = canal_cor_selecionado
            else:
                messagebox.showwarning(
                    "Aviso",
                    f"Canal de cor '{canal_cor_selecionado}' não encontrado nos dados.",
                )

        # Plota o mapa usando a função do módulo plotting
        plotar_mapa_pista_nos_eixos(
            self.data_frame,
            self.canvas_plot,
            self.figura_plot,
            self.eixo_plot,
            lat_col,
            lon_col,
            canal_cor_usar,
        )
        self.atualizar_status("Mapa da pista plotado.")

    # --- Callbacks Abas Específicas ---
    def analisar_skidpad(self):
        """Calcula e exibe métricas da análise Skid Pad."""
        if self.data_frame is None:
            return messagebox.showwarning("Aviso", "Carregue um log primeiro.")
        self.atualizar_status("Calculando métricas Skid Pad...")
        # Chama a função de cálculo
        resultados = calcular_metricas_skidpad(self.data_frame, self.channel_mapping)
        # Atualiza o textbox correspondente
        self.atualizar_texto_resultado("Skid_Pad", resultados)  # Usa chave base
        self.atualizar_status("Métricas Skid Pad calculadas.")

    def plotar_skidpad(self):
        """Plota a análise gráfica do Skid Pad."""
        if self.data_frame is None:
            return messagebox.showwarning("Aviso", "Carregue um log primeiro.")
        self.atualizar_status("Plotando análise Skid Pad...")
        # Chama a função de plotagem
        plotar_analise_skidpad(
            self.data_frame,
            self.canvas_plot,
            self.figura_plot,
            self.eixo_plot,
            self.channel_mapping,
        )
        self.atualizar_status("Análise Skid Pad plotada.")

    def analisar_aceleracao(self):
        """Calcula e exibe métricas da análise de Aceleração."""
        if self.data_frame is None:
            return messagebox.showwarning("Aviso", "Carregue um log primeiro.")
        self.atualizar_status("Calculando métricas Aceleração...")
        # Chama a função de cálculo
        resultados = calcular_metricas_aceleracao(self.data_frame, self.channel_mapping)
        # Atualiza o textbox correspondente
        self.atualizar_texto_resultado("Aceleração", resultados)  # Usa chave base
        self.atualizar_status("Métricas Aceleração calculadas.")

    def plotar_aceleracao(self):
        """Plota a análise gráfica da Aceleração."""
        if self.data_frame is None:
            return messagebox.showwarning("Aviso", "Carregue um log primeiro.")
        self.atualizar_status("Plotando análise Aceleração...")
        # Chama a função de plotagem
        plotar_analise_aceleracao(
            self.data_frame,
            self.canvas_plot,
            self.figura_plot,
            self.eixo_plot,
            self.channel_mapping,
        )
        self.atualizar_status("Análise Aceleração plotada.")

    def analisar_tempos_volta(self):
        """Calcula tempos de volta e atualiza a GUI."""
        if self.data_frame is None:
            return messagebox.showwarning("Aviso", "Carregue um log primeiro.")
        self.atualizar_status("Calculando tempos de volta...")
        # Chama a função de cálculo, passando as configurações relevantes
        lap_numbers, resultados = calcular_tempos_volta(
            self.data_frame,
            self.channel_mapping,
            self.track_config,
            self.analysis_config,
        )
        # Atualiza o textbox correspondente
        self.atualizar_texto_resultado(
            "Autocross_Endurance", resultados
        )  # Usa chave base
        self.lap_numbers_series = (
            lap_numbers  # Guarda a série com os números das voltas
        )

        # Adiciona/Atualiza a coluna 'LapNumber' no DataFrame principal se o cálculo foi bem-sucedido
        if self.lap_numbers_series is not None:
            if "LapNumber" not in self.data_frame.columns:
                self.data_frame.insert(
                    0, "LapNumber", self.lap_numbers_series
                )  # Insere na primeira posição
                self.atualizar_lista_canais()  # Atualiza a lista de canais para incluir LapNumber
            elif not self.data_frame["LapNumber"].equals(
                self.lap_numbers_series
            ):  # Atualiza se mudou
                self.data_frame["LapNumber"] = self.lap_numbers_series
                self.atualizar_lista_canais()  # Atualiza a lista de canais
            self.atualizar_status("Tempos de volta calculados com sucesso.")
        elif (
            "LapNumber" in self.data_frame.columns
        ):  # Remove a coluna se o cálculo falhou e ela existia
            self.data_frame = self.data_frame.drop(columns=["LapNumber"])
            self.atualizar_lista_canais()  # Atualiza a lista de canais
            self.atualizar_status("Falha ao calcular tempos de volta.")
        else:  # Falha no cálculo e coluna não existia
            self.atualizar_status("Falha ao calcular tempos de volta.")

    def plotar_histograma_suspensao(self):
        """Plota o histograma das posições da suspensão."""
        if self.data_frame is None:
            return messagebox.showwarning("Aviso", "Carregue um log primeiro.")
        self.atualizar_status("Plotando histograma de suspensão...")
        # Nomes internos esperados para os canais de suspensão
        susp_internal = ["suspposfl", "suspposfr", "suspposrl", "suspposrr"]
        # Obtém os nomes reais dos canais a partir do mapeamento
        susp_cols_real = [
            get_channel_name(self.channel_mapping, n, self.data_frame.columns)
            for n in susp_internal
        ]
        susp_cols_real = [
            c for c in susp_cols_real if c is not None and c in self.data_frame.columns
        ]  # Filtra nulos e inexistentes
        if not susp_cols_real:
            self.atualizar_status("Erro: Colunas de suspensão não encontradas.")
            return messagebox.showerror(
                "Erro",
                "Nenhuma coluna de posição de suspensão válida encontrada ou mapeada no arquivo de configuração.",
            )
        # Chama a função de plotagem
        plotar_histograma_suspensao(
            self.data_frame,
            self.canvas_plot,
            self.figura_plot,
            self.eixo_plot,
            susp_cols_real,
        )
        self.atualizar_status("Histograma de suspensão plotado.")

    def plotar_delta_time_gui(self):
        """Plota o gráfico Delta-Time (comparação entre voltas)."""
        if self.data_frame is None:
            return messagebox.showwarning("Aviso", "Carregue um log primeiro.")
        # Verifica se as voltas foram calculadas
        if (
            self.lap_numbers_series is None
            or "LapNumber" not in self.data_frame.columns
        ):
            self.atualizar_status("Erro: Calcule as voltas primeiro.")
            return messagebox.showwarning(
                "Aviso", "Calcule as voltas primeiro (e verifique se não houve erro)."
            )
        self.atualizar_status("Plotando Delta-Time...")
        # Chama a função de plotagem
        plotar_delta_time(
            self.data_frame, self.canvas_plot, self.figura_plot, self.eixo_plot
        )  # Passa config implicitamente
        self.atualizar_status("Delta-Time plotado.")

    # --- Funções Selecionar/Desmarcar Todos ---
    def marcar_todos_canais(self):
        """Marca todas as checkboxes de canais."""
        if not self.checkboxes_canais:
            return
        # print("Marcando todos os canais...") # Log para console (removido)
        for nome_canal, var_checkbox in self.checkboxes_canais.items():
            var_checkbox.set(nome_canal)  # Define valor 'on'
        self.checkbox_alterada()  # Atualiza o plot

    def desmarcar_todos_canais(self):
        """Desmarca todas as checkboxes de canais."""
        if not self.checkboxes_canais:
            return
        # print("Desmarcando todos os canais...") # Log para console (removido)
        for nome_canal, var_checkbox in self.checkboxes_canais.items():
            var_checkbox.set("off")  # Define valor 'off'
        self.checkbox_alterada()  # Atualiza o plot (mostrará vazio)

    # --- Funções Auxiliares e Menu ---
    def exportar_dados_csv(self):
        """Exporta o DataFrame atual (log carregado) para um arquivo CSV."""
        if self.data_frame is None:
            return messagebox.showwarning(
                "Aviso", "Nenhum dado de log carregado para exportar."
            )
        self.atualizar_status("Abrindo diálogo para salvar CSV...")
        # Sugere um nome de arquivo padrão
        default_filename = (
            f"processado_{os.path.basename(self.current_filepath or 'dados')}"
        )
        filepath = filedialog.asksaveasfilename(
            title="Salvar Log Processado como CSV",
            defaultextension=".csv",
            filetypes=(("CSV Files", "*.csv"), ("All Files", "*.*")),
            initialfile=default_filename,
        )
        if filepath:
            self.atualizar_status(
                f"Exportando dados para {os.path.basename(filepath)}..."
            )
            try:
                # Verifica se o índice deve ser salvo (útil se for DatetimeIndex)
                save_index = isinstance(self.data_frame.index, pd.DatetimeIndex)
                df_to_export = self.data_frame.copy()
                # Adiciona/Atualiza LapNumber se foi calculado com sucesso
                if (
                    self.lap_numbers_series is not None
                    and "LapNumber" in df_to_export.columns
                ):
                    df_to_export["LapNumber"] = self.lap_numbers_series
                elif self.lap_numbers_series is not None:  # Adiciona se não existia
                    df_to_export.insert(0, "LapNumber", self.lap_numbers_series)

                # Salva o CSV com formato de float específico
                df_to_export.to_csv(
                    filepath,
                    index=save_index,
                    float_format="%.7f",
                    encoding="utf-8-sig",
                )  # utf-8-sig para compatibilidade Excel
                self.atualizar_status(
                    f"Dados exportados com sucesso para {os.path.basename(filepath)}."
                )
                messagebox.showinfo(
                    "Sucesso", f"Dados exportados com sucesso para:\n{filepath}"
                )
            except Exception as e:
                self.atualizar_status("Erro ao exportar CSV.")
                messagebox.showerror(
                    "Erro ao Exportar", f"Não foi possível salvar o arquivo.\nErro: {e}"
                )
        else:
            self.atualizar_status("Exportação cancelada.")

    def habilitar_botoes_pos_carga(self, habilitar: bool = True):
        """Habilita ou desabilita botões que dependem de dados carregados."""
        estado = "normal" if habilitar else "disabled"
        # Botões gerais na aba principal
        self.btn_plotar_selecionados.configure(state=estado)
        self.btn_plotar_gg.configure(state=estado)
        self.btn_plotar_mapa.configure(state=estado)
        # Botões Marcar/Desmarcar na sidebar
        self.btn_marcar_todos.configure(state=estado)
        self.btn_desmarcar_todos.configure(state=estado)
        # Botões das abas específicas
        if hasattr(self, "botoes_analise_especifica"):
            for btn in self.botoes_analise_especifica:
                btn.configure(state=estado)
        # Combobox do mapa (habilita se houver canais)
        estado_combo = (
            "readonly"
            if habilitar
            and self.data_frame is not None
            and len(self.data_frame.columns) > 0
            else "disabled"
        )
        self.combo_cor_mapa.configure(state=estado_combo)
        # Itens de Menu
        if hasattr(self, "file_menu"):  # Verifica se menu existe
            self.file_menu.entryconfigure("Exportar Log Atual (.csv)...", state=estado)

    def editar_arquivo_config(self):
        """Abre o arquivo config.ini no editor de texto padrão do sistema."""
        self.atualizar_status(f"Tentando abrir {CONFIG_FILE}...")
        try:
            # Tenta criar o arquivo de config com valores padrão se ele não existir
            if not os.path.exists(CONFIG_FILE):
                # Chama load_config que deve criar o arquivo se não existir
                # É importante que load_config tenha essa lógica implementada
                self.channel_mapping, self.track_config, self.analysis_config = (
                    load_config()
                )
            # Verifica novamente se o arquivo existe após a tentativa de criação
            if not os.path.exists(CONFIG_FILE):
                self.atualizar_status(
                    f"Erro: '{CONFIG_FILE}' não encontrado e não pôde ser criado."
                )
                return messagebox.showerror(
                    "Erro",
                    f"'{CONFIG_FILE}' não encontrado e não pôde ser criado automaticamente.",
                )

            print(f"Abrindo '{CONFIG_FILE}'...")  # Log para console
            system = platform.system()  # Detecta o sistema operacional
            if system == "Windows":
                os.startfile(CONFIG_FILE)  # Comando para Windows
            elif system == "Darwin":
                subprocess.call(["open", CONFIG_FILE])  # Comando para macOS
            else:  # Linux e outros
                try:
                    subprocess.call(
                        ["xdg-open", CONFIG_FILE]
                    )  # Comando padrão para Linux
                except FileNotFoundError:
                    self.atualizar_status("Erro: Comando 'xdg-open' não encontrado.")
                    messagebox.showerror(
                        "Erro",
                        "Comando 'xdg-open' não encontrado. Abra o arquivo manualmente.",
                    )
                except Exception as e_open:
                    self.atualizar_status(f"Erro ao abrir '{CONFIG_FILE}'.")
                    messagebox.showerror(
                        "Erro", f"Erro ao abrir '{CONFIG_FILE}':\n{e_open}"
                    )
            self.atualizar_status(
                f"Arquivo '{CONFIG_FILE}' aberto no editor padrão (se disponível). Recarregue a aplicação para ver mudanças."
            )
        except Exception as e:
            self.atualizar_status("Erro ao tentar abrir config.")
            messagebox.showerror(
                "Erro", f"Erro ao tentar abrir o arquivo de configuração:\n{e}"
            )

    def mostrar_sobre(self):
        """Exibe uma caixa de diálogo 'Sobre'."""
        messagebox.showinfo(
            "Sobre PUCPR Racing PyAnalysis Tool",
            f"Versão: 1.0\n\n"
            "Ferramenta para análise básica de logs de dados da PUCPR Racing.\n"
            "Desenvolvido por Artur Kuzma Marques. Como parte do Processo Seletivo.\n\n"
            "Funcionalidades Principais:\n"
            "- Carregar logs CSV com mapeamento de canais via config\n"
            "- Plotagem de canais selecionados\n"
            "- Diagrama G-G\n"
            "- Mapa da Pista (GPS)\n"
            "- Análises específicas (Skidpad, Aceleração, Voltas, etc.)\n"
            "- Interface com tema escuro (CustomTkinter)",
        )


# --- Bloco Principal ---
if __name__ == "__main__":
    try:
        app = AppAnalisePUCPR()  # Cria a instância da aplicação
        app.mainloop()  # Inicia o loop principal da interface gráfica
    except Exception as e:
        # Tenta logar antes de mostrar messagebox, pois Tkinter pode não estar pronto
        import logging

        # Configura logging para um arquivo
        log_filename = "app_error.log"
        logging.basicConfig(
            level=logging.ERROR,
            filename=log_filename,
            filemode="a",
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        logging.exception("Erro fatal ao iniciar a aplicação:")
        # Tenta mostrar uma messagebox, mas pode falhar se o Tkinter não inicializou
        try:
            messagebox.showerror(
                "Erro Fatal",
                f"Ocorreu um erro crítico ao iniciar a aplicação:\n{e}\n\nVerifique o arquivo '{log_filename}' para detalhes.",
            )
        except:
            print(f"ERRO FATAL AO INICIAR: {e}")  # Fallback para console
