"""
purge_supabase.py — Limpia TODOS los registros de daily_board y vip_signals
para permitir una reinserción limpia sin duplicados.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("[FAIL] SUPABASE_URL o SUPABASE_KEY no encontradas en .env")
    exit(1)

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
}

for table in ["daily_board", "vip_signals"]:
    # DELETE all rows where id is not null (i.e., all rows)
    endpoint = f"{url}/rest/v1/{table}?id=not.is.null"
    resp = requests.delete(endpoint, headers=headers)
    if resp.status_code in [200, 204]:
        print(f"[OK] Tabla '{table}' purgada exitosamente.")
    else:
        print(f"[ERROR] No se pudo purgar '{table}' (HTTP {resp.status_code}): {resp.text}")

print("\n[DONE] Supabase limpio. Ejecuta supabase_sync.py para reinsertar datos limpios.")
