import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, Union, List

# Importa a função de mapeamento
from config_manager import get_channel_name

# Importa constante global de frequência (definida em main_gui.py)
# Se preferir isolamento total, passe 'frequency' como argumento
global frequency

# Constante para conversão aproximada (pode variar com latitude)
DEG_TO_M = 111111.0

def haversine(lat1: Union[float, np.ndarray], lon1: Union[float, np.ndarray], lat2: float, lon2: float) -> Union[float, np.ndarray]:
    """Calcula a distância em metros entre uma ou mais coordenadas GPS e um ponto fixo usando Haversine."""
    R = 6371000  # Raio da Terra em metros
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    a = np.sin(delta_phi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

def calcular_metricas_gg(df: Optional[pd.DataFrame], config_map: Dict[str, str]) -> Tuple[pd.DataFrame, Optional[str], Optional[str], Optional[str]]:
    """Prepara dados para o diagrama G-G."""
    if df is None: return pd.DataFrame(), None, None, "Erro: Log não carregado."
    lat_col = get_channel_name(config_map, 'lataccel', df.columns)
    lon_col = get_channel_name(config_map, 'lonaccel', df.columns)
    error_msg = ""
    if not lat_col: error_msg += "- Coluna LatAccel (lataccel) não encontrada/mapeada.\n"
    if not lon_col: error_msg += f"- Coluna LonAccel (lonaccel) não encontrada/mapeada.\n"
    if error_msg: return pd.DataFrame(), None, None, f"Erro:\n{error_msg}"
    try:
        return df[[lat_col, lon_col]].dropna(), lat_col, lon_col, None
    except Exception as e:
        return pd.DataFrame(), None, None, f"Erro inesperado G-G: {e}"

def calcular_tempos_volta(df: Optional[pd.DataFrame], config_map: Dict[str, str], track_config: Dict[str, str], analysis_config: Dict[str, str]) -> Tuple[Optional[pd.Series], str]:
    """ Calcula tempos de volta baseado no cruzamento da linha de chegada/partida GPS. """
    global frequency
    if df is None: return None, "Erro: Log não carregado."
    lat_col = get_channel_name(config_map, 'gpslat', df.columns)
    lon_col = get_channel_name(config_map, 'gpslon', df.columns)
    time_col = get_channel_name(config_map, 'timestamp', df.columns)

    error_msg = ""
    if not lat_col: error_msg += "- Coluna GPS Latitude (gpslat) não encontrada/mapeada.\n"
    if not lon_col: error_msg += "- Coluna GPS Longitude (gpslon) não encontrada/mapeada.\n"
    has_time_index = isinstance(df.index, pd.DatetimeIndex)
    has_time_col = time_col and time_col in df.columns and pd.api.types.is_numeric_dtype(df[time_col])
    if not has_time_index and not has_time_col:
         error_msg += f"- Coluna Timestamp ('{time_col or 'timestamp'}') numérica não encontrada/mapeada E índice não é DatetimeIndex.\n"
    if error_msg: return None, f"Erro: Dados insuficientes:\n{error_msg}"

    try:
        start_finish_lat = float(track_config.get('startfinishlat', 0.0))
        start_finish_lon = float(track_config.get('startfinishlon', 0.0))
        threshold_m = float(analysis_config.get('lapdetectionthresholdmeters', 15.0)) # Default 15m
        min_lap_time_s = float(analysis_config.get('minlaptimeseconds', 20.0)) # Default 20s
        print(f"Calculando Voltas: Linha em ({start_finish_lat}, {start_finish_lon}), Threshold: {threshold_m}m, Tempo Mín: {min_lap_time_s}s")

        # --- Lógica de Tempo ---
        time_seconds = None
        if has_time_index:
            time_deltas = df.index - df.index[0]; time_seconds = pd.Series(time_deltas.total_seconds(), index=df.index)
        elif has_time_col:
            time_seconds = df[time_col] - df[time_col].iloc[0]; time_seconds = time_seconds.fillna(0)
        else:
            time_seconds = pd.Series(df.index * (1/frequency), index=df.index); print(f"Aviso: Usando índice numérico (freq={frequency} Hz).")
        if time_seconds is None: return None, "Erro: Tempo decorrido não determinado."
        time_seconds.name = 'elapsed_seconds'

        # --- Lógica de Detecção de Cruzamento ---
        print("Calculando distâncias da linha de chegada...")
        distances = haversine(df[lat_col].values, df[lon_col].values, start_finish_lat, start_finish_lon)
        df_dist = pd.Series(distances, index=df.index)

        below_threshold = df_dist < threshold_m
        crossed_into_zone = below_threshold & ~below_threshold.shift(1).fillna(False)

        crossing_indices = df.index[crossed_into_zone]
        crossing_times = time_seconds[crossed_into_zone].tolist()

        # --- DEBUG PRINTS ---
        print(f"Pontos abaixo do threshold ({threshold_m}m): {below_threshold.sum()}")
        print(f"Cruzamentos detectados (entradas na zona): {len(crossing_times)}")
        if crossing_times: print(f"Tempos dos cruzamentos detectados (s): {[f'{t:.2f}' for t in crossing_times]}")
        # --- FIM DEBUG PRINTS ---

        if len(crossing_times) < 2:
            return None, "Não foram detectados cruzamentos suficientes da linha de chegada (mínimo 2)."

        # --- Filtra Cruzamentos e Calcula Tempos ---
        lap_times = []
        valid_crossing_times = [crossing_times[0]]
        last_valid_crossing_time = crossing_times[0]

        for k in range(1, len(crossing_times)):
            current_crossing_time = crossing_times[k]
            time_diff = current_crossing_time - last_valid_crossing_time
            if time_diff >= min_lap_time_s:
                lap_times.append(time_diff)
                valid_crossing_times.append(current_crossing_time)
                last_valid_crossing_time = current_crossing_time
            else:
                print(f"  -> Cruzamento em {current_crossing_time:.2f}s ignorado (tempo desde último válido: {time_diff:.2f}s < {min_lap_time_s}s)")

        # Atribui números das voltas
        lap_numbers = pd.Series(0, index=df.index, name='LapNumber')
        for lap_idx, cross_time_start in enumerate(valid_crossing_times):
            if lap_idx + 1 < len(valid_crossing_times):
                cross_time_end = valid_crossing_times[lap_idx + 1]
                lap_mask = (time_seconds >= cross_time_start) & (time_seconds < cross_time_end)
            else: lap_mask = (time_seconds >= cross_time_start)
            lap_numbers[lap_mask] = lap_idx + 1

        if not lap_times:
            return lap_numbers, "Nenhuma volta completa detectada (tempo mínimo não atingido entre cruzamentos válidos)."

        lap_times_summary = "Tempos de volta calculados:\n"
        for i, lap_time in enumerate(lap_times):
            lap_times_summary += f"Volta {i+1}: {lap_time:.2f}s\n"

        print("Tempos de volta calculados com sucesso.")
        return lap_numbers, lap_times_summary.strip()

    except Exception as e:
        print(f"Erro durante cálculo de voltas: {e}")
        import traceback
        traceback.print_exc()
        return None, f"Erro durante cálculo de voltas: {e}"

def calcular_metricas_skidpad(df: Optional[pd.DataFrame], config_map: Dict[str, str]) -> str:
    """Calcula métricas básicas do Skid Pad."""
    if df is None: return "Erro: Log não carregado."
    lat_col = get_channel_name(config_map, 'lataccel', df.columns)
    if not lat_col: return "Erro: Canal LatAccel (lataccel) não mapeado."
    try:
        # TODO: Implementar detecção de fase Skid Pad
        max_lat_g = df[lat_col].abs().max()
        avg_lat_g = df[lat_col].abs().mean()
        return f"G Lat Máx (Abs): {max_lat_g:.3f} G\nG Lat Médio (Abs): {avg_lat_g:.3f} G\n(Log Inteiro - Placeholder)"
    except Exception as e: return f"Erro no cálculo: {e}"

# --- MODIFICAÇÃO AQUI: Implementa cálculo 0-75m ---
def calcular_metricas_aceleracao(df: Optional[pd.DataFrame], config_map: Dict[str, str], distance_target: float = 75.0) -> str:
    """
    Calcula o tempo para atingir a distância alvo (ex: 75m) e a velocidade máxima
    durante a puxada de aceleração.
    """
    global frequency
    if df is None: return "Erro: Log não carregado."

    # --- Identifica canais necessários ---
    speed_col = None; speed_data = None; speed_col_name = "Velocidade"
    throttle_col = get_channel_name(config_map, 'throttlepos', df.columns)
    time_col = get_channel_name(config_map, 'timestamp', df.columns)

    # Encontra a melhor fonte de velocidade
    vehicle_speed_col = get_channel_name(config_map, 'vehiclespeed', df.columns)
    ws_fl = get_channel_name(config_map, 'wheelspeedfl', df.columns)
    ws_fr = get_channel_name(config_map, 'wheelspeedfr', df.columns)
    gps_speed = get_channel_name(config_map, 'gpsspeed', df.columns)

    if vehicle_speed_col and vehicle_speed_col in df.columns:
        speed_col = vehicle_speed_col; speed_data = df[speed_col]; speed_col_name = f"{speed_col} (mapeada)"
    elif ws_fl and ws_fr:
        try: speed_data = df[[ws_fl, ws_fr]].mean(axis=1); speed_col = f"Média Rodas ({ws_fl}, {ws_fr})"; speed_col_name = speed_col
        except Exception: speed_data = None
    if speed_data is None and gps_speed and gps_speed in df.columns:
        speed_col = gps_speed; speed_data = df[speed_col]; speed_col_name = f"{speed_col} (GPS)"

    # Verifica se encontrou velocidade e tempo
    error_msg = ""
    if speed_data is None: error_msg += f"- Nenhum canal de velocidade válido encontrado/mapeado.\n"
    has_time_index = isinstance(df.index, pd.DatetimeIndex)
    has_time_col = time_col and time_col in df.columns and pd.api.types.is_numeric_dtype(df[time_col])
    if not has_time_index and not has_time_col: error_msg += f"- Coluna Timestamp ('{time_col or 'timestamp'}') não encontrada/inválida.\n"
    if not throttle_col: error_msg += f"- Coluna ThrottlePos ('{throttle_col or 'throttlepos'}') não encontrada/mapeada.\n"
    if error_msg: return f"Erro: Dados insuficientes para Aceleração:\n{error_msg}"

    print(f"Calculando Aceleração: Usando Velocidade='{speed_col_name}', Throttle='{throttle_col}', Tempo='{time_col or 'Index'}'")

    try:
        # --- Determina vetor de tempo em segundos ---
        time_seconds = None
        if has_time_index:
            time_deltas = df.index - df.index[0]; time_seconds = pd.Series(time_deltas.total_seconds(), index=df.index)
        elif has_time_col:
            time_seconds = df[time_col] - df[time_col].iloc[0]; time_seconds = time_seconds.fillna(0)
        else:
            time_seconds = pd.Series(df.index * (1/frequency), index=df.index); print(f"Aviso: Usando índice numérico (freq={frequency} Hz).")
        if time_seconds is None: return "Erro: Tempo decorrido não determinado."
        time_seconds.name = 'elapsed_seconds'
        dt_series = time_seconds.diff().fillna(0) # Delta T entre pontos

        # --- Detecta início da puxada ---
        # Procura pelo primeiro instante onde velocidade < 1 m/s e throttle > 80%
        start_mask = (speed_data < 1.0) & (df[throttle_col] > 80)
        start_index = start_mask.idxmax() # Pega o índice do primeiro True
        # Se não encontrar um início claro, começa do primeiro ponto (pode ser impreciso)
        if not start_mask.any():
            print("Aviso: Início da aceleração não detectado claramente (Vel < 1 e Thr > 80). Começando do início do log.")
            start_index = df.index[0]

        # Filtra dados a partir do início detectado
        df_run = df.loc[start_index:]
        speed_run = speed_data.loc[start_index:]
        time_run = time_seconds.loc[start_index:]
        dt_run = dt_series.loc[start_index:]
        time_run_relative = time_run - time_run.iloc[0] # Tempo relativo ao início da puxada

        # --- Calcula Distância Percorrida ---
        # Integração trapezoidal simples: dist += V_media * dt
        # V_media = (V_atual + V_anterior) / 2
        distance_run = ((speed_run.shift(fill_value=0) + speed_run) / 2 * dt_run).cumsum()

        # --- Encontra tempo para atingir distance_target ---
        target_reached_mask = distance_run >= distance_target
        time_to_target = np.nan
        idx_target = None
        if target_reached_mask.any():
            idx_target = target_reached_mask.idxmax() # Índice onde atingiu a distância
            time_to_target = time_run_relative.loc[idx_target]
            # Interpolação linear simples para melhorar precisão (opcional)
            try:
                idx_pos = distance_run.index.get_loc(idx_target)
                if idx_pos > 0:
                    dist_prev = distance_run.iloc[idx_pos-1]
                    dist_curr = distance_run.iloc[idx_pos]
                    time_prev = time_run_relative.iloc[idx_pos-1]
                    time_curr = time_run_relative.iloc[idx_pos]
                    if dist_curr > dist_prev: # Evita divisão por zero
                        interp_factor = (distance_target - dist_prev) / (dist_curr - dist_prev)
                        time_to_target = time_prev + interp_factor * (time_curr - time_prev)
            except Exception as e_interp:
                print(f"Aviso: Erro na interpolação do tempo de aceleração: {e_interp}")

        # --- Calcula Velocidade Máxima na Puxada (até atingir o alvo ou fim) ---
        run_data_to_analyze = speed_run
        if idx_target is not None: # Se atingiu o alvo, só considera dados até lá
            run_data_to_analyze = speed_run.loc[:idx_target]

        max_speed_run = run_data_to_analyze.max()

        # --- Monta Resultado ---
        if pd.isna(time_to_target):
            result_text = (f"Distância alvo ({distance_target}m) não atingida.\n"
                           f"Velocidade Máx (durante tentativa): {max_speed_run:.1f} m/s (usando {speed_col_name})")
        else:
            result_text = (f"Tempo para {distance_target:.0f}m: {time_to_target:.3f} s\n"
                           f"Velocidade Máx (na puxada): {max_speed_run:.1f} m/s (usando {speed_col_name})")

        return result_text

    except Exception as e:
        print(f"Erro cálculo Accel: {e}")
        import traceback
        traceback.print_exc()
        return f"Erro nos cálculos de Aceleração: {e}"