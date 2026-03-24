import sys
import time
import subprocess
from datetime import datetime


def ts():
    return datetime.now().strftime("%H:%M:%S")


def run_step(script, step_num, total_steps):
    print(f"\n[{ts()}] -- PASO {step_num}/{total_steps}: {script} --------------------------")
    t0 = time.time()
    result = subprocess.run(["python", script])
    elapsed = round(time.time() - t0, 1)
    if result.returncode != 0:
        print(f"\n[{ts()}] [FALLO] {script} (exit code {result.returncode})")
        print(f"         Ejecucion detenida en el Paso {step_num}/{total_steps}.")
        sys.exit(result.returncode)
    return elapsed


def main():
    print("=" * 70)
    print(" VALIOR - Pipeline matutino")
    print(f" Inicio: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 70)

    steps = [
        "test_runner.py",
        "supabase_sync.py",
    ]

    times = []
    total_start = time.time()

    for i, script in enumerate(steps, start=1):
        elapsed = run_step(script, i, len(steps))
        times.append((script, elapsed))

    total_elapsed = round(time.time() - total_start, 1)

    print("\n" + "=" * 70)
    print(f" RESUMEN - Finalizado a las {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 70)
    for script, t in times:
        print(f"  {script:<22} {t:>7.1f}s")
    print(f"  {'TOTAL':<22} {total_elapsed:>7.1f}s")
    print("=" * 70)


if __name__ == "__main__":
    main()
