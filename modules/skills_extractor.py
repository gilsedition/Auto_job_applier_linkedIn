import re
import unicodedata


SKILL_SCHEMA_KEYS = (
    "tech_stack",
    "technical_skills",
    "other_skills",
    "required_skills",
    "nice_to_have",
)


TECH_STACK_PATTERNS = {
    "Excel": (r"\bmicrosoft excel\b", r"\bms excel\b", r"\bexcel\b"),
    "Microsoft Office": (r"\bmicrosoft office\b", r"\bms office\b", r"\boffice suite\b"),
    "PowerPoint": (r"\bmicrosoft powerpoint\b", r"\bpowerpoint\b"),
    "SAP": (r"\bsap\b",),
    "SAP Finance": (r"\bsap finance\b", r"\bsap fi\b"),
    "S/4HANA": (r"\bs/?4hana\b", r"\bs 4hana\b"),
    "ECC6": (r"\becc6\b", r"\becc 6\b"),
    "ERP": (r"\berp\b",),
    "Oracle": (r"\boracle\b",),
    "NetSuite": (r"\bnetsuite\b",),
    "QuickBooks": (r"\bquickbooks\b",),
    "Power BI": (r"\bpower bi\b",),
    "Tableau": (r"\btableau\b",),
    "Power Query": (r"\bpower query\b",),
    "DAX": (r"\bdax\b",),
    "Power Query M": (r"\bpower query m\b",),
    "VBA": (r"\bvba\b",),
    "SQL": (r"\bsql\b",),
    "Python": (r"\bpython\b",),
    "Java": (r"\bjava\b",),
    "JavaScript": (r"\bjavascript\b",),
    "TypeScript": (r"\btypescript\b",),
    "React": (r"\breact(?:\.js)?\b",),
    "Node.js": (r"\bnode(?:\.js| js)?\b",),
    ".NET": (r"\b\.net\b", r"\bdotnet\b"),
    "C#": (r"\bc#\b", r"\bcsharp\b"),
    "Spring Boot": (r"\bspring boot\b",),
    "MongoDB": (r"\bmongodb\b",),
    "PostgreSQL": (r"\bpostgres(?:ql)?\b",),
    "MySQL": (r"\bmysql\b",),
    "Elasticsearch": (r"\belasticsearch\b",),
    "Algolia": (r"\balgolia\b",),
    "AWS": (r"\baws\b", r"\bamazon web services\b"),
    "Azure": (r"\bazure\b",),
    "GCP": (r"\bgcp\b", r"\bgoogle cloud\b"),
    "Jira": (r"\bjira\b",),
    "Confluence": (r"\bconfluence\b",),
    "UML": (r"\buml\b",),
    "BPMN": (r"\bbpmn\b",),
    "HPQC": (r"\bhpqc\b", r"\bhp qc\b"),
    "Sparx EA": (r"\bsparx ea\b", r"\benterprise architect\b"),
}


TECHNICAL_SKILLS_PATTERNS = {
    "Accounting": (r"\baccounting\b",),
    "Financial Analysis": (r"\bfinancial analys(?:is|es)\b", r"\bfinancial analyst\b"),
    "Financial Reporting": (r"\bfinancial reporting\b",),
    "Financial Operations": (r"\bfinancial operations?\b",),
    "Billing": (r"\bbilling\b", r"\binvoic(?:e|ing)\b"),
    "General Ledger": (r"\bgeneral ledgers?\b", r"\bgeneral ledger\b"),
    "Accounts Payable": (r"\baccounts payable\b",),
    "Accounts Receivable": (r"\baccounts receivable\b",),
    "Collections": (r"\bcollections\b",),
    "Reconciliation": (r"\breconciliation(?:s)?\b", r"\breconcile\b"),
    "Month-End Close": (r"\bmonth[- ]end close\b", r"\bmonth end close\b"),
    "Year-End Close": (r"\byear[- ]end close\b", r"\byear end close\b"),
    "Forecasting": (r"\bforecasting\b",),
    "Budgeting": (r"\bbudgeting\b", r"\bbudget management\b"),
    "Audit": (r"\baudit(?:ing)?\b",),
    "Tax": (r"\btax(?:ation)?\b",),
    "IFRS": (r"\bifrs\b",),
    "GAAP": (r"\bgaap\b",),
    "Treasury": (r"\btreasury\b",),
    "Payroll": (r"\bpayroll\b",),
    "Internal Controls": (r"\binternal controls?\b", r"\bsox\b"),
    "Variance Analysis": (r"\bvariance analys(?:is|es)\b",),
    "Cash Flow Management": (r"\bcash flow\b",),
    "Data Analysis": (r"\bdata analysis\b", r"\banalytical reporting\b", r"\banaly[sz]e financial data\b", r"\banaly[sz]e financial data\b", r"\bfinancial data\b"),
    "Data Visualization": (r"\bdata visualization\b", r"\bvisuali[sz]ations?\b"),
    "Dashboard Development": (r"\bdashboards?\b", r"\binteractive reports?\b"),
    "Data Modeling": (r"\bdata models?\b",),
    "Data Quality": (r"\bdata quality\b",),
    "Consolidation": (r"\bconsolidat(?:e|ion)\b",),
    "KPI Analysis": (r"\bkpis?\b", r"\boperational metrics\b"),
    "Business Intelligence": (r"\bbusiness intelligence\b", r"\bdata-driven decisions?\b"),
    "Business Analysis": (r"\bbusiness analysis\b", r"\bcomprehension metier\b"),
    "Functional Analysis": (r"\bfunctional analysis\b", r"\banalyste fonctionnel\b", r"\bfonctionnel\b"),
    "Requirements Gathering": (r"\brequirements gathering\b", r"\brequirements analysis\b", r"\bfunctional specifications\b", r"\bspecifications fonctionnelles\b"),
    "Documentation": (r"\bdocumentation\b", r"\bredaction\b", r"\btechnical writing\b"),
    "Functional Testing": (r"\bfunctional test(?:ing|s)?\b", r"\btests fonctionnels?\b", r"\btest scenarios?\b", r"\bscenarios? de test\b"),
    "Integration Testing": (r"\bintegration test(?:ing|s)?\b", r"\btests? d integration\b", r"\btests? d'integration\b", r"\btests? fonctionnels? et d integration\b", r"\btests? fonctionnels? et d'integration\b"),
    "UAT": (r"\buser acceptance testing\b", r"\buat\b"),
    "Migration": (r"\bmigration\b",),
    "ERP Implementation": (r"\berp implementation\b", r"\bdeployment\b", r"\bdeploiement\b", r"\bconfiguration\b", r"\bbuild\b"),
    "Process Improvement": (r"\bprocess improvement\b", r"\bcontinuous improvement\b", r"\bamelioration continue\b"),
    "Project Management": (r"\bproject management\b",),
}


OTHER_SKILLS_PATTERNS = {
    "Communication": (r"\bcommunication\b", r"\bcommunicate\b"),
    "Teamwork": (r"\bteamwork\b", r"\bwork in a team\b", r"\btravail en equipe\b", r"\bworking in a team\b", r"\btravailler en equipe\b"),
    "Collaboration": (r"\bcollaboration\b", r"\bcross-functional\b", r"\bcross functional\b", r"\bcross-team\b", r"\bcross team\b", r"\binteragir avec\b"),
    "Leadership": (r"\bleadership\b", r"\blead teams?\b"),
    "Analytical Thinking": (r"\banalytical\b", r"\besprit analytique\b"),
    "Problem Solving": (r"\bproblem solving\b", r"\bsolve problems\b"),
    "Attention to Detail": (r"\battention to detail\b", r"\bdetail[- ]oriented\b"),
    "Time Management": (r"\btime management\b",),
    "Adaptability": (r"\badaptab(?:ility|le)\b", r"\bflexible\b"),
    "Autonomy": (r"\bautonom(?:y|ous)\b", r"\bautonomie\b", r"\bself-starter\b"),
    "Proactivity": (r"\bproactiv(?:e|ity)\b", r"\binitiative\b", r"\bproactivite\b"),
    "Organization": (r"\borganized\b", r"\borganised\b", r"\bstructured\b", r"\bmethode\b", r"\bmeth(?:odical|odique)\b"),
    "Listening": (r"\blistening\b", r"\becoute\b"),
    "Synthesis": (r"\bsynthesis\b", r"\besprit de synthese\b"),
    "Stakeholder Management": (r"\bstakeholders?\b", r"\bparties prenantes\b"),
    "Presentation Skills": (r"\bpresentation skills?\b", r"\bpresentations?\b", r"\banimer des workshops\b", r"\bworkshops?\b"),
    "Customer Focus": (r"\bcustomer[- ]focus(?:ed)?\b",),
    "English": (r"\benglish\b", r"\banglais\b"),
    "French": (r"\bfrench\b", r"\bfrancais\b"),
    "Dutch": (r"\bdutch\b",),
    "Polish": (r"\bpolish\b",),
    "German": (r"\bgerman\b", r"\ballemand\b"),
    "Spanish": (r"\bspanish\b", r"\bespagnol\b"),
}


SECTION_HEADINGS = {
    "required_skills": {
        "must have",
        "requirements",
        "required",
        "mandatory",
        "minimum requirements",
        "qualifications",
        "your profile",
        "candidate profile",
        "profile",
    },
    "nice_to_have": {
        "nice to have",
        "nice-to-have",
        "preferred",
        "preferred qualifications",
        "bonus",
        "a plus",
    },
    "other_skills": {
        "soft skills",
    },
}


REQUIRED_MARKERS = (
    "must have",
    "required",
    "mandatory",
    "minimum",
    "experience with",
    "experience in",
    "strong knowledge of",
    "maitrise",
    "minimum 5 ans",
    "minimum 3 ans",
    "minimum 2 ans",
    "minimum 1 an",
)


NICE_TO_HAVE_MARKERS = (
    "nice to have",
    "nice-to-have",
    "preferred",
    "bonus",
    "strong plus",
    "souhaite",
    "serait un plus",
    "good to have",
    "preferably",
)


def empty_skills_response() -> dict[str, list[str]]:
    return {key: [] for key in SKILL_SCHEMA_KEYS}


def count_extracted_skills(skills: dict[str, list[str]] | None) -> int:
    if not isinstance(skills, dict):
        return 0
    return sum(len(skills.get(key, [])) for key in SKILL_SCHEMA_KEYS if isinstance(skills.get(key), list))


def has_extracted_skills(skills: dict[str, list[str]] | None) -> bool:
    return count_extracted_skills(skills) > 0


def extract_skills_from_job_description(job_description: str | None) -> dict[str, list[str]]:
    if not job_description or job_description == "Unknown":
        return empty_skills_response()

    extracted_skills = empty_skills_response()
    current_section = None

    for raw_line in _split_candidate_lines(job_description):
        normalized_line = _normalize_for_matching(raw_line)
        if not normalized_line:
            continue

        heading_section = _detect_heading_section(normalized_line)
        if heading_section and _is_heading_like(normalized_line):
            current_section = heading_section
            continue

        requirement_bucket = _detect_requirement_bucket(normalized_line, current_section)
        matched_any = False

        for skill in _find_skills_in_line(normalized_line, TECH_STACK_PATTERNS):
            _append_unique(extracted_skills["tech_stack"], skill)
            _append_requirement_skill(extracted_skills, requirement_bucket, skill)
            matched_any = True

        for skill in _find_skills_in_line(normalized_line, TECHNICAL_SKILLS_PATTERNS):
            _append_unique(extracted_skills["technical_skills"], skill)
            _append_requirement_skill(extracted_skills, requirement_bucket, skill)
            matched_any = True

        for skill in _find_skills_in_line(normalized_line, OTHER_SKILLS_PATTERNS):
            _append_unique(extracted_skills["other_skills"], skill)
            _append_requirement_skill(extracted_skills, requirement_bucket, skill)
            matched_any = True

        if matched_any:
            continue

        fallback_phrase = _extract_fallback_requirement_phrase(raw_line, normalized_line, requirement_bucket)
        if fallback_phrase:
            _append_unique(extracted_skills[requirement_bucket], fallback_phrase)

    return extracted_skills


def _split_candidate_lines(text: str) -> list[str]:
    cleaned_text = text.replace("\r\n", "\n").replace("\r", "\n")
    for marker in ("\u2022", "\u25cf", "\u25aa", "\u25e6", "\u2714", "-@-", "\t"):
        cleaned_text = cleaned_text.replace(marker, "\n")

    candidate_lines = []
    for line in cleaned_text.split("\n"):
        for chunk in re.split(r"[;|]", line):
            cleaned_line = re.sub(r"\s+", " ", chunk).strip(" -*:\u2022")
            if cleaned_line:
                candidate_lines.append(cleaned_line)
    return candidate_lines


def _normalize_for_matching(text: str) -> str:
    normalized_text = unicodedata.normalize("NFKD", text)
    normalized_text = normalized_text.replace("'", " ").replace("\u2019", " ")
    normalized_text = normalized_text.encode("ascii", "ignore").decode("ascii")
    normalized_text = normalized_text.lower()
    normalized_text = normalized_text.replace("&", " and ")
    normalized_text = re.sub(r"[^a-z0-9/+#. ]+", " ", normalized_text)
    normalized_text = re.sub(r"\s+", " ", normalized_text).strip()
    return normalized_text


def _detect_heading_section(normalized_line: str) -> str | None:
    heading_line = normalized_line.rstrip(":")
    for section_name, headings in SECTION_HEADINGS.items():
        if heading_line in headings:
            return section_name
    return None


def _is_heading_like(normalized_line: str) -> bool:
    return len(normalized_line.split()) <= 4 or normalized_line.endswith(":")


def _detect_requirement_bucket(normalized_line: str, current_section: str | None) -> str | None:
    if any(marker in normalized_line for marker in NICE_TO_HAVE_MARKERS):
        return "nice_to_have"
    if current_section == "nice_to_have":
        return "nice_to_have"
    if any(marker in normalized_line for marker in REQUIRED_MARKERS):
        return "required_skills"
    if current_section == "required_skills":
        return "required_skills"
    return None


def _find_skills_in_line(normalized_line: str, patterns: dict[str, tuple[str, ...]]) -> list[str]:
    matches = []
    for skill_name, aliases in patterns.items():
        if any(re.search(pattern, normalized_line) for pattern in aliases):
            matches.append(skill_name)
    return matches


def _extract_fallback_requirement_phrase(raw_line: str, normalized_line: str, requirement_bucket: str | None) -> str | None:
    if requirement_bucket not in {"required_skills", "nice_to_have"}:
        return None

    cleaned_line = raw_line.strip(" -*:")
    if len(cleaned_line) < 6 or len(cleaned_line) > 80:
        return None

    if any(token in normalized_line for token in ("experience", "expertise", "knowledge", "maitrise", "capacite", "ability")):
        return cleaned_line
    return None


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _append_requirement_skill(skills: dict[str, list[str]], requirement_bucket: str | None, skill: str) -> None:
    if requirement_bucket in {"required_skills", "nice_to_have"}:
        _append_unique(skills[requirement_bucket], skill)