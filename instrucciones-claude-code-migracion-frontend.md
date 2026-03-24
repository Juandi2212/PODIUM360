# INSTRUCCIONES PARA CLAUDE CODE — Migración Frontend VALIOR
# Fecha: 23 de marzo de 2026
# Contexto: Reemplazar el frontend HTML estático (carpeta web/) por una app React/Vite/Tailwind v4
# ⚠️ LEER TODO ANTES DE EJECUTAR CUALQUIER COSA. EJECUTAR FASE POR FASE, ESPERANDO MI CONFIRMACIÓN.

---

## CONTEXTO QUE DEBES ENTENDER

El proyecto VALIOR tiene esta estructura actual:
- Carpeta `web/` → Frontend actual: `index.html` (landing), `auth.html` (login), `dashboard.html` (dashboard SaaS), `js/config.js`
- Deploy en Vercel → `valior.vercel.app`
- `vercel.json` en la raíz → configuración de headers de seguridad
- Pipeline Python → model_engine.py, data_fetcher.py, test_runner.py, supabase_sync.py, result_updater.py, master_morning.py, master_night.py
- Supabase → Auth + tablas daily_board, vip_signals, historical_results
- CLAUDE.md → documento maestro (NO MODIFICAR excepto donde se indica en Fase 5)

Lo que vamos a hacer: **Reemplazar SOLO la landing page** (`web/index.html`) con una app React/Vite/Tailwind v4 que está en el archivo `valior-landing.zip`. El `auth.html` y `dashboard.html` siguen funcionando tal cual — NO SE TOCAN.

---

## FASE 0: BACKUP OBLIGATORIO

**No avances a la Fase 1 sin completar TODOS estos pasos y mostrarme los resultados.**

### Paso 1 — Commit de backup con Git
```bash
cd C:\Users\juand\Podium360
git add -A
git commit -m "BACKUP: Estado pre-migración landing React/Vite - 23 mar 2026"
git tag backup-pre-react-landing
```

### Paso 2 — Copia física en el escritorio
```bash
xcopy /E /I /H "C:\Users\juand\Podium360" "C:\Users\juand\Desktop\VALIOR-BACKUP-23MAR"
```
(Si la ruta del proyecto es diferente, ajústala — pero SIEMPRE hacer la copia física)

### Paso 3 — CONFIRMARME antes de continuar
Muéstrame:
- El hash del commit de backup
- Que el tag `backup-pre-react-landing` existe (`git tag -l`)
- Que la copia física se creó correctamente

### Cómo revertir si algo sale mal (en cualquier momento):
```bash
git reset --hard backup-pre-react-landing
```
Esto deshace TODO. La copia física en el escritorio es un seguro adicional.

---

## FASE 1: CREAR LA ESTRUCTURA DEL FRONTEND REACT

### Estrategia: carpeta `frontend/` separada

NO tocar la carpeta `web/`. Crear una carpeta `frontend/` nueva al mismo nivel.

Estructura objetivo:
```
Podium360/                         (o como se llame tu raíz)
├── frontend/                      ← NUEVO
│   ├── src/
│   │   ├── App.tsx               ← Landing page completa
│   │   ├── main.tsx              ← Entry point React
│   │   └── index.css             ← Tailwind v4 + fonts
│   ├── public/
│   │   └── favicon.svg           ← Favicon VALIOR
│   ├── index.html                ← HTML entry point
│   ├── package.json              ← Dependencias React
│   ├── vite.config.ts            ← Config Vite + Tailwind plugin
│   └── tsconfig.json             ← Config TypeScript
├── web/                           ← INTACTO — NO TOCAR
│   ├── index.html                ← Landing actual (se deja como fallback)
│   ├── auth.html                 ← Login — SIGUE FUNCIONANDO
│   ├── dashboard.html            ← Dashboard SaaS — SIGUE FUNCIONANDO
│   └── js/config.js              ← Config Supabase — INTACTO
├── model_engine.py                ← INTACTO — NO TOCAR
├── data_fetcher.py                ← INTACTO — NO TOCAR
├── supabase_sync.py               ← INTACTO — NO TOCAR
├── result_updater.py              ← INTACTO — NO TOCAR
├── test_runner.py                 ← INTACTO — NO TOCAR
├── master_morning.py              ← INTACTO — NO TOCAR
├── master_night.py                ← INTACTO — NO TOCAR
├── vercel.json                    ← SE MODIFICA (Fase 3)
├── CLAUDE.md                      ← SE AGREGA SECCIÓN AL FINAL (Fase 5)
└── ...
```

### Acción:
1. Descomprimir `valior-landing.zip` en la carpeta `frontend/`
2. Verificar que los archivos quedaron en `frontend/src/App.tsx`, `frontend/package.json`, etc.

---

## FASE 2: INSTALAR Y VERIFICAR BUILD

```bash
cd frontend
npm install --legacy-peer-deps
```

⚠️ **OBLIGATORIO:** El flag `--legacy-peer-deps` es necesario porque lucide-react@0.383 declara peer dependency de React 16/17/18, pero funciona perfecto con React 19. Sin este flag, npm rechaza la instalación.

### Verificar compilación:
```bash
npx tsc --noEmit
npx vite build
```

**Criterio de éxito:**
- `tsc --noEmit` → 0 errores
- `vite build` → genera carpeta `dist/` sin errores
- Confirmarme ambos resultados antes de continuar

### Test visual local (opcional pero recomendado):
```bash
npx vite preview
```
Abrir en el navegador y verificar que la landing se ve idéntica a la imagen de referencia.

---

## FASE 3: CONFIGURAR VERCEL

### Modificar `vercel.json`

El `vercel.json` actual tiene headers de seguridad. HAY QUE PRESERVARLOS y agregar la config del build de React.

**IMPORTANTE:** Antes de modificar, mostrarme el contenido actual de `vercel.json` para que yo confirme los cambios.

El `vercel.json` resultante debe:
1. Mantener TODOS los headers de seguridad existentes (Cache-Control, X-Frame-Options, X-Content-Type-Options)
2. Agregar la configuración de build para el frontend React
3. Mantener las rutas de `auth.html` y `dashboard.html` funcionales

### Problema a resolver: auth.html y dashboard.html

Estos archivos viven en `web/` y necesitan seguir accesibles en Vercel. La solución es:

**Copiar `web/auth.html`, `web/dashboard.html` y `web/js/` dentro de `frontend/public/`.**

Los archivos en `public/` se sirven tal cual por Vite sin procesamiento. Así:
- `frontend/public/auth.html` → accesible en `valior.vercel.app/auth.html`
- `frontend/public/dashboard.html` → accesible en `valior.vercel.app/dashboard.html`
- `frontend/public/js/config.js` → accesible para los scripts de auth y dashboard

**IMPORTANTE:** NO mover — COPIAR. La carpeta `web/` original queda intacta como fallback.

```bash
cp web/auth.html frontend/public/auth.html
cp web/dashboard.html frontend/public/dashboard.html
cp -r web/js frontend/public/js
```

### vercel.json final (ejemplo — adaptar según headers actuales):
```json
{
  "buildCommand": "cd frontend && npm install --legacy-peer-deps && npm run build",
  "outputDirectory": "frontend/dist",
  "framework": "vite",
  "installCommand": "echo skip",
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "... (mantener el valor actual)" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-Content-Type-Options", "value": "nosniff" }
      ]
    }
  ]
}
```

**Muéstrame el vercel.json propuesto ANTES de escribirlo. Yo confirmo.**

---

## FASE 4: VERIFICACIÓN FINAL (antes de hacer push)

Checklist obligatorio — confirmarme CADA punto:

1. [ ] `cd frontend && npx vite build` → compila sin errores
2. [ ] `npx vite preview` → la landing se ve correcta en localhost
3. [ ] `frontend/public/auth.html` existe y tiene el contenido correcto
4. [ ] `frontend/public/dashboard.html` existe y tiene el contenido correcto
5. [ ] `frontend/public/js/config.js` existe y tiene las credenciales de Supabase
6. [ ] NINGÚN archivo .py fue modificado: `git diff --name-only` no muestra archivos Python
7. [ ] La carpeta `web/` NO fue eliminada ni modificada: `git diff --name-only web/` no muestra cambios
8. [ ] El commit de backup sigue accesible: `git log --oneline | head -5`

### Commit final:
```bash
git add -A
git commit -m "feat: nueva landing React/Vite/Tailwind v4 en frontend/ — web/ intacto como fallback"
```

### Deploy:
```bash
git push origin main
```

### Verificación post-deploy en valior.vercel.app:
- [ ] La landing nueva se muestra correctamente (React con animaciones)
- [ ] `valior.vercel.app/auth.html` funciona (login/registro con Supabase Auth)
- [ ] `valior.vercel.app/dashboard.html` funciona (requiere sesión, muestra daily_board y vip_signals)

---

## FASE 5: ACTUALIZAR CLAUDE.md

### 5A — Agregar al FINAL de CLAUDE.md (después de "Reglas de Desarrollo"):

```markdown

---

## Frontend React — Landing Page (23-Mar-2026)

La landing page de VALIOR (`web/index.html`) fue reemplazada por una app React/Vite/Tailwind v4 ubicada en `frontend/`.

### Stack frontend (landing):
- React 19 + TypeScript
- Vite 6 (bundler)
- Tailwind CSS v4 (via @tailwindcss/vite plugin)
- Motion (Framer Motion) para animaciones
- Recharts para gráfico de ROI
- Lucide React para iconos

### Ubicación: `frontend/`

### Instalación: `npm install --legacy-peer-deps` (obligatorio por peer deps de lucide-react)

### Build: `npm run build` → genera `frontend/dist/`

### Convivencia con web/:
- `web/auth.html` y `web/dashboard.html` se copian a `frontend/public/` para que Vercel los sirva
- `web/` se mantiene como fallback pero ya no es servido directamente por Vercel
- Si se modifica auth.html o dashboard.html en web/, hay que re-copiar a frontend/public/

### Regla Crítica #6:
No modificar `frontend/src/App.tsx` sin confirmación explícita del usuario. Este archivo contiene toda la landing page con diseño aprobado manualmente.
```

### 5B — Actualizar la línea de Stack Técnico:

Cambiar:
```
Frontend         → HTML5, Vanilla JS, Tailwind CSS (Carpeta `web/`) (operativo ✅)
```
Por:
```
Frontend Landing → React 19, Vite 6, Tailwind CSS v4 (Carpeta `frontend/`) (operativo ✅)
Frontend Auth/Dash → HTML5, Vanilla JS, Tailwind CSS (Carpeta `web/` → copiado a `frontend/public/`) (operativo ✅)
```

### 5C — Agregar en Hoja de Ruta, Fase 1:
```
- [x] Landing page migrada a React/Vite/Tailwind v4 (23-Mar-2026)
```

---

## REGLAS ABSOLUTAS DURANTE TODA LA EJECUCIÓN

1. **NUNCA modificar archivos .py** — model_engine.py, data_fetcher.py, supabase_sync.py, result_updater.py, test_runner.py, master_morning.py, master_night.py, utils/naming.py son INTOCABLES.
2. **NUNCA eliminar la carpeta web/** — es el fallback operativo y la fuente de verdad de auth + dashboard.
3. **NUNCA modificar tablas de Supabase** — esta migración es puramente de frontend visual, no de backend.
4. **NUNCA modificar js/config.js ni las credenciales de Supabase** — deben seguir funcionando en auth.html y dashboard.html.
5. **NUNCA modificar CLAUDE.md excepto** las tres adiciones específicas de la Fase 5 (sección nueva al final, línea de stack, línea de roadmap).
6. **SIEMPRE mostrarme el estado** antes de cada acción destructiva o de modificación.
7. **SIEMPRE esperar mi confirmación** entre cada fase.

---

## SI ALGO SALE MAL

### Revertir todo:
```bash
git reset --hard backup-pre-react-landing
git push origin main --force
```

### Si Git se corrompió:
Usar la copia física del escritorio:
```
C:\Users\juand\Desktop\VALIOR-BACKUP-23MAR
```

### Si solo Vercel se rompió pero el código está bien:
En el dashboard de Vercel → Deployments → seleccionar el deployment anterior → "Redeploy"
