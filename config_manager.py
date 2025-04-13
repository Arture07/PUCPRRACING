import configparser
import os
from tkinter import messagebox
from typing import Dict, Tuple, List, Optional, Union
import pandas as pd # Para type hinting

CONFIG_FILE = 'config_pucpr_tool.ini'

def load_config() -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """
    Carrega configurações do arquivo INI. Retorna mapeamento de canais,
    config de pista e config de análise. Cria arquivo com padrões se não existir.
    """
    config = configparser.ConfigParser(interpolation=None, inline_comment_prefixes=('#', ';'))
    default_channels = {
        'timestamp': 'Timestamp', 'gpslat': 'GPS_Lat', 'gpslon': 'GPS_Lon',
        'gpsspeed': 'GPS_Speed', 'lataccel': 'IMU_AccelX', 'lonaccel': 'IMU_AccelY',
        'vertaccel': 'IMU_AccelZ', 'yawrate': 'IMU_GyroZ', 'wheelspeedfl': 'WheelSpeed_FL',
        'wheelspeedfr': 'WheelSpeed_FR', 'wheelspeedrl': 'WheelSpeed_RL', 'wheelspeedrr': 'WheelSpeed_RR',
        'suspposfl': 'SuspensionPos_FL', 'suspposfr': 'SuspensionPos_FR', 'suspposrl': 'SuspensionPos_RL',
        'suspposrr': 'SuspensionPos_RR', 'steerangle': 'SteeringAngle', 'throttlepos': 'ThrottlePos',
        'brakepressf': 'BrakePressure_F', 'enginerpm': 'EngineRPM', 'coolanttemp': 'CoolantTemp',
        'vehiclespeed': 'VehicleSpeed'
    }
    default_track = {'StartFinishLat': '-25.45000', 'StartFinishLon': '-49.23000'}
    default_analysis = {'SkidpadRadius': '9.0', 'LapDetectionThresholdMeters': '15.0', 'MinLapTimeSeconds': '20.0'}
    config['CHANNELS'] = default_channels; config['TRACK'] = default_track; config['ANALYSIS'] = default_analysis

    if not os.path.exists(CONFIG_FILE):
        print(f"Arquivo '{CONFIG_FILE}' não encontrado. Criando com valores padrão.")
        try:
            with open(CONFIG_FILE, 'w') as configfile:
                configfile.write("# Arquivo de Configuração para PUCPR Racing PyAnalysis Tool\n"); configfile.write("# Edite os valores aqui para corresponder aos nomes das colunas no seu CSV.\n"); configfile.write("# Edite [TRACK] com as coordenadas da linha de chegada.\n"); configfile.write("# Edite [ANALYSIS] com parâmetros de análise.\n"); configfile.write("# Use # ou ; para comentários.\n\n"); config.write(configfile)
        except Exception as e:
            print(f"Erro ao criar arquivo de configuração: {e}"); messagebox.showerror("Erro de Configuração", f"Não foi possível criar {CONFIG_FILE}.\nUsando valores padrão internos.")
            return default_channels, default_track, default_analysis

    try:
        config.read(CONFIG_FILE)
        channel_mapping = default_channels.copy()
        if 'CHANNELS' in config:
            for key, value in config.items('CHANNELS'): channel_mapping[key.lower()] = value
        else: print(f"Aviso: Seção [CHANNELS] não encontrada em {CONFIG_FILE}. Usando padrões.")
        track_config = default_track.copy()
        if 'TRACK' in config: track_config.update(dict(config.items('TRACK')))
        else: print(f"Aviso: Seção [TRACK] não encontrada em {CONFIG_FILE}. Usando padrões.")
        analysis_config = default_analysis.copy()
        if 'ANALYSIS' in config: analysis_config.update(dict(config.items('ANALYSIS')))
        else: print(f"Aviso: Seção [ANALYSIS] não encontrada em {CONFIG_FILE}. Usando padrões.")
        print(f"Configuração carregada de '{CONFIG_FILE}'")
        return channel_mapping, track_config, analysis_config
    except Exception as e:
        print(f"Erro ao ler arquivo de configuração: {e}"); messagebox.showerror("Erro de Configuração", f"Erro ao ler {CONFIG_FILE}.\nVerifique o formato.\nUsando valores padrão internos.")
        return default_channels, default_track, default_analysis

def get_channel_name(config_map: Dict[str, str], internal_name: str, df_columns: Union[List[str], pd.Index, None]) -> Optional[str]:
    """Obtém o nome real da coluna no log. Retorna None se não encontrar."""
    internal_name_lower = internal_name.lower()
    log_col_name = config_map.get(internal_name_lower, internal_name)
    if not isinstance(df_columns, (list, pd.Index)): return None
    if log_col_name in df_columns: return log_col_name
    elif internal_name in df_columns: return internal_name
    elif internal_name_lower in df_columns: return internal_name_lower
    else: return None