"""
logic/attendance_engine.py
Motor matemático de análisis de asistencia.
Usa objetos datetime nativos y enteros para evitar errores de punto flotante.
"""
import gc
import pandas as pd
from datetime import datetime, time
from data.db_manager import obtener_logs_rango, obtener_horario_dia, obtener_personal
from typing import Tuple

# ──────────────────────────────────────────────
# CONSTANTES
# ──────────────────────────────────────────────

DIAS_SEMANA = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes"}


# ──────────────────────────────────────────────
# FUNCIÓN CENTRAL DE CÁLCULO
# ──────────────────────────────────────────────

def calcular_tardanza(hora_real: time, hora_oficial: time, tolerancia: int) -> int:
    """
    Retorna los minutos de retraso (entero >= 0).
    Fórmula: Max(0, (minutos_reales - minutos_oficiales) - tolerancia)
    """
    minutos_reales   = hora_real.hour * 60 + hora_real.minute
    minutos_oficiales = hora_oficial.hour * 60 + hora_oficial.minute
    return max(0, (minutos_reales - minutos_oficiales) - tolerancia)


def procesar_asistencia(fecha_inicio: str, fecha_fin: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Procesa los logs del rango dado y genera los dos DataFrames de reporte.

    Parámetros:
        fecha_inicio: 'YYYY-MM-DD'
        fecha_fin:    'YYYY-MM-DD'

    Retorna:
        (df_reporte_a, df_reporte_b)
        df_reporte_a: Logs crudos enriquecidos
        df_reporte_b: Consolidado directivo por docente/día
    """
    logs = obtener_logs_rango(fecha_inicio, fecha_fin)

    if not logs:
        return pd.DataFrame(), pd.DataFrame()

    # ── DataFrame base ──
    df = pd.DataFrame(logs)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"])
    df["fecha"]      = df["fecha_hora"].dt.date
    df["hora"]       = df["fecha_hora"].dt.time
    df["dia_num"]    = df["fecha_hora"].dt.dayofweek  # 0=Lun

    # ── REPORTE A: Logs crudos ──
    df_a = df[["fecha", "id_biometrico", "nombre", "hora", "tipo_marcacion"]].copy()
    df_a.columns = ["Fecha", "ID", "Nombre", "Hora_Marcación", "Tipo"]
    df_a = df_a.sort_values(["Fecha", "Nombre"])

    # ── REPORTE B: Consolidado directivo ──
    filas_b = []
    personal = obtener_personal()

    for docente in personal:
        id_bio  = docente["id_biometrico"]
        nombre  = docente["nombre"]
        df_doc  = df[df["id_biometrico"] == id_bio]

        if df_doc.empty:
            continue

        for fecha_dia, grupo in df_doc.groupby("fecha"):
            dia_num = fecha_dia.weekday()
            horario = obtener_horario_dia(id_bio, dia_num)

            entradas = grupo[grupo["tipo_marcacion"] == "Entrada"]
            salidas  = grupo[grupo["tipo_marcacion"] == "Salida"]

            # ── Detectar marcas huérfanas ──
            alertas = []
            if entradas.empty:
                alertas.append("Sin registro de entrada")
            if salidas.empty:
                alertas.append("Sin registro de salida")

            # ── Calcular estado ──
            if entradas.empty and salidas.empty:
                estado           = "Falta"
                minutos_tardanza = 0
            elif entradas.empty:
                estado           = "Falta"
                minutos_tardanza = 0
                alertas.append("Marca huérfana (solo salida)")
            else:
                primera_entrada = entradas["hora"].min()

                if horario:
                    hora_oficial = time(*map(int, horario["hora_entrada"].split(":")))
                    tolerancia   = horario["tolerancia_minutos"]
                    minutos_tardanza = calcular_tardanza(primera_entrada, hora_oficial, tolerancia)
                    estado = "Tardanza" if minutos_tardanza > 0 else "Puntual"
                else:
                    minutos_tardanza = 0
                    estado = "Sin horario"
                    alertas.append("Docente sin horario para este día")

                # Detectar múltiples marcas de entrada (rebotes de huella)
                if len(entradas) > 2:
                    alertas.append(f"Posibles rebotes: {len(entradas)} marcas de entrada")

            filas_b.append({
                "Nombre":              nombre,
                "Fecha":               fecha_dia,
                "Día":                 DIAS_SEMANA.get(dia_num, "?"),
                "Estado":              estado,
                "Min_Tardanza_Día":    minutos_tardanza,
                "Hora_Entrada_Real":   str(entradas["hora"].min()) if not entradas.empty else "—",
                "Hora_Entrada_Oficial":horario["hora_entrada"] if horario else "—",
                "Alertas":             " | ".join(alertas) if alertas else "",
            })

    df_b = pd.DataFrame(filas_b) if filas_b else pd.DataFrame()

    # ── Acumulado mensual por docente ──
    if not df_b.empty:
        acumulado = df_b.groupby("Nombre")["Min_Tardanza_Día"].sum().reset_index()
        acumulado.columns = ["Nombre", "Acumulado_Min_Mes"]
        df_b = df_b.merge(acumulado, on="Nombre", how="left")
        df_b = df_b.sort_values(["Nombre", "Fecha"])

    # Liberar memoria explícitamente
    del df, df_doc
    gc.collect()

    return df_a, df_b


def obtener_resumen_rapido(fecha_inicio: str, fecha_fin: str) -> dict:
    """
    Retorna métricas rápidas para el dashboard de la GUI.
    """
    _, df_b = procesar_asistencia(fecha_inicio, fecha_fin)

    if df_b.empty:
        return {
            "total_registros": 0,
            "puntuales": 0,
            "tardanzas": 0,
            "faltas": 0,
            "docente_mas_tardanzas": "—",
            "promedio_minutos_tardanza": 0,
        }

    resumen = {
        "total_registros":           len(df_b),
        "puntuales":                 int((df_b["Estado"] == "Puntual").sum()),
        "tardanzas":                 int((df_b["Estado"] == "Tardanza").sum()),
        "faltas":                    int((df_b["Estado"] == "Falta").sum()),
        "docente_mas_tardanzas":     df_b.groupby("Nombre")["Min_Tardanza_Día"]
                                         .sum().idxmax() if not df_b.empty else "—",
        "promedio_minutos_tardanza": round(
            df_b[df_b["Estado"] == "Tardanza"]["Min_Tardanza_Día"].mean() or 0, 1
        ),
    }

    gc.collect()
    return resumen
