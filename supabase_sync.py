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

    # TABLA 1: daily_board
    upsert_board_data = []
    for item in board:
        partido = item.get("partido")
        summary = item.get("match_summary") or {}
        poisson = summary.get("probabilidades_poisson", {})
        
        if not partido: continue
             
        local = partido.get("local", "")
        visit = partido.get("visitante", "")
        unique_id = f"{fecha}_{local}_{visit}".replace(" ", "_")
        
        row = {
            "id": unique_id,
            "match_date": fecha,
            "home_team": local,
            "away_team": visit,
            "poisson_1": poisson.get("local"),
            "poisson_x": poisson.get("empate"),
            "poisson_2": poisson.get("visitante"),
            "xg_diff": summary.get("diferencial_xg_rolling"),
            "estado_mercado": summary.get("estado_mercado", "Desconocido")
        }
        upsert_board_data.append(row)

    upsert_via_rest(url, key, "daily_board", upsert_board_data)

    # TABLA 2: vip_signals
    upsert_vip_data = []
    for item in vips:
        partido = item.get("partido")
        picks = item.get("picks_valiosos", [])
        triple_angulo = item.get("analisis_triple_angulo")
        
        if not partido or not picks: continue
            
        local = partido.get("local", "")
        visit = partido.get("visitante", "")

        if isinstance(triple_angulo, dict):
            ang_mat = triple_angulo.get("angulo_1_matematico", "")
            ang_ten = triple_angulo.get("angulo_2_tendencia", "")
            ang_ctx = triple_angulo.get("angulo_3_contexto", "")
        else:
            ang_mat = "Análisis IA Pendiente..."
            ang_ten = "Análisis IA Pendiente..."
            ang_ctx = triple_angulo if isinstance(triple_angulo, str) else ""
            
        for pick in picks:
            mercado = pick.get("mercado", "")
            unique_pick_id = f"{fecha}_{local}_{visit}_{mercado}".replace(" ", "_")
            
            # Empaquetamos mercado en el ángulo porque su esquema de DB no tiene columna mercado
            packed_matematico = f"[Mercado: {mercado.upper()}] " + ang_mat
            
            row = {
                "id": unique_pick_id,
                "match_date": fecha,
                "home_team": local,
                "away_team": visit,
                "cuota": pick.get("cuota"),
                "ev_pct": pick.get("ev_pct"),
                "ev_initial": pick.get("ev_pct"), 
                "angulo_matematico": packed_matematico,
                "angulo_tendencia": ang_ten,
                "angulo_contexto": ang_ctx
            }
            upsert_vip_data.append(row)

    upsert_via_rest(url, key, "vip_signals", upsert_vip_data)

    print("==================================================")
    print("  SINCRONIZACIÓN COMPLETADA")
    print("==================================================")

if __name__ == "__main__":
    main()
