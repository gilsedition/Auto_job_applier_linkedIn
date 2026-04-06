'''
Author:     Sai Vignesh Golla
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Copyright (C) 2024 Sai Vignesh Golla

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

Support me: https://github.com/sponsors/GodsScion

version:    26.01.20.5.08
'''


# Imports
import os
import csv
import re
import unicodedata
import pyautogui
from collections import deque

# Set CSV field size limit to prevent field size errors
csv.field_size_limit(1000000)  # Set to 1MB instead of default 131KB

from random import shuffle, randint, uniform
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.select import Select
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, NoSuchWindowException, ElementNotInteractableException, WebDriverException

from config.personals import *
from config.questions import *
from config.search import *
from config.secrets import use_AI, username, password, ai_provider
from config.settings import *

from modules.open_chrome import *
from modules.helpers import *
from modules.clickers_and_finders import *
from modules.skills_extractor import count_extracted_skills, empty_skills_response, extract_skills_from_job_description
from modules.validator import validate_config

if use_AI:
    from modules.ai.openaiConnections import ai_create_openai_client, ai_answer_question, ai_close_openai_client
    from modules.ai.deepseekConnections import deepseek_create_client, deepseek_answer_question
    if ai_provider == "gemini":
        from modules.ai.geminiConnections import gemini_create_client, gemini_answer_question

from typing import Any, Literal


pyautogui.FAILSAFE = False
# if use_resume_generator:    from resume_generator import is_logged_in_GPT, login_GPT, open_resume_chat, create_custom_resume


#< Global Variables and logics

if run_in_background == True:
    pause_at_failed_question = False
    pause_before_submit = False
    run_non_stop = False

first_name = first_name.strip()
middle_name = middle_name.strip()
last_name = last_name.strip()
full_name = first_name + " " + middle_name + " " + last_name if middle_name else first_name + " " + last_name

useNewResume = True
randomly_answered_questions = set()

tabs_count = 1
easy_applied_count = 0
external_jobs_count = 0
failed_count = 0
skip_count = 0
dailyEasyApplyLimitReached = False

re_experience = re.compile(
    r"[(]?\s*\+?\s*(\d{1,2})\s*[)]?\s*(?:(?:-|–|to|a|à)\s*\d{1,2}\+?\s*)?(?:\+?\s*)?(?:year|years|yr|yrs|an|ans|annee|annees)\b",
    re.IGNORECASE,
)

current_ctc_lakhs = str(round(current_ctc / 100000, 2))
current_ctc_monthly = str(round(current_ctc/12, 2))
current_ctc = str(current_ctc)

notice_period_months = str(notice_period//30)
notice_period_weeks = str(notice_period//7)
notice_period = str(notice_period)

aiClient = None
##> ------ Dheeraj Deshwal : dheeraj9811 Email:dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Feature ------
about_company_for_ai = None # TODO extract about company for AI
##<


def _normalize_location_hint(value: str | None) -> str:
    return normalize_select_text(value or "")


def _match_location_value(work_location: str, mapping: dict[str, str | int], default_value: str | int) -> str | int:
    normalized_location = _normalize_location_hint(work_location)
    for country, mapped_value in mapping.items():
        if country in normalized_location:
            return mapped_value
    return default_value


def location_requires_sponsorship(work_location: str) -> bool:
    normalized_location = _normalize_location_hint(work_location)
    if not normalized_location:
        return require_visa_default == "Yes"
    for country in no_sponsorship_countries:
        if country in normalized_location:
            return False
    return True


def get_visa_answer(work_location: str) -> str:
    return "Yes" if location_requires_sponsorship(work_location) else "No"


def get_work_authorization_answer(label: str, work_location: str) -> str:
    normalized_label = normalize_select_text(label)
    named_countries = set(no_sponsorship_countries) | set(salary_by_country.keys())
    for country in sorted(named_countries, key=len, reverse=True):
        if country in normalized_label:
            return "No" if country not in no_sponsorship_countries else "Yes"

    if any(term in normalized_label for term in ['european union', 'europe', 'schengen', 'eea', ' eu ', ' eu?', ' eu.', 'eu/']):
        return "No" if location_requires_sponsorship(work_location) else "Yes"

    return "No" if location_requires_sponsorship(work_location) else "Yes"


def get_desired_salary_values(work_location: str) -> tuple[str, str, str]:
    salary_value = int(_match_location_value(work_location, salary_by_country, desired_salary_default))
    desired_salary_value = str(salary_value)
    desired_salary_monthly = str(round(salary_value / 12, 2))
    desired_salary_lakhs = str(round(salary_value / 100000, 2))
    return desired_salary_value, desired_salary_monthly, desired_salary_lakhs

SELECT_PLACEHOLDER_OPTIONS = {
    "select an option",
    "selecteer een optie",
    "seleccione una opcion",
    "selecciona una opcion",
    "seleciona uma opcao",
    "selecione uma opcao",
    "selectionnez une option",
    "seleziona un opzione",
    "wahlen sie eine option",
}
YES_OPTION_WORDS = {"yes", "si", "oui", "ja", "sim"}
YES_OPTION_PHRASES = ("agree", "i do", "i have")
NO_OPTION_WORDS = {"no", "non", "nein", "nao"}
NO_OPTION_PHRASES = ("disagree", "i do not", "i don't")
DECLINE_OPTION_PHRASES = (
    "decline",
    "prefer not",
    "do not wish",
    "don't wish",
    "not wish",
    "do not want",
    "don't want",
    "not want",
)
NONE_LEVEL_WORDS = {"none", "ninguno", "ninguna", "aucun", "aucune", "nessuno", "nessuna", "keine"}
PROFESSIONAL_LEVEL_WORDS = {"professional", "profesional", "professionnel", "profissional"}
CONVERSATIONAL_LEVEL_WORDS = {"conversational", "conversation", "conversacion", "intermediate", "intermedio", "basic", "basico"}
NATIVE_LEVEL_TOKEN_SETS = (
    {"native", "bilingual"},
    {"nativo", "bilingue"},
    {"materna", "bilingue"},
)
PROFICIENCY_LABEL_MARKERS = (
    "proficiency",
    "proficiencia",
    "fluency",
    "level",
    "nivel",
    "language",
    "idioma",
    "langue",
    "lingua",
)
ENGLISH_LANGUAGE_MARKERS = {"english", "ingles", "anglais", "inglese", "inglesa"}
FRENCH_LANGUAGE_MARKERS = {"french", "francais", "frances", "francese"}
KNOWN_LANGUAGE_MARKERS = ENGLISH_LANGUAGE_MARKERS | FRENCH_LANGUAGE_MARKERS | {
    "polish",
    "polaco",
    "polonais",
    "spanish",
    "espanol",
    "espanola",
    "espanol",
    "german",
    "alemao",
    "aleman",
    "allemand",
    "dutch",
    "neerlandes",
    "holandes",
    "italian",
    "italiano",
    "portuguese",
    "portugues",
    "romanian",
    "romano",
    "flemish",
    "arabic",
    "arabe",
}
EDUCATION_LEVEL_ALIASES = {
    "doctorate": (
        "doctor of philosophy",
        "phd",
        "ph.d",
        "doctorate",
        "doctoral",
        "dphil",
        "doctor",
    ),
    "master": (
        "master",
        "masters",
        "msc",
        "m.sc",
        "ma",
        "m.a",
        "mba",
        "mcom",
        "m.com",
    ),
    "bachelor": (
        "bachelor",
        "bachelors",
        "bsc",
        "b.sc",
        "ba",
        "b.a",
        "bcom",
        "b.com",
    ),
}
EMAIL_LABEL_MARKERS = {
    "email",
    "e mail",
    "e-mail",
    "correo",
    "courriel",
    "mail",
    "adresse",
}
CRITICAL_QUESTION_MARKERS = {
    "authorized to work",
    "allowed to work",
    "right to work",
    "permission to work",
    "eligible to work",
    "employment eligibility",
    "legally authorized",
    "legally entitled",
    "residency",
    "residence",
    "citizenship",
    "sponsorship",
    "visa",
    "work permit",
    "clearance",
    "criminal",
    "conviction",
    "background check",
    "disability",
    "veteran",
    "protected veteran",
    "equal opportunity",
    "degree",
    "qualification",
}
DAILY_LIMIT_MESSAGE_MARKERS = (
    "limit daily submissions",
    "save this job and apply tomorrow",
    "daily application limit",
    "exceeded the daily application limit",
    "application limit",
    "apply tomorrow",
)
DEMOGRAPHIC_CHECKBOX_MARKERS = {
    "gender",
    "sexual orientation",
    "orientation",
    "ethnicity",
    "race",
    "veteran",
    "disability",
    "lgbt",
}
CONSENT_CHECKBOX_MARKERS = {
    "confirm",
    "certify",
    "agree",
    "acknowledge",
    "authorization",
    "authorize",
    "consent",
    "terms",
    "privacy",
    "attest",
    "true and complete",
}
MODAL_ACTION_KEYWORDS = {
    "next": ["next", "continue", "continuar", "suivant", "volgende", "weiter", "prossimo", "seguinte"],
    "review": ["review", "revisar", "verificar", "verifier", "controleer", "uberprufen", "rivedi"],
    "submit": ["submit", "send application", "apply", "postuler", "bewerben", "invia", "enviar", "solliciteren"],
    "done": ["done", "close", "finish", "ok", "fechar", "terminer", "schliessen", "chiudi", "cerrar"],
}


def human_type(element: WebElement, text: str, min_delay: float = 0.03, max_delay: float = 0.12) -> None:
    '''Type one character at a time with short random jitter.'''
    for ch in text:
        element.send_keys(ch)
        sleep(uniform(min_delay, max_delay))


def normalize_select_text(text: str) -> str:
    normalized_text = unicodedata.normalize("NFKD", text or "")
    normalized_text = normalized_text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", normalized_text).strip().casefold()


def get_filter_option_aliases(option_text: str) -> list[str]:
    '''Return localized/common aliases for LinkedIn filter options.'''
    normalized_option = normalize_select_text(option_text)
    alias_map = {
        "most recent": ["Most recent", "Most recent first", "Les plus recentes", "Plus recentes"],
        "most relevant": ["Most relevant", "Pertinence", "Les plus pertinentes"],
        "any time": ["Any time", "A tout moment", "Toute date"],
        "past month": ["Past month", "Last month", "Mois dernier", "Au cours du dernier mois"],
        "past week": ["Past week", "Last week", "Semaine derniere", "Au cours de la derniere semaine"],
        "past 24 hours": ["Past 24 hours", "Last 24 hours", "Dernieres 24 heures", "Au cours des dernieres 24 heures"],
    }
    aliases = [option_text]
    aliases.extend(alias_map.get(normalized_option, []))
    return [alias for alias in aliases if alias]


def _text_matches_filter_alias(text_value: str, aliases: list[str]) -> bool:
    normalized_text = normalize_select_text(text_value)
    if not normalized_text:
        return False
    for alias in aliases:
        normalized_alias = normalize_select_text(alias)
        if not normalized_alias:
            continue
        if normalized_alias in normalized_text or normalized_text in normalized_alias:
            return True
    return False


def click_filter_option_with_fallback(option_text: str) -> bool:
    '''Click filter option by exact text first, then fuzzy matching in current filter modal.'''
    if not option_text:
        return True

    aliases = get_filter_option_aliases(option_text)
    for alias in aliases:
        if wait_span_click(driver, alias):
            return True

    candidate_xpaths = [
        "//label[.//input]",
        "//button",
        "//span",
    ]
    for xpath in candidate_xpaths:
        try:
            candidates = driver.find_elements(By.XPATH, xpath)
        except Exception:
            candidates = []
        for candidate in candidates:
            try:
                if not candidate.is_displayed():
                    continue
                text_blob = " ".join(
                    [
                        candidate.text or "",
                        candidate.get_attribute("aria-label") or "",
                        candidate.get_attribute("title") or "",
                    ]
                ).strip()
                if not _text_matches_filter_alias(text_blob, aliases):
                    continue
                scroll_to_view(driver, candidate)
                candidate.click()
                buffer(click_gap)
                return True
            except Exception:
                continue
    return False


def click_show_results_button() -> bool:
    '''Click LinkedIn filter modal confirm button across locale/UI variants.'''
    xpaths = [
        '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "apply current filters to show")]',
        '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "show results")]',
        '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "see results")]',
        '//button[contains(translate(@aria-label, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "afficher")]',
        '//button[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "show results")]',
        '//button[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "see results")]',
        '//button[contains(translate(normalize-space(.), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "afficher les resultats")]',
    ]

    for xp in xpaths:
        try:
            for button in driver.find_elements(By.XPATH, xp):
                if not button.is_displayed() or not button.is_enabled():
                    continue
                scroll_to_view(driver, button)
                button.click()
                buffer(click_gap)
                return True
        except Exception:
            continue

    # Last fallback: pick primary action button in visible modal footer.
    try:
        modal_buttons = driver.find_elements(By.XPATH, '//div[@role="dialog"]//button[contains(@class,"artdeco-button--primary")]')
        for button in modal_buttons:
            if button.is_displayed() and button.is_enabled():
                scroll_to_view(driver, button)
                button.click()
                buffer(click_gap)
                return True
    except Exception:
        pass

    return False


def should_auto_check_checkbox(label_text: str, option_text: str) -> bool:
    normalized = normalize_select_text(f"{label_text} {option_text}")
    if any(marker in normalized for marker in DEMOGRAPHIC_CHECKBOX_MARKERS):
        return False
    return any(marker in normalized for marker in CONSENT_CHECKBOX_MARKERS)


_REGION_QUESTION_MARKERS = {
    "region", "regions", "région", "régions", "quelle",
    "prefecture", "prefecture",
}


def matches_preferred_region(label_text: str, option_text: str) -> bool:
    '''Return True when this checkbox option is in the user-configured preferred_regions list.
    Detects region questions by matching label markers, then compares the option text.
    '''
    label_norm = normalize_select_text(label_text)
    if not any(marker in label_norm for marker in _REGION_QUESTION_MARKERS):
        return False
    option_norm = normalize_select_text(option_text)
    for pref in globals().get("preferred_regions", []):
        pref_norm = normalize_select_text(str(pref))
        if pref_norm and (pref_norm in option_norm or option_norm in pref_norm):
            return True
    return False


def detect_daily_easy_apply_limit(context: str = "") -> bool:
    global dailyEasyApplyLimitReached
    if dailyEasyApplyLimitReached:
        return True

    alert_xpaths = [
        "//div[contains(@class,'artdeco-inline-feedback--error') and @role='alert']//span[contains(@class,'artdeco-inline-feedback__message')]",
        "//div[contains(@class,'artdeco-inline-feedback') and (@role='alert' or contains(@class,'artdeco-inline-feedback--error'))]",
        "//div[contains(@class,'artdeco-inline-feedback__message') and ancestor::div[contains(@class,'artdeco-inline-feedback')]]",
        "//div[@role='dialog']",
        "//div[contains(@class,'artdeco-modal')]",
        "//section[contains(@class,'jobs-easy-apply-content')]",
        "//body",
    ]
    try:
        messages: list[str] = []
        for xp in alert_xpaths:
            for element in driver.find_elements(By.XPATH, xp):
                try:
                    text = (
                        (element.get_attribute("textContent") or "")
                        or (element.text or "")
                    ).strip()
                    if text:
                        # Keep scanning light while preserving full banner phrases.
                        messages.append(text[:6000])
                except Exception:
                    continue

        for message in messages:
            normalized = normalize_select_text(message)
            if any(marker in normalized for marker in DAILY_LIMIT_MESSAGE_MARKERS):
                dailyEasyApplyLimitReached = True
                prefix = f"[{context}] " if context else ""
                print_lg(f"{prefix}LinkedIn Easy Apply daily limit detected. Banner: \"{message}\"")
                return True
    except Exception:
        pass
    return False


def get_select_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", normalize_select_text(text)))


def is_select_placeholder(option_text: str) -> bool:
    normalized_option = normalize_select_text(option_text)
    if not normalized_option:
        return True
    return normalized_option in SELECT_PLACEHOLDER_OPTIONS


def classify_select_option(option_text: str) -> str | None:
    normalized_option = normalize_select_text(option_text)
    if not normalized_option or is_select_placeholder(option_text):
        return "placeholder"

    option_tokens = get_select_tokens(option_text)
    if any(phrase in normalized_option for phrase in DECLINE_OPTION_PHRASES):
        return "decline"
    if normalized_option in NONE_LEVEL_WORDS or bool(option_tokens & NONE_LEVEL_WORDS):
        return "none"
    if normalized_option in YES_OPTION_WORDS or bool(option_tokens & YES_OPTION_WORDS) or any(phrase in normalized_option for phrase in YES_OPTION_PHRASES):
        return "yes"
    if normalized_option in NO_OPTION_WORDS or bool(option_tokens & NO_OPTION_WORDS) or any(phrase in normalized_option for phrase in NO_OPTION_PHRASES):
        return "no"
    if bool(option_tokens & PROFESSIONAL_LEVEL_WORDS):
        return "professional"
    if any(native_tokens.issubset(option_tokens) for native_tokens in NATIVE_LEVEL_TOKEN_SETS):
        return "native_or_bilingual"
    if bool(option_tokens & CONVERSATIONAL_LEVEL_WORDS):
        return "conversational"
    return None


def select_answer_matches(selected_text: str, desired_text: str) -> bool:
    selected_norm = normalize_select_text(selected_text)
    desired_norm = normalize_select_text(desired_text)
    if not selected_norm or not desired_norm:
        return False
    if selected_norm == desired_norm:
        return True

    selected_kind = classify_select_option(selected_text)
    desired_kind = classify_select_option(desired_text)
    if selected_kind and desired_kind and selected_kind == desired_kind:
        return True

    if not selected_kind and not desired_kind and (desired_norm in selected_norm or selected_norm in desired_norm):
        return True

    return False


def find_matching_select_option(select_wrapper: Select, desired_text: str) -> tuple[str, str] | None:
    desired_norm = normalize_select_text(desired_text)
    desired_kind = classify_select_option(desired_text)
    semantic_match = None
    partial_match = None

    for option in select_wrapper.options:
        option_text = option.text.strip()
        option_norm = normalize_select_text(option_text)
        if not option_norm:
            continue
        if option_norm == desired_norm:
            return option_text, option.get_attribute("value") or ""
        if desired_kind and classify_select_option(option_text) == desired_kind and semantic_match is None:
            semantic_match = (option_text, option.get_attribute("value") or "")
        if not desired_kind and not is_select_placeholder(option_text) and partial_match is None and desired_norm and (desired_norm in option_norm or option_norm in desired_norm):
            partial_match = (option_text, option.get_attribute("value") or "")

    return semantic_match or partial_match


def get_language_proficiency_answer(label_text: str) -> str | None:
    normalized_label = normalize_select_text(label_text)
    if not any(marker in normalized_label for marker in PROFICIENCY_LABEL_MARKERS):
        return None
    if any(marker in normalized_label for marker in ENGLISH_LANGUAGE_MARKERS):
        return "Native or Bilingual"
    if any(marker in normalized_label for marker in FRENCH_LANGUAGE_MARKERS):
        return "Professional"
    if any(marker in normalized_label for marker in KNOWN_LANGUAGE_MARKERS):
        return "None"
    return None


def configured_experience_years() -> int:
    experience_values = []
    if isinstance(current_experience, int) and current_experience >= 0:
        experience_values.append(current_experience)
    try:
        experience_values.append(int(str(years_of_experience).strip()))
    except Exception:
        pass
    return max(experience_values) if experience_values else 0


def get_skill_specific_experience_answer(normalized_label: str) -> str | None:
    label = normalize_select_text(normalized_label)
    asks_years = any(token in label for token in ["experience", "years", "annee", "annees", "ans"])
    if not asks_years:
        return None

    if "sap businessobjects" in label or "businessobjects" in label or "business objects" in label:
        return globals().get("sap_businessobjects_years_of_experience", "2")
    if "excel" in label or "spreadsheet" in label:
        return globals().get("excel_years_of_experience", years_of_experience)
    if (
        "human resources" in label
        or "ressources humaines" in label
        or "(rh)" in label
        or "people operations" in label
        or "people ops" in label
        or "recruit" in label
        or " rh " in f" {label} "
        or " hr " in f" {label} "
    ):
        return globals().get("hr_years_of_experience", "1")

    return None


def extract_experience_threshold(label: str) -> tuple[int, bool] | None:
    normalized_label = normalize_select_text(label)
    word_to_number = {
        "one": 1,
        "un": 1,
        "una": 1,
        "two": 2,
        "dos": 2,
        "three": 3,
        "tres": 3,
        "four": 4,
        "cuatro": 4,
        "five": 5,
        "cinco": 5,
        "six": 6,
        "seis": 6,
    }
    match = re.search(
        r"(more than|over|at least|minimum|minimum of|min\.?|mas de|al menos)\s+(\d+|one|un|una|two|dos|three|tres|four|cuatro|five|cinco|six|seis)\s+(?:year|years|ano|anos)",
        normalized_label,
    )
    if not match:
        return None

    comparator = match.group(1)
    raw_value = match.group(2)
    threshold = int(raw_value) if raw_value.isdigit() else word_to_number.get(raw_value)
    if threshold is None:
        return None

    is_strict = comparator in {"more than", "over", "mas de"}
    return threshold, is_strict


def detect_education_level(text_value: str) -> str | None:
    normalized_text = normalize_select_text(text_value)
    if not normalized_text:
        return None

    for level_name, aliases in EDUCATION_LEVEL_ALIASES.items():
        if any(normalize_select_text(alias) in normalized_text for alias in aliases):
            return level_name
    return None


def get_education_completion_answer(label_text: str) -> str | None:
    normalized_label = normalize_select_text(label_text)
    if not normalized_label:
        return None

    if not any(marker in normalized_label for marker in ("education", "degree", "qualification")):
        return None
    if not any(marker in normalized_label for marker in ("completed", "complete", "obtained", "attained")):
        return None

    asked_level = detect_education_level(normalized_label)
    if not asked_level:
        return None

    configured_levels = globals().get("completed_education_levels", []) or []
    completed_levels = {
        detected
        for level in configured_levels
        for detected in [detect_education_level(str(level))]
        if detected
    }
    if not completed_levels:
        return None

    return "Yes" if asked_level in completed_levels else "No"


def should_force_binary_answer(label: str) -> bool:
    normalized_label = normalize_select_text(label)
    if extract_experience_threshold(normalized_label) and any(term in normalized_label for term in ["experience", "experiencia"]):
        return True
    if any(term in normalized_label for term in ["interested in", "interesado", "interesada"]) and any(term in normalized_label for term in ["contract", "contrato"]):
        return True
    return False


def has_yes_no_options(option_texts: list[str]) -> bool:
    option_kinds = {classify_select_option(option_text) for option_text in option_texts}
    return "yes" in option_kinds and "no" in option_kinds


QuestionEntry = tuple[str, Any, str, Any]


def question_entry_key(question_entry: QuestionEntry) -> str:
    return f"{question_entry[2]}|{normalize_select_text(str(question_entry[0]))}"


def upsert_question(questions_list: list[QuestionEntry], entry: QuestionEntry) -> list[QuestionEntry]:
    target_key = question_entry_key(entry)
    for idx, existing in enumerate(questions_list):
        if question_entry_key(existing) == target_key:
            questions_list[idx] = entry
            return questions_list
    questions_list.append(entry)
    return questions_list


def remove_questions(questions_list: list[QuestionEntry], predicate) -> list[QuestionEntry]:
    return [entry for entry in questions_list if not predicate(entry)]


def is_critical_question(label_text: str) -> bool:
    normalized_label = normalize_select_text(label_text)
    return any(marker in normalized_label for marker in CRITICAL_QUESTION_MARKERS)


def find_modal_action_button(modal: WebElement, action: str) -> WebElement | None:
    keywords = MODAL_ACTION_KEYWORDS.get(action, [])
    if not keywords:
        return None

    buttons = modal.find_elements(By.XPATH, ".//button[not(@disabled)]")
    for button in buttons:
        try:
            button_text = normalize_select_text((button.text or "") + " " + (button.get_attribute("aria-label") or ""))
            if any(keyword in button_text for keyword in keywords):
                return button
        except Exception:
            continue
    return None


def click_modal_action(modal: WebElement, action: str, retries: int = 2) -> bool:
    for _ in range(max(1, retries)):
        try:
            button = find_modal_action_button(modal, action)
            if not button:
                return False
            scroll_to_view(driver, button, top=True)
            button.click()
            return True
        except ElementClickInterceptedException:
            sleep(0.4)
            try:
                modal = find_by_class(driver, "jobs-easy-apply-modal")
            except Exception:
                pass
        except Exception:
            sleep(0.3)
    return False


def is_easy_apply_modal_open() -> bool:
    try:
        overlays = driver.find_elements(By.XPATH, "//div[@data-test-modal-id='easy-apply-modal' and @aria-hidden='false']")
        return len(overlays) > 0
    except Exception:
        return False


def close_easy_apply_modal_if_open() -> bool:
    if not is_easy_apply_modal_open():
        return False
    try:
        actions.send_keys(Keys.ESCAPE).perform()
        sleep(0.4)
        discard_button = try_xp(driver, "//button[.//span[normalize-space()='Discard'] or normalize-space()='Discard']", False)
        if discard_button:
            discard_button.click()
            sleep(0.4)
        return not is_easy_apply_modal_open()
    except Exception:
        return False


def dismiss_job_search_safety_reminder(context: str = "") -> bool:
    '''Dismiss LinkedIn safety reminder popup by clicking "Continue applying" when present.'''
    try:
        dialogs = driver.find_elements(By.XPATH, "//div[@role='dialog']")
    except Exception:
        dialogs = []

    for dialog in dialogs:
        try:
            if not dialog.is_displayed():
                continue
            dialog_text = normalize_select_text(dialog.get_attribute("textContent") or dialog.text or "")
            if "job search safety reminder" not in dialog_text and "report suspicious jobs" not in dialog_text:
                continue

            continue_xpaths = [
                ".//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue applying')]",
                ".//button[.//span[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue applying')]]",
                ".//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]",
            ]
            for xp in continue_xpaths:
                buttons = dialog.find_elements(By.XPATH, xp)
                for button in buttons:
                    if not button.is_displayed() or not button.is_enabled():
                        continue
                    scroll_to_view(driver, button)
                    button.click()
                    buffer(click_gap)
                    prefix = f"[{context}] " if context else ""
                    print_lg(prefix + 'Dismissed Job search safety reminder via "Continue applying".')
                    return True
        except Exception:
            continue
    return False


def get_selected_option_text(question: WebElement, fallback: str = "", strict: bool = False) -> str:
    try:
        select_element = try_xp(question, ".//select", False)
        if not select_element:
            return "" if strict else fallback
        return Select(select_element).first_selected_option.text.strip()
    except Exception:
        return "" if strict else fallback


def get_question_label_text(question: WebElement) -> str:
    label_selectors = [
        ".//label[.//span]",
        ".//label",
        ".//legend",
        ".//span[contains(@class, 'visually-hidden')]",
        ".//*[@aria-label]",
    ]
    for selector in label_selectors:
        try:
            candidates = question.find_elements(By.XPATH, selector)
        except Exception:
            continue
        for candidate in candidates:
            try:
                text = (candidate.text or candidate.get_attribute("aria-label") or "").strip()
            except Exception:
                text = ""
            if text:
                return text
    return "Unknown"


def element_identifier(element: WebElement) -> str:
    attrs = [
        element.get_attribute("id") or "",
        element.get_attribute("name") or "",
        element.get_attribute("data-test-id") or "",
        element.get_attribute("aria-label") or "",
        element.get_attribute("autocomplete") or "",
    ]
    for attr in attrs:
        if attr and attr.strip():
            return attr.strip()
    return str(element.id)


def is_email_question_label(label_text: str) -> bool:
    normalized_label = normalize_select_text(label_text)
    if not normalized_label:
        return False
    return any(marker in normalized_label for marker in EMAIL_LABEL_MARKERS)


def looks_like_email_text(text: str) -> bool:
    normalized_text = normalize_select_text(text)
    raw_text = (text or "").strip()
    if "@" in raw_text:
        return True
    return any(marker in normalized_text for marker in EMAIL_LABEL_MARKERS)


def control_looks_email_related(element: WebElement) -> bool:
    try:
        attrs = [
            element.get_attribute("type") or "",
            element.get_attribute("name") or "",
            element.get_attribute("id") or "",
            element.get_attribute("aria-label") or "",
            element.get_attribute("autocomplete") or "",
            element.get_attribute("placeholder") or "",
            element.get_attribute("value") or "",
        ]
        return any(looks_like_email_text(attr) for attr in attrs)
    except Exception:
        return False


def dispatch_select_value(select_element: WebElement, option_value: str, option_text: str) -> bool:
    try:
        return bool(select_element.parent.execute_script(
            """
            const select = arguments[0];
            const targetValue = arguments[1];
            const targetText = arguments[2];
            let option = Array.from(select.options).find(opt => opt.value === targetValue);
            if (!option) {
                option = Array.from(select.options).find(opt => opt.text.trim() === targetText);
            }
            if (!option) {
                return false;
            }
            option.selected = true;
            select.value = option.value;
            for (const eventName of ['input', 'change', 'blur']) {
                select.dispatchEvent(new Event(eventName, { bubbles: true }));
            }
            return true;
            """,
            select_element,
            option_value,
            option_text,
        ))
    except Exception:
        return False


def dispatch_input_value(input_element: WebElement, desired_text: str) -> bool:
    try:
        return bool(input_element.parent.execute_script(
            """
            const input = arguments[0];
            const targetValue = arguments[1];
            const descriptor = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value');
            input.focus();
            if (descriptor && descriptor.set) {
                descriptor.set.call(input, targetValue);
            } else {
                input.value = targetValue;
            }
            for (const eventName of ['input', 'change', 'blur']) {
                input.dispatchEvent(new Event(eventName, { bubbles: true }));
            }
            return true;
            """,
            input_element,
            desired_text,
        ))
    except Exception:
        return False


def force_select_option(question: WebElement, desired_text: str) -> str:
    select_element = try_xp(question, ".//select", False)
    if not select_element:
        return ""

    select_wrapper = Select(select_element)
    matched_option = find_matching_select_option(select_wrapper, desired_text)
    if matched_option is None:
        return get_selected_option_text(question, strict=True)

    matched_text, matched_value = matched_option

    try:
        select_wrapper.select_by_visible_text(matched_text)
    except Exception:
        dispatch_select_value(select_element, matched_value or matched_text, matched_text)

    sleep(0.2)
    selected_text = get_selected_option_text(question, strict=True)
    if select_answer_matches(selected_text, desired_text) or select_answer_matches(selected_text, matched_text):
        return selected_text

    select_element = try_xp(question, ".//select", False)
    if select_element and dispatch_select_value(select_element, matched_value or matched_text, matched_text):
        sleep(0.2)
        selected_text = get_selected_option_text(question, strict=True)
        if select_answer_matches(selected_text, desired_text) or select_answer_matches(selected_text, matched_text):
            return selected_text

    return selected_text


def force_input_option(question: WebElement, desired_text: str) -> str:
    input_element = try_xp(question, ".//input[@type='email' or contains(@autocomplete, 'email') or @name='email' or @type='text']", False)
    if not input_element:
        return ""

    try:
        input_element.click()
        input_element.send_keys(Keys.CONTROL + 'a')
        input_element.send_keys(Keys.DELETE)
        human_type(input_element, desired_text)
    except Exception:
        dispatch_input_value(input_element, desired_text)

    sleep(0.2)
    selected_text = (input_element.get_attribute("value") or "").strip()
    if normalize_select_text(selected_text) == normalize_select_text(desired_text):
        return selected_text

    if dispatch_input_value(input_element, desired_text):
        sleep(0.2)
        selected_text = (input_element.get_attribute("value") or "").strip()

    return selected_text


def enforce_email_dropdowns(modal: WebElement, questions_list: list[QuestionEntry]) -> list[QuestionEntry]:
    candidate_questions = modal.find_elements(
        By.XPATH,
        ".//div[@data-test-form-element] | .//div[.//select or .//input[@type='email' or contains(@autocomplete, 'email') or @name='email']] | .//fieldset[.//select]",
    )
    candidate_questions.extend(
        modal.find_elements(
            By.XPATH,
            ".//select | .//input[@type='email' or contains(@autocomplete, 'email') or @name='email']",
        )
    )
    seen_controls = set()
    seen_questions = set()

    for question in candidate_questions:
        question_scope = question
        try:
            tag_name = (question.tag_name or "").lower()
        except Exception:
            tag_name = ""

        if tag_name in {"select", "input"}:
            parent_scope = try_xp(question, "./ancestor::*[self::div or self::fieldset][1]", False)
            if parent_scope:
                question_scope = parent_scope

        question_key = element_identifier(question_scope)
        if question_key in seen_questions:
            continue
        seen_questions.add(question_key)

        label_org = get_question_label_text(question_scope)

        input_element = question if tag_name == "input" else try_xp(question_scope, ".//input[@type='email' or contains(@autocomplete, 'email') or @name='email']", False)
        select_element = question if tag_name == "select" else try_xp(question_scope, ".//select", False)
        label_indicates_email = is_email_question_label(label_org)
        input_indicates_email = bool(input_element and control_looks_email_related(input_element))

        if not label_indicates_email and not input_indicates_email and not input_element and not select_element:
            continue

        if select_element:
            options_text = []
            try:
                options_text = [option.text for option in Select(select_element).options]
            except Exception:
                options_text = []

            has_email_option = any(normalize_select_text(option_text) == normalize_select_text(email) for option_text in options_text)
            option_looks_email = any(looks_like_email_text(option_text) for option_text in options_text)
            select_indicates_email = control_looks_email_related(select_element)
            if not has_email_option and not option_looks_email and not label_indicates_email and not select_indicates_email:
                continue

            control_key = f'select:{element_identifier(select_element)}'
            if control_key in seen_controls:
                continue
            seen_controls.add(control_key)

            select_wrapper = Select(select_element)
            prev_answer = select_wrapper.first_selected_option.text.strip()
            options_text = [option.text for option in select_wrapper.options]
            options = "".join([f' "{option}",' for option in options_text])

            final_answer = force_select_option(question_scope, email)
            logged_answer = final_answer if final_answer else "[selection not verified]"
            questions_list = remove_questions(
                questions_list,
                lambda item: len(item) >= 3 and item[2] == "select" and isinstance(item[0], str) and item[0].startswith(f'{label_org} ['),
            )
            upsert_question(questions_list, (f'{label_org} [ {options} ]', logged_answer, "select", prev_answer))

            if not final_answer:
                print_lg(f'WARNING: Unable to verify email dropdown selection for question labelled "{label_org}"')
            elif normalize_select_text(final_answer) != normalize_select_text(email):
                print_lg(f'WARNING: Email dropdown still selected "{final_answer}" instead of "{email}" for question labelled "{label_org}"')
            continue

        if not input_element:
            continue

        control_key = f'input:{element_identifier(input_element)}'
        if control_key in seen_controls:
            continue
        seen_controls.add(control_key)

        prev_answer = (input_element.get_attribute("value") or "").strip()
        final_answer = force_input_option(question_scope, email)
        logged_answer = final_answer if final_answer else "[selection not verified]"
        questions_list = remove_questions(
            questions_list,
            lambda item: len(item) >= 3 and item[2] == "text" and isinstance(item[0], str) and item[0] == label_org.lower(),
        )
        upsert_question(questions_list, (label_org.lower(), logged_answer, "text", prev_answer))

        if not final_answer:
            print_lg(f'WARNING: Unable to verify email input for question labelled "{label_org}"')
        elif normalize_select_text(final_answer) != normalize_select_text(email):
            print_lg(f'WARNING: Email input still contains "{final_answer}" instead of "{email}" for question labelled "{label_org}"')

    return questions_list


def has_security_challenge() -> bool:
    '''Detect LinkedIn verification/challenge pages or captcha surfaces.'''
    try:
        cur_url = driver.current_url.lower()
        # Match only LinkedIn's specific challenge/checkpoint URL paths
        if any(key in cur_url for key in ["linkedin.com/checkpoint/challenge", "linkedin.com/checkpoint/lg", "linkedin.com/uas/challenge", "/captcha/"]):
            return True
        # Check for a visible security verification heading (not invisible reCAPTCHA scripts)
        challenge_banner = try_xp(driver, "//h1[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'security verification')]", False)
        return bool(challenge_banner)
    except Exception:
        return False

#>


#< Login Functions
def is_logged_in_LN() -> bool:
    '''
    Function to check if user is logged-in in LinkedIn
    * Returns: `True` if user is logged-in or `False` if not
    '''
    if driver.current_url == "https://www.linkedin.com/feed/": return True
    if try_linkText(driver, "Sign in"): return False
    if try_xp(driver, '//button[@type="submit" and contains(text(), "Sign in")]'):  return False
    if try_linkText(driver, "Join now"): return False
    print_lg("Didn't find Sign in link, so assuming user is logged in!")
    return True


def login_LN() -> None:
    '''
    Function to login for LinkedIn
    * Tries to login using given `username` and `password` from `secrets.py`
    * If failed, tries to login using saved LinkedIn profile button if available
    * If both failed, asks user to login manually
    '''
    # Find the username and password fields and fill them with user credentials
    driver.get("https://www.linkedin.com/login")
    if username == "username@example.com" and password == "example_password":
        pyautogui.alert("User did not configure username and password in secrets.py, hence can't login automatically! Please login manually!", "Login Manually","Okay")
        print_lg("User did not configure username and password in secrets.py, hence can't login automatically! Please login manually!")
        manual_login_retry(is_logged_in_LN, 2)
        return
    try:
        wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Forgot password?")))
        try:
            text_input_by_ID(driver, "username", username, 1)
        except Exception:
            print_lg("Couldn't find username field.")
        try:
            text_input_by_ID(driver, "password", password, 1)
        except Exception:
            print_lg("Couldn't find password field.")
            # print_lg(e)
        # Find the login submit button and click it
        driver.find_element(By.XPATH, '//button[@type="submit" and contains(text(), "Sign in")]').click()
    except Exception:
        try:
            profile_button = find_by_class(driver, "profile__details")
            profile_button.click()
        except Exception:
            print_lg("Couldn't Login!")

    try:
        # Wait until successful redirect, indicating successful login
        wait.until(EC.url_to_be("https://www.linkedin.com/feed/")) # wait.until(EC.presence_of_element_located((By.XPATH, '//button[normalize-space(.)="Start a post"]')))
        return print_lg("Login successful!")
    except Exception:
        print_lg("Seems like login attempt failed! Possibly due to wrong credentials or already logged in! Try logging in manually!")
        manual_login_retry(is_logged_in_LN, 2)
#>



def get_applied_job_ids() -> set[str]:
    '''
    Function to get a `set` of applied job's Job IDs
    * Returns a set of Job IDs from existing applied jobs history csv file
    '''
    job_ids: set[str] = set()
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                job_ids.add(row[0])
    except FileNotFoundError:
        print_lg(f"The CSV file '{file_name}' does not exist.")
    return job_ids



def set_search_location(search_location_override: str | None = None) -> None:
    '''
    Function to set search location
    '''
    target_search_location = (search_location_override or search_location).strip()
    if target_search_location:
        try:
            print_lg(f'Setting search location as: "{target_search_location}"')
            search_location_ele = try_xp(driver, ".//input[@aria-label='City, state, or zip code'and not(@disabled)]", False) #  and not(@aria-hidden='true')]")
            if search_location_ele:
                current_value = (search_location_ele.get_attribute("value") or "").strip()
                if normalize_select_text(current_value) == normalize_select_text(target_search_location):
                    print_lg(f'Search location already set to "{target_search_location}"; skipping re-entry.')
                    return
            text_input(actions, search_location_ele, target_search_location, "Search Location")
        except ElementNotInteractableException:
            try_xp(driver, ".//label[@class='jobs-search-box__input-icon jobs-search-box__keywords-label']")
            actions.send_keys(Keys.TAB, Keys.TAB).perform()
            actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL).perform()
            actions.send_keys(target_search_location).perform()
            sleep(2)
            actions.send_keys(Keys.ENTER).perform()
            try_xp(driver, ".//button[@aria-label='Cancel']")
        except Exception as e:
            try_xp(driver, ".//button[@aria-label='Cancel']")
            print_lg("Failed to update search location, continuing with default location!", e)


def apply_filters(
    force_under_10: bool = False,
    date_posted_override: str | None = None,
    search_location_override: str | None = None,
    location_override: list[str] | None = None,
) -> bool:
    '''
    Function to apply job search filters.
    force_under_10: when True, enables the "Under 10 applicants" filter regardless of config.
    date_posted_override: when provided, applies this date filter for the current pass.
    '''
    set_search_location(search_location_override)
    selected_date_posted = date_posted_override or date_posted
    selected_locations = location_override if location_override is not None else location

    try:
        recommended_wait = 1 if click_gap < 1 else 0

        wait.until(EC.presence_of_element_located((By.XPATH, '//button[normalize-space()="All filters"]'))).click()
        buffer(recommended_wait)

        sort_clicked = click_filter_option_with_fallback(sort_by)
        date_clicked = click_filter_option_with_fallback(selected_date_posted)
        buffer(recommended_wait)

        multi_sel_noWait(driver, experience_level) 
        multi_sel_noWait(driver, companies, actions)
        if experience_level or companies: buffer(recommended_wait)

        multi_sel_noWait(driver, job_type)
        multi_sel_noWait(driver, on_site)
        if job_type or on_site: buffer(recommended_wait)

        set_boolean_filter_state("Easy Apply", bool(easy_apply_only))
        
        location_click_failures = 0
        for loc in selected_locations:
            try:
                btn = driver.find_element(By.XPATH, f'.//span[normalize-space(.)="{loc}"]')
                scroll_to_view(driver, btn)
                btn.click()
                buffer(click_gap)
            except Exception:
                if not location_search_click(driver, actions, loc):
                    location_click_failures += 1
        if selected_locations and location_click_failures == len(selected_locations):
            print_lg("Location filters could not be applied; continuing without strict location chips for this term.")
        multi_sel_noWait(driver, industry)
        if selected_locations or industry: buffer(recommended_wait)

        multi_sel_noWait(driver, job_function)
        multi_sel_noWait(driver, job_titles)
        if job_function or job_titles: buffer(recommended_wait)

        desired_under_10 = bool(under_10_applicants or force_under_10)
        set_boolean_filter_state("Under 10 applicants", desired_under_10)
        if in_your_network: boolean_button_click(driver, actions, "In your network")
        if fair_chance_employer: boolean_button_click(driver, actions, "Fair Chance Employer")

        wait_span_click(driver, salary)
        buffer(recommended_wait)
        
        multi_sel_noWait(driver, benefits)
        multi_sel_noWait(driver, commitments)
        if benefits or commitments: buffer(recommended_wait)

        if not click_show_results_button():
            print_lg('Preflight failed: could not find/click "Show results" button in filters modal.')
            actions.send_keys(Keys.ESCAPE).perform()
            return False

        if sort_by and not sort_clicked:
            print_lg(f'Preflight failed: sort option "{sort_by}" was not applied.')
        if selected_date_posted and not date_clicked:
            print_lg(f'Preflight failed: date filter "{selected_date_posted}" was not applied.')

        global pause_after_filters
        if pause_after_filters and "Turn off Pause after search" == pyautogui.confirm("These are your configured search results and filter. It is safe to change them while this dialog is open, any changes later could result in errors and skipping this search run.", "Please check your results", ["Turn off Pause after search", "Look's good, Continue"]):
            pause_after_filters = False

        # Non-blocking preflight: LinkedIn frequently localizes filter labels; continue run when
        # filters modal completes, even if one label-specific click could not be verified.
        return True

    except Exception as e:
        print_lg("Setting the preferences failed!", e)
        return False


def set_boolean_filter_state(filter_text: str, should_enable: bool) -> bool:
    '''Ensure a boolean filter switch has the desired state.'''
    try:
        list_container = driver.find_element(By.XPATH, f'.//h3[normalize-space()="{filter_text}"]/ancestor::fieldset')
        button = list_container.find_element(By.XPATH, './/input[@role="switch"]')
        def _read_state(switch_input: WebElement) -> bool:
            # LinkedIn toggles are inconsistent across DOM versions; read multiple indicators.
            try:
                if switch_input.is_selected():
                    return True
            except Exception:
                pass
            aria_checked = str(switch_input.get_attribute("aria-checked") or "").strip().lower()
            if aria_checked in {"true", "false"}:
                return aria_checked == "true"
            return str(switch_input.get_attribute("checked") or "").strip().lower() in {"true", "checked"}

        current_state = _read_state(button)
        if current_state != should_enable:
            scroll_to_view(driver, button)
            actions.move_to_element(button).click().perform()
            buffer(click_gap)
            # Re-read after click; if still not matching, retry once with refreshed element.
            list_container = driver.find_element(By.XPATH, f'.//h3[normalize-space()="{filter_text}"]/ancestor::fieldset')
            button = list_container.find_element(By.XPATH, './/input[@role="switch"]')
            if _read_state(button) != should_enable:
                actions.move_to_element(button).click().perform()
                buffer(click_gap)
        return True
    except Exception:
        print_lg(f"Click Failed! Didn't find '{filter_text}'")
        return False



def get_page_info() -> tuple[WebElement | None, int | None]:
    '''
    Function to get pagination element and current page number
    '''
    try:
        pagination_element = try_find_by_classes(driver, ["jobs-search-pagination__pages", "artdeco-pagination", "artdeco-pagination__pages"])
        scroll_to_view(driver, pagination_element)
        current_page = int(pagination_element.find_element(By.XPATH, "//button[contains(@class, 'active')]").text)
    except Exception as e:
        print_lg("Failed to find Pagination element, hence couldn't scroll till end!")
        pagination_element = None
        current_page = None
        print_lg(e)
    return pagination_element, current_page


def has_no_matching_jobs_banner() -> bool:
    '''
    Detect LinkedIn "no matching jobs" banner so we can skip suggested jobs and move to next term.
    '''
    banner_selectors = [
        "//div[contains(@class, 'jobs-search-no-results-banner')]",
        "//div[contains(@class, 'jobs-search-no-results')]",
    ]

    for selector in banner_selectors:
        try:
            banners = driver.find_elements(By.XPATH, selector)
        except Exception:
            banners = []
        for banner in banners:
            try:
                if not banner.is_displayed():
                    continue
                banner_text = normalize_select_text(banner.text or "")
                if any(
                    token in banner_text
                    for token in [
                        "no matching jobs found",
                        "aucun emploi correspondant",
                        "no jobs found",
                    ]
                ):
                    return True
            except Exception:
                continue

    # Fallback text detection for localized/variant DOM layouts.
    fallback_xpaths = [
        "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'no matching jobs found')]",
        "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aucun emploi correspondant')]",
    ]
    for selector in fallback_xpaths:
        try:
            match_nodes = driver.find_elements(By.XPATH, selector)
            if match_nodes:
                return True
        except Exception:
            continue

    return False


def has_suggested_jobs_context() -> bool:
    '''Detect suggested/recommended job contexts that appear when search has no real matches.'''
    markers = [
        "suggested jobs",
        "suggested searches",
        "based on your profile",
        "jobs you may be interested in",
        "recommended jobs",
        "emplois suggeres",
        "offres suggerees",
        "recommande",
        "recommandes",
    ]
    container_xpaths = [
        "//div[contains(@class, 'jobs-search-results-list')]",
        "//div[contains(@class, 'jobs-search-two-pane')]",
        "//main",
    ]

    for selector in container_xpaths:
        try:
            containers = driver.find_elements(By.XPATH, selector)
        except Exception:
            containers = []
        for container in containers[:2]:
            try:
                if not container.is_displayed():
                    continue
                text_blob = normalize_select_text((container.text or "")[:5000])
                if any(marker in text_blob for marker in markers):
                    return True
            except Exception:
                continue
    return False


def looks_like_suggested_results_for_term(job_listings: list[WebElement], search_term: str) -> bool:
    '''If first visible cards are unrelated to the search term, treat this as suggested results mode.'''
    term_tokens = {
        token
        for token in re.findall(r"[a-z]+", normalize_select_text(search_term))
        if len(token) >= 4 and token not in {"with", "from", "dans", "pour", "avec", "specialist"}
    }
    if not term_tokens:
        return False

    checked = 0
    matches = 0
    for job in job_listings[:6]:
        try:
            title_text = normalize_select_text(job.find_element(By.TAG_NAME, "a").text or "")
        except Exception:
            continue
        if not title_text:
            continue
        checked += 1
        title_tokens = set(re.findall(r"[a-z]+", title_text))
        if term_tokens & title_tokens:
            matches += 1

    if checked >= 3 and matches == 0:
        return True
    return False


STRONG_ROLE_TOKENS = {
    "finance",
    "financial",
    "accounting",
    "billing",
    "invoice",
    "treasury",
    "payable",
    "receivable",
    "credit",
    "ledger",
    "comptable",
    "facturation",
    "analyste",
}
WEAK_ROLE_STOPWORDS = {
    "and",
    "with",
    "from",
    "for",
    "the",
    "senior",
    "junior",
    "specialist",
    "associate",
    "analyst",
    "h",
    "f",
}


def _tokenize_title_intent(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z]+", normalize_select_text(text))
        if len(token) >= 3 and token not in WEAK_ROLE_STOPWORDS
    }


def is_title_relevant(title: str, search_term: str) -> bool:
    if not bool(globals().get("strict_title_relevance", False)):
        return True

    title_norm = normalize_select_text(title)
    if not title_norm:
        return False

    allow_words = globals().get("title_allow_words", [])
    for keyword in allow_words:
        if normalize_select_text(str(keyword)) in title_norm:
            return True

    title_tokens = _tokenize_title_intent(title)
    search_tokens = _tokenize_title_intent(search_term)
    if not title_tokens:
        return False

    overlap = title_tokens & search_tokens
    if overlap & STRONG_ROLE_TOKENS:
        return True

    # Fallback: allow when at least two intent tokens overlap (excluding generic words).
    return len(overlap) >= 2


def is_description_relevant(description: str, title: str, search_term: str) -> bool:
    '''Second-stage relevance check used in balanced mode for uncertain titles.'''
    if not description:
        return False

    combined_text = normalize_select_text(f"{title} {description}")
    if not combined_text:
        return False

    for keyword in globals().get("description_allow_words", []):
        keyword_norm = normalize_select_text(str(keyword))
        if keyword_norm and keyword_norm in combined_text:
            return True

    combined_tokens = _tokenize_title_intent(combined_text)
    search_tokens = _tokenize_title_intent(search_term)
    overlap = combined_tokens & search_tokens
    if overlap & STRONG_ROLE_TOKENS:
        return True
    return len(overlap) >= 2



def get_job_main_details(job: WebElement, blacklisted_companies: set, rejected_jobs: set, search_term: str) -> tuple[str, str, str, str, str, bool, bool]:
    '''
    # Function to get job main details.
    Returns a tuple of (job_id, title, company, work_location, work_style, skip)
    * job_id: Job ID
    * title: Job title
    * company: Company name
    * work_location: Work location of this job
    * work_style: Work style of this job (Remote, On-site, Hybrid)
    * skip: A boolean flag to skip this job
    '''
    skip = False
    needs_description_relevance_check = False
    job_id = job.get_dom_attribute('data-occludable-job-id') or "Unknown"
    title = "Unknown"
    company = "Unknown"
    work_location = "Unknown"
    work_style = "Unknown"

    try:
        job_details_button = job.find_element(By.TAG_NAME, 'a')  # job.find_element(By.CLASS_NAME, "job-card-list__title")  # Problem in India
        scroll_to_view(driver, job_details_button, True)
        title = job_details_button.text
        title = title[:title.find("\n")] if "\n" in title else title
    except Exception as e:
        print_lg(f'Skipping malformed/expired job card (missing title link). Job ID: {job_id}!', e)
        return (job_id, title, company, work_location, work_style, True, False)

    try:
        # company = job.find_element(By.CLASS_NAME, "job-card-container__primary-description").text
        # work_location = job.find_element(By.CLASS_NAME, "job-card-container__metadata-item").text
        other_details = job.find_element(By.CLASS_NAME, 'artdeco-entity-lockup__subtitle').text
        index = other_details.find(' · ')
        if index != -1:
            company = other_details[:index]
            work_location = other_details[index+3:]
        else:
            company = other_details
            work_location = "Unknown"
        if "(" in work_location and ")" in work_location:
            work_style = work_location[work_location.rfind('(')+1:work_location.rfind(')')]
            work_location = work_location[:work_location.rfind('(')].strip()
    except Exception:
        # Some cards omit subtitle metadata; keep defaults and continue with title-based screening.
        pass
    
    # Skip if previously rejected due to blacklist or already applied
    title_low = title.lower()
    title_norm = normalize_select_text(title)
    if not is_title_relevant(title, search_term):
        mode = str(globals().get("title_relevance_mode", "strict")).strip().lower()
        if mode == "balanced":
            needs_description_relevance_check = True
            print_lg(f'Flagging "{title} | {company}" for balanced relevance check (title uncertain, search_term="{search_term}"). Job ID: {job_id}!')
        else:
            print_lg(f'Skipping "{title} | {company}" job (skip_reason=title_not_relevant, search_term="{search_term}"). Job ID: {job_id}!')
            skip = True
    for word in title_bad_words:
        if word.lower() in title_low:
            print_lg(f'Skipping "{title} | {company}" job (skip_reason=title_bad_word, bad_word="{word}"). Job ID: {job_id}!')
            skip = True
            break
    if not skip and re.search(r"\blead\b", title_norm):
        print_lg(f'Skipping "{title} | {company}" job (Lead role in title). Job ID: {job_id}!')
        skip = True
    if not skip and company in blacklisted_companies:
        print_lg(f'Skipping "{title} | {company}" job (Blacklisted Company). Job ID: {job_id}!')
        skip = True
    if not skip and job_id in rejected_jobs: 
        print_lg(f'Skipping previously rejected "{title} | {company}" job. Job ID: {job_id}!')
        skip = True
    try:
        if job.find_element(By.CLASS_NAME, "job-card-container__footer-job-state").text == "Applied":
            skip = True
            print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id}!')
    except: pass
    try: 
        if not skip: job_details_button.click()
    except Exception:
        print_lg(f'Failed to click "{title} | {company}" job on details button. Job ID: {job_id}!')
        discard_job()
        job_details_button.click()
    buffer(click_gap)
    return (job_id,title,company,work_location,work_style,skip,needs_description_relevance_check)


# Function to check for Blacklisted words in About Company
def check_blacklist(rejected_jobs: set, job_id: str, company: str, blacklisted_companies: set) -> tuple[set, set, WebElement] | ValueError:
    jobs_top_card = try_find_by_classes(driver, ["job-details-jobs-unified-top-card__primary-description-container","job-details-jobs-unified-top-card__primary-description","jobs-unified-top-card__primary-description","jobs-details__main-content"])
    about_company_org = find_by_class(driver, "jobs-company__box")
    scroll_to_view(driver, about_company_org)
    about_company_org = about_company_org.text
    about_company = about_company_org.lower()
    skip_checking = False
    for word in about_company_good_words:
        if word.lower() in about_company:
            print_lg(f'Found the word "{word}". So, skipped checking for blacklist words.')
            skip_checking = True
            break
    if not skip_checking:
        for word in about_company_bad_words: 
            if word.lower() in about_company: 
                rejected_jobs.add(job_id)
                blacklisted_companies.add(company)
                raise ValueError(f'\n"{about_company_org}"\n\nContains "{word}".')
    buffer(click_gap)
    scroll_to_view(driver, jobs_top_card)
    return rejected_jobs, blacklisted_companies, jobs_top_card



def get_linkedin_skills_match() -> tuple[int, int] | None:
    '''
    Reads LinkedIn's built-in "X of Y skills match" indicator from the job detail panel.
    Returns (matched, total) as integers, or None if the element is absent or unparseable.
    '''
    try:
        el = driver.find_element(By.CLASS_NAME, "job-details-fit-level-preferences")
        m = re.search(r'(\d+)\s+of\s+(\d+)\s+skills?\s+match', el.text, re.IGNORECASE)
        if m:
            return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return None


# Function to extract years of experience required from About Job
def extract_years_of_experience(text: str) -> int:
    # Extract all patterns like '10+ years', '5 years', '3-5 years', etc.
    # Preserve range separators before ASCII normalization so "3–6 years" does not become "36 years".
    normalized_text = unicodedata.normalize("NFKD", text or "")
    normalized_text = normalized_text.replace("–", "-").replace("—", "-").replace("−", "-")
    normalized_text = normalized_text.encode("ascii", "ignore").decode("ascii")
    normalized_text = re.sub(r"\s+", " ", normalized_text).strip().casefold()
    matches = re.findall(re_experience, normalized_text)
    if len(matches) == 0: 
        print_lg("Couldn't find experience requirement in About the Job!")
        return 0
    experience_values = [int(match) for match in matches if int(match) <= 12]
    if not experience_values:
        # If only very high values were found (e.g., 15+ years), avoid crashing and keep the highest parsed value.
        return max(int(match) for match in matches)
    return max(experience_values)



def get_job_description(
) -> tuple[
    str | Literal['Unknown'],
    int | Literal['Unknown'],
    bool,
    str | None,
    str | None
    ]:
    '''
    # Job Description
    Function to extract job description from About the Job.
    ### Returns:
    - `jobDescription: str | 'Unknown'`
    - `experience_required: int | 'Unknown'`
    - `skip: bool`
    - `skipReason: str | None`
    - `skipMessage: str | None`
    '''
    jobDescription = "Unknown"
    experience_required: int | Literal['Unknown', 'Error in extraction'] = "Unknown"
    skip = False
    skipReason: str | None = None
    skipMessage: str | None = None
    try:
        ##> ------ Dheeraj Deshwal : dheeraj9811 Email:dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Feature ------
        ##<
        found_masters = 0
        jobDescription = find_by_class(driver, "jobs-box__html-content").text
        jobDescriptionLow = jobDescription.lower()
        desc_snippet = jobDescription[:300] + ("..." if len(jobDescription) > 300 else "")
        for word in bad_words:
            if word.lower() in jobDescriptionLow:
                skipMessage = f'Contains bad word "{word}". Skipping this job!\nDescription snippet: "{desc_snippet}"'
                skipReason = "Found a Bad Word in About Job"
                skip = True
                break
        if not skip and security_clearance == False and ('polygraph' in jobDescriptionLow or 'clearance' in jobDescriptionLow or 'secret' in jobDescriptionLow):
            skipMessage = f'Found "Clearance" or "Polygraph". Skipping this job!\nDescription snippet: "{desc_snippet}"'
            skipReason = "Asking for Security clearance"
            skip = True
        if not skip:
            if did_masters and 'master' in jobDescriptionLow:
                print_lg(f'Found the word "master".\nDescription snippet: "{desc_snippet}"')
                found_masters = 2
            experience_required = extract_years_of_experience(jobDescription)
            if current_experience > -1 and experience_required > current_experience + found_masters:
                skipMessage = f'Experience required {experience_required} > Current Experience {current_experience + found_masters}. Skipping this job!\nDescription snippet: "{desc_snippet}"'
                skipReason = "Required experience is high"
                skip = True
    except Exception:
        if jobDescription == "Unknown":    print_lg("Unable to extract job description!")
        else:
            experience_required = "Error in extraction"
            print_lg("Unable to extract years of experience required!")
    return jobDescription, experience_required, skip, skipReason, skipMessage
        


# Function to upload resume
def upload_resume(modal: WebElement, resume: str) -> tuple[bool, str]:
    try:
        modal.find_element(By.NAME, "file").send_keys(os.path.abspath(resume))
        return True, os.path.join(os.path.basename(os.path.dirname(resume)), os.path.basename(resume))
    except: return False, "Previous resume"


def get_resume_for_term(search_term: str) -> str:
    '''Return the tailored resume path for this search term, falling back to default_resume_path.'''
    for keyword, path in resume_map.items():
        if keyword.lower() in search_term.lower():
            if os.path.exists(path):
                print_lg(f'[Resume] Using tailored resume for "{search_term}": {path}')
                return path
            else:
                print_lg(f'[Resume] Tailored resume not found at "{path}", falling back to default.')
    return default_resume_path

# Function to answer common questions for Easy Apply
def answer_common_questions(label: str, answer: str, work_location: str) -> str:
    normalized_label = normalize_select_text(label)
    experience_threshold = extract_experience_threshold(normalized_label)
    skill_specific_experience = get_skill_specific_experience_answer(normalized_label)
    education_completion_answer = get_education_completion_answer(normalized_label)
    if education_completion_answer is not None:
        answer = education_completion_answer
    elif 'sponsorship' in normalized_label or 'visa' in normalized_label:
        answer = get_visa_answer(work_location)
    elif any(phrase in normalized_label for phrase in ['living in', 'based in', 'reside in', 'residing in', 'located in', 'authorized to work in', 'allowed to work in', 'right to work in', 'permission to work in', 'eligible to work in', 'currently in', 'live in']):
        answer = get_work_authorization_answer(normalized_label, work_location)
    elif experience_threshold and any(term in normalized_label for term in ['experience', 'experiencia']):
        threshold, is_strict = experience_threshold
        profile_experience = configured_experience_years()
        meets_threshold = profile_experience > threshold if is_strict else profile_experience >= threshold
        answer = 'Yes' if meets_threshold else 'No'
    elif skill_specific_experience is not None:
        answer = skill_specific_experience
    elif any(token in normalized_label for token in ['experience', 'years', 'annee', 'annees', 'ans']):
        answer = years_of_experience
    elif any(term in normalized_label for term in ['interested in', 'interesado', 'interesada']) and any(term in normalized_label for term in ['contract', 'contrato']):
        answer = 'Yes'
    elif any(phrase in normalized_label for phrase in ['prevent you from working', 'conditions or agreements prevent', 'conditions prevent you', 'agreement prevent']):
        # "Would any employment conditions/agreements prevent you from working here?" → No
        answer = 'No'
    elif any(term in normalized_label for term in ENGLISH_LANGUAGE_MARKERS) and any(w in normalized_label for w in ['level', 'proficiency', 'fluency', 'fluent', 'speak', 'advanced', 'ingles']):
        answer = 'Yes'
    return answer


# Function to answer the questions for Easy Apply
def answer_questions(modal: WebElement, questions_list: list[QuestionEntry], work_location: str, job_description: str | None = None ) -> list[QuestionEntry]:
    # Get all questions from the page
     
    all_questions = modal.find_elements(By.XPATH, ".//div[@data-test-form-element]")
    # all_questions = modal.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-element")
    # all_list_questions = modal.find_elements(By.XPATH, ".//div[@data-test-text-entity-list-form-component]")
    # all_single_line_questions = modal.find_elements(By.XPATH, ".//div[@data-test-single-line-text-form-component]")
    # all_questions = all_questions + all_list_questions + all_single_line_questions

    for Question in all_questions:
        # Check if it's a select Question
        select = try_xp(Question, ".//select", False)
        if select:
            label_org = "Unknown"
            try:
                label = Question.find_element(By.TAG_NAME, "label")
                label_org = label.find_element(By.TAG_NAME, "span").text
            except: pass
            answer = 'Yes'
            label = label_org.lower()
            label_norm = normalize_select_text(label_org)
            select = Select(select)
            selected_option = select.first_selected_option.text
            optionsText = []
            options = '"List of phone country codes"'
            if label_norm != "phone country code":
                optionsText = [option.text for option in select.options]
                options = "".join([f' "{option}",' for option in optionsText])
            prev_answer = selected_option
            answer = prev_answer
            proficiency_answer = get_language_proficiency_answer(label_org)
            force_binary_answer = should_force_binary_answer(label_norm) and has_yes_no_options(optionsText)
            critical_select = is_critical_question(label_org)
            if overwrite_previous_answers or is_select_placeholder(selected_option) or force_binary_answer or label_norm == "phone country code" or 'email' in label_norm or proficiency_answer is not None:
                if label_norm == "phone country code" and not optionsText:
                    optionsText = [option.text for option in select.options]  # needed for fallback fuzzy match
                if 'email' in label_norm and not optionsText:
                    optionsText = [option.text for option in select.options]  # needed for fallback fuzzy match
                ##> ------ WINDY_WINDWARD Email:karthik.sarode23@gmail.com - Added fuzzy logic to answer location based questions ------
                if 'email' in label_norm:
                    answer = email
                elif label_norm == 'phone country code':
                    answer = phone_country_code
                elif 'phone' in label_norm:
                    answer = prev_answer
                elif 'gender' in label_norm or 'sex' in label_norm: 
                    answer = gender
                elif 'disability' in label_norm: 
                    answer = disability_status
                elif proficiency_answer is not None:
                    answer = proficiency_answer
                elif 'category' in label_norm or 'function' in label_norm or 'department' in label_norm:
                    answer = job_category
                # Add location handling
                elif any(loc_word in label_norm for loc_word in ['location', 'city', 'state', 'country']):
                    if 'country' in label_norm:
                        answer = current_country
                    elif 'state' in label_norm:
                        answer = state
                    elif 'city' in label_norm:
                        answer = current_city if current_city else work_location
                    else:
                        answer = work_location
                else: 
                    answer = answer_common_questions(label_norm, answer, work_location)
                # If the answer is still a placeholder after all rule checks, proactively ask AI.
                # Selecting the placeholder passes select_answer_matches but fails LinkedIn's form validation.
                if is_select_placeholder(answer) and 'email' not in label_norm:
                    if use_AI and aiClient:
                        try:
                            if ai_provider.lower() == "openai":
                                ai_answer = ai_answer_question(aiClient, label_org, options=optionsText, question_type="single_select", job_description=job_description, user_information_all=user_information_all)
                            elif ai_provider.lower() == "deepseek":
                                ai_answer = deepseek_answer_question(aiClient, label_org, options=optionsText, question_type="single_select", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            elif ai_provider.lower() == "gemini":
                                ai_answer = gemini_answer_question(aiClient, label_org, options=optionsText, question_type="single_select", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            else:
                                ai_answer = None
                            if ai_answer and isinstance(ai_answer, str) and len(ai_answer) > 0:
                                answer = ai_answer
                                print_lg(f'AI proactively answered unanswered select "{label_org}" with "{answer}"')
                        except Exception as e:
                            print_lg("AI failed to proactively answer select question!", e)
                    # Final fallback: if still a placeholder, default Yes for binary questions
                    if is_select_placeholder(answer) and has_yes_no_options(optionsText) and not critical_select:
                        answer = 'Yes'
                        print_lg(f'Defaulting to "Yes" for unanswered binary select "{label_org}"')
                selected_answer = force_select_option(Question, answer)
                if not select_answer_matches(selected_answer, answer):
                    if 'email' in label_norm:
                        print_lg(f'Failed to verify email option "{answer}" for question labelled "{label_org}".')
                    else:
                        ai_select_answered = False
                        if use_AI and aiClient:
                            try:
                                if ai_provider.lower() == "openai":
                                    ai_answer = ai_answer_question(aiClient, label_org, options=optionsText, question_type="single_select", job_description=job_description, user_information_all=user_information_all)
                                elif ai_provider.lower() == "deepseek":
                                    ai_answer = deepseek_answer_question(aiClient, label_org, options=optionsText, question_type="single_select", job_description=job_description, about_company=None, user_information_all=user_information_all)
                                elif ai_provider.lower() == "gemini":
                                    ai_answer = gemini_answer_question(aiClient, label_org, options=optionsText, question_type="single_select", job_description=job_description, about_company=None, user_information_all=user_information_all)
                                else:
                                    ai_answer = None
                                if ai_answer and isinstance(ai_answer, str) and len(ai_answer) > 0:
                                    ai_selected = force_select_option(Question, ai_answer)
                                    if select_answer_matches(ai_selected, ai_answer):
                                        selected_answer = ai_selected
                                        answer = ai_selected
                                        ai_select_answered = True
                                        print_lg(f'AI answered select question "{label_org}" with "{ai_selected}"')
                            except Exception as e:
                                print_lg("AI failed to answer select question!", e)
                        if not ai_select_answered:
                            if critical_select:
                                raise Exception(f'Critical select unresolved: {label_org}')
                            print_lg(f'Failed to verify select option "{answer}" for question labelled "{label_org}", answering randomly!')
                            rand_max = max(1, len(select.options) - 1)
                            select.select_by_index(randint(1, rand_max) if rand_max > 1 else 0)
                            selected_answer = get_selected_option_text(Question, select.first_selected_option.text)
                            randomly_answered_questions.add((f'{label_org} [ {options} ]',"select"))
                if 'email' in label_norm:
                    answer = selected_answer
                    if not answer:
                        print_lg(f'WARNING: Unable to verify email dropdown selection for "{label_org}".')
                        answer = "[selection not verified]"
                    elif normalize_select_text(answer) != normalize_select_text(email):
                        print_lg(f'WARNING: Email select verification failed for "{label_org}". Current selection is "{answer}".')
                else:
                    answer = selected_answer or get_selected_option_text(Question, answer)
            else:
                answer = get_selected_option_text(Question, answer)
            upsert_question(questions_list, (f'{label_org} [ {options} ]', answer, "select", prev_answer))
            continue
        
        # Check if it's a radio Question
        radio = try_xp(Question, './/fieldset[@data-test-form-builder-radio-button-form-component="true"]', False)
        if radio:
            prev_answer = None
            label = try_xp(radio, './/span[@data-test-form-builder-radio-button-form-component__title]', False)
            try: label = find_by_class(label, "visually-hidden", 2.0)
            except: pass
            label_org = label.text if label else "Unknown"
            answer = 'Yes'
            label = label_org.lower()

            label_org += ' [ '
            options = radio.find_elements(By.TAG_NAME, 'input')
            options_labels = []
            
            for option in options:
                id = option.get_attribute("id")
                option_label = try_xp(radio, f'.//label[@for="{id}"]', False)
                options_labels.append( f'"{option_label.text if option_label else "Unknown"}"<{option.get_attribute("value")}>' ) # Saving option as "label <value>"
                if option.is_selected(): prev_answer = options_labels[-1]
                label_org += f' {options_labels[-1]},'

            is_work_auth = any(phrase in label for phrase in ['authorized to work', 'allowed to work', 'right to work', 'permission to work', 'eligible to work', 'legally authorized', 'legally entitled', 'living in', 'based in', 'reside in', 'residing in'])
            force_binary_answer = should_force_binary_answer(label) and has_yes_no_options(options_labels)
            critical_radio = is_critical_question(label_org)
            if overwrite_previous_answers or prev_answer is None or is_work_auth or force_binary_answer:
                if 'citizenship' in label or 'employment eligibility' in label: answer = us_citizenship
                elif 'veteran' in label or 'protected' in label: answer = veteran_status
                elif 'disability' in label or 'handicapped' in label: 
                    answer = disability_status
                else: answer = answer_common_questions(label, answer, work_location)
                foundOption = try_xp(radio, f".//label[normalize-space()='{answer}']", False)
                if foundOption: 
                    actions.move_to_element(foundOption).click().perform()
                else:    
                    answer_intent = classify_select_option(answer) or normalize_select_text(answer)
                    possible_answer_phrases = ["Decline", "not wish", "don't wish", "Prefer not", "not want"] if answer_intent == 'decline' else [answer]
                    if answer_intent == 'yes':
                        possible_answer_phrases += ["Sí", "Si", "Oui", "Ja", "Yes"]
                    elif answer_intent == 'no':
                        possible_answer_phrases += ["No", "Non", "Nein"]
                    ele = None
                    if answer_intent in {'yes', 'no', 'decline'}:
                        for i, option_label in enumerate(options_labels):
                            if classify_select_option(option_label) == answer_intent:
                                foundOption = options[i]
                                ele = foundOption
                                answer = f'Decline ({option_label})' if answer_intent == 'decline' else option_label
                                break
                    for phrase in possible_answer_phrases:
                        for i, option_label in enumerate(options_labels):
                            if phrase in option_label:
                                foundOption = options[i]
                                ele = foundOption
                                answer = f'Decline ({option_label})' if answer_intent == 'decline' else option_label
                                break
                        if foundOption: break
                    # if answer == 'Decline':
                    #     answer = options_labels[0]
                    #     for phrase in ["Prefer not", "not want", "not wish"]:
                    #         foundOption = try_xp(radio, f".//label[normalize-space()='{phrase}']", False)
                    #         if foundOption:
                    #             answer = f'Decline ({phrase})'
                    #             ele = foundOption
                    #             break
                    if foundOption and ele:
                        actions.move_to_element(ele).click().perform()
                    if not foundOption:
                        ai_radio_answered = False
                        if use_AI and aiClient:
                            try:
                                if ai_provider.lower() == "openai":
                                    ai_answer = ai_answer_question(aiClient, label_org, options=options_labels, question_type="single_select", job_description=job_description, user_information_all=user_information_all)
                                elif ai_provider.lower() == "deepseek":
                                    ai_answer = deepseek_answer_question(aiClient, label_org, options=options_labels, question_type="single_select", job_description=job_description, about_company=None, user_information_all=user_information_all)
                                elif ai_provider.lower() == "gemini":
                                    ai_answer = gemini_answer_question(aiClient, label_org, options=options_labels, question_type="single_select", job_description=job_description, about_company=None, user_information_all=user_information_all)
                                else:
                                    ai_answer = None
                                if ai_answer and isinstance(ai_answer, str):
                                    ai_option = try_xp(radio, f".//label[normalize-space()='{ai_answer}']", False)
                                    if not ai_option:
                                        for i, opt_label in enumerate(options_labels):
                                            if ai_answer.lower() in opt_label.lower():
                                                ai_option = try_xp(radio, f'.//label[@for="{options[i].get_attribute("id")}"]', False)
                                                ai_answer = opt_label
                                                break
                                    if ai_option:
                                        actions.move_to_element(ai_option).click().perform()
                                        answer = ai_answer
                                        ai_radio_answered = True
                                        print_lg(f'AI answered radio question "{label_org}" with "{ai_answer}"')
                            except Exception as e:
                                print_lg("AI failed to answer radio question!", e)
                        if not ai_radio_answered:
                            if critical_radio:
                                raise Exception(f'Critical radio unresolved: {label_org}')
                            ele = options[0]
                            answer = options_labels[0]
                            actions.move_to_element(ele).click().perform()
                            randomly_answered_questions.add((f'{label_org} ]',"radio"))
            else: answer = prev_answer
            upsert_question(questions_list, (label_org+" ]", answer, "radio", prev_answer))
            continue
        
        # Check if it's a text question
        text = try_xp(Question, ".//input[@type='text' or @type='number']", False)
        if text: 
            do_actions = False
            label = try_xp(Question, ".//label[@for]", False)
            try: label = label.find_element(By.CLASS_NAME,'visually-hidden')
            except: pass
            label_org = label.text if label else "Unknown"
            answer = "" # years_of_experience
            label = label_org.lower()

            prev_answer = text.get_attribute("value")
            if not prev_answer or overwrite_previous_answers or 'phone' in label or 'mobile' in label or 'email' in label or 'experience' in label or 'years' in label:
                if 'birth' in label: answer = birth_year
                elif ('experience' in label or 'years' in label) and ('excel' in label or 'spreadsheet' in label):
                    answer = globals().get("excel_years_of_experience", years_of_experience)
                elif ('experience' in label or 'years' in label or 'annee' in label or 'annees' in label or 'an' in label or 'ans' in label) and (
                    'human resources' in label
                    or 'ressources humaines' in label
                    or '(rh)' in label
                    or 'rh ' in f"{label} "
                    or 'hr ' in f"{label} "
                    or 'people ops' in label
                    or 'people operations' in label
                    or 'recruit' in label
                ):
                    answer = globals().get("hr_years_of_experience", "1")
                elif 'experience' in label or 'years' in label: answer = years_of_experience
                elif 'phone' in label or 'mobile' in label: answer = phone_number
                elif 'email' in label: answer = email
                elif 'street' in label: answer = street
                elif 'city' in label or 'location' in label or 'address' in label:
                    answer = current_city if current_city else work_location
                    do_actions = True
                elif 'how did you hear' in label or 'heard about this job' in label or 'heard about this role' in label:
                    answer = globals().get("how_heard_about_job", "LinkedIn Jobs")
                elif 'signature' in label: answer = full_name # 'signature' in label or 'legal name' in label or 'your name' in label or 'full name' in label: answer = full_name     # What if question is 'name of the city or university you attend, name of referral etc?'
                elif 'name' in label:
                    if 'full' in label: answer = full_name
                    elif 'first' in label and 'last' not in label: answer = first_name
                    elif 'middle' in label and 'last' not in label: answer = middle_name
                    elif 'last' in label and 'first' not in label: answer = last_name
                    elif 'employer' in label: answer = recent_employer
                    else: answer = full_name
                elif 'notice' in label:
                    if 'month' in label:
                        answer = notice_period_months
                    elif 'week' in label:
                        answer = notice_period_weeks
                    else: answer = notice_period
                elif 'salary' in label or 'compensation' in label or 'ctc' in label or 'pay' in label:
                    desired_salary_value, desired_salary_monthly, desired_salary_lakhs = get_desired_salary_values(work_location)
                    if 'current' in label or 'present' in label:
                        if 'month' in label:
                            answer = current_ctc_monthly
                        elif 'lakh' in label:
                            answer = current_ctc_lakhs
                        else:
                            answer = current_ctc
                    else:
                        if 'month' in label:
                            answer = desired_salary_monthly
                        elif 'lakh' in label:
                            answer = desired_salary_lakhs
                        else:
                            answer = desired_salary_value
                elif 'linkedin' in label: answer = linkedIn
                elif 'website' in label or 'blog' in label or 'portfolio' in label or 'link' in label: answer = website
                elif 'scale of 1-10' in label: answer = confidence_level
                elif 'headline' in label: answer = linkedin_headline
                elif ('hear' in label or 'come across' in label) and 'this' in label and ('job' in label or 'position' in label): answer = "LinkedIn"
                elif 'state' in label or 'province' in label: answer = state
                elif 'zip' in label or 'postal' in label or 'code' in label: answer = zipcode
                elif 'country' in label: answer = current_country
                else: answer = answer_common_questions(label, answer, work_location)
                ##> ------ Yang Li : MARKYangL - Feature ------
                if answer == "":
                    if use_AI and aiClient:
                        try:
                            print_lg(f'No deterministic answer for "{label_org}". Asking AI...')
                            if ai_provider.lower() == "openai":
                                answer = ai_answer_question(aiClient, label_org, question_type="text", job_description=job_description, user_information_all=user_information_all)
                            elif ai_provider.lower() == "deepseek":
                                answer = deepseek_answer_question(aiClient, label_org, options=None, question_type="text", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            elif ai_provider.lower() == "gemini":
                                answer = gemini_answer_question(aiClient, label_org, options=None, question_type="text", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            else:
                                randomly_answered_questions.add((label_org, "text"))
                                answer = years_of_experience
                            if answer and isinstance(answer, str) and len(answer) > 0:
                                print_lg(f'AI Answered received for question "{label_org}" \nhere is answer: "{answer}"')
                            else:
                                randomly_answered_questions.add((label_org, "text"))
                                answer = years_of_experience
                        except Exception as e:
                            print_lg("Failed to get AI answer!", e)
                            randomly_answered_questions.add((label_org, "text"))
                            answer = years_of_experience
                    else:
                        randomly_answered_questions.add((label_org, "text"))
                        answer = years_of_experience
                ##<
                text.clear()
                text.send_keys(Keys.CONTROL + 'a')
                text.send_keys(Keys.DELETE)
                answer = str(answer)
                # For number fields, extract only the numeric value (AI may return a full sentence)
                if text.get_attribute("type") == "number":
                    nums = re.findall(r'\d[\d,.]*', re.sub(r'[€$£¥]', '', answer))
                    candidates = []
                    for n in nums:
                        try: candidates.append(float(n.replace(',', '')))
                        except: pass
                    # Prefer values > 100 (salaries/quantities, not years like 2024 unless nothing better)
                    salary_candidates = [c for c in candidates if c > 100]
                    pick = max(salary_candidates) if salary_candidates else (max(candidates) if candidates else None)
                    if pick is not None:
                        extracted = str(int(pick)) if pick == int(pick) else str(pick)
                        print_lg(f'Extracted number "{extracted}" from answer for number field "{label_org}"')
                        answer = extracted
                # Respect the field's maxlength attribute to avoid validation errors
                max_length = text.get_attribute("maxlength")
                if max_length and max_length.isdigit():
                    answer = answer[:int(max_length)]
                human_type(text, answer)
                if do_actions:
                    sleep(2)
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.send_keys(Keys.ENTER).perform()
            upsert_question(questions_list, (label, text.get_attribute("value"), "text", prev_answer))
            continue

        # Check if it's a textarea question
        text_area = try_xp(Question, ".//textarea", False)
        if text_area:
            do_actions = False
            label = try_xp(Question, ".//label[@for]", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = ""
            prev_answer = text_area.get_attribute("value")
            if not prev_answer or overwrite_previous_answers:
                if 'summary' in label: answer = linkedin_summary
                if answer == "":
                ##> ------ Yang Li : MARKYangL - Feature ------
                    # Determine AI question_type hint for cover/motivation so the prompt gives the right length/style
                    if 'cover' in label:
                        ai_qtype = "cover_letter"
                    elif any(phrase in label for phrase in [
                        'why are you considering', 'why do you want to work', 'why do you want to join',
                        'why are you interested', 'why do you see yourself', 'what draws you to',
                        'employer of choice', 'why this company', 'why apply', 'why do you wish',
                        'why would you like to', 'why are you applying',
                    ]):
                        ai_qtype = "motivation"
                    else:
                        ai_qtype = "textarea"
                    if use_AI and aiClient:
                        try:
                            if ai_provider.lower() == "openai":
                                answer = ai_answer_question(aiClient, label_org, question_type=ai_qtype, job_description=job_description, user_information_all=user_information_all)
                            elif ai_provider.lower() == "deepseek":
                                answer = deepseek_answer_question(aiClient, label_org, options=None, question_type=ai_qtype, job_description=job_description, about_company=None, user_information_all=user_information_all)
                            elif ai_provider.lower() == "gemini":
                                answer = gemini_answer_question(aiClient, label_org, options=None, question_type=ai_qtype, job_description=job_description, about_company=None, user_information_all=user_information_all)
                            else:
                                randomly_answered_questions.add((label_org, "textarea"))
                                answer = ""
                            if answer and isinstance(answer, str) and len(answer) > 0:
                                print_lg(f'AI Answered received for question "{label_org}" \nhere is answer: "{answer}"')
                            else:
                                randomly_answered_questions.add((label_org, "textarea"))
                                answer = ""
                        except Exception as e:
                            print_lg("Failed to get AI answer!", e)
                            randomly_answered_questions.add((label_org, "textarea"))
                            answer = ""
                    else:
                        randomly_answered_questions.add((label_org, "textarea"))
                    # Hardcoded fallbacks when AI is off or returned empty
                    if not answer:
                        if 'cover' in label:
                            answer = cover_letter
                            randomly_answered_questions.discard((label_org, "textarea"))
                        elif ai_qtype == "motivation":
                            answer = motivation_answer
                            randomly_answered_questions.discard((label_org, "textarea"))
                text_area.clear()
                answer = str(answer)
                max_length = text_area.get_attribute("maxlength")
                if max_length and max_length.isdigit():
                    answer = answer[:int(max_length)]
                # Keep textarea reasonably fast while avoiding single-shot paste.
                for i in range(0, len(answer), 80):
                    text_area.send_keys(answer[i:i+80])
                    sleep(uniform(0.05, 0.18))
            if do_actions:
                    sleep(2)
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.send_keys(Keys.ENTER).perform()
            upsert_question(questions_list, (label, text_area.get_attribute("value"), "textarea", prev_answer))
            ##<
            continue

        # Check if it's a checkbox question
        checkbox = try_xp(Question, ".//input[@type='checkbox']", False)
        if checkbox:
            label = try_xp(Question, ".//span[@class='visually-hidden']", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = try_xp(Question, ".//label[@for]", False)  # Sometimes multiple checkboxes are given for 1 question, Not accounted for that yet
            answer = answer.text if answer else "Unknown"
            prev_answer = checkbox.is_selected()
            checked = prev_answer
            if not prev_answer:
                if should_auto_check_checkbox(label_org, answer):
                    try:
                        actions.move_to_element(checkbox).click().perform()
                        checked = True
                    except Exception as e:
                        print_lg("Checkbox click failed!", e)
                elif matches_preferred_region(label_org, answer):
                    try:
                        actions.move_to_element(checkbox).click().perform()
                        checked = True
                        print_lg(f'Auto-selected preferred region "{answer}" for "{label_org}"')
                    except Exception as e:
                        print_lg(f'Region checkbox click failed for "{answer}"!', e)
                else:
                    ai_checked = False
                    if use_AI and aiClient and not any(marker in normalize_select_text(f"{label_org} {answer}") for marker in DEMOGRAPHIC_CHECKBOX_MARKERS):
                        try:
                            print_lg(f'Checkbox decision uncertain for "{label_org}". Asking AI...')
                            ai_checkbox_answer = None
                            option_hints = ["Yes (check)", "No (leave unchecked)"]
                            if ai_provider.lower() == "openai":
                                ai_checkbox_answer = ai_answer_question(aiClient, label_org, options=option_hints, question_type="single_select", job_description=job_description, user_information_all=user_information_all)
                            elif ai_provider.lower() == "deepseek":
                                ai_checkbox_answer = deepseek_answer_question(aiClient, label_org, options=option_hints, question_type="single_select", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            elif ai_provider.lower() == "gemini":
                                ai_checkbox_answer = gemini_answer_question(aiClient, label_org, options=option_hints, question_type="single_select", job_description=job_description, about_company=None, user_information_all=user_information_all)
                            intent = classify_select_option(ai_checkbox_answer or "")
                            if intent == "yes":
                                actions.move_to_element(checkbox).click().perform()
                                checked = True
                                ai_checked = True
                                print_lg(f'AI selected checkbox for "{label_org}"')
                        except Exception as e:
                            print_lg("AI checkbox decision failed!", e)
                    if not ai_checked:
                        print_lg(f'Leaving checkbox unchecked for manual or user-specific choice: "{label_org}"')
            upsert_question(questions_list, (f'{label} ([X] {answer})', checked, "checkbox", prev_answer))
            continue


    # Select todays date
    questions_list = enforce_email_dropdowns(modal, questions_list)
    try_xp(driver, "//button[contains(@aria-label, 'This is today')]")

    # Collect important skills
    # if 'do you have' in label and 'experience' in label and ' in ' in label -> Get word (skill) after ' in ' from label
    # if 'how many years of experience do you have in ' in label -> Get word (skill) after ' in '

    return questions_list


def rectify_field_errors(modal: WebElement, questions_list: list[QuestionEntry], job_description: str | None = None) -> int:
    '''
    After a failed Next click, reads LinkedIn inline validation error messages and uses AI to re-answer
    the specific fields that failed. Returns the number of fields that had errors.
    '''
    try:
        error_elements = modal.find_elements(
            By.XPATH,
            ".//div[@data-test-form-element][.//*[contains(@class,'artdeco-inline-feedback--error')]]"
        )
    except Exception:
        return 0
    if not error_elements:
        return 0

    print_lg(f"Found {len(error_elements)} field(s) with validation errors, attempting to rectify...")

    for elem in error_elements:
        try:
            label_org = get_question_label_text(elem)
            error_msg = ""
            try:
                error_span = elem.find_element(By.XPATH, ".//*[contains(@class,'artdeco-inline-feedback--error')]")
                error_msg = error_span.text.strip()
            except Exception:
                pass
            if not error_msg:
                error_msg = "Invalid answer — please provide a valid value."
            print_lg(f'Validation error on "{label_org}": "{error_msg}"')
            question_with_error = f"{label_org}\n[Form validation error: {error_msg}]"

            # --- Select field ---
            select_el = try_xp(elem, ".//select", False)
            if select_el:
                optionsText = []
                try:
                    optionsText = [o.text for o in Select(select_el).options if not is_select_placeholder(o.text)]
                except Exception:
                    pass
                ai_answer = None
                if use_AI and aiClient:
                    try:
                        if ai_provider.lower() == "openai":
                            ai_answer = ai_answer_question(aiClient, question_with_error, options=optionsText, question_type="single_select", job_description=job_description, user_information_all=user_information_all)
                        elif ai_provider.lower() == "deepseek":
                            ai_answer = deepseek_answer_question(aiClient, question_with_error, options=optionsText, question_type="single_select", job_description=job_description, about_company=None, user_information_all=user_information_all)
                        elif ai_provider.lower() == "gemini":
                            ai_answer = gemini_answer_question(aiClient, question_with_error, options=optionsText, question_type="single_select", job_description=job_description, about_company=None, user_information_all=user_information_all)
                    except Exception as e:
                        print_lg(f'AI failed to rectify select "{label_org}"!', e)
                if ai_answer and isinstance(ai_answer, str):
                    force_select_option(elem, ai_answer)
                    print_lg(f'Rectified select "{label_org}" with "{ai_answer}"')
                elif optionsText:
                    force_select_option(elem, optionsText[0])
                    print_lg(f'Rectified select "{label_org}" with fallback first option "{optionsText[0]}"')
                continue

            # --- Text / number field ---
            text_el = try_xp(elem, ".//input[@type='text' or @type='number']", False)
            if text_el:
                field_type = text_el.get_attribute("type") or "text"
                ai_answer = None
                if use_AI and aiClient:
                    try:
                        if ai_provider.lower() == "openai":
                            ai_answer = ai_answer_question(aiClient, question_with_error, question_type="text", job_description=job_description, user_information_all=user_information_all)
                        elif ai_provider.lower() == "deepseek":
                            ai_answer = deepseek_answer_question(aiClient, question_with_error, options=None, question_type="text", job_description=job_description, about_company=None, user_information_all=user_information_all)
                        elif ai_provider.lower() == "gemini":
                            ai_answer = gemini_answer_question(aiClient, question_with_error, options=None, question_type="text", job_description=job_description, about_company=None, user_information_all=user_information_all)
                    except Exception as e:
                        print_lg(f'AI failed to rectify {field_type} field "{label_org}"!', e)
                if ai_answer and isinstance(ai_answer, str) and ai_answer.strip():
                    answer_str = str(ai_answer)
                    if field_type == "number":
                        nums = re.findall(r'\d[\d,.]*', re.sub(r'[€$£¥]', '', answer_str))
                        candidates = []
                        for n in nums:
                            try: candidates.append(float(n.replace(',', '')))
                            except: pass
                        salary_candidates = [c for c in candidates if c > 100]
                        pick = max(salary_candidates) if salary_candidates else (max(candidates) if candidates else None)
                        if pick is not None:
                            answer_str = str(int(pick)) if pick == int(pick) else str(pick)
                    text_el.click()
                    text_el.send_keys(Keys.CONTROL + 'a')
                    text_el.send_keys(Keys.DELETE)
                    max_length = text_el.get_attribute("maxlength")
                    if max_length and max_length.isdigit():
                        answer_str = answer_str[:int(max_length)]
                    human_type(text_el, answer_str)
                    print_lg(f'Rectified {field_type} field "{label_org}" with "{answer_str}"')
                continue

            # --- Textarea field ---
            ta_el = try_xp(elem, ".//textarea", False)
            if ta_el:
                ai_answer = None
                if use_AI and aiClient:
                    try:
                        if ai_provider.lower() == "openai":
                            ai_answer = ai_answer_question(aiClient, question_with_error, question_type="textarea", job_description=job_description, user_information_all=user_information_all)
                        elif ai_provider.lower() == "deepseek":
                            ai_answer = deepseek_answer_question(aiClient, question_with_error, options=None, question_type="textarea", job_description=job_description, about_company=None, user_information_all=user_information_all)
                        elif ai_provider.lower() == "gemini":
                            ai_answer = gemini_answer_question(aiClient, question_with_error, options=None, question_type="textarea", job_description=job_description, about_company=None, user_information_all=user_information_all)
                    except Exception as e:
                        print_lg(f'AI failed to rectify textarea "{label_org}"!', e)
                if ai_answer and isinstance(ai_answer, str) and ai_answer.strip():
                    answer_str = str(ai_answer)
                    max_length = ta_el.get_attribute("maxlength")
                    if max_length and max_length.isdigit():
                        answer_str = answer_str[:int(max_length)]
                    ta_el.clear()
                    for i in range(0, len(answer_str), 80):
                        ta_el.send_keys(answer_str[i:i+80])
                        sleep(uniform(0.05, 0.18))
                    print_lg(f'Rectified textarea "{label_org}" with AI answer')

        except Exception as e:
            print_lg("Failed to rectify a field error!", e)

    return len(error_elements)


def external_apply(pagination_element: WebElement, job_id: str, job_link: str, resume: str, date_listed, application_link: str, screenshot_name: str) -> tuple[bool, str, int]:
    '''
    Function to open new tab and save external job application links
    '''
    global tabs_count
    if easy_apply_only:
        detect_daily_easy_apply_limit("external-apply")
        print_lg("Easy apply failed I guess!")
        if pagination_element != None: return True, application_link, tabs_count
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, ".//button[contains(@class,'jobs-apply-button') and contains(@class, 'artdeco-button--3')]"))).click() # './/button[contains(span, "Apply") and not(span[contains(@class, "disabled")])]'
        wait_span_click(driver, "Continue", 1, True, False)
        windows = driver.window_handles
        tabs_count = len(windows)
        driver.switch_to.window(windows[-1])
        application_link = driver.current_url
        print_lg('Got the external application link "{}"'.format(application_link))
        if close_tabs and driver.current_window_handle != linkedIn_tab: driver.close()
        driver.switch_to.window(linkedIn_tab)
        return False, application_link, tabs_count
    except Exception as e:
        # print_lg(e)
        print_lg("Failed to apply!")
        failed_job(job_id, job_link, resume, date_listed, "Probably didn't find Apply button or unable to switch tabs.", e, application_link, screenshot_name)
        global failed_count
        failed_count += 1
        return True, application_link, tabs_count



def follow_company(modal: WebDriver = driver) -> None:
    '''
    Function to follow or un-follow easy applied companies based on `follow_companies`
    '''
    try:
        follow_checkbox_input = None
        checkbox_id = None
        # Try known ID first
        follow_checkbox_input = try_xp(modal, ".//input[@id='follow-company-checkbox' and @type='checkbox']", False)
        if follow_checkbox_input:
            checkbox_id = 'follow-company-checkbox'
        else:
            # Fallback: find a label containing 'follow' and use its paired checkbox
            follow_label = try_xp(modal, ".//label[contains(translate(., 'FOLLOW', 'follow'), 'follow')]", False)
            if follow_label:
                checkbox_id = follow_label.get_attribute("for")
                if checkbox_id:
                    follow_checkbox_input = try_xp(modal, f".//input[@id='{checkbox_id}' and @type='checkbox']", False)
        if follow_checkbox_input and follow_checkbox_input.is_selected() != follow_companies:
            label = try_xp(modal, f".//label[@for='{checkbox_id}']", False)
            if label: actions.move_to_element(label).click().perform()
            print_lg(f'{"Followed" if follow_companies else "Unfollowed"} company.')
    except Exception as e:
        print_lg("Failed to update follow companies checkbox!", e)
    


#< Failed attempts logging
def failed_job(
    job_id: str,
    job_link: str,
    resume: str,
    date_listed,
    error: str,
    exception: Exception,
    application_link: str,
    screenshot_name: str,
    full_job_description: str | None = None,
) -> None:
    '''
    Function to update failed jobs list in excel
    '''
    try:
        fieldnames = ['Job ID', 'Job Link', 'Resume Tried', 'Date listed', 'Date Tried', 'Assumed Reason', 'Stack Trace', 'External Job link', 'Screenshot Name', 'Full Job Description']
        legacy_fieldnames = ['Job ID', 'Job Link', 'Resume Tried', 'Date listed', 'Date Tried', 'Assumed Reason', 'Stack Trace', 'External Job link', 'Screenshot Name']

        # One-time schema repair for failed history file to avoid shifted columns.
        if os.path.exists(failed_file_name):
            try:
                with open(failed_file_name, mode='r', newline='', encoding='utf-8') as existing_csv:
                    rows = list(csv.reader(existing_csv))
                if rows:
                    header = rows[0]
                    if header != fieldnames:
                        migrated_rows: list[list[str]] = [fieldnames]
                        if header == legacy_fieldnames:
                            for row in rows[1:]:
                                if len(row) == len(legacy_fieldnames):
                                    row = row + [""]
                                elif len(row) < len(fieldnames):
                                    row = row + [""] * (len(fieldnames) - len(row))
                                elif len(row) > len(fieldnames):
                                    row = row[:len(fieldnames)]
                                migrated_rows.append(row)
                        else:
                            for row in rows[1:]:
                                if len(row) < len(fieldnames):
                                    row = row + [""] * (len(fieldnames) - len(row))
                                elif len(row) > len(fieldnames):
                                    row = row[:len(fieldnames)]
                                migrated_rows.append(row)

                        with open(failed_file_name, mode='w', newline='', encoding='utf-8') as migrated_csv:
                            writer = csv.writer(migrated_csv)
                            writer.writerows(migrated_rows)
                        print_lg('Migrated failed jobs CSV schema to include "Full Job Description" column.')
            except Exception as migration_error:
                print_lg("Failed jobs CSV schema migration skipped due to error.", migration_error)

        with open(failed_file_name, 'a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0: writer.writeheader()
            writer.writerow({
                'Job ID':truncate_for_csv(job_id),
                'Job Link':truncate_for_csv(job_link),
                'Resume Tried':truncate_for_csv(resume),
                'Date listed':fmt_date(date_listed),
                'Date Tried':fmt_datetime(datetime.now()),
                'Assumed Reason':truncate_for_csv(error),
                'Stack Trace':truncate_for_csv(exception),
                'External Job link':truncate_for_csv(application_link),
                'Screenshot Name':truncate_for_csv(screenshot_name),
                'Full Job Description':truncate_for_csv(full_job_description or ""),
            })
            file.close()
    except Exception as e:
        print_lg("Failed to update failed jobs list!", e)
        pyautogui.alert("Failed to update the excel of failed jobs!\nProbably because of 1 of the following reasons:\n1. The file is currently open or in use by another program\n2. Permission denied to write to the file\n3. Failed to find the file", "Failed Logging")


def screenshot(driver: WebDriver, job_id: str, failedAt: str) -> str:
    '''
    Function to to take screenshot for debugging
    - Returns screenshot name as String
    '''
    screenshot_name = "{} - {} - {}.png".format( job_id, failedAt, str(datetime.now()) )
    path = logs_folder_path+"/screenshots/"+screenshot_name.replace(":",".")
    # special_chars = {'*', '"', '\\', '<', '>', ':', '|', '?'}
    # for char in special_chars:  path = path.replace(char, '-')
    driver.save_screenshot(path.replace("//","/"))
    return screenshot_name
#>



def submitted_jobs(job_id: str, title: str, company: str, work_location: str, work_style: str, description: str, experience_required: int | Literal['Unknown', 'Error in extraction'], 
                   skills: dict[str, list[str]] | str, hr_name: str | Literal['Unknown'], hr_link: str | Literal['Unknown'], resume: str, 
                   reposted: bool, date_listed: datetime | Literal['Unknown'], date_applied:  datetime | Literal['Pending'], job_link: str, application_link: str, 
                   questions_list: list[QuestionEntry] | None, connect_request: Literal['In Development'], search_term: str = '') -> None:
    '''
    Function to create or update the Applied jobs CSV file, once the application is submitted successfully
    '''
    questions_formatted = ' | '.join(f"{q[0]}: {q[1]}" for q in questions_list) if questions_list else ''
    fieldnames = ['Job ID', 'Title', 'Company', 'Work Location', 'Work Style', 'About Job', 'Experience required', 'Skills required', 'HR Name', 'HR Link', 'Resume', 'Search Term', 'Re-posted', 'Date Posted', 'Date Applied', 'Job Link', 'External Job link', 'Questions Found', 'Connect Request']
    legacy_fieldnames = ['Job ID', 'Title', 'Company', 'Work Location', 'Work Style', 'About Job', 'Experience required', 'Skills required', 'HR Name', 'HR Link', 'Resume', 'Re-posted', 'Date Posted', 'Date Applied', 'Job Link', 'External Job link', 'Questions Found', 'Connect Request']

    # One-time schema repair: old files may miss "Search Term" header while newer rows already include it.
    # This causes Connect Request values to appear under wrong columns.
    try:
        if os.path.exists(file_name):
            with open(file_name, mode='r', newline='', encoding='utf-8') as existing_csv:
                rows = list(csv.reader(existing_csv))
            if rows:
                header = rows[0]
                if header != fieldnames:
                    migrated_rows: list[list[str]] = [fieldnames]
                    if header == legacy_fieldnames:
                        for row in rows[1:]:
                            # Legacy rows had no Search Term. Newer rows might already have 19 fields.
                            if len(row) == len(legacy_fieldnames):
                                row = row[:11] + [""] + row[11:]
                            elif len(row) < len(fieldnames):
                                row = row + [""] * (len(fieldnames) - len(row))
                            elif len(row) > len(fieldnames):
                                row = row[:len(fieldnames)]
                            migrated_rows.append(row)
                    else:
                        # Unknown header drift: preserve data rows best-effort with padding/truncation.
                        for row in rows[1:]:
                            if len(row) < len(fieldnames):
                                row = row + [""] * (len(fieldnames) - len(row))
                            elif len(row) > len(fieldnames):
                                row = row[:len(fieldnames)]
                            migrated_rows.append(row)

                    with open(file_name, mode='w', newline='', encoding='utf-8') as migrated_csv:
                        writer = csv.writer(migrated_csv)
                        writer.writerows(migrated_rows)
                    print_lg('Migrated applied jobs CSV schema to include "Search Term" column.')
    except Exception as migration_error:
        print_lg("Applied jobs CSV schema migration skipped due to error.", migration_error)

    try:
        with open(file_name, mode='a', newline='', encoding='utf-8') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            if csv_file.tell() == 0: writer.writeheader()
            writer.writerow({'Job ID':truncate_for_csv(job_id), 'Title':truncate_for_csv(title), 'Company':truncate_for_csv(company), 'Work Location':truncate_for_csv(work_location), 'Work Style':truncate_for_csv(work_style), 
                            'About Job':truncate_for_csv(description[:300] + ("..." if len(description) > 300 else "")), 'Experience required': truncate_for_csv(experience_required), 'Skills required':truncate_for_csv(skills), 
                                'HR Name':truncate_for_csv(hr_name), 'HR Link':truncate_for_csv(hr_link), 'Resume':truncate_for_csv(resume), 'Search Term':truncate_for_csv(search_term), 'Re-posted':truncate_for_csv(reposted), 
                                'Date Posted':fmt_date(date_listed), 'Date Applied':fmt_datetime(date_applied), 'Job Link':truncate_for_csv(job_link), 
                                'External Job link':truncate_for_csv(application_link), 'Questions Found':truncate_for_csv(questions_formatted), 'Connect Request':truncate_for_csv(connect_request)})
        csv_file.close()
    except Exception as e:
        print_lg("Failed to update submitted jobs list!", e)
        pyautogui.alert("Failed to update the excel of applied jobs!\nProbably because of 1 of the following reasons:\n1. The file is currently open or in use by another program\n2. Permission denied to write to the file\n3. Failed to find the file", "Failed Logging")



# Function to discard the job application
def discard_job() -> None:
    actions.send_keys(Keys.ESCAPE).perform()
    wait_span_click(driver, 'Discard', 2)


def recover_browser_session(reason: Exception | str = "") -> bool:
    '''Attempt a one-time browser/session recovery and LinkedIn re-login.'''
    global driver, actions, wait, linkedIn_tab, tabs_count

    print_lg(f"Attempting browser session recovery... Reason: {reason}")
    try:
        try:
            if driver:
                driver.quit()
        except Exception:
            pass

        if auto_close_conflicting_chrome and bot_profile_dir:
            close_conflicting_chrome_sessions(bot_profile_dir)

        _, driver, actions, wait = createChromeSession()

        tabs_count = len(driver.window_handles)
        driver.get("https://www.linkedin.com/login")
        if not is_logged_in_LN():
            login_LN()
        linkedIn_tab = driver.current_window_handle
        print_lg("Browser session recovery successful.")
        return True
    except Exception as recovery_error:
        print_lg("Browser session recovery failed.", recovery_error)
        return False






# Function to apply to jobs
def apply_to_jobs(
    search_terms: list[str],
    per_term_cap: int = None,
    force_under_10: bool = False,
    date_posted_override: str | None = None,
    search_location_override: str | None = None,
    location_override: list[str] | None = None,
    stage_label: str | None = None,
) -> int:
    '''
    Apply to jobs across all search terms.
    per_term_cap: max applications per search term this pass (overrides session_switch_cap if lower).
    force_under_10: override config to require "Under 10 applicants" filter for this pass.
    date_posted_override: applies this date filter for this pass.
    Returns total applications submitted this pass.
    '''
    applied_jobs = get_applied_job_ids()
    rejected_jobs = set()
    blacklisted_companies = set()
    global current_city, failed_count, skip_count, easy_applied_count, external_jobs_count, tabs_count, pause_before_submit, useNewResume
    current_city = current_city.strip()
    # Vary interaction tempo and cap run size to reduce aggressive behavior patterns.
    session_click_gap = round(uniform(1.2, 3.2), 1)
    session_switch_cap = min(switch_number, 6)   # Hard safety cap: never exceed 6/term regardless of config (30 total with 10 terms)
    if per_term_cap is not None:
        session_switch_cap = min(per_term_cap, session_switch_cap)
    pass_label = stage_label or ("Pass 1 [<10 applicants]" if force_under_10 else "Pass 2 [all jobs]")
    selected_date_posted = date_posted_override or date_posted
    print_lg(f"Session pacing: click_gap={session_click_gap}s, max applies/search={session_switch_cap} | {pass_label} | date_posted={selected_date_posted}")
    pass_total = 0

    if randomize_search_order:  shuffle(search_terms)
    last_uploaded_resume = None  # track which resume was last uploaded to trigger re-upload on term switch
    max_term_recovery_attempts = 2
    term_recovery_attempts: dict[str, int] = {}
    pending_search_terms = deque(search_terms)
    while pending_search_terms:
        searchTerm = pending_search_terms.popleft()
        # Select tailored resume for this search term; trigger re-upload if it differs from last.
        active_resume = get_resume_for_term(searchTerm)
        if active_resume != last_uploaded_resume:
            useNewResume = True

        driver.get(f"https://www.linkedin.com/jobs/search/?keywords={searchTerm}")
        print_lg("\n________________________________________________________________________________________________________________________\n")
        print_lg(f'\n>>>> Now searching for "{searchTerm}" <<<<\n\n')

        filters_ok = apply_filters(
            force_under_10=force_under_10,
            date_posted_override=selected_date_posted,
            search_location_override=search_location_override,
            location_override=location_override,
        )
        if not filters_ok:
            print_lg(f'Skipping search term "{searchTerm}" because filter preflight verification failed.')
            continue

        if has_no_matching_jobs_banner():
            print_lg(f'No matching jobs found for "{searchTerm}". Skipping to next term.')
            continue

        current_count = 0
        try:
            while current_count < session_switch_cap:
                if has_no_matching_jobs_banner():
                    print_lg(f'No matching jobs found for "{searchTerm}". Skipping to next term.')
                    break
                if detect_daily_easy_apply_limit("apply-loop"):
                    print_lg("\n###############  Daily application limit for Easy Apply is reached!  ###############\n")
                    return pass_total
                if has_security_challenge():
                    print_lg("Security challenge detected. Pausing automation to protect account health.")
                    sleep(randint(1800, 3600))
                    return pass_total
                # Wait until job listings are loaded
                wait.until(EC.presence_of_all_elements_located((By.XPATH, "//li[@data-occludable-job-id]")))

                pagination_element, current_page = get_page_info()

                # Find all job listings in current page
                buffer(3)
                job_listings = driver.find_elements(By.XPATH, "//li[@data-occludable-job-id]")  

                if not job_listings and (has_no_matching_jobs_banner() or has_suggested_jobs_context()):
                    print_lg(f'No visible job cards for "{searchTerm}". Skipping to next term.')
                    break

                if has_no_matching_jobs_banner():
                    print_lg(f'No matching jobs found for "{searchTerm}". Skipping to next term.')
                    break

            
                for job in job_listings:
                    if keep_screen_awake: pyautogui.press('shiftright')
                    if current_count >= session_switch_cap: break
                    print_lg("\n-@-\n")
                    if detect_daily_easy_apply_limit(f"job {job_id if 'job_id' in locals() else ''}"):
                        print_lg("\n###############  Daily application limit for Easy Apply is reached!  ###############\n")
                        return pass_total

                    job_id,title,company,work_location,work_style,skip,needs_description_relevance_check = get_job_main_details(job, blacklisted_companies, rejected_jobs, searchTerm)
                    
                    if skip: continue
                    # Redundant fail safe check for applied jobs!
                    try:
                        if job_id in applied_jobs or find_by_class(driver, "jobs-s-apply__application-link", 2):
                            print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id}!')
                            continue
                    except Exception:
                        print_lg(f'Trying to Apply to "{title} | {company}" job. Job ID: {job_id}')

                    # Simulate reading behavior before interacting with Easy Apply.
                    read_pause = uniform(12.0, 38.0)
                    sleep(read_pause)
                    if randint(1, 3) == 1:
                        try:
                            scroll_amount = randint(180, 520)
                            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                            sleep(uniform(0.4, 1.2))
                            driver.execute_script(f"window.scrollBy(0, -{scroll_amount});")
                        except Exception:
                            pass

                    job_link = "https://www.linkedin.com/jobs/view/"+job_id
                    application_link = "Easy Applied"
                    date_applied = "Pending"
                    hr_link = "Unknown"
                    hr_name = "Unknown"
                    connect_request = "In Development" # Still in development
                    date_listed = "Unknown"
                    skills = empty_skills_response()
                    resume = "Pending"
                    reposted = False
                    questions_list = None
                    screenshot_name = "Not Available"
                    jobs_top_card = None

                    try:
                        rejected_jobs, blacklisted_companies, jobs_top_card = check_blacklist(rejected_jobs,job_id,company,blacklisted_companies)
                    except ValueError as e:
                        print_lg(e, 'Skipping this job!\n')
                        failed_job(job_id, job_link, resume, date_listed, "Found Blacklisted words in About Company", e, "Skipped", screenshot_name)
                        skip_count += 1
                        continue
                    except Exception:
                        print_lg("Failed to scroll to About Company!")

                    if min_skills_match_percentage > 0:
                        skills_match = get_linkedin_skills_match()
                        if skills_match is not None:
                            matched, total = skills_match
                            pct = int(matched / total * 100) if total > 0 else 100
                            print_lg(f"LinkedIn skills match: {matched} of {total} ({pct}%)")
                            if pct < min_skills_match_percentage:
                                reason = f"Skills match too low: {matched} of {total} ({pct}% < {min_skills_match_percentage}% required)"
                                print_lg(reason + " Skipping this job!")
                                failed_job(job_id, job_link, resume, date_listed, "Low skills match", reason, "Skipped", screenshot_name)
                                rejected_jobs.add(job_id)
                                skip_count += 1
                                continue

                    # Hiring Manager info
                    try:
                        hr_info_card = WebDriverWait(driver,2).until(EC.presence_of_element_located((By.CLASS_NAME, "hirer-card__hirer-information")))
                        hr_link = hr_info_card.find_element(By.TAG_NAME, "a").get_attribute("href")
                        hr_name = hr_info_card.find_element(By.TAG_NAME, "span").text
                        # if connect_hr:
                        #     driver.switch_to.new_window('tab')
                        #     driver.get(hr_link)
                        #     wait_span_click("More")
                        #     wait_span_click("Connect")
                        #     wait_span_click("Add a note")
                        #     message_box = driver.find_element(By.XPATH, "//textarea")
                        #     message_box.send_keys(connect_request_message)
                        #     if close_tabs: driver.close()
                        #     driver.switch_to.window(linkedIn_tab) 
                        # def message_hr(hr_info_card):
                        #     if not hr_info_card: return False
                        #     hr_info_card.find_element(By.XPATH, ".//span[normalize-space()='Message']").click()
                        #     message_box = driver.find_element(By.XPATH, "//div[@aria-label='Write a message…']")
                        #     message_box.send_keys()
                        #     try_xp(driver, "//button[normalize-space()='Send']")        
                    except Exception:
                        print_lg(f'HR info was not given for "{title}" with Job ID: {job_id}!')


                    # Calculation of date posted
                    try:
                        # try: time_posted_text = find_by_class(driver, "jobs-unified-top-card__posted-date", 2).text
                        # except: 
                        if jobs_top_card is None:
                            raise Exception("jobs_top_card was not set (check_blacklist failed)")
                        time_posted_text = jobs_top_card.find_element(By.XPATH, './/span[contains(normalize-space(), " ago")]').text
                        print("Time Posted: " + time_posted_text)
                        if time_posted_text.__contains__("Reposted"):
                            reposted = True
                            time_posted_text = time_posted_text.replace("Reposted", "")
                        date_listed = calculate_date_posted(time_posted_text.strip())
                    except Exception as e:
                        print_lg("Failed to calculate the date posted!",e)


                    description, experience_required, skip, reason, message = get_job_description()
                    if skip:
                        print_lg(message)
                        failed_job(job_id, job_link, resume, date_listed, reason, message, "Skipped", screenshot_name, full_job_description=description)
                        rejected_jobs.add(job_id)
                        skip_count += 1
                        continue

                    if needs_description_relevance_check and not is_description_relevant(description, title, searchTerm):
                        reason = f'skip_reason=title_uncertain_description_not_relevant, search_term="{searchTerm}"'
                        print_lg(f'Skipping "{title} | {company}" job ({reason}). Job ID: {job_id}!')
                        failed_job(job_id, job_link, resume, date_listed, "Balanced relevance check failed", reason, "Skipped", screenshot_name, full_job_description=description)
                        rejected_jobs.add(job_id)
                        skip_count += 1
                        continue
                    if needs_description_relevance_check:
                        print_lg(f'Balanced relevance check passed for "{title} | {company}". Job ID: {job_id}!')

                    try:
                        skills = extract_skills_from_job_description(description)
                        extracted_skill_count = count_extracted_skills(skills)
                        if extracted_skill_count:
                            print_lg(f"Extracted {extracted_skill_count} skill matches using NLP")
                        else:
                            print_lg("Skills extraction returned empty schema using NLP")
                    except Exception as e:
                        print_lg("Skills extraction failed using NLP, using empty schema", e)
                        skills = empty_skills_response()

                    
                    uploaded = False
                    # Case 1: Easy Apply Button
                    if try_xp(driver, ".//button[contains(@class,'jobs-apply-button') and contains(@class, 'artdeco-button--3') and contains(@aria-label, 'Easy')]"):
                        try: 
                            modal = None
                            try:
                                errored = ""
                                easy_apply_stage = "open-modal"
                                dismiss_job_search_safety_reminder("easy-apply-open")
                                modal = find_by_class(driver, "jobs-easy-apply-modal")
                                # Initial step may already be on questions/review; avoid noisy failure logs.
                                easy_apply_stage = "initial-next"
                                click_modal_action(modal, "next", retries=2)
                                # if description != "Unknown":
                                #     resume = create_custom_resume(description)
                                resume = os.path.join(os.path.basename(os.path.dirname(active_resume)), os.path.basename(active_resume))
                                next_button = True
                                questions_list: list[QuestionEntry] = []
                                next_counter = 0
                                ai_retry_attempted = False
                                while next_button:
                                    dismiss_job_search_safety_reminder("easy-apply-loop")
                                    modal = find_by_class(driver, "jobs-easy-apply-modal")
                                    if detect_daily_easy_apply_limit("easy-apply-modal"):
                                        print_lg("\n###############  Daily application limit for Easy Apply is reached!  ###############\n")
                                        return pass_total
                                    next_counter += 1
                                    if next_counter >= 15:
                                        if not ai_retry_attempted:
                                            # One-shot AI re-answer pass before resorting to pause or fail
                                            print_lg("Stuck on questions page, attempting AI re-answer pass...")
                                            questions_list = answer_questions(modal, questions_list, work_location, job_description=description)
                                            ai_retry_attempted = True
                                            next_counter = 1
                                            continue
                                        if pause_at_failed_question:
                                            screenshot(driver, job_id, "Needed manual intervention for failed question")
                                            pyautogui.alert("Couldn't answer one or more questions.\nPlease click \"Continue\" once done.\nDO NOT CLICK Back, Next or Review button in LinkedIn.\n\n\n\n\nYou can turn off \"Pause at failed question\" setting in config.py", "Help Needed", "Continue")
                                            next_counter = 1
                                            continue
                                        if questions_list: print_lg("Stuck for one or some of the following questions...", questions_list)
                                        screenshot_name = screenshot(driver, job_id, "Failed at questions")
                                        errored = "stuck"
                                        raise Exception("Seems like stuck in a continuous loop of next, probably because of new questions.")
                                    easy_apply_stage = "answer-questions"
                                    questions_list = answer_questions(modal, questions_list, work_location, job_description=description)
                                    if useNewResume and not uploaded: uploaded, resume = upload_resume(modal, active_resume)
                                    if detect_daily_easy_apply_limit("easy-apply-modal"):
                                        print_lg("\n###############  Daily application limit for Easy Apply is reached!  ###############\n")
                                        return pass_total
                                    if find_modal_action_button(modal, "review"):
                                        next_button = False
                                        easy_apply_stage = "review-click"
                                        click_modal_action(modal, "review", retries=3)
                                        buffer(click_gap)
                                        break
                                    easy_apply_stage = "next-click"
                                    next_button = click_modal_action(modal, "next", retries=3)
                                    if not next_button:
                                        break
                                    buffer(click_gap)
                                    # After clicking Next, detect inline field errors and rectify them before next loop
                                    easy_apply_stage = "rectify-field-errors"
                                    rectified = rectify_field_errors(modal, questions_list, job_description=description)
                                    if rectified:
                                        next_counter = max(next_counter - 2, 0)  # Give back counter budget for error-recovery iterations

                            except NoSuchElementException: errored = "nose"
                            finally:
                                if questions_list and errored != "stuck":
                                    formatted_qs = "\n".join(f"  Q: {q[0]}\n  A: {q[1]}" for q in questions_list)
                                    print_lg(f"Answered the following questions...\n{formatted_qs}")
                                try:
                                    modal = find_by_class(driver, "jobs-easy-apply-modal")
                                    easy_apply_stage = "review-final"
                                    click_modal_action(modal, "review", retries=2)
                                    buffer(click_gap)
                                except Exception:
                                    pass
                                cur_pause_before_submit = pause_before_submit
                                if errored != "stuck" and cur_pause_before_submit:
                                    decision = pyautogui.confirm('1. Please verify your information.\n2. If you edited something, please return to this final screen.\n3. DO NOT CLICK "Submit Application".\n\n\n\n\nYou can turn off "Pause before submit" setting in config.py\nTo TEMPORARILY disable pausing, click "Disable Pause"', "Confirm your information",["Disable Pause", "Discard Application", "Submit Application"])
                                    if decision == "Discard Application": raise Exception("Job application discarded by user!")
                                    pause_before_submit = False if "Disable Pause" == decision else True
                                    # try_xp(modal, ".//span[normalize-space(.)='Review']")
                                if not modal:
                                    try:
                                        modal = find_by_class(driver, "jobs-easy-apply-modal")
                                    except Exception:
                                        modal = None
                                if modal:
                                    follow_company(modal)
                                submit_clicked = False
                                try:
                                    modal = find_by_class(driver, "jobs-easy-apply-modal")
                                    easy_apply_stage = "submit-click"
                                    submit_clicked = click_modal_action(modal, "submit", retries=3)
                                except Exception:
                                    submit_clicked = False

                                if submit_clicked or wait_span_click(driver, "Submit application", 2, scrollTop=True):
                                    if detect_daily_easy_apply_limit("submit-stage"):
                                        print_lg("\n###############  Daily application limit for Easy Apply is reached!  ###############\n")
                                        return pass_total
                                    date_applied = datetime.now()
                                    try:
                                        modal = find_by_class(driver, "jobs-easy-apply-modal")
                                        easy_apply_stage = "done-click"
                                        done_clicked = click_modal_action(modal, "done", retries=2)
                                    except Exception:
                                        done_clicked = False
                                    if not done_clicked and not wait_span_click(driver, "Done", 2):
                                        actions.send_keys(Keys.ESCAPE).perform()
                                    # Cooldown after submission to avoid bursty submit patterns.
                                    sleep(uniform(8.0, 22.0))
                                elif errored != "stuck" and cur_pause_before_submit and "Yes" in pyautogui.confirm("You submitted the application, didn't you 😒?", "Failed to find Submit Application!", ["Yes", "No"]):
                                    date_applied = datetime.now()
                                    wait_span_click(driver, "Done", 2)
                                    sleep(uniform(8.0, 22.0))
                                else:
                                    if detect_daily_easy_apply_limit("submit-not-found"):
                                        print_lg("\n###############  Daily application limit for Easy Apply is reached!  ###############\n")
                                        return pass_total
                                    easy_apply_stage = "submit-not-found"
                                    print_lg("Since, Submit Application failed, discarding the job application...")
                                    # if screenshot_name == "Not Available":  screenshot_name = screenshot(driver, job_id, "Failed to click Submit application")
                                    # else:   screenshot_name = [screenshot_name, screenshot(driver, job_id, "Failed to click Submit application")]
                                    if errored == "nose": raise Exception("Failed to click Submit application 😑")


                        except Exception as e:
                            print_lg("Failed to Easy apply!")
                            if detect_daily_easy_apply_limit("easy-apply-exception"):
                                print_lg("\n###############  Daily application limit for Easy Apply is reached!  ###############\n")
                                return pass_total
                            stage_info = locals().get("easy_apply_stage", "unknown")
                            critical_error_log(f"Easy Apply failed at stage: {stage_info}",e)
                            failed_job(job_id, job_link, resume, date_listed, f"Problem in Easy Applying ({stage_info})", e, application_link, screenshot_name)
                            failed_count += 1
                            discard_job()
                            continue
                    else:
                        # Case 2: Apply externally
                        skip, application_link, tabs_count = external_apply(pagination_element, job_id, job_link, resume, date_listed, application_link, screenshot_name)
                        if dailyEasyApplyLimitReached:
                            print_lg("\n###############  Daily application limit for Easy Apply is reached!  ###############\n")
                            return pass_total
                        if skip: continue

                    submitted_jobs(job_id, title, company, work_location, work_style, description, experience_required, skills, hr_name, hr_link, resume, reposted, date_listed, date_applied, job_link, application_link, questions_list, connect_request, searchTerm)
                    if uploaded:
                        useNewResume = False
                        last_uploaded_resume = active_resume  # remember what was uploaded for this term

                    print_lg(f'Successfully saved "{title} | {company}" job. Job ID: {job_id} info')
                    current_count += 1
                    pass_total += 1
                    if application_link == "Easy Applied": easy_applied_count += 1
                    else:   external_jobs_count += 1
                    applied_jobs.add(job_id)



                # Switching to next page
                if pagination_element == None:
                    print_lg("Couldn't find pagination element, probably at the end page of results!")
                    break
                if is_easy_apply_modal_open():
                    print_lg("Easy Apply modal still open before pagination. Trying to close it...")
                    if not close_easy_apply_modal_if_open():
                        print_lg("Could not close Easy Apply modal safely. Ending pagination for this term.")
                        break
                try:
                    next_page_button = pagination_element.find_element(By.XPATH, f"//button[@aria-label='Page {current_page+1}']")
                    switched_page = False
                    for _ in range(2):
                        try:
                            next_page_button.click()
                            switched_page = True
                            break
                        except ElementClickInterceptedException:
                            print_lg("Pagination click intercepted, attempting to close modal and retry.")
                            if not close_easy_apply_modal_if_open():
                                break
                            sleep(0.4)
                    if not switched_page:
                        print_lg("Unable to paginate safely with current overlays. Ending pagination for this term.")
                        break
                    print_lg(f"\n>-> Now on Page {current_page+1} \n")
                except NoSuchElementException:
                    print_lg(f"\n>-> Didn't find Page {current_page+1}. Probably at the end page of results!\n")
                    break

        except (NoSuchWindowException, WebDriverException) as e:
            print_lg("Browser window closed or session is invalid during apply loop.", e)
            term_recovery_attempts[searchTerm] = term_recovery_attempts.get(searchTerm, 0) + 1
            current_attempt = term_recovery_attempts[searchTerm]
            if recover_browser_session(e):
                if current_attempt < max_term_recovery_attempts:
                    pending_search_terms.append(searchTerm)
                    print_lg(f'Recovery succeeded. Re-queueing "{searchTerm}" (attempt {current_attempt}/{max_term_recovery_attempts}).')
                    continue
                print_lg(f'Recovery succeeded but retry budget exhausted for "{searchTerm}". Skipping this term.')
                continue
            print_lg("Recovery failed. Ending application process.")
            raise e # Re-raise to be caught by main
        except Exception as e:
            print_lg("Failed to find Job listings!")
            critical_error_log("In Applier", e)
            try:
                print_lg(driver.page_source, pretty=True)
            except Exception as page_source_error:
                print_lg(f"Failed to get page source, browser might have crashed. {page_source_error}")
            # print_lg(e)

    return pass_total

        
def run(total_runs: int) -> int:
    if dailyEasyApplyLimitReached:
        return total_runs
    print_lg("\n########################################################################################################################\n")
    print_lg(f"Date and Time: {datetime.now()}")
    print_lg(f"Cycle number: {total_runs}")
    print_lg(f"Currently looking for jobs posted within '{date_posted}' and sorting them by '{sort_by}'")

    def _ordered_unique(values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            text = str(value).strip()
            if not text:
                continue
            key = normalize_select_text(text)
            if key in seen:
                continue
            seen.add(key)
            result.append(text)
        return result

    def _build_country_priority() -> list[str]:
        configured = _ordered_unique(location)
        if search_location.strip() and normalize_select_text(search_location) not in {normalize_select_text(x) for x in configured}:
            configured.insert(0, search_location.strip())

        normalized_map = {normalize_select_text(country): country for country in configured}
        front_norm = ["france", "united kingdom"]
        front = [normalized_map[norm] for norm in front_norm if norm in normalized_map]

        front_keys = {normalize_select_text(country) for country in front}
        remaining = [country for country in configured if normalize_select_text(country) not in front_keys]

        english_group = {"ireland", "malta", "cyprus"}
        french_group = {"belgium", "luxembourg", "switzerland", "monaco"}

        english_first = [country for country in remaining if normalize_select_text(country) in english_group]
        french_first = [country for country in remaining if normalize_select_text(country) in french_group]
        grouped_keys = {normalize_select_text(country) for country in english_first + french_first}
        rest = [country for country in remaining if normalize_select_text(country) not in grouped_keys]

        return front + english_first + french_first + rest

    def _build_stage_plan() -> list[dict[str, str | bool]]:
        countries = _build_country_priority()
        if not countries:
            countries = [search_location.strip() or "France"]

        core_keys = {"france", "united kingdom"}
        core = [country for country in countries if normalize_select_text(country) in core_keys]
        others = [country for country in countries if normalize_select_text(country) not in core_keys]

        stages: list[dict[str, str | bool]] = []

        # Stage 1: Past 24h under-10 first, then Past 24h all-applicants (France, then UK).
        for country in core:
            stages.append({"country": country, "date": "Past 24 hours", "under10": True})
            stages.append({"country": country, "date": "Past 24 hours", "under10": False})

        # Stage 2: Past week under-10, then Past week all-applicants (France, then UK).
        for country in core:
            stages.append({"country": country, "date": "Past week", "under10": True})
            stages.append({"country": country, "date": "Past week", "under10": False})

        # Stage 3: Same sequence for remaining configured countries.
        for country in others:
            stages.append({"country": country, "date": "Past 24 hours", "under10": True})
            stages.append({"country": country, "date": "Past week", "under10": True})
            stages.append({"country": country, "date": "Past week", "under10": False})

        return stages

    stage_plan = _build_stage_plan()
    under10_cap = max(1, switch_number // 2)

    for stage_index, stage in enumerate(stage_plan, start=1):
        if dailyEasyApplyLimitReached:
            break
        country = str(stage["country"])
        stage_date = str(stage["date"])
        stage_under10 = bool(stage["under10"])
        stage_cap = under10_cap if stage_under10 else switch_number
        stage_label = f"Stage {stage_index}/{len(stage_plan)} | country={country} | date={stage_date} | under10={stage_under10}"
        print_lg(stage_label)
        stage_total = apply_to_jobs(
            search_terms,
            per_term_cap=stage_cap,
            force_under_10=stage_under10,
            date_posted_override=stage_date,
            search_location_override=country,
            location_override=[country],
            stage_label=stage_label,
        )
        print_lg(f"Completed {stage_label} | applied this stage={stage_total}")

    print_lg("########################################################################################################################\n")
    if run_non_stop and not dailyEasyApplyLimitReached:
        print_lg("Sleeping for 10 min...")
        sleep(300)
        print_lg("Few more min... Gonna start with in next 5 min...")
        sleep(300)
    buffer(3)
    return total_runs + 1



chatGPT_tab = False
linkedIn_tab = False

def main() -> None:
    total_runs = 1
    try:
        global linkedIn_tab, tabs_count, useNewResume, aiClient
        alert_title = "Error Occurred. Closing Browser!"
        print_lg(f"---- main() started at {datetime.now()} ----")
        validate_config()
        
        if not os.path.exists(default_resume_path):
            pyautogui.alert(text='Your default resume "{}" is missing! Please update it\'s folder path "default_resume_path" in config.py\n\nOR\n\nAdd a resume with exact name and path (check for spelling mistakes including cases).\n\n\nFor now the bot will continue using your previous upload from LinkedIn!'.format(default_resume_path), title="Missing Resume", button="OK")
            useNewResume = False
        
        # Login to LinkedIn
        tabs_count = len(driver.window_handles)
        driver.get("https://www.linkedin.com/login")
        if not is_logged_in_LN(): login_LN()
        
        linkedIn_tab = driver.current_window_handle

        # # Login to ChatGPT in a new tab for resume customization
        # if use_resume_generator:
        #     try:
        #         driver.switch_to.new_window('tab')
        #         driver.get("https://chat.openai.com/")
        #         if not is_logged_in_GPT(): login_GPT()
        #         open_resume_chat()
        #         global chatGPT_tab
        #         chatGPT_tab = driver.current_window_handle
        #     except Exception as e:
        #         print_lg("Opening OpenAI chatGPT tab failed!")
        if use_AI:
            if ai_provider == "openai":
                aiClient = ai_create_openai_client()
            ##> ------ Yang Li : MARKYangL - Feature ------
            # Create DeepSeek client
            elif ai_provider == "deepseek":
                aiClient = deepseek_create_client()
            elif ai_provider == "gemini":
                aiClient = gemini_create_client()
            ##<

            try:
                about_company_for_ai = " ".join([word for word in (first_name+" "+last_name).split() if len(word) > 3])
                print_lg(f"Extracted about company info for AI: '{about_company_for_ai}'")
            except Exception as e:
                print_lg("Failed to extract about company info!", e)
        
        # Start applying to jobs
        driver.switch_to.window(linkedIn_tab)
        total_runs = run(total_runs)
        while(run_non_stop):
            if cycle_date_posted:
                date_options = ["Any time", "Past month", "Past week", "Past 24 hours"]
                global date_posted
                try:
                    current_idx = date_options.index(date_posted)
                except ValueError:
                    current_idx = 0
                if stop_date_cycle_at_24hr:
                    # Advance one step each cycle and clamp at "Past 24 hours".
                    date_posted = date_options[min(current_idx + 1, len(date_options) - 1)]
                else:
                    # Advance one step and wrap around to the beginning.
                    date_posted = date_options[(current_idx + 1) % len(date_options)]
            if alternate_sortby:
                global sort_by
                sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
                total_runs = run(total_runs)
                sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"
            total_runs = run(total_runs)
            if dailyEasyApplyLimitReached:
                break
        

    except (NoSuchWindowException, WebDriverException) as e:
        print_lg("Browser window closed or session is invalid. Exiting.", e)
    except Exception as e:
        critical_error_log("In Applier Main", e)
        pyautogui.alert(e,alert_title)
    finally:
        summary = "Total runs: {}\nJobs Easy Applied: {}\nExternal job links collected: {}\nTotal applied or collected: {}\nFailed jobs: {}\nIrrelevant jobs skipped: {}\n".format(total_runs,easy_applied_count,external_jobs_count,easy_applied_count + external_jobs_count,failed_count,skip_count)
        print_lg(summary)
        print_lg("\n\nTotal runs:                     {}".format(total_runs))
        print_lg("Jobs Easy Applied:              {}".format(easy_applied_count))
        print_lg("External job links collected:   {}".format(external_jobs_count))
        print_lg("                              ----------")
        print_lg("Total applied or collected:     {}".format(easy_applied_count + external_jobs_count))
        print_lg("\nFailed jobs:                    {}".format(failed_count))
        print_lg("Irrelevant jobs skipped:        {}\n".format(skip_count))
        if randomly_answered_questions: print_lg("\n\nQuestions randomly answered:\n  {}  \n\n".format(";\n".join(str(question) for question in randomly_answered_questions)))
        if tabs_count >= 10:
            print_lg("\nNOTE: YOU HAVE 10+ TABS OPEN. Close or bookmark them before next run or the bot may not work correctly.")
        ##> ------ Yang Li : MARKYangL - Feature ------
        if use_AI and aiClient:
            try:
                if ai_provider.lower() == "openai":
                    ai_close_openai_client(aiClient)
                elif ai_provider.lower() == "deepseek":
                    ai_close_openai_client(aiClient)
                elif ai_provider.lower() == "gemini":
                    pass # Gemini client does not need to be closed
                print_lg(f"Closed {ai_provider} AI client.")
            except Exception as e:
                print_lg("Failed to close AI client:", e)
        ##<
        try:
            if driver:
                driver.quit()
        except WebDriverException as e:
            print_lg("Browser already closed.", e)
        except Exception as e: 
            critical_error_log("When quitting...", e)


if __name__ == "__main__":
    main()
