"""
Management command: seed_jobs
==============================
Populates the database with realistic sample data for the Job Recommendation Engine.

Creates:
  - 16 industry categories
  - 16 real-world companies operating in Uganda / globally
  - 100 realistic job postings across those companies and categories

Idempotent: safe to run multiple times — uses get_or_create for categories and
companies, and skips jobs that already exist (matched by title + company).

Usage:
    python manage.py seed_jobs
    python manage.py seed_jobs --clear   # wipe all jobs/companies/categories first
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandError


def clean_salary(amount: int, step: int = 500_000) -> int:
    """Round salary to the nearest 'step' so values look realistic.

    Examples (step=500_000):
        3_399_514  ->  3_500_000
        12_429_658 -> 12_500_000
        800_000    ->    500_000  (but we always enforce a floor of step)
    """
    rounded = round(amount / step) * step
    return max(rounded, step)

from recommender.models import Company, Job, JobCategory


# ---------------------------------------------------------------------------
# Static seed data
# ---------------------------------------------------------------------------

CATEGORIES: list[dict[str, str]] = [
    {"name": "Technology",          "description": "Software, hardware, IT infrastructure and engineering roles."},
    {"name": "Finance & Banking",   "description": "Accounting, investment, banking and financial services."},
    {"name": "Telecommunications",  "description": "Mobile networks, broadband, customer experience and NOC roles."},
    {"name": "Healthcare",          "description": "Clinical, pharmaceutical, public health and medical research."},
    {"name": "Engineering",         "description": "Civil, mechanical, electrical and industrial engineering."},
    {"name": "Sales & Marketing",   "description": "Business development, digital marketing and brand management."},
    {"name": "Human Resources",     "description": "Talent acquisition, learning & development and HR operations."},
    {"name": "Logistics & Supply",  "description": "Procurement, warehouse management and supply chain."},
    {"name": "Education",           "description": "Teaching, curriculum design, EdTech and academic administration."},
    {"name": "Legal & Compliance",  "description": "Corporate law, regulatory affairs and risk management."},
    {"name": "Data & Analytics",    "description": "Data science, business intelligence and machine learning."},
    {"name": "Design & Creative",   "description": "UI/UX, graphic design, brand identity and content creation."},
    {"name": "Operations",          "description": "Business operations, project management and process improvement."},
    {"name": "Customer Service",    "description": "Support, CRM, contact centre and client success roles."},
    {"name": "Research & Policy",   "description": "Policy analysis, development research and public affairs."},
    {"name": "Manufacturing",       "description": "Production, quality control, assembly and plant operations."},
]

COMPANIES: list[dict[str, str]] = [
    {
        "name": "Google Uganda",
        "email": "careers@google.co.ug",
        "website": "https://careers.google.com",
        "location": "Kampala",
        "description": (
            "Google's sub-Saharan African hub, driving digital transformation across East Africa "
            "through cloud computing, AI research, developer programmes and internet connectivity projects."
        ),
    },
    {
        "name": "Microsoft Africa",
        "email": "jobs@microsoft.co.ug",
        "website": "https://careers.microsoft.com",
        "location": "Kampala",
        "description": (
            "Microsoft's regional centre supporting enterprise cloud (Azure), M365, AI services "
            "and the 4Afrika initiative to skill up African talent."
        ),
    },
    {
        "name": "Amazon Web Services",
        "email": "aws-careers@amazon.com",
        "website": "https://aws.amazon.com/careers",
        "location": "Kampala",
        "description": (
            "AWS provides cloud infrastructure to governments, fintechs and startups across Uganda "
            "and the East African Community, with a growing local solutions-architect team."
        ),
    },
    {
        "name": "MTN Uganda",
        "email": "hr@mtn.co.ug",
        "website": "https://www.mtn.co.ug",
        "location": "Kampala",
        "description": (
            "Uganda's largest mobile network operator offering voice, data, MoMo (Mobile Money) "
            "and enterprise solutions to over 17 million subscribers."
        ),
    },
    {
        "name": "Airtel Uganda",
        "email": "careers@airtel.co.ug",
        "website": "https://www.airtel.co.ug",
        "location": "Kampala",
        "description": (
            "Airtel Uganda provides affordable mobile and broadband services, fintech through Airtel Money, "
            "and B2B connectivity solutions across the country."
        ),
    },
    {
        "name": "Stanbic Bank Uganda",
        "email": "recruitment@stanbic.co.ug",
        "website": "https://www.stanbicbank.co.ug",
        "location": "Kampala",
        "description": (
            "Stanbic Bank Uganda, a member of Standard Bank Group, is the country's largest bank "
            "by assets, offering retail, business and corporate banking services."
        ),
    },
    {
        "name": "Centenary Bank",
        "email": "hr@centenarybank.co.ug",
        "website": "https://www.centenarybank.co.ug",
        "location": "Kampala",
        "description": (
            "Uganda's leading microfinance-oriented commercial bank, serving over 1.8 million customers "
            "with a focus on rural and agricultural financing."
        ),
    },
    {
        "name": "NSSF Uganda",
        "email": "recruitment@nssfug.org",
        "website": "https://www.nssfug.org",
        "location": "Kampala",
        "description": (
            "The National Social Security Fund of Uganda manages retirement savings for Ugandan workers, "
            "with assets exceeding UGX 20 trillion invested in real estate, equities and bonds."
        ),
    },
    {
        "name": "Andela",
        "email": "talent@andela.com",
        "website": "https://andela.com",
        "location": "Kampala",
        "description": (
            "Andela connects African software engineers with global technology companies, "
            "running intensive training programmes and remote-first placements across 40+ countries."
        ),
    },
    {
        "name": "SafeBoda",
        "email": "jobs@safeboda.com",
        "website": "https://safeboda.com",
        "location": "Kampala",
        "description": (
            "SafeBoda is Uganda's leading ride-hailing and delivery super-app, operating a fleet "
            "of vetted boda-boda riders with integrated payments and logistics services."
        ),
    },
    {
        "name": "Kiira Motors Corporation",
        "email": "hr@kiiramotos.com",
        "website": "https://www.kiiramotos.com",
        "location": "Jinja",
        "description": (
            "Kiira Motors is Uganda's indigenous electric vehicle manufacturer, producing the Kayoola "
            "electric bus and solar-powered Kiira EV for the African market."
        ),
    },
    {
        "name": "Uganda Revenue Authority",
        "email": "recruitment@ura.go.ug",
        "website": "https://www.ura.go.ug",
        "location": "Kampala",
        "description": (
            "URA is the government agency responsible for tax assessment, collection and enforcement, "
            "modernising revenue administration through digital platforms and data analytics."
        ),
    },
    {
        "name": "Uganda Airlines",
        "email": "careers@ugandaairlines.co.ug",
        "website": "https://www.ugandaairlines.co.ug",
        "location": "Entebbe",
        "description": (
            "Uganda's national carrier, operating regional and international routes with a modern fleet "
            "of Airbus A330s and CRJ900s out of Entebbe International Airport."
        ),
    },
    {
        "name": "TotalEnergies Uganda",
        "email": "ug-careers@totalenergies.com",
        "website": "https://www.totalenergies.co.ug",
        "location": "Kampala",
        "description": (
            "TotalEnergies operates fuel retail, lubricants and the EACOP pipeline project in Uganda, "
            "transitioning to renewable energy alongside its petroleum business."
        ),
    },
    {
        "name": "Huawei Uganda",
        "email": "uganda.careers@huawei.com",
        "website": "https://www.huawei.com/en",
        "location": "Kampala",
        "description": (
            "Huawei Uganda supplies ICT infrastructure, 5G equipment, enterprise cloud and smart city "
            "solutions to government and telecoms clients across East Africa."
        ),
    },
    {
        "name": "Flutterwave Africa",
        "email": "careers@flutterwave.com",
        "website": "https://flutterwave.com",
        "location": "Kampala",
        "description": (
            "Flutterwave is Africa's leading payments technology company, enabling businesses "
            "to accept and disburse payments across 34 African countries and globally."
        ),
    },
]

LOCATIONS = ["Kampala", "Entebbe", "Jinja", "Mbarara", "Gulu", "Mukono"]
JOB_TYPES = ["Full-Time", "Part-Time", "Internship", "Contract", "Remote"]


# ---------------------------------------------------------------------------
# Job definitions  (title, category, description, requirements, skills, salary_range, exp_range)
# ---------------------------------------------------------------------------
# salary_range: (min_ugx, max_ugx)  — realistic UGX monthly salaries
# exp_range:    (min_years, max_years)

JOB_SPECS: list[dict[str, Any]] = [
    # ── Technology ─────────────────────────────────────────────────────────
    {
        "title": "Senior Software Engineer",
        "category": "Technology",
        "description": (
            "Design and build scalable backend services powering millions of users. "
            "You will architect RESTful APIs, optimise database queries, lead code reviews "
            "and mentor junior engineers in a fast-paced agile environment."
        ),
        "requirements": (
            "Bachelor's degree in Computer Science or equivalent. "
            "Strong understanding of distributed systems and microservices. "
            "Experience with containerisation (Docker/Kubernetes). "
            "Excellent communication and teamwork skills."
        ),
        "skills": "Python, Django, PostgreSQL, Docker, Kubernetes, REST APIs, Git",
        "salary_range": (6_000_000, 15_000_000),
        "exp_range": (4, 8),
    },
    {
        "title": "Frontend Developer",
        "category": "Technology",
        "description": (
            "Build responsive, accessible web interfaces using React and TypeScript. "
            "Collaborate closely with designers and backend engineers to deliver pixel-perfect "
            "user experiences optimised for performance and accessibility."
        ),
        "requirements": (
            "Degree in Computer Science, Software Engineering or related field. "
            "Strong portfolio demonstrating production React projects. "
            "Familiarity with CI/CD pipelines and Agile/Scrum workflows."
        ),
        "skills": "React, TypeScript, JavaScript, HTML, CSS, Tailwind, Git, REST APIs",
        "salary_range": (4_000_000, 9_000_000),
        "exp_range": (2, 5),
    },
    {
        "title": "DevOps Engineer",
        "category": "Technology",
        "description": (
            "Own the CI/CD pipeline, cloud infrastructure and reliability of production systems. "
            "Work with engineering teams to automate deployments, monitor system health "
            "and reduce mean time to recovery across AWS and GCP environments."
        ),
        "requirements": (
            "3+ years in a DevOps, SRE or infrastructure role. "
            "Strong scripting skills in Bash or Python. "
            "Experience with infrastructure-as-code (Terraform or Ansible). "
            "On-call availability required."
        ),
        "skills": "AWS, Docker, Kubernetes, Terraform, CI/CD, Linux, Bash, Python, Ansible",
        "salary_range": (7_000_000, 16_000_000),
        "exp_range": (3, 7),
    },
    {
        "title": "Mobile App Developer (Android)",
        "category": "Technology",
        "description": (
            "Develop and maintain our Android application serving 2 million+ users. "
            "Work on new features, integrate payment APIs and ensure smooth performance "
            "across a wide range of Android devices and OS versions."
        ),
        "requirements": (
            "BSc Computer Science or equivalent practical experience. "
            "Published apps on the Google Play Store preferred. "
            "Experience integrating mobile payment SDKs (MTN MoMo, Airtel Money) is a plus."
        ),
        "skills": "Kotlin, Java, Android SDK, REST APIs, Firebase, Git, Jetpack Compose",
        "salary_range": (4_500_000, 10_000_000),
        "exp_range": (2, 6),
    },
    {
        "title": "Software Engineering Intern",
        "category": "Technology",
        "description": (
            "Join our engineering team for a 6-month internship. You will contribute to real "
            "features under the mentorship of senior engineers, participate in sprint planning "
            "and learn industry best practices in software development."
        ),
        "requirements": (
            "Currently pursuing or recently completed a degree in Computer Science or related field. "
            "Basic knowledge of at least one programming language. "
            "Eagerness to learn and receive feedback."
        ),
        "skills": "Python, JavaScript, HTML, CSS, Git",
        "salary_range": (800_000, 1_500_000),
        "exp_range": (0, 1),
    },
    {
        "title": "Cloud Solutions Architect",
        "category": "Technology",
        "description": (
            "Design cloud-native architectures for enterprise clients migrating to AWS or Azure. "
            "Lead pre-sales technical workshops, produce architecture blueprints and ensure "
            "solutions meet security, compliance and performance standards."
        ),
        "requirements": (
            "AWS Certified Solutions Architect – Professional or Azure equivalent. "
            "5+ years of experience designing enterprise cloud solutions. "
            "Excellent presentation and client-facing skills."
        ),
        "skills": "AWS, Azure, Cloud Architecture, Terraform, Security, Networking, Python",
        "salary_range": (12_000_000, 25_000_000),
        "exp_range": (5, 10),
    },
    {
        "title": "IT Support Technician",
        "category": "Technology",
        "description": (
            "Provide first and second-line technical support to internal staff. "
            "Troubleshoot hardware, software and network issues, manage asset inventory "
            "and maintain system documentation for a 200-person office."
        ),
        "requirements": (
            "Diploma or degree in IT, Networking or related field. "
            "CompTIA A+ or Network+ certification preferred. "
            "Strong interpersonal and problem-solving skills. "
            "Ability to work under pressure."
        ),
        "skills": "Windows, Linux, Networking, Active Directory, Hardware Troubleshooting",
        "salary_range": (1_500_000, 3_000_000),
        "exp_range": (1, 3),
    },
    {
        "title": "Cybersecurity Analyst",
        "category": "Technology",
        "description": (
            "Monitor, detect and respond to security threats across the organisation's "
            "IT landscape. Conduct vulnerability assessments, manage SIEM tools "
            "and develop incident response playbooks."
        ),
        "requirements": (
            "BSc in Cybersecurity, IT or related field. "
            "CEH, CISSP or CompTIA Security+ certification preferred. "
            "Experience with SIEM platforms (Splunk, IBM QRadar). "
            "Understanding of regulatory frameworks (ISO 27001, PCI-DSS)."
        ),
        "skills": "Cybersecurity, SIEM, Penetration Testing, Network Security, Python, ISO 27001",
        "salary_range": (6_000_000, 14_000_000),
        "exp_range": (3, 7),
    },
    {
        "title": "Full-Stack Developer (Remote)",
        "category": "Technology",
        "description": (
            "Work fully remotely building and maintaining web applications for our global client base. "
            "You will own features end-to-end — from database design through to production deployment — "
            "in a distributed, async-first team spanning multiple time zones."
        ),
        "requirements": (
            "3+ years of full-stack development experience. "
            "Strong portfolio of shipped products. "
            "Excellent written communication skills for async collaboration. "
            "Reliable internet connection and home office setup."
        ),
        "skills": "Python, Django, React, PostgreSQL, Docker, REST APIs, Git, AWS",
        "salary_range": (5_000_000, 12_000_000),
        "exp_range": (3, 6),
    },
    {
        "title": "Backend Engineer – Payments",
        "category": "Technology",
        "description": (
            "Build and scale the payment processing engine handling thousands of transactions "
            "per second. Integrate mobile money APIs (MTN, Airtel, Visa), ensure PCI-DSS compliance "
            "and drive reliability of the payments platform."
        ),
        "requirements": (
            "Strong understanding of payment systems and financial protocols. "
            "Experience with high-throughput, low-latency distributed systems. "
            "Knowledge of PCI-DSS compliance requirements."
        ),
        "skills": "Python, Go, PostgreSQL, Redis, Kafka, REST APIs, PCI-DSS, Docker",
        "salary_range": (8_000_000, 18_000_000),
        "exp_range": (4, 8),
    },
    # ── Data & Analytics ───────────────────────────────────────────────────
    {
        "title": "Data Scientist",
        "category": "Data & Analytics",
        "description": (
            "Build predictive models and machine learning pipelines to derive actionable insights "
            "from large datasets. Present findings to executive stakeholders and translate "
            "complex analyses into clear business recommendations."
        ),
        "requirements": (
            "Master's degree in Statistics, Mathematics, Computer Science or related field preferred. "
            "Experience deploying ML models to production environments. "
            "Strong storytelling and data visualisation skills."
        ),
        "skills": "Python, Machine Learning, TensorFlow, Pandas, SQL, Tableau, Statistics",
        "salary_range": (7_000_000, 16_000_000),
        "exp_range": (3, 7),
    },
    {
        "title": "Business Intelligence Analyst",
        "category": "Data & Analytics",
        "description": (
            "Design and maintain BI dashboards and reports that guide strategic decisions. "
            "Work with product, finance and operations teams to define KPIs, build data pipelines "
            "and deliver self-service analytics capabilities."
        ),
        "requirements": (
            "BSc in Business Analytics, Statistics or related field. "
            "Experience with at least one BI tool (Power BI, Tableau, Looker). "
            "Strong SQL skills and understanding of data warehousing concepts."
        ),
        "skills": "SQL, Power BI, Tableau, Python, Data Warehousing, Excel, ETL",
        "salary_range": (4_000_000, 9_000_000),
        "exp_range": (2, 5),
    },
    {
        "title": "Data Engineer",
        "category": "Data & Analytics",
        "description": (
            "Design and build robust data pipelines that ingest, transform and deliver data "
            "at scale. Maintain our data lake architecture and work with data scientists to "
            "productionise their models."
        ),
        "requirements": (
            "3+ years of data engineering experience. "
            "Experience with distributed processing frameworks (Spark, Flink). "
            "Strong understanding of data modelling and warehousing best practices."
        ),
        "skills": "Python, Apache Spark, Airflow, SQL, AWS S3, Redshift, dbt, Kafka",
        "salary_range": (6_000_000, 14_000_000),
        "exp_range": (3, 6),
    },
    # ── Finance & Banking ──────────────────────────────────────────────────
    {
        "title": "Credit Analyst",
        "category": "Finance & Banking",
        "description": (
            "Assess creditworthiness of individual and corporate loan applicants. "
            "Analyse financial statements, cash flows and collateral, prepare credit reports "
            "and present recommendations to the Credit Committee."
        ),
        "requirements": (
            "BSc in Finance, Accounting or Economics. "
            "CPA or ACCA qualification (or ongoing) preferred. "
            "Strong analytical and report-writing skills. "
            "Knowledge of Bank of Uganda lending regulations."
        ),
        "skills": "Financial Analysis, Credit Risk, Excel, SQL, Report Writing, IFRS",
        "salary_range": (3_000_000, 7_000_000),
        "exp_range": (2, 5),
    },
    {
        "title": "Relationship Manager – Corporate Banking",
        "category": "Finance & Banking",
        "description": (
            "Manage a portfolio of corporate clients, cross-selling banking products including "
            "trade finance, treasury services and lending. Achieve deposit and revenue targets "
            "while ensuring excellent client service."
        ),
        "requirements": (
            "5+ years of corporate banking or relationship management experience. "
            "Strong commercial acumen and established corporate network. "
            "Excellent negotiation and presentation skills."
        ),
        "skills": "Corporate Banking, Trade Finance, Relationship Management, CRM, Excel, Financial Modelling",
        "salary_range": (8_000_000, 18_000_000),
        "exp_range": (5, 10),
    },
    {
        "title": "Accountant",
        "category": "Finance & Banking",
        "description": (
            "Maintain accurate financial records, prepare monthly management accounts, "
            "reconcile general ledger accounts and support the annual audit process. "
            "Ensure compliance with IFRS and URA tax requirements."
        ),
        "requirements": (
            "BSc in Accounting or Finance. CPA (U) or ACCA qualification. "
            "Proficiency in accounting software (QuickBooks, SAP, Oracle). "
            "Attention to detail and ability to meet reporting deadlines."
        ),
        "skills": "Accounting, IFRS, QuickBooks, SAP, Taxation, Excel, Financial Reporting",
        "salary_range": (2_500_000, 5_500_000),
        "exp_range": (2, 5),
    },
    {
        "title": "Risk & Compliance Officer",
        "category": "Finance & Banking",
        "description": (
            "Identify, assess and monitor operational, credit and market risks. "
            "Ensure compliance with Bank of Uganda regulations, develop risk frameworks "
            "and coordinate internal audits and regulatory examinations."
        ),
        "requirements": (
            "BSc in Finance, Law or Risk Management. "
            "Professional certification in risk management (FRM, PRMIA) preferred. "
            "Deep knowledge of Bank of Uganda prudential guidelines."
        ),
        "skills": "Risk Management, Compliance, Basel III, AML, Regulatory Reporting, Excel",
        "salary_range": (5_000_000, 11_000_000),
        "exp_range": (3, 7),
    },
    {
        "title": "Treasury Dealer",
        "category": "Finance & Banking",
        "description": (
            "Execute foreign exchange, money market and government securities transactions. "
            "Manage daily liquidity positions, monitor FX exposure "
            "and provide market intelligence to senior management."
        ),
        "requirements": (
            "BSc Finance or Economics. ACI dealing certificate preferred. "
            "2+ years of experience in treasury or financial markets. "
            "Strong mathematical and analytical skills."
        ),
        "skills": "FX Trading, Money Markets, Treasury, Bloomberg, Financial Modelling, Excel",
        "salary_range": (6_000_000, 13_000_000),
        "exp_range": (2, 6),
    },
    # ── Telecommunications ─────────────────────────────────────────────────
    {
        "title": "Network Engineer",
        "category": "Telecommunications",
        "description": (
            "Plan, deploy and optimise the organisation's radio access, transmission and core network. "
            "Troubleshoot network outages, perform capacity planning and drive continuous "
            "improvement of network KPIs."
        ),
        "requirements": (
            "BSc in Telecommunications, Electrical Engineering or related field. "
            "CCNA/CCNP certification preferred. "
            "Experience with vendor equipment (Huawei, Ericsson, Nokia)."
        ),
        "skills": "Networking, CCNA, 4G LTE, 5G, IP/MPLS, Huawei, Ericsson, Transmission",
        "salary_range": (5_000_000, 12_000_000),
        "exp_range": (3, 7),
    },
    {
        "title": "Customer Experience Agent",
        "category": "Customer Service",
        "description": (
            "Handle inbound calls, chats and emails from customers, resolving queries related "
            "to mobile services, billing and mobile money. Maintain high CSAT scores "
            "and adhere to quality and compliance standards."
        ),
        "requirements": (
            "Diploma or degree in any field. "
            "Excellent verbal and written communication skills. "
            "Ability to work in rotational shifts including weekends."
        ),
        "skills": "Customer Service, CRM, Communication, Problem Solving, Mobile Money",
        "salary_range": (1_200_000, 2_500_000),
        "exp_range": (0, 2),
    },
    {
        "title": "Sales Executive – Enterprise",
        "category": "Sales & Marketing",
        "description": (
            "Acquire and grow enterprise accounts for our B2B connectivity and cloud solutions. "
            "Develop tailored proposals, negotiate contracts and manage relationships "
            "with C-suite decision makers in large organisations."
        ),
        "requirements": (
            "3+ years of B2B or enterprise sales experience. "
            "Proven track record of meeting and exceeding revenue targets. "
            "Strong network within Ugandan corporate sector."
        ),
        "skills": "B2B Sales, CRM, Negotiation, Proposal Writing, Networking, Salesforce",
        "salary_range": (4_000_000, 10_000_000),
        "exp_range": (3, 7),
    },
    {
        "title": "MoMo Product Manager",
        "category": "Technology",
        "description": (
            "Own the product roadmap for our Mobile Money platform. Drive feature development, "
            "analyse user behaviour, coordinate with engineering and compliance teams "
            "and ensure the product meets regulatory requirements."
        ),
        "requirements": (
            "BSc in Business, Computer Science or related field. MBA preferred. "
            "3+ years of product management experience in fintech or mobile money. "
            "Data-driven with strong analytical skills."
        ),
        "skills": "Product Management, Mobile Money, Agile, SQL, User Research, Fintech",
        "salary_range": (8_000_000, 18_000_000),
        "exp_range": (3, 7),
    },
    # ── Sales & Marketing ──────────────────────────────────────────────────
    {
        "title": "Digital Marketing Manager",
        "category": "Sales & Marketing",
        "description": (
            "Lead all digital marketing activities — SEO, paid search, social media, email and "
            "content marketing. Own the marketing budget, drive lead generation and report "
            "on campaign ROI to the executive team."
        ),
        "requirements": (
            "BSc in Marketing or related field. Google Ads / Meta Blueprint certifications preferred. "
            "3+ years of digital marketing experience. "
            "Excellent analytical skills and data-driven mindset."
        ),
        "skills": "SEO, Google Ads, Facebook Ads, Email Marketing, Google Analytics, Content Marketing",
        "salary_range": (4_000_000, 9_000_000),
        "exp_range": (3, 6),
    },
    {
        "title": "Brand & Communications Officer",
        "category": "Sales & Marketing",
        "description": (
            "Manage brand identity, internal and external communications, PR and corporate events. "
            "Develop messaging strategies, oversee agency partners and ensure brand consistency "
            "across all touchpoints."
        ),
        "requirements": (
            "BSc in Communications, Marketing or Journalism. "
            "2+ years of brand management or PR experience. "
            "Excellent writing and storytelling ability."
        ),
        "skills": "Brand Management, PR, Content Writing, Adobe Creative Suite, Social Media",
        "salary_range": (3_000_000, 7_000_000),
        "exp_range": (2, 5),
    },
    # ── Human Resources ────────────────────────────────────────────────────
    {
        "title": "HR Business Partner",
        "category": "Human Resources",
        "description": (
            "Partner with business unit leaders to deliver people strategies aligned with "
            "organisational goals. Drive talent acquisition, performance management, "
            "employee engagement and change management initiatives."
        ),
        "requirements": (
            "BSc in Human Resource Management or related field. CIPD or SHRM certification preferred. "
            "5+ years of generalist HR experience. "
            "Strong knowledge of Ugandan labour law."
        ),
        "skills": "HR Management, Labour Law, Talent Acquisition, HRIS, Performance Management",
        "salary_range": (5_000_000, 11_000_000),
        "exp_range": (5, 9),
    },
    {
        "title": "Talent Acquisition Specialist",
        "category": "Human Resources",
        "description": (
            "Own the end-to-end recruitment process for technical and commercial roles. "
            "Build talent pipelines, manage relationships with universities and agencies, "
            "and deliver an excellent candidate experience."
        ),
        "requirements": (
            "BSc in HRM or related field. "
            "2+ years of recruitment experience (in-house or agency). "
            "Experience hiring for technology roles is an advantage."
        ),
        "skills": "Recruitment, LinkedIn Recruiter, ATS, Interviewing, Talent Sourcing",
        "salary_range": (3_000_000, 6_500_000),
        "exp_range": (2, 5),
    },
    # ── Engineering ────────────────────────────────────────────────────────
    {
        "title": "Electrical Engineer",
        "category": "Engineering",
        "description": (
            "Design and oversee electrical systems for commercial and industrial projects. "
            "Prepare specifications, conduct site inspections, review contractor work "
            "and ensure compliance with Uganda's electrical safety standards."
        ),
        "requirements": (
            "BSc in Electrical Engineering. Engineers Registration Board (ERB) registration. "
            "3+ years of project experience. "
            "Proficiency in AutoCAD Electrical."
        ),
        "skills": "Electrical Engineering, AutoCAD, Power Systems, Project Management, ERB",
        "salary_range": (5_000_000, 11_000_000),
        "exp_range": (3, 7),
    },
    {
        "title": "Mechanical Engineer – EV Systems",
        "category": "Engineering",
        "description": (
            "Design and test mechanical components for electric vehicles including the Kayoola EV bus. "
            "Work on powertrain systems, thermal management and structural analysis "
            "using CAD tools and finite element analysis."
        ),
        "requirements": (
            "BSc/MEng in Mechanical Engineering. "
            "Experience with EV or automotive engineering preferred. "
            "Proficiency in SolidWorks or CATIA."
        ),
        "skills": "Mechanical Engineering, SolidWorks, FEA, EV Systems, AutoCAD, MATLAB",
        "salary_range": (4_500_000, 10_000_000),
        "exp_range": (2, 6),
    },
    {
        "title": "Civil Engineer",
        "category": "Engineering",
        "description": (
            "Lead the design and supervision of civil infrastructure projects including roads, "
            "bridges and buildings. Manage contractors, review drawings and ensure projects "
            "are delivered on time, within budget and to specification."
        ),
        "requirements": (
            "BSc in Civil Engineering. ERB registration. "
            "3+ years of site supervision experience. "
            "Knowledge of Uganda National Roads Authority standards."
        ),
        "skills": "Civil Engineering, AutoCAD, Structural Analysis, Project Management, UNRA Standards",
        "salary_range": (5_000_000, 12_000_000),
        "exp_range": (3, 8),
    },
    # ── Legal & Compliance ─────────────────────────────────────────────────
    {
        "title": "Legal Counsel",
        "category": "Legal & Compliance",
        "description": (
            "Provide legal advice on commercial contracts, regulatory matters and corporate governance. "
            "Draft and review agreements, manage litigation and liaise with external counsel "
            "and regulatory bodies."
        ),
        "requirements": (
            "LLB degree and Diploma in Legal Practice. Advocate of the High Court of Uganda. "
            "4+ years of post-qualification experience. "
            "Strong knowledge of Ugandan commercial law and sector regulations."
        ),
        "skills": "Commercial Law, Contract Drafting, Compliance, Regulatory Affairs, Litigation",
        "salary_range": (7_000_000, 16_000_000),
        "exp_range": (4, 9),
    },
    {
        "title": "Compliance & AML Officer",
        "category": "Legal & Compliance",
        "description": (
            "Ensure the organisation's compliance with AML/CFT regulations, Bank of Uganda "
            "directives and international sanctions. Monitor transactions, file STRs "
            "and conduct compliance training."
        ),
        "requirements": (
            "BSc in Law, Finance or related field. CAMS certification preferred. "
            "3+ years of AML compliance experience in financial services."
        ),
        "skills": "AML, CFT, KYC, Compliance, Regulatory Reporting, Risk Assessment",
        "salary_range": (5_000_000, 11_000_000),
        "exp_range": (3, 7),
    },
    # ── Logistics & Supply ─────────────────────────────────────────────────
    {
        "title": "Procurement Manager",
        "category": "Logistics & Supply",
        "description": (
            "Lead the procurement function, manage supplier relationships and ensure cost-effective "
            "acquisition of goods and services. Develop procurement strategies, conduct supplier "
            "evaluations and ensure compliance with PPDA regulations."
        ),
        "requirements": (
            "BSc in Procurement, Supply Chain or Business. CIPS certification preferred. "
            "5+ years of procurement experience. "
            "Knowledge of PPDA Act and public procurement procedures."
        ),
        "skills": "Procurement, Supply Chain, PPDA, Supplier Management, ERP, Negotiation",
        "salary_range": (6_000_000, 13_000_000),
        "exp_range": (5, 9),
    },
    {
        "title": "Logistics Coordinator",
        "category": "Logistics & Supply",
        "description": (
            "Coordinate inbound and outbound shipments, manage fleet operations and liaise with "
            "customs and freight forwarders. Maintain accurate records in the ERP system "
            "and resolve logistics bottlenecks."
        ),
        "requirements": (
            "Diploma or BSc in Logistics, Supply Chain or related field. "
            "2+ years of logistics experience. "
            "Proficiency in ERP systems and Google Workspace."
        ),
        "skills": "Logistics, Supply Chain, ERP, Customs, Fleet Management, Excel",
        "salary_range": (2_500_000, 5_000_000),
        "exp_range": (2, 4),
    },
    # ── Design & Creative ──────────────────────────────────────────────────
    {
        "title": "UI/UX Designer",
        "category": "Design & Creative",
        "description": (
            "Design intuitive and beautiful digital products — from mobile apps to web dashboards. "
            "Conduct user research, create wireframes and prototypes, "
            "run usability tests and deliver final assets to engineering."
        ),
        "requirements": (
            "BSc in Design, HCI or related field. "
            "Portfolio demonstrating end-to-end product design process. "
            "Proficiency in Figma. "
            "Experience with mobile-first and accessibility-focused design."
        ),
        "skills": "Figma, UI Design, UX Research, Prototyping, Adobe XD, Usability Testing",
        "salary_range": (3_500_000, 8_000_000),
        "exp_range": (2, 5),
    },
    {
        "title": "Graphic Designer",
        "category": "Design & Creative",
        "description": (
            "Create compelling visual content for digital and print — social media graphics, "
            "marketing collateral, pitch decks and brand materials. "
            "Work with the marketing team to bring campaigns to life."
        ),
        "requirements": (
            "Diploma or BSc in Graphic Design or Fine Art. "
            "Strong portfolio. Proficiency in Adobe Creative Suite. "
            "Motion graphics experience (After Effects) is a plus."
        ),
        "skills": "Adobe Photoshop, Illustrator, InDesign, After Effects, Canva, Brand Design",
        "salary_range": (2_000_000, 5_000_000),
        "exp_range": (1, 4),
    },
    # ── Operations ─────────────────────────────────────────────────────────
    {
        "title": "Project Manager",
        "category": "Operations",
        "description": (
            "Lead complex, cross-functional projects from initiation to closure. "
            "Define scope, manage budgets, identify risks and communicate progress "
            "to senior stakeholders using structured project management methodologies."
        ),
        "requirements": (
            "BSc in Business, Engineering or related field. PMP or PRINCE2 certification preferred. "
            "5+ years of project management experience. "
            "Strong leadership and stakeholder management skills."
        ),
        "skills": "Project Management, PMP, PRINCE2, MS Project, Risk Management, Agile",
        "salary_range": (7_000_000, 15_000_000),
        "exp_range": (5, 9),
    },
    {
        "title": "Business Analyst",
        "category": "Operations",
        "description": (
            "Bridge the gap between business needs and technology solutions. "
            "Gather and document requirements, facilitate workshops, create process maps "
            "and support UAT for system implementations."
        ),
        "requirements": (
            "BSc in Business, IT or related field. "
            "2+ years of business analysis experience. "
            "Experience with BPMN and requirements documentation tools."
        ),
        "skills": "Business Analysis, BPMN, Requirements Gathering, SQL, Jira, Excel",
        "salary_range": (4_000_000, 9_000_000),
        "exp_range": (2, 5),
    },
    # ── Healthcare ─────────────────────────────────────────────────────────
    {
        "title": "Health Informatics Officer",
        "category": "Healthcare",
        "description": (
            "Implement and maintain electronic health record systems in clinic and hospital settings. "
            "Train healthcare workers on digital tools, generate health data reports "
            "and support the Ministry of Health's digital transformation agenda."
        ),
        "requirements": (
            "BSc in Health Informatics, Public Health or Computer Science. "
            "Experience with DHIS2 or OpenMRS. "
            "Ability to work in a rural health facility setting."
        ),
        "skills": "DHIS2, OpenMRS, SQL, Health Data, Training, Public Health",
        "salary_range": (3_000_000, 6_000_000),
        "exp_range": (2, 5),
    },
    {
        "title": "Pharmacist",
        "category": "Healthcare",
        "description": (
            "Dispense medications, counsel patients on drug use, manage pharmacy inventory "
            "and ensure compliance with NDA regulations. "
            "Support clinical teams in medication management and adverse event reporting."
        ),
        "requirements": (
            "Bachelor of Pharmacy. Registered with the Pharmacy and Medicines Board of Uganda. "
            "1+ years of hospital or retail pharmacy experience."
        ),
        "skills": "Pharmacy, Drug Dispensing, Pharmacovigilance, Inventory Management, NDA Compliance",
        "salary_range": (3_500_000, 7_000_000),
        "exp_range": (1, 4),
    },
    # ── Research & Policy ──────────────────────────────────────────────────
    {
        "title": "Policy Analyst",
        "category": "Research & Policy",
        "description": (
            "Research, analyse and develop policy briefs on economic and fiscal matters. "
            "Support the development of tax policy, budget frameworks and regulatory guidelines, "
            "presenting evidence-based recommendations to senior officials."
        ),
        "requirements": (
            "Master's degree in Economics, Public Policy or related field. "
            "3+ years of policy research or advisory experience. "
            "Excellent analytical and writing skills."
        ),
        "skills": "Policy Analysis, Research, Economics, Stata, Excel, Report Writing",
        "salary_range": (5_000_000, 11_000_000),
        "exp_range": (3, 7),
    },
    # ── Education ──────────────────────────────────────────────────────────
    {
        "title": "Software Trainer",
        "category": "Education",
        "description": (
            "Design and deliver technical training programmes on Python, web development and cloud "
            "for cohorts of 20–50 trainees. Develop curriculum, assess student progress "
            "and iterate on course content based on industry feedback."
        ),
        "requirements": (
            "BSc in Computer Science or related field. "
            "Proven ability to explain complex concepts simply. "
            "2+ years of software development or training experience."
        ),
        "skills": "Python, Django, JavaScript, Curriculum Design, Training, Git",
        "salary_range": (3_000_000, 7_000_000),
        "exp_range": (2, 5),
    },
    # ── Manufacturing ──────────────────────────────────────────────────────
    {
        "title": "Quality Control Engineer",
        "category": "Manufacturing",
        "description": (
            "Ensure manufactured products meet design specifications and regulatory standards. "
            "Conduct inspections, analyse defect data, implement corrective actions "
            "and maintain ISO 9001 quality management documentation."
        ),
        "requirements": (
            "BSc in Industrial Engineering or related field. "
            "ISO 9001 Lead Auditor certification preferred. "
            "3+ years of QC experience in a manufacturing environment."
        ),
        "skills": "Quality Control, ISO 9001, Statistical Process Control, Root Cause Analysis, AutoCAD",
        "salary_range": (4_000_000, 9_000_000),
        "exp_range": (3, 6),
    },
    {
        "title": "Production Supervisor",
        "category": "Manufacturing",
        "description": (
            "Oversee daily production operations, manage a team of 30+ operators "
            "and ensure output targets are met safely and efficiently. "
            "Drive continuous improvement through lean manufacturing techniques."
        ),
        "requirements": (
            "BSc or Diploma in Production Engineering or related field. "
            "4+ years of production supervisory experience. "
            "Lean or Six Sigma certification preferred."
        ),
        "skills": "Production Management, Lean Manufacturing, Six Sigma, ERP, Team Leadership",
        "salary_range": (4_500_000, 9_000_000),
        "exp_range": (4, 8),
    },
    # ── Aviation / Operations ──────────────────────────────────────────────
    {
        "title": "Airline Operations Coordinator",
        "category": "Operations",
        "description": (
            "Coordinate ground handling, crew scheduling and flight operations to ensure "
            "on-time performance. Liaise with UCAA, immigration and handling agents "
            "and manage irregular operations (IROPs) with minimal disruption."
        ),
        "requirements": (
            "BSc in Aviation Management, Logistics or related field. "
            "2+ years of airline or ground handling experience. "
            "Knowledge of ICAO and IATA standards."
        ),
        "skills": "Aviation, Flight Operations, ICAO, Crew Scheduling, Ground Handling",
        "salary_range": (4_000_000, 8_000_000),
        "exp_range": (2, 5),
    },
    {
        "title": "Cabin Crew Member",
        "category": "Customer Service",
        "description": (
            "Deliver exceptional in-flight service, ensure passenger safety and uphold "
            "Uganda Airlines' brand standards. Conduct safety briefings, manage emergency "
            "procedures and provide personalised service on regional and international routes."
        ),
        "requirements": (
            "Diploma or degree in any field. "
            "Minimum height 1.60m. Fluent in English; French or Swahili is an advantage. "
            "IATA cabin crew certification preferred. "
            "Excellent grooming and interpersonal skills."
        ),
        "skills": "Customer Service, Safety Procedures, First Aid, Communication, Multilingual",
        "salary_range": (2_500_000, 5_000_000),
        "exp_range": (0, 3),
    },
    # ── Energy ─────────────────────────────────────────────────────────────
    {
        "title": "HSE Officer",
        "category": "Engineering",
        "description": (
            "Implement and enforce Health, Safety and Environment policies across field operations. "
            "Conduct risk assessments, investigate incidents, deliver HSE training "
            "and ensure compliance with NEMA and ISO 14001 requirements."
        ),
        "requirements": (
            "BSc in Environmental Science, Engineering or related field. "
            "NEBOSH certification preferred. "
            "3+ years of HSE experience in oil, gas or heavy industry."
        ),
        "skills": "HSE, NEBOSH, ISO 14001, Risk Assessment, Incident Investigation, NEMA",
        "salary_range": (5_000_000, 11_000_000),
        "exp_range": (3, 7),
    },
    {
        "title": "Petroleum Geoscientist",
        "category": "Research & Policy",
        "description": (
            "Interpret seismic data, well logs and geological models to identify and evaluate "
            "hydrocarbon prospects in the Albertine Graben. Support exploration and appraisal "
            "drilling programmes and resource estimation."
        ),
        "requirements": (
            "BSc/MSc in Geology or Geophysics. "
            "3+ years of upstream oil and gas experience. "
            "Proficiency in Petrel or Kingdom seismic interpretation software."
        ),
        "skills": "Geology, Seismic Interpretation, Petrel, Petrophysics, GIS, Reservoir Modelling",
        "salary_range": (10_000_000, 22_000_000),
        "exp_range": (3, 8),
    },
    # ── Fintech / Payments ─────────────────────────────────────────────────
    {
        "title": "Fintech Product Designer",
        "category": "Design & Creative",
        "description": (
            "Design seamless mobile and web payment experiences for our African market. "
            "Conduct user research with low-bandwidth users, create accessible prototypes "
            "and collaborate with engineers on implementation."
        ),
        "requirements": (
            "BSc in Design or HCI. "
            "Portfolio of fintech or mobile money product work preferred. "
            "Understanding of USSD, mobile-first and offline-first design patterns."
        ),
        "skills": "Figma, UX Research, Mobile Design, Prototyping, Accessibility, USSD",
        "salary_range": (4_000_000, 9_000_000),
        "exp_range": (2, 5),
    },
    {
        "title": "Financial Inclusion Analyst",
        "category": "Research & Policy",
        "description": (
            "Research and analyse financial inclusion trends across East Africa. "
            "Evaluate the impact of mobile money products, develop market expansion strategies "
            "and produce thought leadership reports for regulators and investors."
        ),
        "requirements": (
            "Master's degree in Economics, Finance or Development Studies. "
            "3+ years of research or advisory experience in financial services. "
            "Strong data analysis and report writing skills."
        ),
        "skills": "Research, Financial Inclusion, Mobile Money, Data Analysis, Report Writing, STATA",
        "salary_range": (5_000_000, 11_000_000),
        "exp_range": (3, 6),
    },
    # ── Tax / Government ───────────────────────────────────────────────────
    {
        "title": "Tax Auditor",
        "category": "Finance & Banking",
        "description": (
            "Conduct desk and field audits of corporate and individual tax returns. "
            "Verify financial records, assess tax liabilities, issue audit findings "
            "and negotiate settlements in line with the Income Tax Act."
        ),
        "requirements": (
            "BSc in Accounting, Finance or Law. CPA (U) or ACCA preferred. "
            "2+ years of tax audit or accounting experience. "
            "Knowledge of Uganda's tax laws and EFRIS system."
        ),
        "skills": "Tax Auditing, Accounting, EFRIS, Income Tax Act, Excel, Financial Analysis",
        "salary_range": (3_500_000, 7_500_000),
        "exp_range": (2, 5),
    },
    {
        "title": "Customs Officer (Contract)",
        "category": "Legal & Compliance",
        "description": (
            "Inspect imports and exports, assess customs duties, prevent smuggling "
            "and facilitate legitimate trade at border posts. "
            "Use ASYCUDA World for customs declarations and risk profiling."
        ),
        "requirements": (
            "BSc in any field. Training in customs procedures preferred. "
            "High level of integrity and attention to detail. "
            "Willingness to be posted at any border entry point in Uganda."
        ),
        "skills": "Customs, ASYCUDA, Trade Facilitation, Compliance, Risk Profiling",
        "salary_range": (2_000_000, 4_000_000),
        "exp_range": (0, 3),
    },
    # ── Ride-hailing / Super App ───────────────────────────────────────────
    {
        "title": "Operations Analyst – Ride Hailing",
        "category": "Operations",
        "description": (
            "Analyse trip data, driver performance metrics and city-level supply-demand dynamics. "
            "Produce operational dashboards, identify inefficiencies and recommend improvements "
            "that increase earnings for riders and satisfaction for passengers."
        ),
        "requirements": (
            "BSc in Statistics, Computer Science or related field. "
            "Proficiency in SQL and at least one BI tool. "
            "1+ years of operations analytics experience."
        ),
        "skills": "SQL, Python, Power BI, Operations Research, Data Analysis, Excel",
        "salary_range": (3_000_000, 6_500_000),
        "exp_range": (1, 4),
    },
    {
        "title": "Driver Operations Manager",
        "category": "Operations",
        "description": (
            "Recruit, onboard and manage a network of boda-boda and vehicle drivers. "
            "Drive driver satisfaction, handle escalations, run training programmes "
            "and implement incentive schemes to improve retention and quality."
        ),
        "requirements": (
            "BSc in Business or related field. "
            "3+ years of fleet or field operations management experience. "
            "Strong leadership and community engagement skills."
        ),
        "skills": "Operations Management, Fleet Management, Community Engagement, CRM, Excel",
        "salary_range": (4_000_000, 8_000_000),
        "exp_range": (3, 6),
    },
]


class Command(BaseCommand):
    help = (
        "Seed the database with realistic sample data: "
        "categories, companies, and 100 job postings. "
        "Safe to run multiple times — skips existing records."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing jobs, companies and categories before seeding.",
        )

    def handle(self, *args, **options) -> None:
        if options["clear"]:
            self.stdout.write(self.style.WARNING("Clearing existing data…"))
            Job.objects.all().delete()
            Company.objects.all().delete()
            JobCategory.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("Data cleared."))

        # ── 1. Seed categories ─────────────────────────────────────────────
        self.stdout.write("\n[1/3] Seeding job categories...")
        category_map: dict[str, JobCategory] = {}
        cat_created = cat_skipped = 0

        for cat_data in CATEGORIES:
            obj, created = JobCategory.objects.get_or_create(
                name=cat_data["name"],
                defaults={"description": cat_data["description"]},
            )
            category_map[obj.name] = obj
            if created:
                cat_created += 1
            else:
                cat_skipped += 1

        self.stdout.write(
            f"   OK: {cat_created} created, {cat_skipped} already existed."
        )

        # ── 2. Seed companies ──────────────────────────────────────────────
        self.stdout.write("\n[2/3] Seeding companies...")
        company_map: dict[str, Company] = {}
        comp_created = comp_skipped = 0

        for comp_data in COMPANIES:
            obj, created = Company.objects.get_or_create(
                name=comp_data["name"],
                defaults={
                    "email":       comp_data["email"],
                    "website":     comp_data["website"],
                    "location":    comp_data["location"],
                    "description": comp_data["description"],
                },
            )
            company_map[obj.name] = obj
            if created:
                comp_created += 1
            else:
                comp_skipped += 1

        self.stdout.write(
            f"   OK: {comp_created} created, {comp_skipped} already existed."
        )

        # ── 3. Seed jobs ───────────────────────────────────────────────────
        self.stdout.write("\n[3/3] Seeding jobs...")
        company_list  = list(company_map.values())
        job_created   = 0
        job_skipped   = 0
        today         = date.today()

        # We iterate over JOB_SPECS and assign companies / locations / types
        # deterministically so the output is stable across runs.
        for idx, spec in enumerate(JOB_SPECS):
            # Rotate through companies, locations and job types deterministically
            company  = company_list[idx % len(company_list)]
            location = LOCATIONS[idx % len(LOCATIONS)]
            job_type = JOB_TYPES[idx % len(JOB_TYPES)]

            # Internship: force 0 experience and lower salary
            exp_min, exp_max = spec["exp_range"]
            sal_min, sal_max = spec["salary_range"]

            if job_type == "Internship":
                experience_required = 0
                salary = clean_salary(random.randint(600_000, 1_500_000))  # noqa: S311
            else:
                experience_required = random.randint(exp_min, exp_max)  # noqa: S311
                salary = clean_salary(random.randint(sal_min, sal_max))  # noqa: S311

            # Deadline: 30–120 days from today
            deadline = today + timedelta(days=random.randint(30, 120))  # noqa: S311

            # Unique key: title + company (matches uniqueness expectation)
            _, created = Job.objects.get_or_create(
                title=spec["title"],
                company=company,
                defaults={
                    "category":            category_map[spec["category"]],
                    "description":         spec["description"],
                    "requirements":        spec["requirements"],
                    "required_skills":     spec["skills"],
                    "location":            location,
                    "salary":              salary,
                    "experience_required": experience_required,
                    "job_type":            job_type,
                    "deadline":            deadline,
                },
            )

            if created:
                job_created += 1
                self.stdout.write(
                    f"   + [{company.name}] {spec['title']} "
                    f"-- {job_type} | {location} | UGX {salary:,}"
                )
            else:
                job_skipped += 1

        # ── 4. Generate extra postings by varying company assignments ──────
        # This gives us 100+ jobs by re-using specs with different companies.
        extra_combos = [
            (spec, company)
            for spec in JOB_SPECS
            for company in company_list
            if not Job.objects.filter(title=spec["title"], company=company).exists()
        ]

        random.shuffle(extra_combos)  # noqa: S311
        target_total = 100
        existing_count = Job.objects.count()
        extras_needed = max(0, target_total - existing_count)

        for spec, company in extra_combos[:extras_needed]:
            location = random.choice(LOCATIONS)  # noqa: S311
            job_type = random.choice(JOB_TYPES)   # noqa: S311
            exp_min, exp_max = spec["exp_range"]
            sal_min, sal_max = spec["salary_range"]

            if job_type == "Internship":
                experience_required = 0
                salary = clean_salary(random.randint(600_000, 1_500_000))  # noqa: S311
            else:
                experience_required = random.randint(exp_min, exp_max)  # noqa: S311
                salary = clean_salary(random.randint(sal_min, sal_max))  # noqa: S311

            deadline = today + timedelta(days=random.randint(30, 120))  # noqa: S311

            Job.objects.create(
                title=spec["title"],
                company=company,
                category=category_map[spec["category"]],
                description=spec["description"],
                requirements=spec["requirements"],
                required_skills=spec["skills"],
                location=location,
                salary=salary,
                experience_required=experience_required,
                job_type=job_type,
                deadline=deadline,
            )
            job_created += 1
            self.stdout.write(
                f"   + [{company.name}] {spec['title']} "
                f"-- {job_type} | {location} | UGX {salary:,}"
            )

        # ── Summary ────────────────────────────────────────────────────────
        total_jobs = Job.objects.count()
        self.stdout.write("\n" + "-" * 55)
        self.stdout.write(self.style.SUCCESS(
            f"Seeding complete!\n"
            f"   Categories : {JobCategory.objects.count()}\n"
            f"   Companies  : {Company.objects.count()}\n"
            f"   Jobs       : {total_jobs} total "
            f"({job_created} created, {job_skipped} skipped)"
        ))
