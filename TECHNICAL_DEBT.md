# Technical Debt — Podium 360 v1.9

Last updated: 2026-03-16

## Summary
**Total Issues**: 35 | Critical: 3 | High: 9 | Medium: 13 | Low: 18

---

## CRITICAL Issues

### [C1] Service Role Key Exposed in Client-Side HTML
**Agent**: security-expert + architecture-reviewer
**File**: `landing page/dashboard.html:256`
**Code**:
```javascript
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...role":"service_role"...';
```
**Fix**:
1. **IMMEDIATELY** revoke this key in Supabase → Settings → API Keys
2. Generate a new **anon key** (not service_role) for frontend use
3. Implement RLS: `daily_board` and `vip_signals` read-only for anon; `historical_results` service_role only
4. Never use service_role key client-side

**Effort**: Medium
- [x] C1 resolved — `dashboard.html` now uses `__SUPABASE_ANON_KEY__` placeholder; `supabase_sync.py` generates `dashboard_live.html` with key injected from `.env`; `dashboard_live.html` is gitignored.

---

### [C2] All API Keys Committed to .env (Git-Tracked)
**Agent**: security-expert
**File**: `.env:1-8`
**Code**:
```
FOOTBALL_DATA_KEY=471e750b5f064384b80643887006624c
ODDS_API_KEY=d5de5d60630076846e617655b43045c4
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
GOOGLE_API_KEY=AIzaSyDx6T-A2Yqg8PYSis_w7MntKM96s48cVJ0
```
**Fix**:
1. Add `.env` to `.gitignore` now (verify it's not already tracked)
2. Rotate ALL keys immediately — they are publicly visible in git history
3. Use `.env.example` with placeholder values only

**Effort**: Small (URGENT)
- [x] C2 resolved — `.env` was never committed to git (confirmed via `git ls-files`); already in `.gitignore` at line 7. `SUPABASE_ANON_KEY` added to `.env.example`.

---

### [C3] Non-Atomic Purge + Insert in supabase_sync.py
**Agent**: architecture-reviewer
**File**: `supabase_sync.py:340-452`
**Code**:
```python
delete_all_rows(url, key, "daily_board")   # destroys data
delete_all_rows(url, key, "vip_signals")   # destroys data
# ... 100+ lines of processing ...
upsert_via_rest(url, key, "daily_board", ...)  # if fails: empty dashboard
```
**Fix**:
1. Reverse order: insert NEW data first, then delete OLD by timestamp/ID
2. Or wrap in a Supabase transaction
3. Add pre/post row-count validation to detect silent failures

**Effort**: Medium
- [ ] C3 resolved

---

## HIGH Issues

### [H1] XSS via innerHTML with Supabase Data
**Agent**: security-expert
**File**: `landing page/dashboard.html:313-625`
**Code**:
```javascript
${item.home_team} vs ${item.away_team}  // injected via innerHTML
```
**Fix**: Replace with `textContent` or implement `escapeHtml()` wrapper for all user-sourced values.
**Effort**: Medium
- [x] H1 resolved — added `escapeHtml()` function; all Supabase string values (team names, AI text, market names) wrapped before innerHTML injection; onclick uses `escapeHtml(matchKey)`.

---

### [H2] Error Messages Expose API Response Bodies
**Agent**: security-expert
**File**: `supabase_sync.py:129, 186`
**Code**:
```python
print(f"[ERROR] Gemini API falló (HTTP {response.status_code}): {response.text}")
```
**Fix**: Log full response to file only; show sanitized message to stdout.
**Effort**: Small
- [x] H2 resolved — removed `response.text` from all stdout prints in `supabase_sync.py`; only HTTP status code shown.

---

### [H3] Missing Indexes on historical_results
**Agent**: architecture-reviewer
**File**: `migrations/create_historical_results.sql`
**Fix**:
```sql
CREATE INDEX idx_historical_results_status ON historical_results(status_win_loss);
CREATE INDEX idx_historical_results_match_date ON historical_results(match_date DESC);
```
**Effort**: Small
- [x] H3 resolved — `migrations/add_historical_results_indexes.sql` created; run in Supabase SQL Editor. Also adds `mercado` column to `vip_signals` and backfills it.

---

### [H4] mercado Embedded in angulo_matematico via Regex
**Agent**: architecture-reviewer + code-quality
**File**: `supabase_sync.py:434`
**Code**:
```python
packed_matematico = f"[Mercado: {mercado.upper()}] " + ang_mat
```
**Fix**: `ALTER TABLE vip_signals ADD COLUMN IF NOT EXISTS mercado TEXT;` and write it as a real column. Remove regex parsing from result_updater.py.
**Effort**: Small
- [x] H4 resolved — `"mercado": mercado` added to vip row dict in `supabase_sync.py`; regex embed kept for backwards compat; schema migration in H3 migration file.

---

### [H5] partido_data.json Brittle Inter-Module Interface
**Agent**: architecture-reviewer
**File**: `data_fetcher.py` → `model_engine.py`
**Fix**: Add Pydantic validation at model_engine.py entry point; raise on missing critical fields.
**Effort**: Small
- [x] H5 resolved — `_validate_input()` added to `model_engine.py`; raises `ValueError` with clear message if `partido`, `elo`, `partido.local`, or `partido.visitante` are missing.

---

### [H6] N+1 Linear VIP Search in Sync Loop
**Agent**: performance-engineer
**File**: `supabase_sync.py:297-330`
**Code**:
```python
match_vip = next((v for v in vips if normalize_team_name(...) == local ...), None)
```
**Fix**: Build a `vip_dict = {(local, visit): v for v in vips}` before the loop; then `O(1)` lookup.
**Effort**: Small
- [x] H6 resolved — `vip_dict` built before loop in `supabase_sync.py`; lookup is now O(1) instead of O(n×m).

---

### [H7] Redundant Poisson Matrix Multi-Sweep
**Agent**: performance-engineer
**File**: `model_engine.py:186-230`
**Code**: 12 × 49 matrix sweeps for totals, 15 × 49 × 2 for spreads
**Fix**: Single combined sweep; accumulate all lines in one O(n²) pass.
**Effort**: Small
- [x] H7 resolved — `paso_e_extended_market_probs()` reduced from 27 separate matrix sweeps to 1 combined O(n²) pass; all totals and spreads accumulated simultaneously.

---

### [H8] Bare `except:` Clauses — Silent Failures
**Agent**: code-quality-reviewer
**File**: `data_fetcher.py:62, 397` | `tracker_engine.py:21`
**Code**:
```python
try:
    return json.load(f)
except:       # catches KeyboardInterrupt, SystemExit, etc.
    pass
```
**Fix**: Replace with specific exceptions: `except (json.JSONDecodeError, IOError) as e:`
**Effort**: Small
- [x] H8 resolved — 3 bare `except:` replaced: `data_fetcher.py:62` → `(json.JSONDecodeError, OSError)`, `data_fetcher.py:397` → `(ValueError, json.JSONDecodeError)`, `tracker_engine.py:21` → `(json.JSONDecodeError, OSError)`.

---

### [H9] run_model() — 198-Line Monolith
**Agent**: code-quality-reviewer
**File**: `model_engine.py:613-810`
**Fix**: Split into `_prepare_inputs()`, `_compute_probabilities()`, `_filter_ev()`, `_format_output()`.
**Effort**: Large
- [x] H9 resolved — extracted `_validate_input()`, `_impute_elo()`, `_process_market_outputs()` from `run_model()`; function reduced from 198 to ~65 lines.

---

## MEDIUM Issues

### [M1] RLS Policy: service_role key bypass via frontend
**File**: `migrations/create_historical_results.sql` + C1
**Fix**: Fix C1 first; then add explicit `FOR ALL USING (FALSE)` for anon on `historical_results`.
**Effort**: Medium — [ ] resolved

### [M2] Blocking time.sleep(12) in Gemini sync loop (108s for 9 matches)
**File**: `supabase_sync.py:329`
**Fix**: asyncio + semaphore pattern to batch calls while respecting 5 req/min limit.
**Effort**: Medium — [ ] resolved

### [M3] Silent API Failures in data_fetcher.py
**File**: `data_fetcher.py` (API fallbacks)
**Fix**: Add validation stage post-fetch; halt pipeline if critical fields missing.
**Effort**: Small — [ ] resolved

### [M4] Race Condition in tracker_engine.py JSON file writes
**File**: `tracker_engine.py:123-142`
**Fix**: `fcntl.flock()` exclusive lock before read/write of `TRACKING_FILE`.
**Effort**: Small — [ ] resolved

### [M5] missing competition field in archive_finished_matches
**File**: `supabase_sync.py:61-72`
**Fix**: Extract `competition` from `partido.liga` and inject into `archive_row`.
**Effort**: Small — [ ] resolved

### [M6] Persistent disk cache for Football-Data results
**File**: `result_updater.py:74-96`
**Fix**: Save `_fd_cache` to `database/fd_cache_YYYY-MM-DD.json` with 24h TTL.
**Effort**: Small — [ ] resolved

### [M7] Repeated Supabase header construction
**File**: `supabase_sync.py:17-22, 98-102, 115-120`
**Fix**: Extract `_supa_headers(key)` factory function (already done in result_updater.py — replicate pattern).
**Effort**: Small — [ ] resolved

### [M8] Inconsistent error logging (_errors list vs print)
**File**: `data_fetcher.py, supabase_sync.py`
**Fix**: Adopt Python `logging` module uniformly across all modules.
**Effort**: Medium — [ ] resolved

### [M9] Incorrect elapsed time in test_runner.py
**File**: `test_runner.py:67`
**Code**: `t1` captured before model execution; `elapsed` measures only fetch time
**Fix**: Move `t1 = time.time()` to after `p2` subprocess call.
**Effort**: Small — [ ] resolved

### [M10] Missing docstring on generate_triple_angle_gemini() sleep side-effect
**File**: `supabase_sync.py:133`
**Fix**: Add docstring noting `time.sleep(12)` inside, with rationale.
**Effort**: Small — [ ] resolved

### [M11] Duplicate team name normalization in result_updater.py
**File**: `result_updater.py:105-120`
**Fix**: Pre-normalize all match teams before search loop; reuse cached values.
**Effort**: Small — [ ] resolved

### [M12] Gemini API key passed as URL query param (logged by proxies)
**File**: `supabase_sync.py:170`
**Code**: `url = f"...?key={api_key}"`
**Fix**: Use Bearer header if Gemini API supports it.
**Effort**: Small — [ ] resolved

### [M13] Undefined behavior if Gemini always fails (fallback text silently uploaded)
**File**: `supabase_sync.py:319-328`
**Fix**: Queue failed matches for retry; flag them distinctly in upload payload.
**Effort**: Medium — [ ] resolved

---

## LOW Issues

### [L1] Missing Supabase RLS policies for public tables
**File**: `supabase_sync.py` (implicit) — add explicit `SELECT USING (true)` for anon on `daily_board`, `vip_signals`.
**Effort**: Medium — [ ] resolved

### [L2] regex `_mercado_re` compiled inside function on every call
**File**: `supabase_sync.py:49` — move to module-level constant.
**Effort**: Small — [ ] resolved

### [L3] Uncached Poisson matrix (no lru_cache)
**File**: `model_engine.py:134` — add `@lru_cache(maxsize=512)`.
**Effort**: Small — [ ] resolved

### [L4] Google API key in URL param
**File**: `supabase_sync.py:170` — see M12.
**Effort**: Small — [ ] resolved

### [L5] Unused import timedelta in data_fetcher.py:28
**Effort**: Small — [ ] resolved

### [L6] Unused variable c_val in model_engine.py:579
**Effort**: Small — [ ] resolved

### [L7] Unused import `requests` in tracker_engine.py:7
**Effort**: Small — [ ] resolved

### [L8] Mock fetch_match_result() always returns 2-1
**File**: `tracker_engine.py:24-37` — remove or integrate real API call.
**Effort**: Small — [ ] resolved

### [L9] Magic number `time.sleep(12)` — no named constant
**File**: `supabase_sync.py:329` — define `GEMINI_RATE_LIMIT_SEC = 12`.
**Effort**: Small — [ ] resolved

### [L10] Magic number thresholds in consensus logic (35, 26, 52, 70)
**File**: `model_engine.py:468-489` — define named constants.
**Effort**: Small — [ ] resolved

### [L11] HTTP status code magic numbers scattered
**File**: `result_updater.py:46, 57`, `supabase_sync.py:84, 106, 125`
**Fix**: Define `HTTP_OK = 200`, `HTTP_CREATED = 201`, `HTTP_NO_CONTENT = 204`.
**Effort**: Small — [ ] resolved

### [L12] Ambiguous shorthand variable names (hs, as_, m)
**File**: `data_fetcher.py:773, 781, 841` — rename to `home_score`, `away_score`, `match`.
**Effort**: Small — [ ] resolved

### [L13] Rate limit 429 not retried in result_updater.py
**File**: `result_updater.py:85-96` — add exponential backoff on 429.
**Effort**: Small — [ ] resolved

### [L14] No rate limiting for Gemini (sleep is workaround, not enforcement)
**File**: `supabase_sync.py:329` — use `ratelimit` package or token bucket.
**Effort**: Small — [ ] resolved

### [L15] No Gemini API call de-duplication (waste of free-tier quota on reruns)
**File**: `supabase_sync.py:313-328` — check cache before calling.
**Effort**: Small — [ ] resolved

### [L16] historical_results lacks soft-delete flag
**Fix**: Add `deleted_at TIMESTAMPTZ NULL` column for reversible corrections.
**Effort**: Small — [ ] resolved

### [L17] Consensus logic thresholds undocumented
**File**: `model_engine.py:422-489` — document rationale for 35%, 26%, 52% thresholds.
**Effort**: Small — [ ] resolved

### [L18] No CSRF protection (forward-compatibility if writes added to dashboard)
**File**: `landing page/dashboard.html`
**Effort**: Medium — [ ] resolved

---

## Progress Tracking

| Severity | Total | Fixed | Remaining |
|----------|-------|-------|-----------|
| Critical | 3 | 2 | 1 |
| High | 9 | 9 | 0 |
| Medium | 13 | 0 | 13 |
| Low | 18 | 0 | 18 |
| **Total** | **35** | **11** | **24** |
