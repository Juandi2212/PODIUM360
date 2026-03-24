"""
upload_to_supabase.py — Podium 360 SaaS Data Uploader
=====================================================
Lee los datos procesados (Poisson, xG, EV, Triple Ángulo) desde 
daily_report_*.json y los sube (upsert) a las tablas de Supabase:
  - daily_board: partidos de la jornada
  - vip_signals: señales VIP con EV+

NO genera HTML local. El dashboard SaaS lee directamente de Supabase.
"""

import os
import re
import json
import glob
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from utils.naming import normalize_team_name


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def _headers(key, prefer=None):
    """Construye los headers HTTP para la REST API de Supabase."""
    h = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        h["Prefer"] = prefer
    return h


def _extract_event_date(partido, fecha_reporte):
    """Extrae la fecha real del evento (YYYY-MM-DD) desde hora_utc o fecha del reporte."""
    hora_utc = partido.get("hora_utc") if partido else None
    if hora_utc:
        return hora_utc.split("T")[0]
    parts = fecha_reporte.split("_")
    if len(parts) == 3:
        return f"20{parts[2]}-{parts[1]}-{parts[0]}"
    return fecha_reporte


def _build_unique_id(event_date, local, visit):
    """ID determinístico: fecha_local_visitante (normalizado)."""
    norm_local = normalize_team_name(local).replace(" ", "_")
    norm_visit = normalize_team_name(visit).replace(" ", "_")
    return f"{event_date}_{norm_local}_{norm_visit}"


def _compute_status(hora_utc_str):
    """Determina si el partido está activo o finalizado."""
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


def _is_real_match(item):
    """Filtra partidos fantasma (sin fixture ni odds)."""
    partido = item.get("partido", {})
    summary = item.get("match_summary", {})
    return bool(partido.get("hora_utc")) or bool(summary.get("all_markets"))


# ═══════════════════════════════════════════════════════════════════
# SUPABASE OPERATIONS
# ═══════════════════════════════════════════════════════════════════

def _req_with_retry(method, url, headers=None, json_data=None, retries=3, delay=5):
    """Ejecuta una llamada HTTP con reintentos automáticos (robustez)."""
    for i in range(retries):
        try:
            if method == "GET":
                return requests.get(url, headers=headers, timeout=15)
            elif method == "POST":
                return requests.post(url, headers=headers, json=json_data, timeout=25)
            elif method == "DELETE":
                return requests.delete(url, headers=headers, timeout=15)
        except requests.exceptions.RequestException as e:
            if i < retries - 1:
                print(f"  ⚠ Error de red ({e}). Reintentando en {delay}s ({i+1}/{retries})...")
                time.sleep(delay)
            else:
                print(f"  ✗ Falla definitiva tras {retries} intentos: {e}")
                raise


def delete_all_rows(url, key, table_name):
    """Purga todos los registros de una tabla antes de reinsertar."""
    try:
        resp = _req_with_retry(
            "DELETE",
            f"{url}/rest/v1/{table_name}?id=not.is.null",
            headers=_headers(key)
        )
        if resp.status_code in [200, 204]:
            print(f"  ✓ Tabla '{table_name}' purgada")
        else:
            print(f"  ⚠ No se pudo purgar '{table_name}' (HTTP {resp.status_code})")
    except Exception as e:
        print(f"  ✗ Error al purgar '{table_name}': {e}")


def upsert_rows(url, key, table_name, data_list):
    """Upsert de filas en una tabla vía REST API."""
    if not data_list:
        print(f"  – Sin datos para '{table_name}'")
        return
    try:
        resp = _req_with_retry(
            "POST",
            f"{url}/rest/v1/{table_name}",
            headers=_headers(key, prefer="resolution=merge-duplicates"),
            json_data=data_list
        )
        if resp.status_code in [200, 201]:
            print(f"  ✓ {len(data_list)} registros → '{table_name}'")
        else:
            print(f"  ✗ Falló upsert en '{table_name}' (HTTP {resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        print(f"  ✗ Error de conexión: {e}")


def archive_finished_matches(url, key):
    """Archiva picks VIP finalizados en historical_results."""
    hdrs = _headers(key, prefer="return=representation")

    # 1. Leer VIP finalizados
    try:
        resp = _req_with_retry("GET", f"{url}/rest/v1/vip_signals?status=eq.finished&select=*", headers=hdrs)
        if resp.status_code != 200:
            print(f"  ⚠ No se pudo leer vip_signals finalizados (HTTP {resp.status_code})")
            return 0
        finished_rows = resp.json()
    except Exception as e:
        print(f"  ✗ Error al leer vip_signals: {e}")
        return 0

    if not finished_rows:
        return 0

    # 2. IDs ya archivados
    try:
        resp_ex = _req_with_retry("GET", f"{url}/rest/v1/historical_results?select=id", headers=hdrs)
        existing_ids = {row["id"] for row in resp_ex.json()} if resp_ex.status_code == 200 else set()
    except Exception:
        existing_ids = set()

    # 3. Construir payload
    _mercado_re = re.compile(r'\[Mercado:\s*(.+?)\]', re.IGNORECASE)
    to_archive = []

    for row in finished_rows:
        rid = row.get("id", "")
        if rid in existing_ids:
            continue

        mercado = row.get("mercado", "")
        if not mercado:
            match_mercado = _mercado_re.search(row.get("angulo_matematico", ""))
            mercado = match_mercado.group(1) if match_mercado else "unknown"

        to_archive.append({
            "id": rid,
            "match_date": row.get("match_date"),
            "home_team": row.get("home_team"),
            "away_team": row.get("away_team"),
            "mercado": mercado,
            "cuota": row.get("cuota"),
            "ev_pct": row.get("ev_pct") or row.get("ev_initial"),
        })

    if not to_archive:
        return 0

    # 4. Insertar
    try:
        resp_ins = _req_with_retry(
            "POST",
            f"{url}/rest/v1/historical_results",
            headers=hdrs,
            json_data=to_archive
        )
        if resp_ins.status_code in [200, 201]:
            print(f"  ✓ {len(to_archive)} picks archivados en historical_results")
        else:
            print(f"  ⚠ Fallo al archivar (HTTP {resp_ins.status_code})")
    except Exception as e:
        print(f"  ✗ Error al archivar: {e}")
        return 0

    return len(to_archive)


# ═══════════════════════════════════════════════════════════════════
# GEMINI IA — Triple Ángulo
# ═══════════════════════════════════════════════════════════════════

def generate_triple_angle_gemini(partido, picks, summary):
    """Genera análisis Triple Ángulo vía Gemini API."""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None

    local = partido.get("local", "Local")
    visit = partido.get("visitante", "Visitante")
    liga = partido.get("liga", "Competición")
    fecha = partido.get("fecha", "Desconocida")
    picks_str = json.dumps(picks, ensure_ascii=False) if picks else "SIN MERCADOS SECUNDARIOS."
    summary_str = json.dumps(summary, ensure_ascii=False)

    prompt = f"""
Actúa como analista deportivo profesional. Análisis Triple Ángulo para:
{local} vs {visit} ({liga}) el {fecha}.

Datos Técnicos (VIP Picks EV+): {picks_str}
Resumen del Partido: {summary_str}

Responde SOLO con un JSON parseable:
{{
  "angulo_matematico": "...",
  "angulo_tendencia": "...",
  "angulo_contexto": "..."
}}
"""

    try:
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        resp = _req_with_retry(
            "POST",
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json_data=payload,
            retries=4,   # Gemini falla un poco más por ser free tier
            delay=10     # Delay mayor
        )
        if resp.status_code == 200:
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        else:
            print(f"  ⚠ Gemini API error (HTTP {resp.status_code})")
    except Exception as e:
        print(f"  ✗ Error Gemini: {e}")

    return None


# ═══════════════════════════════════════════════════════════════════
# MAIN — Lee daily_report JSON y sube todo a Supabase
# ═══════════════════════════════════════════════════════════════════

def main():
    print()
    print("══════════════════════════════════════════════════")
    print("  PODIUM 360 — UPLOAD TO SUPABASE")
    print("══════════════════════════════════════════════════")

    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("✗ SUPABASE_URL o SUPABASE_KEY no encontradas en .env")
        return

    # ── Localizar el daily_report más reciente ──
    date_str = datetime.now().strftime("%d_%m_%y")
    report_file = os.path.join("database", f"daily_report_{date_str}.json")

    if not os.path.exists(report_file):
        archivos = glob.glob("database/daily_report_*.json")
        if not archivos:
            print("✗ No hay archivos daily_report_*.json en /database")
            return
        report_file = max(archivos, key=os.path.getctime)
        print(f"  ℹ Usando el reporte más reciente: {report_file}")

    print(f"  ℹ Cargando: {report_file}")
    with open(report_file, "r", encoding="utf-8") as f:
        daily_report = json.load(f)

    fecha = daily_report.get("fecha", date_str)
    board = daily_report.get("daily_board", [])
    vips = daily_report.get("vip_signals", [])

    # Filtrar datos corruptos y partidos fantasma
    board = [item for item in board if item.get("partido")]
    vips = [item for item in vips if item.get("partido")]
    board_before = len(board)
    board = [item for item in board if _is_real_match(item)]
    if len(board) < board_before:
        print(f"  ℹ Excluidos {board_before - len(board)} partidos fantasma")

    print(f"  ℹ {len(board)} partidos reales, {len(vips)} señales VIP")

    # ── Generar análisis IA ──
    ai_cache = {}
    vip_dict = {
        (normalize_team_name(v["partido"]["local"]),
         normalize_team_name(v["partido"]["visitante"])): v
        for v in vips if v.get("partido")
    }

    for item in board:
        partido = item.get("partido")
        summary = item.get("match_summary") or {}
        if not partido:
            continue

        local = normalize_team_name(partido.get("local", ""))
        visit = normalize_team_name(partido.get("visitante", ""))
        event_date = _extract_event_date(partido, fecha)
        unique_id = _build_unique_id(event_date, local, visit)

        match_vip = vip_dict.get((local, visit))
        picks = match_vip.get("picks_valiosos", []) if match_vip else []
        triple_angulo = match_vip.get("analisis_triple_angulo") if match_vip else None

        if isinstance(triple_angulo, dict) and "angulo_1_matematico" in triple_angulo:
            ai_cache[unique_id] = {
                "angulo_matematico": triple_angulo.get("angulo_1_matematico", ""),
                "angulo_tendencia": triple_angulo.get("angulo_2_tendencia", ""),
                "angulo_contexto": triple_angulo.get("angulo_3_contexto", ""),
            }
        else:
            print(f"  🤖 Generando IA para {local} vs {visit}...")
            ai_data = generate_triple_angle_gemini(partido, picks, summary)
            if ai_data:
                ai_cache[unique_id] = ai_data
            else:
                ai_cache[unique_id] = {
                    "angulo_matematico": "Análisis IA Pendiente...",
                    "angulo_tendencia": "Análisis IA Pendiente...",
                    "angulo_contexto": triple_angulo if isinstance(triple_angulo, str) else "Esperando Gemini...",
                }
            time.sleep(12)

    # ── ARCHIVE: Mover picks finalizados a historical_results ──
    print("\n── ARCHIVANDO ──")
    archived = archive_finished_matches(url, key)
    if archived > 0:
        print(f"  {archived} pick(s) archivados para ROI tracking")

    # ── PURGE: Limpiar tablas ──
    print("\n── LIMPIANDO TABLAS ──")
    delete_all_rows(url, key, "daily_board")
    delete_all_rows(url, key, "vip_signals")

    # ── UPSERT daily_board ──
    print("\n── SUBIENDO DAILY_BOARD ──")
    upsert_board_data = []
    seen_board_ids = set()

    for item in board:
        partido = item.get("partido")
        summary = item.get("match_summary") or {}
        poisson = summary.get("probabilidades_poisson", {})
        if not partido:
            continue

        local = normalize_team_name(partido.get("local", ""))
        visit = normalize_team_name(partido.get("visitante", ""))
        hora_utc_str = partido.get("hora_utc")
        event_date = _extract_event_date(partido, fecha)
        unique_id = _build_unique_id(event_date, local, visit)

        if unique_id in seen_board_ids:
            continue
        seen_board_ids.add(unique_id)

        mercados_completos = summary.get("all_markets", [])
        if not mercados_completos:
            ai_text = ai_cache.get(unique_id, {})
            mercados_completos = [{
                "mercado": "IA_ANALYSIS",
                "angulo_matematico": ai_text.get("angulo_matematico", ""),
                "angulo_tendencia": ai_text.get("angulo_tendencia", ""),
                "angulo_contexto": ai_text.get("angulo_contexto", ""),
            }]

        # Inject Form & H2H
        forma_data = item.get("forma")
        h2h_data = item.get("h2h")
        diag_global = item.get("diagnostico_global")
        if forma_data or h2h_data or diag_global:
            mercados_completos.append({
                "mercado": "MOMENTUM_DATA",
                "forma": forma_data,
                "h2h": h2h_data,
                "diagnostico_global": diag_global,
            })

        upsert_board_data.append({
            "id": unique_id,
            "match_date": event_date,
            "home_team": local,
            "away_team": visit,
            "poisson_1": poisson.get("local"),
            "poisson_x": poisson.get("empate"),
            "poisson_2": poisson.get("visitante"),
            "xg_diff": summary.get("diferencial_xg_rolling"),
            "estado_mercado": summary.get("estado_mercado", "Desconocido"),
            "mercados_completos": mercados_completos,
            "status": _compute_status(hora_utc_str),
        })

    upsert_rows(url, key, "daily_board", upsert_board_data)

    # ── UPSERT vip_signals ──
    print("\n── SUBIENDO VIP_SIGNALS ──")
    upsert_vip_data = []
    seen_vip_ids = set()

    for item in vips:
        partido = item.get("partido")
        picks = item.get("picks_valiosos", [])
        if not partido or not picks:
            continue

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

            if vip_id in seen_vip_ids:
                continue
            seen_vip_ids.add(vip_id)

            upsert_vip_data.append({
                "id": vip_id,
                "match_date": event_date,
                "home_team": local,
                "away_team": visit,
                "mercado": mercado,
                "cuota": pick.get("cuota"),
                "ev_pct": pick.get("ev_pct"),
                "ev_initial": pick.get("ev_pct"),
                "angulo_matematico": f"[Mercado: {mercado.upper()}] {ang_mat}",
                "angulo_tendencia": ang_ten,
                "angulo_contexto": ang_ctx,
                "status": match_status,
            })

    upsert_rows(url, key, "vip_signals", upsert_vip_data)

    # ── DONE ──
    print()
    print("══════════════════════════════════════════════════")
    print(f"  ✓ UPLOAD COMPLETADO — {len(upsert_board_data)} board + {len(upsert_vip_data)} VIP")
    print("══════════════════════════════════════════════════")
    print()


if __name__ == "__main__":
    main()
