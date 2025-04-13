import pandas as pd
from tkinter import messagebox
from typing import Dict, Optional

# Depende da constante frequency definida em main_gui.py se usada
# ou pode ser passada como argumento se preferir isolamento total.
# Para simplificar, assumir que está no escopo global quando chamado.
# from main_gui import frequency # Ou importar de onde estiver definida

def carregar_log_csv(filepath: str, config_map: Dict[str, str]) -> Optional[pd.DataFrame]:
    """
    Carrega dados de um arquivo CSV e tenta configurar o índice de tempo.

    Args:
        filepath: Caminho para o arquivo CSV.
        config_map: Dicionário de mapeamento de canais.

    Returns:
        DataFrame carregado com índice de tempo (se possível), ou None em caso de erro.
    """
    global frequency # Acessa a frequência global definida no main_gui.py

    if not filepath:
        return None
    try:
        df = pd.read_csv(filepath, sep=',')
        time_col_found = False
        # Usa o config_map para encontrar o nome da coluna de timestamp
        timestamp_log_name = config_map.get('timestamp', 'Timestamp')
        potential_time_cols = [col for col in df.columns if col.lower() == timestamp_log_name.lower()]

        if potential_time_cols:
            timestamp_col = potential_time_cols[0] # Pega o nome exato como está no log
            try:
                # Tenta converter para numérico primeiro (segundos/ms)
                numeric_time = pd.to_numeric(df[timestamp_col], errors='coerce')
                if numeric_time.notna().sum() > len(df) * 0.5: # Maioria numérica?
                    # Converte para datetime (assume segundos desde epoch)
                    df['Timestamp_dt'] = pd.to_datetime(numeric_time, unit='s', errors='coerce')
                else: # Tenta converter como string de data/hora
                     df['Timestamp_dt'] = pd.to_datetime(df[timestamp_col], errors='coerce')

                # Se a conversão funcionou bem, usa como índice
                if 'Timestamp_dt' in df.columns and df['Timestamp_dt'].notna().sum() > len(df) * 0.8:
                    df = df.set_index('Timestamp_dt')
                    print(f"Coluna '{timestamp_col}' usada como índice DatetimeIndex.")
                    time_col_found = True
                else: # Limpa coluna temporária se falhou
                    if 'Timestamp_dt' in df.columns: df = df.drop(columns=['Timestamp_dt'])
            except Exception as e:
                print(f"Aviso: Não foi possível converter '{timestamp_col}' para índice: {e}")
                if 'Timestamp_dt' in df.columns: df = df.drop(columns=['Timestamp_dt'])

        if not time_col_found:
             print("Aviso: Nenhuma coluna de timestamp válida encontrada/convertida. Usando índice numérico padrão.")
             # Garante que a coluna original (se existir) seja numérica
             if potential_time_cols and potential_time_cols[0] in df.columns:
                 df[potential_time_cols[0]] = pd.to_numeric(df[potential_time_cols[0]], errors='coerce')

        print(f"Dados carregados. Colunas disponíveis: {df.columns.tolist()}")
        return df
    except FileNotFoundError:
        messagebox.showerror("Erro", f"Arquivo não encontrado: {filepath}")
        return None
    except pd.errors.EmptyDataError:
         messagebox.showerror("Erro", f"Arquivo CSV vazio: {filepath}")
         return None
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao carregar dados: {e}\nVerifique o formato e o nome das colunas.")
        return None