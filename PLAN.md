# Sharon Job Application Bot — Improvement Plan

## Context
- Sharon graduated last year (MSc, INSEEC Paris), has been applying manually for ~1 year and via this bot for 2–3 days.
- 68 applications sent, 51 skipped/failed, 0 callbacks as of April 2, 2026.
- French APS (Autorisation Provisoire de Séjour) post-study visa: grants right to work in France without employer sponsorship; requires sponsorship everywhere else.
- APS valid until ~May 2026; will apply for a 1-year renewal.

---

## What Was Implemented (April 2, 2026)

### Phase 1 — Search Widening (`config/search.py`)
| Change | Before | After |
|---|---|---|
| `search_location` | `"Europe"` (unreliable on LI) | `"France"` |
| `location` filter | `[]` | France + UK + Ireland + 7 EU countries |
| `switch_number` | 3 | 5 (uses more of LI's ~50/day budget) |
| `date_posted` (config base) | Past 24 hours | Past 24 hours *(config unchanged)* |
| **Pass 1 date at runtime** | Past 24 hours | **Past 24 hours** (< 10 applicants priority pass) |
| **Pass 2 date at runtime** | Past 24 hours | **Past week** (broader second sweep) |
| `experience_level` | Associate, Mid-Senior | Entry level, Associate, Mid-Senior |
| `current_experience` | 4 | **Deferred — kept as-is** |
| `min_skills_match_percentage` | 20 | 0 (LI's match is unreliable) |
| `title_bad_words` | includes "Consultant" | Removed "Consultant" (blocked Finance/Billing Consultant) |

New search terms added (12 total):
- `Finance Assistant`, `Accounts Payable Clerk`, `Billing Coordinator`, `Finance Coordinator`
- `Junior Financial Analyst`, `Finance Associate`, `Treasury Analyst`, `Purchase Ledger Clerk`, `Credit Controller`
- French: `Analyste financier`, `Comptable`, `Analyste facturation`

### Phase 2 — Dynamic Visa Logic (`runAiBot.py`, `config/questions.py`)
- Replaced static `require_visa = "No"` with `no_sponsorship_countries = ["france"]` + `require_visa_default = "Yes"`.
- Added `get_visa_answer(work_location)` in `runAiBot.py` — returns `"No"` for France jobs, `"Yes"` for all others.
- Added `get_work_authorization_answer(label, work_location)` replacing the old EU/non-EU heuristic — now uses the same `no_sponsorship_countries` list, so Ireland (EU but needs sponsorship) is handled correctly.
- `answer_common_questions` now accepts `work_location` and uses these helpers.

### Phase 3 — Dynamic Salary Logic (`runAiBot.py`, `config/questions.py`)
- Added `salary_by_country` map in `config/questions.py`:
  - France 38k, UK 30k, Ireland 38k, Germany 42k, Netherlands 40k, Belgium 38k, Luxembourg 45k, Spain 28k, Italy 28k, Portugal 22k
- Added `get_desired_salary_values(work_location)` in `runAiBot.py` — computes salary/monthly/lakhs variants per job. Zero extra AI calls.
- Salary section in `answer_questions` now calls this function instead of module-level static variables.

### Phase 4 — Candidate Profile Corrections (`config/questions.py`)
- `user_information_all` visa line corrected from "Fully authorised to work across the EU without sponsorship" → "Authorised to work in France without employer sponsorship. Requires employer visa sponsorship for positions outside France."
- `motivation_answer` and `cover_letter` updated to reflect APS status accurately.
- `linkedin_headline` updated to include "Open to Entry, Associate & EU Finance Roles".

### Phase 5 — Browser Stability
- `click_gap` raised from 2 → 3 (`config/settings.py`).
- **Manual step still required**: delete `C:\temp\sharon-bot-profile` — April 2 run got 0 applications due to session crashes on the dedicated Chrome profile. Bot will recreate it cleanly on next run.

### Phase 6 — `resume_map` Additions (`config/questions.py`)
- Added entries for all new search terms, mapped to the closest existing resume PDF.
- Fixed indentation inconsistency and reordered keys so specific keys (e.g. `"Billing Coordinator"`) always appear before broader ones (e.g. `"Billing"`).

---

## Bugs Fixed (`runAiBot.py`)

| Bug | Severity | Location |
|---|---|---|
| `return` inside `finally` in `get_job_description` silently suppressed all exceptions | High | `get_job_description()` |
| `extract_years_of_experience` crashed with `ValueError` when all regex hits were > 12 | High | `extract_years_of_experience()` |
| Bare `return` (not `return pass_total`) in security-challenge branch lost the run count | Medium | `apply_to_jobs()` inner loop |
| Date cycling in non-stop mode could jump directly to "Past 24 hours" instead of stepping | Medium | `main()` while loop |
| Unused dead variable `total_daily_cap` in `run()` | Minor | `run()` |

---

## Deferred Items
- **`current_experience = -1`** — kept at 4 for now. Set to -1 to stop auto-skipping "Required experience is high" when ready.

---

## Verification Checklist (run with `pause_before_submit = True`)
1. France jobs → visa sponsorship answer = "No"; UK/Ireland jobs → "Yes"
2. UK jobs → salary auto-fills ~30000; France jobs → ~38000
3. Run logs show: `Pass 1 date filter: Past 24 hours; Pass 2 date filter: Past week`
4. Applied CSV grows faster (target: 40–50/day with expanded search pool)
5. Chrome launches cleanly after profile folder reset
6. No `return in finally` warnings from `python -m py_compile runAiBot.py`

---

## Beyond-Bot Recommendations (no code required)
- Enable **"Open to Work"** on LinkedIn with all target countries and job titles
- Use **Welcome to the Jungle** (large in France), Indeed France, Michael Page, Hays
- **Direct message hiring managers** after the bot applies — increases response rate significantly
- Add all relevant finance skills to LinkedIn profile (affects recruiter search ranking + LI skills match %)
- Consider French-language manual applications for roles where JD is entirely in French
