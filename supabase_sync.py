import os
import json
import glob
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from utils.naming import normalize_team_name

def archive_finished_matches(url, key):
    """
    Antes del PURGE: lee los partidos con status='finished' en daily_board
    y los archiva en historical_results (upsert, no sobreescribe si ya existe).
    Devuelve el número de filas archivadas.
    """
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    # 1. Obtener finished desde daily_board
    fetch_url = f"{url}/rest/v1/daily_board?status=eq.finished&select=*"
    try:
        resp = requests.get(fetch_url, headers=headers)
        if resp.status_code != 200:
            print(f"[WARN] No se pudo leer daily_board para archivar (HTTP {resp.status_code}): {resp.text}")
            return 0
        finished_rows = resp.json()
    except Exception as e:
        print(f"[ERROR] Fallo al leer daily_board: {e}")
        return 0

    if not finished_rows:
        print("[ARCHIVE] No hay partidos finalizados que archivar.")
        return 0

    # 2. Obtener IDs ya archivados para no sobreescribir actual_result / status_win_loss
    existing_ids_url = f"{url}/rest/v1/historical_results?select=id"
    try:
        resp_ex = requests.get(existing_ids_url, headers=headers)
        existing_ids = {row["id"] for row in resp_ex.json()} if resp_ex.status_code == 200 else set()
    except Exception:
        existing_ids = set()

    # 3. Construir payload solo con filas nuevas
    to_archive = []
    for row in finished_rows:
        if row.get("id") in existing_ids:
            continue  # ya archivado, no tocar actual_result ni status_win_loss
        archive_row = {
            "id":                  row.get("id"),
            "match_date":          row.get("match_date"),
            "home_team":           row.get("home_team"),
            "away_team":           row.get("away_team"),
            "poisson_1":           row.get("poisson_1"),
            "poisson_x":           row.get("poisson_x"),
            "poisson_2":           row.get("poisson_2"),
            "xg_diff":             row.get("xg_diff"),
            "estado_mercado":      row.get("estado_mercado"),
            "mercados_completos":  row.get("mercados_completos"),
            "status":              "finished",
            # ROI — null hasta carga manual o futura integración de resultados
            "actual_result":       None,
            "status_win_loss":     "pending",
        }
        to_archive.append(archive_row)

    if not to_archive:
        print(f"[ARCHIVE] {len(finished_rows)} partido(s) finalizado(s) ya estaban archivados.")
        return 0

    # 4. Insertar en historical_results
    insert_url = f"{url}/rest/v1/historical_results"
    insert_headers = {**headers, "Prefer": "resolution=ignore-duplicates"}
    try:
        resp_ins = requests.post(insert_url, headers=insert_headers, json=to_archive)
        if resp_ins.status_code in [200, 201]:
            print(f"[ARCHIVE] {len(to_archive)} partido(s) archivado(s) en historical_results.")
        else:
            print(f"[WARN] Fallo al insertar en historical_results (HTTP {resp_ins.status_code}): {resp_ins.text}")
            return 0
    except Exception as e:
        print(f"[ERROR] Excepción al archivar: {e}")
        return 0

    return len(to_archive)


def delete_all_rows(url, key, table_name):
    """Purga todos los registros de una tabla antes de reinsertar."""
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    endpoint = f"{url}/rest/v1/{table_name}?id=not.is.null"
    try:
        resp = requests.delete(endpoint, headers=headers)
        if resp.status_code in [200, 204]:
            print(f"[PURGE] Tabla '{table_name}' limpiada antes de sync.")
        else:
            print(f"[WARN] No se pudo purgar '{table_name}' (HTTP {resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"[ERROR] Error al purgar '{table_name}': {e}")

def upsert_via_rest(url, key, table_name, data_list):
    if not data_list: return
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    endpoint = f"{url}/rest/v1/{table_name}"
    
    try:
        response = requests.post(endpoint, headers=headers, json=data_list)
        if response.status_code in [200, 201]:
            print(f"[OK] Sincronizados {len(data_list)} registros en '{table_name}'.")
        else:
            print(f"[ERROR] Falló upsert en '{table_name}' (Status: {response.status_code})")
            print(f"        Respuesta: {response.text}")
    except Exception as e:
        print(f"[ERROR] Error de conexión REST al sincronizar '{table_name}': {e}")

def generate_triple_angle_gemini(partido, picks, summary):
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[WARN] GOOGLE_API_KEY no configurada. Saltando análisis IA.")
        return None
        
    local = partido.get("local", "Local")
    visit = partido.get("visitante", "Visitante")
    liga = partido.get("liga", "Competición")
    fecha = partido.get("fecha", "Desconocida")
    
    if picks:
        picks_str = json.dumps(picks, ensure_ascii=False)
    else:
        picks_str = "SIN MERCADOS SECUNDARIOS VALIOSOS. ANALIZAR PROBABILIDADES 1X2."
        
    summary_str = json.dumps(summary, ensure_ascii=False)
    
    prompt = f"""
Actúa como un analista deportivo profesional de apuestas. Necesito el análisis estratégico (Triple Ángulo) para:
{local} vs {visit} ({liga}) el {fecha}.

Datos Técnicos del Modelo (VIP Picks con EV+):
{picks_str}

Resumen del Partido (Probabilidades Poisson, Diferencial xG):
{summary_str}

Basado EXCLUSIVAMENTE en estos datos (y deducciones lógicas breves), genera un análisis en formato JSON estricto con 3 llaves exactas:
{{
  "angulo_matematico": "Explicación de las probabilidades implícitas del modelo (Poisson) y el valor si lo hay (EV).",
  "angulo_tendencia": "Explicación basada en la tendencia estadística (xG Diff o forma implícita).",
  "angulo_contexto": "Breve nota sobre contexto general o de mercado. No inventar datos inexistentes."
}}
Responde SOLO con un JSON válido y parseable, sin bloques asincrónicos (sin ```json).
    """
    
    url_api = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    try:
        response = requests.post(url_api, headers=headers, json=data)
        if response.status_code == 200:
            res_json = response.json()
            text_response = res_json['candidates'][0]['content']['parts'][0]['text']
            # Limpiar posibles delimitadores de código
            text_response = text_response.replace("```json", "").replace("```", "").strip()
            return json.loads(text_response)
        else:
            print(f"[ERROR] Gemini API falló (HTTP {response.status_code}): {response.text}")
    except Exception as e:
        print(f"[ERROR] Error al procesar IA con Gemini: {e}")
        
    return None


def _extract_event_date(partido, fecha_reporte):
    """
    Extrae la fecha REAL del evento (YYYY-MM-DD) desde hora_utc del partido.
    Si no existe hora_utc, convierte la fecha del reporte DD_MM_YY a YYYY-MM-DD.
    """
    hora_utc = partido.get("hora_utc") if partido else None
    if hora_utc:
        return hora_utc.split("T")[0]  # "2026-03-11T20:00:00Z" → "2026-03-11"
    
    # Fallback: convertir fecha del reporte (DD_MM_YY) a YYYY-MM-DD
    parts = fecha_reporte.split("_")
    if len(parts) == 3:
        return f"20{parts[2]}-{parts[1]}-{parts[0]}"  # "11_03_26" → "2026-03-11"
    return fecha_reporte


def _build_unique_id(event_date, local, visit):
    """
    Construye un ID determinístico usando fecha real + nombres normalizados.
    Siempre produce el mismo ID para el mismo partido real.
    """
    norm_local = normalize_team_name(local).replace(" ", "_")
    norm_visit = normalize_team_name(visit).replace(" ", "_")
    return f"{event_date}_{norm_local}_{norm_visit}"


def _compute_status(hora_utc_str):
    """
    Determina si el partido está activo o finalizado basado en hora_utc.
    Si no hay hora_utc, devuelve 'active' por defecto.
    """
    if not hora_utc_str:
        return "active"
    try:
        match_dt = datetime.strptime(hora_utc_str, "%Y-%m-%dT%H:%M:%SZ")
        match_dt = match_dt.replace(tzinfo=timezone.utc)
        if match_dt < datetime.now(timezone.utc):
            return "finished"
    except Exception:
        pass
    return "active"


def main():
    print("==================================================")
    print("  PODIUM 360 - SUPABASE SYNC (VIA REST API)")
    print("==================================================")

    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("[FAIL] Credenciales SUPABASE_URL o SUPABASE_KEY no encontradas en .env")
        return

    # Buscar JSON
    date_str = datetime.now().strftime("%d_%m_%y")
    report_file = os.path.join("database", f"daily_report_{date_str}.json")
    
    if not os.path.exists(report_file):
        archivos = glob.glob("database/daily_report_*.json")
        if not archivos:
            print("[WARN] No hay archivos daily_report_*.json en /database para sincronizar.")
            return
        report_file = max(archivos, key=os.path.getctime)
        print(f"[INFO] Usando el reporte más reciente encontrado: {report_file}")

    print(f"[INFO] Cargando JSON: {report_file}")
    with open(report_file, "r", encoding="utf-8") as f:
        daily_report = json.load(f)

    fecha = daily_report.get("fecha", date_str)
    board = daily_report.get("daily_board", [])
    vips = daily_report.get("vip_signals", [])
    
    print(f"[INFO] Parseando {len(board)} partidos en Daily Board y {len(vips)} señales VIP.")

    # ══════════════════════════════════════════════════════════════════════════
    # Filtrar entradas con partido=null (datos corruptos de ejecuciones previas)
    # ══════════════════════════════════════════════════════════════════════════
    board = [item for item in board if item.get("partido")]
    vips = [item for item in vips if item.get("partido")]
    
    # Filtro de seguridad: excluir partidos fantasma (sin fixture ni odds)
    def _is_real_match(item):
        partido = item.get("partido", {})
        summary = item.get("match_summary", {})
        has_hora = bool(partido.get("hora_utc"))
        has_markets = bool(summary.get("all_markets"))
        return has_hora or has_markets
    
    board_before = len(board)
    board = [item for item in board if _is_real_match(item)]
    if len(board) < board_before:
        print(f"[FILTER] Excluidos {board_before - len(board)} partidos fantasma (sin fixture ni odds).")
    
    print(f"[INFO] Tras filtrado: {len(board)} partidos reales, {len(vips)} VIP.")

    # ══════════════════════════════════════════════════════════════════════════
    # Generar análisis IA para toda la jornada
    # ══════════════════════════════════════════════════════════════════════════
    ai_cache = {}
    print("[INFO] Evaluando generación IA para toda la jornada...")
    for item in board:
        partido = item.get("partido")
        summary = item.get("match_summary") or {}
        if not partido: continue
        
        local = normalize_team_name(partido.get("local", ""))
        visit = normalize_team_name(partido.get("visitante", ""))
        event_date = _extract_event_date(partido, fecha)
        unique_id = _build_unique_id(event_date, local, visit)

        match_vip = next((v for v in vips 
                         if normalize_team_name(v.get("partido", {}).get("local", "")) == local 
                         and normalize_team_name(v.get("partido", {}).get("visitante", "")) == visit), None)
        picks = match_vip.get("picks_valiosos", []) if match_vip else []
        triple_angulo = match_vip.get("analisis_triple_angulo") if match_vip else None

        if isinstance(triple_angulo, dict) and "angulo_1_matematico" in triple_angulo:
            ang_mat = triple_angulo.get("angulo_1_matematico", "")
            ang_ten = triple_angulo.get("angulo_2_tendencia", "")
            ang_ctx = triple_angulo.get("angulo_3_contexto", "")
            ai_cache[unique_id] = {"angulo_matematico": ang_mat, "angulo_tendencia": ang_ten, "angulo_contexto": ang_ctx}
        else:
            print(f"[IA] Generando análisis (Gemini) para {local} vs {visit}...")
            ai_data = generate_triple_angle_gemini(partido, picks, summary)
            if ai_data:
                ai_cache[unique_id] = ai_data
            else:
                ai_cache[unique_id] = {
                    "angulo_matematico": "Análisis IA Pendiente...",
                    "angulo_tendencia": "Análisis IA Pendiente...",
                    "angulo_contexto": triple_angulo if isinstance(triple_angulo, str) else "Esperando conexión a Gemini..."
                }

    # ══════════════════════════════════════════════════════════════════════════
    # ARCHIVE: Mover partidos finalizados a historical_results ANTES del PURGE
    # ══════════════════════════════════════════════════════════════════════════
    print("[INFO] Archivando partidos finalizados en historical_results...")
    archived_count = archive_finished_matches(url, key)
    if archived_count > 0:
        print(f"[ARCHIVE] {archived_count} partido(s) nuevo(s) guardados para auditoría ROI.")

    # ══════════════════════════════════════════════════════════════════════════
    # PURGE: Limpiar tablas antes de insertar datos frescos
    # ══════════════════════════════════════════════════════════════════════════
    print("[INFO] Purgando tablas de Supabase antes de reinsertar...")
    delete_all_rows(url, key, "daily_board")
    delete_all_rows(url, key, "vip_signals")

    # ══════════════════════════════════════════════════════════════════════════
    # TABLA 1: daily_board
    # ══════════════════════════════════════════════════════════════════════════
    upsert_board_data = []
    seen_board_ids = set()  # Deduplicación extra
    
    for item in board:
        partido = item.get("partido")
        summary = item.get("match_summary") or {}
        poisson = summary.get("probabilidades_poisson", {})
        
        if not partido: continue
             
        local = normalize_team_name(partido.get("local", ""))
        visit = normalize_team_name(partido.get("visitante", ""))
        hora_utc_str = partido.get("hora_utc")
        event_date = _extract_event_date(partido, fecha)
        unique_id = _build_unique_id(event_date, local, visit)
        
        # Deduplicación: si ya procesamos este partido, saltar
        if unique_id in seen_board_ids:
            print(f"[DEDUP] Saltando duplicado en board: {unique_id}")
            continue
        seen_board_ids.add(unique_id)
        
        match_status = _compute_status(hora_utc_str)
        
        mercados_completos = summary.get("all_markets", [])
        if not mercados_completos:
            ai_text = ai_cache.get(unique_id, {})
            mercados_completos = [{
                "mercado": "IA_ANALYSIS",
                "angulo_matematico": ai_text.get("angulo_matematico", ""),
                "angulo_tendencia": ai_text.get("angulo_tendencia", ""),
                "angulo_contexto": ai_text.get("angulo_contexto", "")
            }]
            
        row = {
            "id": unique_id,
            "match_date": event_date,  # ← FECHA REAL DEL EVENTO, no del reporte
            "home_team": local,
            "away_team": visit,
            "poisson_1": poisson.get("local"),
            "poisson_x": poisson.get("empate"),
            "poisson_2": poisson.get("visitante"),
            "xg_diff": summary.get("diferencial_xg_rolling"),
            "estado_mercado": summary.get("estado_mercado", "Desconocido"),
            "mercados_completos": mercados_completos,
            "status": match_status
        }
        upsert_board_data.append(row)

    upsert_via_rest(url, key, "daily_board", upsert_board_data)

    # ══════════════════════════════════════════════════════════════════════════
    # TABLA 2: vip_signals
    # ══════════════════════════════════════════════════════════════════════════
    upsert_vip_data = []
    seen_vip_ids = set()  # Deduplicación extra
    
    for item in vips:
        partido = item.get("partido")
        picks = item.get("picks_valiosos", [])
        
        if not partido or not picks: continue
            
        local = normalize_team_name(partido.get("local", ""))
        visit = normalize_team_name(partido.get("visitante", ""))
        hora_utc_str = partido.get("hora_utc")
        event_date = _extract_event_date(partido, fecha)
        unique_id = _build_unique_id(event_date, local, visit)
        match_status = _compute_status(hora_utc_str)
        
        ai_data = ai_cache.get(unique_id, {})
        ang_mat = ai_data.get("angulo_matematico", "No generado.")
        ang_ten = ai_data.get("angulo_tendencia", "No generado.")
        ang_ctx = ai_data.get("angulo_contexto", "No generado.")
            
        for pick in picks:
            mercado = pick.get("mercado", "")
            vip_id = f"{unique_id}_{mercado}".replace(" ", "_")
            
            # Deduplicación
            if vip_id in seen_vip_ids:
                print(f"[DEDUP] Saltando duplicado en VIP: {vip_id}")
                continue
            seen_vip_ids.add(vip_id)
            
            # Empaquetamos mercado en el ángulo porque su esquema de DB no tiene columna mercado
            packed_matematico = f"[Mercado: {mercado.upper()}] " + ang_mat
            
            row = {
                "id": vip_id,
                "match_date": event_date,  # ← FECHA REAL DEL EVENTO
                "home_team": local,
                "away_team": visit,
                "cuota": pick.get("cuota"),
                "ev_pct": pick.get("ev_pct"),
                "ev_initial": pick.get("ev_pct"), 
                "angulo_matematico": packed_matematico,
                "angulo_tendencia": ang_ten,
                "angulo_contexto": ang_ctx,
                "status": match_status
            }
            upsert_vip_data.append(row)

    upsert_via_rest(url, key, "vip_signals", upsert_vip_data)

    print("==================================================")
    print("  SINCRONIZACIÓN COMPLETADA")
    print("==================================================")

if __name__ == "__main__":
    main()
