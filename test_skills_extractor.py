import json

from modules.skills_extractor import extract_skills_from_job_description


LOGGED_SAP_JOB_DESCRIPTION = """About the job
afarax cherche un(e) SAP Finance Functional Analyst (S/4HANA) freelance. Nous avons besoin de vous!

Le projet:
Notre client dans le secteur de l'energie recherche un(e) SAP Finance Functional Analyst (S/4HANA) pour renforcer son equipe.

En tant qu'Analyste Fonctionnel SAP finance, vous serez responsable de:
Recueillir, analyser et structurer les besoins metiers sous forme de requirements clairs et tracables
Traduire les besoins en specifications fonctionnelles detaillees (SFD)
Produire des diagrammes UML (notamment sequence) sur base des modeles BPMN fournis
Animer des workshops avec les parties prenantes metier et IT
Contribuer a l'analyse et au choix des solutions
Participer a la configuration (build) des solutions dans l'environnement SAP
Definir et executer les scenarios de test (fonctionnels et integration)
Participer activement aux phases de migration (S/4HANA)
Assurer une documentation complete et de qualite

Est-ce vous?
Must have:
\u2714\ufe0f Minimum 5 ans d'experience en tant qu'Analyste Fonctionnel SAP
\u2714\ufe0f Solide expertise SAP Finance (ECC6 & S/4HANA)
\u2714\ufe0f Experience avec les nouvelles structures S/4HANA Finance (Universal Journal, simplification des tables)
\u2714\ufe0f Participation a au moins un projet de migration ou deploiement S/4HANA
\u2714\ufe0f Maitrise de la redaction de specifications fonctionnelles et scenarios de test
\u2714\ufe0f Capacite a produire des diagrammes UML
\u2714\ufe0f Excellente maitrise du francais (C2)
Nice to have:
\u2795 Bonne comprehension des diagrammes BPMN
\u2795 Experience avec des outils de testing (HPQC ou equivalent)
\u2795 Experience avec des outils de modelisation (Sparx EA ou equivalent)
\u2795 Connaissance de l\u2019anglais (min. B1)
\u2795 Expertise en tests fonctionnels et d\u2019integration
Soft skills :
Esprit analytique, structure et methodique
Capacite d\u2019ecoute et de comprehension metier
Proactivite et autonomie
Excellente communication et esprit de synthese
Capacite a travailler en equipe et a interagir avec des profils varies
"""


LOGGED_FINANCIAL_ANALYST_JOB_DESCRIPTION = """About the job
Are you an ambitious finance professional looking to turn financial data into actionable business insights? Join Normec Foodcare at Utrecht (The Netherlands) as a Financial Analyst and play a key role in supporting strategic and operational decision-making across our business units.

Your new role
As a Financial Analyst, you will bridge the gap between raw financial data and actionable insights. You will collect, structure, and analyse financial data, and build high-quality Power BI dashboards and reports that enable data-driven decisions at every level of the organization. You will work closely with the Finance Director, Business Controller, and Group Finance to deliver timely and accurate analytical insights.

Key responsibilities include:
Build, maintain, and continuously improve Power BI dashboards and reports for the Normec Foodcare finance team and Group Finance
Collect and consolidate financial data from multiple business units into clear analyses and comparison tables
Perform financial analyses on KPIs and other operational metrics
Prepare analytical summaries, variance analyses, and ad-hoc reports to support Group Finance requests
Support the monthly and periodic financial reporting cycle with data extraction, validation, and visualization
Identify trends, anomalies, and opportunities in financial data and communicate findings clearly
Collaborate with business unit controllers to ensure data quality and consistency across the organization

Our Offer
A role with significant autonomy, responsibility, and room for personal growth within a professional, ambitious, and informal environment where collaboration and innovation are prioritized.

Your Profile
You are an ambitious and curious early-career finance professional, eager to develop your analytical and reporting skills while contributing to business decisions. You are available to work 32-40 hours per week and meet the following criteria:
Bachelor's or Master's degree in Finance, Accounting, Business Economics, or a related field
Preferably a few years of work experience in a Private Equity (PE) environment (internships and graduate projects count)
Strong Power BI skills: able to independently build data models, create interactive reports, and design meaningful visualizations
Proficient in Excel (Power Query, pivot tables, advanced formulas)
Analytical mindset with strong attention to detail and accuracy
Good communication skills; able to translate numbers into clear stories for non-financial stakeholders
Comfortable working in a dynamic, multi-entity environment
Fluent in English; Dutch is a strong plus

Nice to have:
Experience with DAX and Power Query M language
Familiarity with ERP systems or financial consolidation tools
Basic understanding of SQL or other data querying languages
Affinity with the food industry
"""


def assert_contains(actual: dict[str, list[str]], key: str, expected_values: set[str]) -> None:
    actual_values = set(actual.get(key, []))
    missing_values = expected_values - actual_values
    if missing_values:
        raise AssertionError(f"Missing {key} values: {sorted(missing_values)}")


def main() -> None:
    result = extract_skills_from_job_description(LOGGED_SAP_JOB_DESCRIPTION)

    assert_contains(result, "tech_stack", {"SAP", "SAP Finance", "S/4HANA", "ECC6", "UML", "BPMN", "HPQC", "Sparx EA"})
    assert_contains(result, "technical_skills", {"Functional Analysis", "Requirements Gathering", "Migration", "Documentation", "Functional Testing", "Integration Testing"})
    assert_contains(result, "other_skills", {"French", "English", "Listening", "Teamwork", "Communication", "Synthesis", "Analytical Thinking", "Proactivity", "Autonomy"})
    assert_contains(result, "required_skills", {"SAP", "French", "UML", "Requirements Gathering"})
    assert_contains(result, "nice_to_have", {"BPMN", "HPQC", "Sparx EA", "English", "Integration Testing"})

    finance_result = extract_skills_from_job_description(LOGGED_FINANCIAL_ANALYST_JOB_DESCRIPTION)

    assert_contains(finance_result, "tech_stack", {"Power BI", "Excel", "Power Query", "DAX", "Power Query M", "ERP", "SQL"})
    assert_contains(finance_result, "technical_skills", {"Financial Analysis", "Financial Reporting", "Data Analysis", "Data Visualization", "Data Modeling", "Variance Analysis", "Data Quality", "Consolidation", "KPI Analysis"})
    assert_contains(finance_result, "other_skills", {"English", "Dutch", "Analytical Thinking", "Communication", "Collaboration", "Autonomy", "Attention to Detail"})
    assert_contains(finance_result, "required_skills", {"Power BI", "Excel", "Power Query", "Data Modeling", "Data Visualization", "English", "Communication"})
    assert_contains(finance_result, "nice_to_have", {"DAX", "Power Query M", "ERP", "SQL", "Dutch", "Consolidation"})

    print(json.dumps({"sap": result, "financial_analyst": finance_result}, indent=2, ensure_ascii=False))
    print("PASS")


if __name__ == "__main__":
    main()