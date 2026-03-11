import os
import json
import glob
import requests
from datetime import datetime
from dotenv import load_dotenv

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
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
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

    ai_cache = {}
    print("[INFO] Evaluando generación IA para toda la jornada...")
    for item in board:
        partido = item.get("partido")
        summary = item.get("match_summary") or {}
        if not partido: continue
        local = partido.get("local", "")
        visit = partido.get("visitante", "")
        
        # ID uses Real match date (hora_utc), fallback to fecha
        hora_utc_str = partido.get("hora_utc")
        if hora_utc_str:
            # Extract YYYY-MM-DD
            real_date = hora_utc_str.split("T")[0]
        else:
            real_date = fecha
            
        unique_id = f"{real_date}_{local}_{visit}".replace(" ", "_")

        match_vip = next((v for v in vips if v.get("partido", {}).get("local") == local and v.get("partido", {}).get("visitante") == visit), None)
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

    # TABLA 1: daily_board
    upsert_board_data = []
    for item in board:
        partido = item.get("partido")
        summary = item.get("match_summary") or {}
        poisson = summary.get("probabilidades_poisson", {})
        
        if not partido: continue
             
        local = partido.get("local", "")
        visit = partido.get("visitante", "")
        
        hora_utc_str = partido.get("hora_utc")
        if hora_utc_str:
            real_date = hora_utc_str.split("T")[0]
        else:
            real_date = fecha
            
        unique_id = f"{real_date}_{local}_{visit}".replace(" ", "_")
        
        # Calculate Status
        match_status = "active"
        if hora_utc_str:
            try:
                # Basic compare against UTC now
                match_dt = datetime.strptime(hora_utc_str, "%Y-%m-%dT%H:%M:%SZ")
                if match_dt < datetime.utcnow():
                    match_status = "finished"
            except:
                pass
        
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
            "match_date": fecha,
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

    # TABLA 2: vip_signals
    upsert_vip_data = []
    for item in vips:
        partido = item.get("partido")
        picks = item.get("picks_valiosos", [])
        
        if not partido or not picks: continue
            
        local = partido.get("local", "")
        visit = partido.get("visitante", "")
        
        hora_utc_str = partido.get("hora_utc")
        if hora_utc_str:
            real_date = hora_utc_str.split("T")[0]
        else:
            real_date = fecha
            
        unique_id = f"{real_date}_{local}_{visit}".replace(" ", "_")
        
        match_status = "active"
        if hora_utc_str:
            try:
                match_dt = datetime.strptime(hora_utc_str, "%Y-%m-%dT%H:%M:%SZ")
                if match_dt < datetime.utcnow():
                    match_status = "finished"
            except:
                pass
        
        ai_data = ai_cache.get(unique_id, {})
        ang_mat = ai_data.get("angulo_matematico", "No generado.")
        ang_ten = ai_data.get("angulo_tendencia", "No generado.")
        ang_ctx = ai_data.get("angulo_contexto", "No generado.")
            
        for pick in picks:
            mercado = pick.get("mercado", "")
            unique_pick_id = f"{fecha}_{local}_{visit}_{mercado}".replace(" ", "_")
            
            # Empaquetamos mercado en el ángulo porque su esquema de DB no tiene columna mercado
            packed_matematico = f"[Mercado: {mercado.upper()}] " + ang_mat
            
            row = {
                "id": f"{unique_id}_{mercado}".replace(" ", "_"),
                "match_date": fecha,
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
