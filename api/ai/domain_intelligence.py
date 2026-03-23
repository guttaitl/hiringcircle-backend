import re

# =========================================================
# DOMAIN VOCABULARY — ENTERPRISE SCALE
# =========================================================
DOMAIN_KEYWORDS = {

    # -----------------------------------------------------
    # FINANCIAL SERVICES
    # -----------------------------------------------------
    "banking": [
        "bank", "core banking", "trading", "payments", "swift",
        "aml", "kyc", "treasury", "settlement", "fraud",
        "transaction processing", "credit risk", "fintech",
        "investment banking", "capital markets"
    ],

    "insurance": [
        "insurance", "claims", "underwriting", "actuarial",
        "policy", "premium", "reinsurance", "brokerage"
    ],

    "asset_management": [
        "asset management", "portfolio management",
        "fund", "wealth management", "hedge fund"
    ],

    # -----------------------------------------------------
    # HEALTHCARE & LIFE SCIENCES
    # -----------------------------------------------------
    "healthcare": [
        "patient", "clinical", "hospital", "ehr",
        "hipaa", "medical", "diagnosis", "healthcare",
        "care management", "clinical workflow"
    ],

    "pharmaceuticals": [
        "pharma", "drug development", "clinical trial",
        "fda", "gmp", "biotech", "life sciences"
    ],

    "medical_devices": [
        "medical device", "radiology", "imaging",
        "diagnostic equipment", "medtech"
    ],

    # -----------------------------------------------------
    # TECHNOLOGY
    # -----------------------------------------------------
    "software": [
        "software", "saas", "platform", "web app",
        "backend", "frontend", "microservices",
        "distributed systems"
    ],

    "cloud": [
        "cloud", "aws", "azure", "gcp",
        "serverless", "kubernetes", "container",
        "infrastructure as code"
    ],

    "cybersecurity": [
        "security", "cybersecurity", "soc", "siem",
        "threat detection", "penetration testing",
        "identity access management", "zero trust"
    ],

    "ai_ml": [
        "machine learning", "deep learning", "nlp",
        "computer vision", "model training",
        "data science", "artificial intelligence",
        "transformers", "llm"
    ],

    "data_engineering": [
        "data pipeline", "etl", "data warehouse",
        "big data", "spark", "hadoop", "analytics"
    ],

    # -----------------------------------------------------
    # TELECOM
    # -----------------------------------------------------
    "telecom": [
        "telecom", "5g", "lte", "network",
        "subscriber", "billing", "voip",
        "carrier", "bss", "oss"
    ],

    # -----------------------------------------------------
    # E-COMMERCE & RETAIL
    # -----------------------------------------------------
    "retail": [
        "retail", "merchandising", "inventory",
        "pos", "supply chain", "store operations"
    ],

    "ecommerce": [
        "ecommerce", "shopping cart", "checkout",
        "catalog", "product listing",
        "marketplace", "order fulfillment"
    ],

    # -----------------------------------------------------
    # MANUFACTURING & INDUSTRIAL
    # -----------------------------------------------------
    "manufacturing": [
        "manufacturing", "production line",
        "factory automation", "lean manufacturing",
        "quality control"
    ],

    "automotive": [
        "automotive", "vehicle", "oem",
        "autonomous driving", "infotainment"
    ],

    "aerospace": [
        "aerospace", "aviation", "aircraft",
        "flight systems", "defense contractor"
    ],

    # -----------------------------------------------------
    # ENERGY & UTILITIES
    # -----------------------------------------------------
    "energy": [
        "energy", "power generation", "electric grid",
        "renewable energy", "solar", "wind"
    ],

    "oil_gas": [
        "oil", "gas", "drilling", "refinery",
        "upstream", "downstream"
    ],

    "utilities": [
        "utilities", "water supply", "electric utility",
        "grid operations"
    ],

    # -----------------------------------------------------
    # GOVERNMENT & PUBLIC SECTOR
    # -----------------------------------------------------
    "government": [
        "public sector", "federal", "state",
        "municipal", "government", "defense"
    ],

    "defense": [
        "military", "defense systems",
        "weapons systems", "classified"
    ],

    # -----------------------------------------------------
    # EDUCATION
    # -----------------------------------------------------
    "education": [
        "education", "university", "student",
        "learning management", "lms",
        "curriculum", "academic"
    ],

    "edtech": [
        "edtech", "online learning",
        "virtual classroom", "course platform"
    ],

    # -----------------------------------------------------
    # LOGISTICS & SUPPLY CHAIN
    # -----------------------------------------------------
    "logistics": [
        "logistics", "shipping", "transport",
        "warehouse", "fleet management",
        "last mile delivery"
    ],

    "supply_chain": [
        "supply chain", "procurement",
        "inventory planning", "demand forecasting"
    ],

    # -----------------------------------------------------
    # REAL ESTATE & CONSTRUCTION
    # -----------------------------------------------------
    "real_estate": [
        "real estate", "property management",
        "leasing", "commercial property"
    ],

    "construction": [
        "construction", "infrastructure",
        "civil engineering", "site management"
    ],

    # -----------------------------------------------------
    # MEDIA & ENTERTAINMENT
    # -----------------------------------------------------
    "media": [
        "media", "broadcast", "publishing",
        "content management"
    ],

    "entertainment": [
        "gaming", "film", "music",
        "streaming platform"
    ],

    # -----------------------------------------------------
    # TRAVEL & HOSPITALITY
    # -----------------------------------------------------
    "travel": [
        "travel", "booking", "reservation",
        "airline", "tourism"
    ],

    "hospitality": [
        "hotel", "hospitality",
        "guest services", "resort"
    ],

    # -----------------------------------------------------
    # HR & RECRUITMENT
    # -----------------------------------------------------
    "hr_tech": [
        "hr", "recruitment", "talent acquisition",
        "payroll", "benefits administration"
    ],

    # -----------------------------------------------------
    # AGRICULTURE
    # -----------------------------------------------------
    "agriculture": [
        "agriculture", "farming",
        "crop management", "agritech"
    ],

    # -----------------------------------------------------
    # LEGAL
    # -----------------------------------------------------
    "legal": [
        "legal", "compliance",
        "contract management", "law firm"
    ]
}


# =========================================================
# DOMAIN DETECTION
# =========================================================
def detect_domains(text: str):
    if not text:
        return []

    text = text.lower()
    found = []

    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", text):
                found.append(domain)
                break

    return found


# =========================================================
# DOMAIN SIMILARITY SCORE (0-100)
# =========================================================
def domain_similarity(job_domains, resume_domains):
    if not job_domains or not resume_domains:
        return 0

    overlap = len(set(job_domains) & set(resume_domains))
    return overlap / len(set(job_domains)) * 100