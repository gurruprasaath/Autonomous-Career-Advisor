"""Generates the bundled sample datasets (deterministic, seeded).

Produces in app/data/:
  - skills_taxonomy.json   ESCO-style curated tech-skill taxonomy
  - jobs_sample.json       SYNTHETIC job postings (clearly marked as such)
  - courses_sample.json    catalog of real, well-known learning resources

The job postings are synthetic stand-ins so the pipeline works offline.
For the research evaluation, switch JOB_PROVIDER=adzuna to use live data.

Run:  python scripts/generate_data.py
"""
import json
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "app" / "data"
OUT.mkdir(parents=True, exist_ok=True)
rng = random.Random(42)

# --------------------------------------------------------------------------
# 1. Skills taxonomy
# --------------------------------------------------------------------------
# category -> list of (id, name, aliases, prerequisites)
TAXONOMY = {
    "programming": [
        ("python", "Python", ["python3", "py"], []),
        ("javascript", "JavaScript", ["js", "ecmascript"], []),
        ("typescript", "TypeScript", ["ts"], ["javascript"]),
        ("java", "Java", [], []),
        ("go", "Go", ["golang"], []),
        ("cpp", "C++", ["c plus plus"], []),
        ("bash", "Bash / Shell Scripting", ["shell", "shell scripting"], []),
        ("r-lang", "R", ["r programming"], []),
    ],
    "web-frontend": [
        ("html-css", "HTML & CSS", ["html", "css", "html5", "css3"], []),
        ("react", "React", ["reactjs", "react.js"], ["javascript"]),
        ("nextjs", "Next.js", ["next"], ["react"]),
        ("vue", "Vue.js", ["vuejs"], ["javascript"]),
        ("tailwind", "Tailwind CSS", ["tailwindcss"], ["html-css"]),
        ("state-management", "Frontend State Management", ["redux", "zustand"], ["react"]),
        ("web-accessibility", "Web Accessibility", ["a11y", "wcag"], ["html-css"]),
    ],
    "web-backend": [
        ("nodejs", "Node.js", ["node"], ["javascript"]),
        ("express", "Express.js", ["expressjs"], ["nodejs"]),
        ("fastapi", "FastAPI", [], ["python"]),
        ("django", "Django", [], ["python"]),
        ("rest-api", "REST API Design", ["restful apis", "rest apis", "api design"], []),
        ("graphql", "GraphQL", [], ["rest-api"]),
        ("auth", "Authentication & Authorization", ["oauth", "jwt", "sso"], ["rest-api"]),
        ("microservices", "Microservices Architecture", ["micro-services"], ["rest-api"]),
    ],
    "data-science": [
        ("statistics", "Statistics & Probability", ["statistical analysis", "hypothesis testing"], []),
        ("pandas", "Pandas", ["dataframes"], ["python"]),
        ("numpy", "NumPy", [], ["python"]),
        ("data-viz", "Data Visualization", ["matplotlib", "seaborn", "tableau", "power bi", "dashboards"], ["pandas"]),
        ("eda", "Exploratory Data Analysis", ["data exploration", "data analysis"], ["pandas", "statistics"]),
        ("ab-testing", "A/B Testing & Experimentation", ["experiment design"], ["statistics"]),
        ("feature-engineering", "Feature Engineering", [], ["pandas"]),
        ("storytelling", "Data Storytelling", ["presenting insights"], ["data-viz"]),
    ],
    "machine-learning": [
        ("ml-fundamentals", "Machine Learning Fundamentals", ["machine learning", "ml", "supervised learning"], ["python", "statistics"]),
        ("scikit-learn", "scikit-learn", ["sklearn"], ["ml-fundamentals"]),
        ("deep-learning", "Deep Learning", ["neural networks", "dl"], ["ml-fundamentals"]),
        ("pytorch", "PyTorch", ["torch"], ["deep-learning"]),
        ("tensorflow", "TensorFlow", ["keras"], ["deep-learning"]),
        ("nlp", "Natural Language Processing", ["text mining"], ["deep-learning"]),
        ("computer-vision", "Computer Vision", ["cv", "image processing"], ["deep-learning"]),
        ("llms", "Large Language Models & Prompting", ["llm", "generative ai", "genai", "prompt engineering"], ["nlp"]),
        ("rag", "Retrieval-Augmented Generation", ["vector search", "embeddings"], ["llms"]),
        ("agentic-ai", "Agentic AI & LLM Orchestration", ["ai agents", "langchain", "langgraph", "multi-agent"], ["llms"]),
        ("mlops", "MLOps & Model Deployment", ["model serving", "ml pipelines", "model monitoring"], ["ml-fundamentals", "docker"]),
        ("model-evaluation", "Model Evaluation & Metrics", ["cross-validation", "metrics"], ["ml-fundamentals"]),
    ],
    "data-engineering": [
        ("sql", "SQL", ["postgresql", "mysql", "structured query language"], []),
        ("etl", "ETL / Data Pipelines", ["elt", "data pipelines"], ["sql", "python"]),
        ("spark", "Apache Spark", ["pyspark"], ["python", "sql"]),
        ("airflow", "Apache Airflow", ["workflow orchestration"], ["etl"]),
        ("kafka", "Apache Kafka", ["event streaming"], []),
        ("data-warehousing", "Data Warehousing", ["snowflake", "bigquery", "redshift"], ["sql"]),
        ("dbt", "dbt (Data Build Tool)", [], ["sql"]),
        ("data-modeling", "Data Modeling", ["dimensional modeling", "star schema"], ["sql"]),
        ("nosql", "NoSQL Databases", ["mongodb", "dynamodb", "cassandra"], []),
    ],
    "devops-cloud": [
        ("linux", "Linux Administration", ["unix"], []),
        ("git", "Git & Version Control", ["github", "gitlab", "version control"], []),
        ("docker", "Docker & Containers", ["containers", "containerization"], ["linux"]),
        ("kubernetes", "Kubernetes", ["k8s"], ["docker"]),
        ("aws", "AWS", ["amazon web services", "ec2", "s3", "lambda"], []),
        ("azure", "Microsoft Azure", [], []),
        ("gcp", "Google Cloud Platform", [], []),
        ("terraform", "Terraform / IaC", ["infrastructure as code", "iac"], ["aws"]),
        ("cicd", "CI/CD Pipelines", ["jenkins", "github actions", "continuous integration"], ["git"]),
        ("monitoring", "Monitoring & Observability", ["prometheus", "grafana", "logging"], ["linux"]),
    ],
    "cybersecurity": [
        ("networking", "Computer Networking", ["tcp/ip", "dns", "network protocols"], []),
        ("network-security", "Network Security", ["firewalls", "ids", "ips", "vpn"], ["networking"]),
        ("siem", "SIEM & Log Analysis", ["splunk", "security monitoring", "soc"], ["network-security"]),
        ("incident-response", "Incident Response", ["ir", "forensics"], ["siem"]),
        ("vuln-assessment", "Vulnerability Assessment", ["penetration testing basics", "nessus", "vulnerability scanning"], ["network-security"]),
        ("threat-intel", "Threat Intelligence", ["mitre att&ck", "threat hunting"], ["incident-response"]),
        ("appsec", "Application Security", ["owasp", "secure coding", "sast", "dast"], ["rest-api"]),
        ("cryptography", "Cryptography Basics", ["encryption", "pki", "tls"], []),
        ("iam", "Identity & Access Management", ["zero trust"], ["auth"]),
        ("cloud-security", "Cloud Security", ["cspm"], ["aws", "network-security"]),
    ],
    "professional": [
        ("communication", "Technical Communication", ["presentation skills", "stakeholder communication"], []),
        ("agile", "Agile & Scrum", ["scrum", "kanban", "jira"], []),
        ("problem-solving", "Problem Solving & DSA", ["data structures", "algorithms", "dsa"], []),
        ("system-design", "System Design", ["scalability", "architecture"], ["rest-api"]),
        ("testing", "Software Testing", ["unit testing", "pytest", "jest", "tdd"], []),
    ],
}

skills = []
for category, entries in TAXONOMY.items():
    for sid, name, aliases, prereqs in entries:
        skills.append({
            "id": sid, "name": name, "aliases": aliases,
            "category": category, "prerequisites": prereqs,
        })
SKILL_IDS = {s["id"] for s in skills}
for s in skills:
    assert all(p in SKILL_IDS for p in s["prerequisites"]), f"bad prereq in {s['id']}"

(OUT / "skills_taxonomy.json").write_text(
    json.dumps({"source": "Curated ESCO-style subset for tech roles (student project v1). "
                          "Replace/extend with the full ESCO download for the final evaluation.",
                "skills": skills}, indent=2),
    encoding="utf-8")
print(f"skills_taxonomy.json: {len(skills)} skills")

# --------------------------------------------------------------------------
# 2. Synthetic job postings
# --------------------------------------------------------------------------
# role -> list of (skill_id, probability of appearing, required_level)
ROLE_PROFILES = {
    "Data Scientist": [
        ("python", 0.97, "advanced"), ("sql", 0.88, "intermediate"),
        ("statistics", 0.85, "advanced"), ("pandas", 0.82, "advanced"),
        ("ml-fundamentals", 0.92, "advanced"), ("scikit-learn", 0.60, "intermediate"),
        ("data-viz", 0.72, "intermediate"), ("eda", 0.55, "intermediate"),
        ("deep-learning", 0.45, "intermediate"), ("nlp", 0.30, "beginner"),
        ("llms", 0.42, "intermediate"), ("ab-testing", 0.38, "intermediate"),
        ("feature-engineering", 0.44, "intermediate"), ("model-evaluation", 0.50, "intermediate"),
        ("aws", 0.35, "beginner"), ("communication", 0.58, "intermediate"),
        ("storytelling", 0.33, "intermediate"), ("git", 0.40, "beginner"),
        ("spark", 0.22, "beginner"), ("numpy", 0.35, "intermediate"),
    ],
    "ML Engineer": [
        ("python", 0.98, "advanced"), ("ml-fundamentals", 0.90, "advanced"),
        ("pytorch", 0.62, "advanced"), ("tensorflow", 0.42, "intermediate"),
        ("mlops", 0.78, "advanced"), ("docker", 0.75, "intermediate"),
        ("kubernetes", 0.48, "intermediate"), ("aws", 0.55, "intermediate"),
        ("cicd", 0.52, "intermediate"), ("llms", 0.58, "intermediate"),
        ("rag", 0.40, "intermediate"), ("agentic-ai", 0.30, "intermediate"),
        ("model-evaluation", 0.55, "advanced"), ("sql", 0.50, "intermediate"),
        ("git", 0.60, "intermediate"), ("system-design", 0.45, "intermediate"),
        ("fastapi", 0.38, "intermediate"), ("deep-learning", 0.70, "advanced"),
        ("spark", 0.25, "beginner"), ("monitoring", 0.30, "beginner"),
    ],
    "Full-Stack Developer": [
        ("javascript", 0.95, "advanced"), ("typescript", 0.68, "intermediate"),
        ("react", 0.85, "advanced"), ("nodejs", 0.80, "advanced"),
        ("html-css", 0.75, "advanced"), ("rest-api", 0.82, "advanced"),
        ("sql", 0.65, "intermediate"), ("nosql", 0.42, "intermediate"),
        ("git", 0.70, "intermediate"), ("docker", 0.45, "beginner"),
        ("testing", 0.55, "intermediate"), ("auth", 0.48, "intermediate"),
        ("nextjs", 0.40, "intermediate"), ("express", 0.50, "intermediate"),
        ("graphql", 0.25, "beginner"), ("tailwind", 0.35, "intermediate"),
        ("state-management", 0.38, "intermediate"), ("cicd", 0.32, "beginner"),
        ("system-design", 0.30, "intermediate"), ("agile", 0.45, "beginner"),
    ],
    "DevOps Engineer": [
        ("linux", 0.92, "advanced"), ("docker", 0.90, "advanced"),
        ("kubernetes", 0.80, "advanced"), ("aws", 0.72, "advanced"),
        ("terraform", 0.68, "intermediate"), ("cicd", 0.88, "advanced"),
        ("bash", 0.65, "intermediate"), ("python", 0.55, "intermediate"),
        ("monitoring", 0.62, "intermediate"), ("git", 0.70, "intermediate"),
        ("networking", 0.50, "intermediate"), ("azure", 0.35, "intermediate"),
        ("gcp", 0.25, "beginner"), ("microservices", 0.40, "intermediate"),
        ("system-design", 0.35, "intermediate"), ("cloud-security", 0.30, "beginner"),
        ("agile", 0.35, "beginner"), ("kafka", 0.18, "beginner"),
    ],
    "Cybersecurity Analyst": [
        ("networking", 0.90, "advanced"), ("network-security", 0.88, "advanced"),
        ("siem", 0.75, "intermediate"), ("incident-response", 0.70, "intermediate"),
        ("vuln-assessment", 0.65, "intermediate"), ("linux", 0.68, "intermediate"),
        ("threat-intel", 0.45, "intermediate"), ("python", 0.48, "beginner"),
        ("appsec", 0.35, "beginner"), ("cryptography", 0.40, "beginner"),
        ("iam", 0.38, "intermediate"), ("cloud-security", 0.42, "intermediate"),
        ("aws", 0.30, "beginner"), ("communication", 0.50, "intermediate"),
        ("bash", 0.30, "beginner"), ("monitoring", 0.35, "intermediate"),
    ],
    "Data Engineer": [
        ("python", 0.90, "advanced"), ("sql", 0.95, "advanced"),
        ("etl", 0.85, "advanced"), ("spark", 0.65, "intermediate"),
        ("airflow", 0.60, "intermediate"), ("data-warehousing", 0.70, "intermediate"),
        ("kafka", 0.40, "intermediate"), ("dbt", 0.35, "intermediate"),
        ("data-modeling", 0.55, "intermediate"), ("aws", 0.50, "intermediate"),
        ("docker", 0.40, "beginner"), ("git", 0.55, "intermediate"),
        ("nosql", 0.35, "beginner"), ("cicd", 0.28, "beginner"),
        ("linux", 0.35, "beginner"), ("system-design", 0.30, "intermediate"),
        ("gcp", 0.22, "beginner"), ("pandas", 0.45, "intermediate"),
    ],
}

COMPANIES = [
    "NimbusWorks Technologies", "Kestrel Analytics", "BlueFern Systems", "Vantara Labs",
    "Orbita Software", "HeliosGrid", "Cobalt Peak Solutions", "Mirava Digital",
    "StratusForge", "QuillStack", "Aurelia Cloud", "Zenith DataWorks",
    "PineBridge Tech", "LumenRiver", "OakShore Infotech", "CedarPoint AI",
]
CITIES = ["Bengaluru", "Chennai", "Hyderabad", "Pune", "Mumbai", "Coimbatore",
          "Gurugram", "Remote (India)", "Noida", "Kochi"]
SENIORITY = [("Junior ", 0.35), ("", 0.45), ("Senior ", 0.20)]

LEVEL_PHRASES = {
    "beginner": ["familiarity with", "exposure to", "basic knowledge of"],
    "intermediate": ["working knowledge of", "hands-on experience with", "solid grasp of"],
    "advanced": ["strong expertise in", "deep experience with", "proven proficiency in"],
}
SKILL_BY_ID = {s["id"]: s for s in skills}

postings = []
pid = 1000
for role, profile in ROLE_PROFILES.items():
    for i in range(20):
        seniority = rng.choices([s for s, _ in SENIORITY], weights=[w for _, w in SENIORITY])[0]
        company = rng.choice(COMPANIES)
        city = rng.choice(CITIES)
        required = []
        for sid, prob, level in profile:
            if rng.random() < prob:
                required.append((sid, level))
        # every posting keeps its top-3 core skills so postings stay realistic
        core = [sid for sid, _, _ in profile[:3]]
        for c, lvl in [(s, l) for s, _, l in profile[:3]]:
            if c not in [r[0] for r in required]:
                required.insert(0, (c, lvl))
        lines = []
        for sid, level in required:
            sk = SKILL_BY_ID[sid]
            mention = rng.choice([sk["name"]] + (sk["aliases"] or [sk["name"]]))
            lines.append(f"- {rng.choice(LEVEL_PHRASES[level]).capitalize()} {mention}")
        desc = (
            f"{company} is hiring a {seniority}{role} in {city}. "
            f"You will join a team of {rng.randint(4, 25)} building products for "
            f"{rng.choice(['fintech', 'healthcare', 'e-commerce', 'edtech', 'logistics', 'SaaS'])} clients.\n"
            "Requirements:\n" + "\n".join(lines)
        )
        postings.append({
            "id": f"job-{pid}",
            "role": role,
            "title": f"{seniority}{role}",
            "company": company,
            "location": city,
            "description": desc,
            "skills": [{"skill_id": sid, "level": level} for sid, level in required],
        })
        pid += 1

(OUT / "jobs_sample.json").write_text(
    json.dumps({"notice": "SYNTHETIC postings generated by scripts/generate_data.py for offline "
                          "development. NOT real job ads. Use JOB_PROVIDER=adzuna for real data.",
                "postings": postings}, indent=2),
    encoding="utf-8")
print(f"jobs_sample.json: {len(postings)} postings across {len(ROLE_PROFILES)} roles")

# --------------------------------------------------------------------------
# 3. Course catalog (real, well-known free resources)
# --------------------------------------------------------------------------
COURSES = {
    "python": [("Python for Everybody", "Coursera (University of Michigan)", "https://www.coursera.org/specializations/python"),
               ("Official Python Tutorial", "python.org", "https://docs.python.org/3/tutorial/")],
    "javascript": [("JavaScript Algorithms and Data Structures", "freeCodeCamp", "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/"),
                   ("MDN JavaScript Guide", "MDN Web Docs", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide")],
    "typescript": [("TypeScript Handbook", "typescriptlang.org", "https://www.typescriptlang.org/docs/handbook/intro.html")],
    "java": [("Java Programming and Software Engineering Fundamentals", "Coursera (Duke)", "https://www.coursera.org/specializations/java-programming")],
    "go": [("A Tour of Go", "go.dev", "https://go.dev/tour/")],
    "cpp": [("C++ Tutorial", "learncpp.com", "https://www.learncpp.com/")],
    "bash": [("The Linux Command Line & Shell Scripting", "linuxcommand.org", "https://linuxcommand.org/")],
    "r-lang": [("R Programming", "Coursera (Johns Hopkins)", "https://www.coursera.org/learn/r-programming")],
    "html-css": [("Responsive Web Design", "freeCodeCamp", "https://www.freecodecamp.org/learn/2022/responsive-web-design/")],
    "react": [("React Official Tutorial", "react.dev", "https://react.dev/learn"),
              ("Front End Development Libraries", "freeCodeCamp", "https://www.freecodecamp.org/learn/front-end-development-libraries/")],
    "nextjs": [("Next.js Learn Course", "nextjs.org", "https://nextjs.org/learn")],
    "vue": [("Vue.js Official Tutorial", "vuejs.org", "https://vuejs.org/tutorial/")],
    "tailwind": [("Tailwind CSS Docs & Screencasts", "tailwindcss.com", "https://tailwindcss.com/docs")],
    "state-management": [("Redux Essentials", "redux.js.org", "https://redux.js.org/tutorials/essentials/part-1-overview-concepts")],
    "web-accessibility": [("Learn Accessibility", "web.dev", "https://web.dev/learn/accessibility")],
    "nodejs": [("Node.js Official Learn Guides", "nodejs.org", "https://nodejs.org/en/learn"),
               ("Back End Development and APIs", "freeCodeCamp", "https://www.freecodecamp.org/learn/back-end-development-and-apis/")],
    "express": [("Express Guide", "expressjs.com", "https://expressjs.com/en/guide/routing.html")],
    "fastapi": [("FastAPI Official Tutorial", "fastapi.tiangolo.com", "https://fastapi.tiangolo.com/tutorial/")],
    "django": [("Django Official Tutorial", "djangoproject.com", "https://docs.djangoproject.com/en/stable/intro/tutorial01/")],
    "rest-api": [("REST API Design Best Practices", "Microsoft Learn", "https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design")],
    "graphql": [("Introduction to GraphQL", "graphql.org", "https://graphql.org/learn/")],
    "auth": [("OAuth 2.0 Simplified", "oauth.net", "https://www.oauth.com/")],
    "microservices": [("Microservices Guide", "martinfowler.com", "https://martinfowler.com/microservices/")],
    "statistics": [("Statistics and Probability", "Khan Academy", "https://www.khanacademy.org/math/statistics-probability")],
    "pandas": [("Pandas Getting Started Tutorials", "pandas.pydata.org", "https://pandas.pydata.org/docs/getting_started/intro_tutorials/")],
    "numpy": [("NumPy Beginner's Guide", "numpy.org", "https://numpy.org/doc/stable/user/absolute_beginners.html")],
    "data-viz": [("Data Visualization", "freeCodeCamp", "https://www.freecodecamp.org/learn/data-visualization/"),
                 ("Tableau Public Training", "Tableau", "https://public.tableau.com/app/learn/how-to-videos")],
    "eda": [("Exploratory Data Analysis with Python", "Coursera (IBM)", "https://www.coursera.org/learn/data-analysis-with-python")],
    "ab-testing": [("A/B Testing", "Udacity", "https://www.udacity.com/course/ab-testing--ud257")],
    "feature-engineering": [("Feature Engineering", "Kaggle Learn", "https://www.kaggle.com/learn/feature-engineering")],
    "storytelling": [("Data Storytelling Guide", "storytellingwithdata.com", "https://www.storytellingwithdata.com/blog")],
    "ml-fundamentals": [("Machine Learning Specialization", "Coursera (DeepLearning.AI & Stanford)", "https://www.coursera.org/specializations/machine-learning-introduction"),
                        ("Intro to Machine Learning", "Kaggle Learn", "https://www.kaggle.com/learn/intro-to-machine-learning")],
    "scikit-learn": [("scikit-learn User Guide", "scikit-learn.org", "https://scikit-learn.org/stable/user_guide.html")],
    "deep-learning": [("Deep Learning Specialization", "Coursera (DeepLearning.AI)", "https://www.coursera.org/specializations/deep-learning"),
                      ("Practical Deep Learning for Coders", "fast.ai", "https://course.fast.ai/")],
    "pytorch": [("PyTorch Official Tutorials", "pytorch.org", "https://pytorch.org/tutorials/")],
    "tensorflow": [("TensorFlow Core Tutorials", "tensorflow.org", "https://www.tensorflow.org/tutorials")],
    "nlp": [("NLP Course", "Hugging Face", "https://huggingface.co/learn/nlp-course")],
    "computer-vision": [("Computer Vision", "Kaggle Learn", "https://www.kaggle.com/learn/computer-vision")],
    "llms": [("Generative AI for Everyone", "Coursera (DeepLearning.AI)", "https://www.coursera.org/learn/generative-ai-for-everyone"),
             ("Prompt Engineering Guide", "promptingguide.ai", "https://www.promptingguide.ai/")],
    "rag": [("LangChain RAG Tutorial", "langchain.com", "https://python.langchain.com/docs/tutorials/rag/")],
    "agentic-ai": [("LangGraph Tutorials", "langchain.com", "https://langchain-ai.github.io/langgraph/tutorials/"),
                   ("Building AI Agents (Anthropic docs)", "anthropic.com", "https://docs.anthropic.com/en/docs/build-with-claude/overview")],
    "mlops": [("MLOps Zoomcamp", "DataTalks.Club", "https://github.com/DataTalksClub/mlops-zoomcamp"),
              ("Made With ML MLOps Course", "madewithml.com", "https://madewithml.com/")],
    "model-evaluation": [("Model Validation", "Kaggle Learn", "https://www.kaggle.com/learn/intro-to-machine-learning")],
    "sql": [("SQLBolt Interactive Lessons", "sqlbolt.com", "https://sqlbolt.com/"),
            ("Intro to SQL", "Kaggle Learn", "https://www.kaggle.com/learn/intro-to-sql")],
    "etl": [("Data Engineering Zoomcamp", "DataTalks.Club", "https://github.com/DataTalksClub/data-engineering-zoomcamp")],
    "spark": [("Spark Quick Start", "spark.apache.org", "https://spark.apache.org/docs/latest/quick-start.html")],
    "airflow": [("Airflow Tutorials", "airflow.apache.org", "https://airflow.apache.org/docs/apache-airflow/stable/tutorial/index.html")],
    "kafka": [("Kafka Quickstart", "kafka.apache.org", "https://kafka.apache.org/quickstart")],
    "data-warehousing": [("BigQuery Getting Started", "Google Cloud", "https://cloud.google.com/bigquery/docs/introduction")],
    "dbt": [("dbt Fundamentals", "dbt Labs", "https://learn.getdbt.com/")],
    "data-modeling": [("Kimball Dimensional Modeling Techniques", "kimballgroup.com", "https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/")],
    "nosql": [("MongoDB University Basics", "MongoDB", "https://learn.mongodb.com/")],
    "linux": [("Linux Journey", "linuxjourney.com", "https://linuxjourney.com/")],
    "git": [("Pro Git Book", "git-scm.com", "https://git-scm.com/book/en/v2"),
            ("GitHub Skills", "GitHub", "https://skills.github.com/")],
    "docker": [("Docker Get Started Guide", "docker.com", "https://docs.docker.com/get-started/")],
    "kubernetes": [("Kubernetes Basics", "kubernetes.io", "https://kubernetes.io/docs/tutorials/kubernetes-basics/")],
    "aws": [("AWS Cloud Practitioner Essentials", "AWS Skill Builder", "https://skillbuilder.aws/"),
            ("AWS Free Tier Hands-on", "AWS", "https://aws.amazon.com/getting-started/hands-on/")],
    "azure": [("Azure Fundamentals Learning Path", "Microsoft Learn", "https://learn.microsoft.com/en-us/training/paths/microsoft-azure-fundamentals-describe-cloud-concepts/")],
    "gcp": [("Google Cloud Skills Boost", "Google", "https://www.cloudskillsboost.google/")],
    "terraform": [("Terraform Tutorials", "HashiCorp", "https://developer.hashicorp.com/terraform/tutorials")],
    "cicd": [("GitHub Actions Documentation", "GitHub", "https://docs.github.com/en/actions"),
             ("CI/CD with Jenkins", "jenkins.io", "https://www.jenkins.io/doc/tutorials/")],
    "monitoring": [("Prometheus Getting Started", "prometheus.io", "https://prometheus.io/docs/prometheus/latest/getting_started/")],
    "networking": [("Computer Networking Full Course", "freeCodeCamp (YouTube)", "https://www.youtube.com/watch?v=qiQR5rTSshw"),
                   ("Cisco Networking Basics", "Cisco Networking Academy", "https://www.netacad.com/courses/networking-basics")],
    "network-security": [("Introduction to Cybersecurity", "Cisco Networking Academy", "https://www.netacad.com/courses/introduction-to-cybersecurity")],
    "siem": [("Splunk Free Training", "Splunk", "https://www.splunk.com/en_us/training/free-courses/overview.html")],
    "incident-response": [("Incident Handler's Handbook", "SANS Reading Room", "https://www.sans.org/white-papers/33901/")],
    "vuln-assessment": [("TryHackMe Vulnerability Research Path", "TryHackMe", "https://tryhackme.com/")],
    "threat-intel": [("MITRE ATT&CK Fundamentals", "MITRE", "https://attack.mitre.org/resources/learn-more-about-attack/")],
    "appsec": [("OWASP Top 10", "OWASP", "https://owasp.org/www-project-top-ten/"),
               ("PortSwigger Web Security Academy", "PortSwigger", "https://portswigger.net/web-security")],
    "cryptography": [("Cryptography I", "Coursera (Stanford)", "https://www.coursera.org/learn/crypto")],
    "iam": [("Identity Fundamentals", "Microsoft Learn", "https://learn.microsoft.com/en-us/entra/fundamentals/identity-fundamental-concepts")],
    "cloud-security": [("AWS Security Fundamentals", "AWS Skill Builder", "https://skillbuilder.aws/")],
    "communication": [("Technical Writing Courses", "Google", "https://developers.google.com/tech-writing")],
    "agile": [("Agile with Atlassian Jira", "Coursera (Atlassian)", "https://www.coursera.org/learn/agile-atlassian-jira")],
    "problem-solving": [("NeetCode Roadmap", "neetcode.io", "https://neetcode.io/roadmap"),
                        ("LeetCode Study Plans", "LeetCode", "https://leetcode.com/studyplan/")],
    "system-design": [("System Design Primer", "GitHub (donnemartin)", "https://github.com/donnemartin/system-design-primer")],
    "testing": [("Test Automation University", "Applitools", "https://testautomationu.applitools.com/")],
}

courses = []
cid = 1
for sid, entries in COURSES.items():
    assert sid in SKILL_IDS, f"course maps to unknown skill {sid}"
    for title, provider, url in entries:
        courses.append({
            "id": f"course-{cid:03d}", "skill_id": sid, "title": title,
            "provider": provider, "url": url, "free": True,
        })
        cid += 1

uncovered = SKILL_IDS - set(COURSES.keys())
(OUT / "courses_sample.json").write_text(
    json.dumps({"note": "Real, well-known free learning resources. URLs point to stable "
                        "top-level course pages.",
                "courses": courses}, indent=2),
    encoding="utf-8")
print(f"courses_sample.json: {len(courses)} courses covering {len(COURSES)} skills")
if uncovered:
    print(f"WARNING: {len(uncovered)} skills without courses: {sorted(uncovered)}")
