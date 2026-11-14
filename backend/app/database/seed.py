"""Idempotent catalog seeding plus clearly-labelled demo accounts.

The catalog (skills, careers, trusted resources, question bank) is required for
the platform to function. Demo accounts and demo evidence are separate and are
only created when SEED_DEMO_ON_START is enabled and the database is empty.
"""

from app.repositories import (
    catalog_repo,
    learning_repo,
    operations_repo,
    organizations_repo,
    profiles_repo,
    users_repo,
)
from app.security.passwords import hash_password
from app.services import skill_service
from app.utils.ids import now_utc

SKILLS = [
    ("Python", "Programming", "General-purpose programming language."),
    ("SQL", "Data", "Querying and shaping relational data."),
    ("HTML", "Web", "Semantic structure for web pages."),
    ("CSS", "Web", "Styling, layout and responsive design."),
    ("JavaScript", "Web", "Client-side programming for the web."),
    ("React", "Web", "Component-based UI library."),
    ("Node.js", "Web", "Server-side JavaScript runtime."),
    ("Git", "Engineering", "Version control and collaboration."),
    ("Data Analysis", "Data", "Exploring and summarising datasets."),
    ("Statistics", "Data", "Statistical reasoning and inference."),
    ("Machine Learning", "AI", "Building models that learn from data."),
    ("Cloud Fundamentals", "Cloud", "Core cloud computing concepts."),
    ("Cybersecurity Fundamentals", "Security", "Security principles and threats."),
    ("UI/UX Design", "Design", "Designing usable digital experiences."),
    ("Communication", "Soft skills", "Clear written and verbal communication."),
    ("Problem Solving", "Soft skills", "Structured analytical problem solving."),
]

CAREERS = [
    (
        "Full Stack Developer",
        "Builds and maintains both client-side and server-side web applications.",
        "Entry to mid level",
        [("Python", 60, 3), ("SQL", 55, 2.5), ("HTML", 75, 3), ("CSS", 70, 3),
         ("JavaScript", 75, 3), ("React", 65, 3), ("Node.js", 60, 3), ("Git", 50, 2)],
        [("Communication", 60), ("Problem Solving", 65)],
        "A deployed full stack application with authentication and a documented database.",
    ),
    (
        "Frontend Developer",
        "Builds accessible, responsive user interfaces for web products.",
        "Entry level",
        [("HTML", 80, 3), ("CSS", 80, 3), ("JavaScript", 75, 3), ("React", 70, 3),
         ("Git", 50, 2), ("UI/UX Design", 50, 2)],
        [("Communication", 60), ("Problem Solving", 60)],
        "A responsive multi-page interface with reusable components and accessibility checks.",
    ),
    (
        "Backend Developer",
        "Designs APIs, business logic and data access layers.",
        "Entry to mid level",
        [("Python", 75, 3), ("SQL", 70, 3), ("Node.js", 65, 3), ("Git", 55, 2),
         ("Cloud Fundamentals", 45, 1.5)],
        [("Cybersecurity Fundamentals", 50), ("Problem Solving", 65)],
        "A documented REST API with authentication, validation and tests.",
    ),
    (
        "Data Analyst",
        "Turns data into clear, decision-ready insights.",
        "Entry level",
        [("SQL", 70, 3), ("Data Analysis", 75, 3), ("Statistics", 65, 2.5),
         ("Python", 55, 2), ("Communication", 60, 2)],
        [("Machine Learning", 40), ("Problem Solving", 60)],
        "An exploratory analysis with a clean notebook and a stakeholder-ready summary.",
    ),
    (
        "Data Scientist",
        "Uses statistics and machine learning to answer business questions.",
        "Mid level",
        [("Python", 75, 3), ("Statistics", 75, 3), ("Machine Learning", 70, 3),
         ("Data Analysis", 75, 3), ("SQL", 60, 2.5)],
        [("Communication", 65), ("Cloud Fundamentals", 45)],
        "An end-to-end model project with evaluation, limitations and a written report.",
    ),
    (
        "AI/ML Engineer",
        "Builds and operates machine learning systems in production.",
        "Mid level",
        [("Python", 80, 3), ("Machine Learning", 80, 3), ("Statistics", 70, 3),
         ("Cloud Fundamentals", 50, 1.5), ("Git", 50, 1.5)],
        [("Cybersecurity Fundamentals", 45), ("Problem Solving", 70)],
        "A reproducible training pipeline and a served model with monitoring notes.",
    ),
    (
        "Cloud Engineer",
        "Designs and operates cloud infrastructure and deployments.",
        "Entry to mid level",
        [("Cloud Fundamentals", 80, 3), ("Git", 55, 2), ("Python", 50, 2),
         ("Cybersecurity Fundamentals", 55, 2), ("SQL", 40, 1)],
        [("Communication", 55), ("Problem Solving", 65)],
        "A deployed application with infrastructure documentation and cost awareness.",
    ),
    (
        "Cybersecurity Analyst",
        "Monitors, investigates and reduces security risk.",
        "Entry level",
        [("Cybersecurity Fundamentals", 80, 3), ("Cloud Fundamentals", 50, 2),
         ("Communication", 60, 2), ("Problem Solving", 70, 2.5)],
        [("Python", 45), ("SQL", 40)],
        "A threat assessment write-up with evidence and practical mitigations.",
    ),
    (
        "DevOps Engineer",
        "Automates build, release and reliable operations.",
        "Mid level",
        [("Git", 80, 3), ("Cloud Fundamentals", 70, 3), ("Python", 55, 2),
         ("Cybersecurity Fundamentals", 50, 2)],
        [("Communication", 55), ("Problem Solving", 65)],
        "A CI/CD pipeline for a small service with rollback notes.",
    ),
    (
        "Mobile App Developer",
        "Builds mobile applications with a polished user experience.",
        "Entry level",
        [("JavaScript", 65, 2.5), ("React", 60, 3), ("UI/UX Design", 50, 2), ("Git", 50, 1.5)],
        [("Communication", 55), ("Problem Solving", 60)],
        "A mobile application with navigation, local state and a tested user flow.",
    ),
    (
        "UI/UX Designer",
        "Designs usable, accessible product experiences.",
        "Entry level",
        [("UI/UX Design", 80, 3), ("HTML", 55, 2), ("CSS", 60, 2), ("Communication", 70, 2.5)],
        [("JavaScript", 40), ("Problem Solving", 60)],
        "A usability-tested prototype with documented design decisions.",
    ),
    (
        "Business Analyst",
        "Bridges business needs and technical delivery.",
        "Entry level",
        [("SQL", 60, 2.5), ("Data Analysis", 65, 2.5), ("Communication", 75, 3),
         ("Problem Solving", 70, 3)],
        [("UI/UX Design", 45), ("Cloud Fundamentals", 35)],
        "A requirements analysis with process maps and measurable success criteria.",
    ),
]

RESOURCES = [
    ("Python Tutorial (official)", "Python Software Foundation", "https://docs.python.org/3/tutorial/", "DOCS", ["Python"], "BEGINNER", 8),
    ("Automate the Boring Stuff with Python", "Al Sweigart", "https://automatetheboringstuff.com/", "TUTORIAL", ["Python"], "BEGINNER", 12),
    ("Exercism Python Track", "Exercism", "https://exercism.org/tracks/python", "EXERCISE", ["Python"], "INTERMEDIATE", 10),
    ("SQLBolt Interactive Lessons", "SQLBolt", "https://sqlbolt.com/", "TUTORIAL", ["SQL"], "BEGINNER", 4),
    ("Mode SQL Tutorial", "Mode Analytics", "https://mode.com/sql-tutorial/", "TUTORIAL", ["SQL"], "INTERMEDIATE", 6),
    ("Intro to SQL", "Kaggle", "https://www.kaggle.com/learn/intro-to-sql", "COURSE", ["SQL"], "BEGINNER", 4),
    ("Learn HTML", "MDN Web Docs", "https://developer.mozilla.org/en-US/docs/Learn/HTML", "DOCS", ["HTML"], "BEGINNER", 6),
    ("Responsive Web Design", "freeCodeCamp", "https://www.freecodecamp.org/learn/2022/responsive-web-design/", "COURSE", ["HTML", "CSS"], "BEGINNER", 12),
    ("Learn CSS", "MDN Web Docs", "https://developer.mozilla.org/en-US/docs/Learn/CSS", "DOCS", ["CSS"], "BEGINNER", 6),
    ("CSS Grid Garden", "Grid Garden", "https://cssgridgarden.com/", "EXERCISE", ["CSS"], "BEGINNER", 2),
    ("Flexbox Froggy", "Flexbox Froggy", "https://flexboxfroggy.com/", "EXERCISE", ["CSS"], "BEGINNER", 2),
    ("The Modern JavaScript Tutorial", "javascript.info", "https://javascript.info/", "TUTORIAL", ["JavaScript"], "BEGINNER", 10),
    ("JavaScript Guide", "MDN Web Docs", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "DOCS", ["JavaScript"], "INTERMEDIATE", 8),
    ("JavaScript Algorithms and Data Structures", "freeCodeCamp", "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures-v8/", "COURSE", ["JavaScript"], "INTERMEDIATE", 15),
    ("React Learn", "React", "https://react.dev/learn", "DOCS", ["React"], "INTERMEDIATE", 8),
    ("Full Stack Open", "University of Helsinki", "https://fullstackopen.com/en/", "COURSE", ["React", "Node.js"], "ADVANCED", 20),
    ("Learn Node.js", "Node.js", "https://nodejs.org/en/learn", "DOCS", ["Node.js"], "BEGINNER", 6),
    ("Express/Node introduction", "MDN Web Docs", "https://developer.mozilla.org/en-US/docs/Learn/Server-side/Express_Nodejs", "TUTORIAL", ["Node.js"], "INTERMEDIATE", 10),
    ("Pro Git", "Scott Chacon and Ben Straub", "https://git-scm.com/book/en/v2", "DOCS", ["Git"], "BEGINNER", 6),
    ("GitHub Skills", "GitHub", "https://skills.github.com/", "EXERCISE", ["Git"], "BEGINNER", 4),
    ("Pandas", "Kaggle", "https://www.kaggle.com/learn/pandas", "COURSE", ["Data Analysis"], "BEGINNER", 4),
    ("Pandas User Guide", "pandas", "https://pandas.pydata.org/docs/user_guide/", "DOCS", ["Data Analysis"], "INTERMEDIATE", 8),
    ("Statistics and Probability", "Khan Academy", "https://www.khanacademy.org/math/statistics-probability", "COURSE", ["Statistics"], "BEGINNER", 12),
    ("StatQuest with Josh Starmer", "StatQuest", "https://www.youtube.com/@statquest", "VIDEO", ["Statistics", "Machine Learning"], "INTERMEDIATE", 10),
    ("Machine Learning Crash Course", "Google", "https://developers.google.com/machine-learning/crash-course", "COURSE", ["Machine Learning"], "BEGINNER", 15),
    ("scikit-learn User Guide", "scikit-learn", "https://scikit-learn.org/stable/user_guide.html", "DOCS", ["Machine Learning"], "INTERMEDIATE", 10),
    ("AWS Cloud Practitioner Essentials", "AWS", "https://aws.amazon.com/training/digital/aws-cloud-practitioner-essentials/", "COURSE", ["Cloud Fundamentals"], "BEGINNER", 7),
    ("Cloud Digital Leader learning path", "Google Cloud", "https://cloud.google.com/learn/certification/digital-leader", "COURSE", ["Cloud Fundamentals"], "BEGINNER", 8),
    ("OWASP Top 10", "OWASP", "https://owasp.org/www-project-top-ten/", "DOCS", ["Cybersecurity Fundamentals"], "BEGINNER", 4),
    ("Pre Security path", "TryHackMe", "https://tryhackme.com/path/outline/presecurity", "COURSE", ["Cybersecurity Fundamentals"], "BEGINNER", 12),
    ("Material Design 3", "Google", "https://m3.material.io/", "DOCS", ["UI/UX Design"], "BEGINNER", 5),
    ("Laws of UX", "Jon Yablonski", "https://lawsofux.com/", "TUTORIAL", ["UI/UX Design"], "BEGINNER", 3),
    ("Figma Learn", "Figma", "https://help.figma.com/hc/en-us/categories/360002051613", "TUTORIAL", ["UI/UX Design"], "BEGINNER", 6),
    ("Toastmasters Pathways", "Toastmasters International", "https://www.toastmasters.org/education/pathways", "COURSE", ["Communication"], "BEGINNER", 8),
    ("Communication topic", "Harvard Business Review", "https://hbr.org/topic/subject/communication", "TUTORIAL", ["Communication"], "INTERMEDIATE", 5),
    ("Learning English", "BBC Learning English", "https://www.bbc.co.uk/learningenglish", "COURSE", ["Communication"], "BEGINNER", 8),
    ("LeetCode Learning Paths", "LeetCode", "https://leetcode.com/explore/learn/", "EXERCISE", ["Problem Solving"], "INTERMEDIATE", 10),
    ("Algorithms domain", "HackerRank", "https://www.hackerrank.com/domains/algorithms", "EXERCISE", ["Problem Solving"], "INTERMEDIATE", 10),
    ("Problem Solving course", "Brilliant", "https://brilliant.org/courses/problem-solving/", "COURSE", ["Problem Solving"], "INTERMEDIATE", 6),
]

QUESTIONS = [
    ("Python", "EASY", "Which keyword defines a function in Python?", ["def", "function", "func", "define"], 0, "def is the function definition keyword."),
    ("Python", "MEDIUM", "What does len([10, 20, 30][1:]) evaluate to?", ["3", "2", "1", "It raises an error"], 1, "The slice [1:] is [20, 30], which has length 2."),
    ("Python", "MEDIUM", "You need to store unique tags and check membership quickly. Which structure fits best?", ["list", "set", "tuple", "string"], 1, "A set stores unique values with fast membership checks."),
    ("Python", "HARD", "Why is `with open('file.txt') as handle:` preferred over calling open manually?", ["It compresses the file", "It closes the file automatically", "It makes reads faster", "It prevents editing"], 1, "The context manager closes the file even when an error occurs."),
    ("SQL", "EASY", "Which SQL clause filters rows?", ["ORDER BY", "WHERE", "GROUP BY", "LIMIT"], 1, "WHERE filters rows before grouping."),
    ("SQL", "MEDIUM", "What does SELECT COUNT(*) FROM users return?", ["The number of columns", "The number of rows", "The first row", "A list of emails"], 1, "COUNT(*) counts rows."),
    ("SQL", "MEDIUM", "You need customer names with their orders, keeping only matching rows. Which join fits?", ["CROSS JOIN", "INNER JOIN", "SELF JOIN", "UNION"], 1, "INNER JOIN keeps rows that match in both tables."),
    ("SQL", "HARD", "What is the main purpose of an index on the email column?", ["Encrypt values", "Speed up lookups", "Enforce a minimum length", "Rename the column"], 1, "An index speeds up lookups for matching values."),
    ("HTML", "EASY", "Which element represents the main content of a page?", ["<div>", "<main>", "<section>", "<span>"], 1, "<main> is the semantic landmark for primary content."),
    ("HTML", "EASY", "Which attribute provides alternative text for an image?", ["title", "alt", "src", "aria-role"], 1, "alt describes the image for assistive technology."),
    ("HTML", "MEDIUM", "How does <label for=\"email\"> help accessibility?", ["It styles the input", "It links the label to the input", "It validates the email", "It hides the input"], 1, "The for attribute associates the label with the control."),
    ("HTML", "HARD", "You need a clickable control for an important action. What is most accessible?", ["A div with onclick", "An anchor with href='#'", "A native button element", "A span with role='button'"], 2, "A native button has correct semantics and keyboard behaviour by default."),
    ("CSS", "EASY", "Which property sets text colour?", ["background", "font-color", "color", "text-style"], 2, "color sets the text colour."),
    ("CSS", "MEDIUM", "Which order matches the CSS box model from inside out?", ["margin, border, padding, content", "content, padding, border, margin", "padding, content, margin, border", "content, margin, padding, border"], 1, "Content sits inside padding, then border, then margin."),
    ("CSS", "MEDIUM", "What does the selector .card target?", ["Elements with id card", "Elements with class card", "All cards in the document", "Only the first card"], 1, "A dot targets a class."),
    ("CSS", "HARD", "Which layout tool is designed for one-dimensional row or column alignment?", ["CSS Grid", "Flexbox", "Float", "Absolute positioning"], 1, "Flexbox handles one-dimensional layout."),
    ("JavaScript", "EASY", "Which keyword declares a block-scoped constant?", ["var", "let", "const", "static"], 2, "const declares a block-scoped binding that cannot be reassigned."),
    ("JavaScript", "MEDIUM", "What is the result of typeof []?", ["array", "object", "list", "undefined"], 1, "typeof [] is 'object'."),
    ("JavaScript", "MEDIUM", "What is addEventListener used for?", ["Creating elements", "Attaching event handlers", "Fetching data", "Writing cookies"], 1, "It attaches an event handler to a target."),
    ("JavaScript", "HARD", "Promise callbacks scheduled with .then run when?", ["Immediately inside the current stack", "After the current synchronous stack (microtask)", "Before any synchronous code", "Only after a page reload"], 1, "Promise reactions run as microtasks after the current stack."),
    ("React", "EASY", "JSX is best described as...", ["A database language", "A JavaScript syntax extension", "A CSS framework", "A testing tool"], 1, "JSX lets you describe UI with JavaScript syntax."),
    ("React", "MEDIUM", "Which hook manages local component state?", ["useEffect", "useState", "useMemo", "useContext"], 1, "useState manages local state."),
    ("React", "MEDIUM", "Why is the key prop important in lists?", ["It styles items", "It helps React identify items", "It sorts items", "It validates items"], 1, "Keys give list items a stable identity."),
    ("React", "HARD", "When does a useEffect cleanup function run?", ["Only on first render", "Before unmount and before the effect re-runs", "On every state update", "Only after a timeout"], 1, "Cleanup runs before unmount and before re-running the effect."),
    ("Node.js", "EASY", "Node.js runs JavaScript using which engine?", ["SpiderMonkey", "V8", "JavaScriptCore", "Chakra"], 1, "Node.js uses V8."),
    ("Node.js", "MEDIUM", "Which built-in module creates an HTTP server?", ["fs", "http", "path", "url"], 1, "The http module provides server and client APIs."),
    ("Node.js", "MEDIUM", "What is npm mainly used for?", ["Managing packages", "Rendering UI", "Compiling CSS", "Hosting databases"], 0, "npm is the Node package manager."),
    ("Node.js", "HARD", "How do you read environment variables in Node.js?", ["window.env", "process.env", "os.env", "env.get()"], 1, "process.env exposes environment variables."),
    ("Git", "EASY", "Which command stages all changes in the current directory?", ["git commit -m", "git add .", "git push", "git status"], 1, "git add . stages current changes."),
    ("Git", "MEDIUM", "Why create a branch?", ["To delete history", "To isolate work", "To merge automatically", "To compress files"], 1, "Branches isolate work in progress."),
    ("Git", "MEDIUM", "Which command shows commit history?", ["git log", "git diff", "git status", "git init"], 0, "git log shows commit history."),
    ("Git", "HARD", "How does rebase differ from merge?", ["Rebase never changes history", "Rebase replays commits onto a new base", "Merge deletes branches", "Rebase only works on main"], 1, "Rebase replays commits onto another base, rewriting them."),
    ("Data Analysis", "EASY", "Which pandas structure is a two-dimensional table?", ["Series", "DataFrame", "Index", "Array"], 1, "A DataFrame is a two-dimensional labelled table."),
    ("Data Analysis", "MEDIUM", "Which method previews the first rows of a DataFrame?", ["tail()", "head()", "describe()", "info()"], 1, "head() previews the first rows."),
    ("Data Analysis", "MEDIUM", "You want the average salary per department. Which operation fits best?", ["A pivot only", "groupby with mean", "dropna", "sort_values"], 1, "groupby aggregates per group."),
    ("Data Analysis", "HARD", "What does groupby primarily enable?", ["Row deletion", "Aggregation by groups", "Column renaming", "Type conversion"], 1, "groupby enables grouped aggregation."),
    ("Statistics", "EASY", "Which is a measure of central tendency?", ["standard deviation", "mean", "variance", "range"], 1, "The mean is a measure of central tendency."),
    ("Statistics", "MEDIUM", "What does standard deviation describe?", ["The middle value", "Spread around the mean", "The largest value", "Correlation"], 1, "Standard deviation measures spread around the mean."),
    ("Statistics", "MEDIUM", "A p-value is...", ["The chance the null hypothesis is true", "The probability of results at least as extreme under the null", "The effect size", "The sample size"], 1, "A p-value is calculated assuming the null hypothesis is true."),
    ("Statistics", "HARD", "Which statement is correct?", ["Correlation implies causation", "Correlation does not imply causation", "Causation cannot be studied", "Correlation equals regression"], 1, "Correlation alone does not establish causation."),
    ("Machine Learning", "EASY", "Supervised learning requires...", ["Unlabelled data", "Labelled data", "No data", "Only text data"], 1, "Supervised learning uses labelled examples."),
    ("Machine Learning", "MEDIUM", "What is overfitting?", ["Poor training and test performance", "Good training but poor unseen performance", "Too little data", "Training too slowly"], 1, "Overfitting means memorising training data and generalising poorly."),
    ("Machine Learning", "MEDIUM", "Regression predicts...", ["Categories", "Continuous values", "Clusters", "Anomalies"], 1, "Regression predicts continuous values."),
    ("Machine Learning", "HARD", "Why split data into train and test sets?", ["To reduce file size", "To estimate generalisation performance", "To speed up training", "To create labels"], 1, "A held-out set estimates performance on unseen data."),
    ("Cloud Fundamentals", "EASY", "IaaS primarily provides...", ["Managed applications", "Virtualised infrastructure", "Only storage", "Only databases"], 1, "IaaS provides virtualised compute, storage and networking."),
    ("Cloud Fundamentals", "MEDIUM", "Which is an object storage service?", ["Amazon S3", "Amazon EC2", "AWS Lambda", "Amazon RDS"], 0, "Amazon S3 is object storage."),
    ("Cloud Fundamentals", "MEDIUM", "What is autoscaling?", ["Backing up data", "Adjusting capacity to demand", "Encrypting traffic", "Renaming servers"], 1, "Autoscaling adjusts capacity with demand."),
    ("Cloud Fundamentals", "HARD", "Under the shared responsibility model, the cloud provider normally manages...", ["User passwords", "Application code", "Physical infrastructure", "User data access"], 2, "Providers manage the physical infrastructure."),
    ("Cybersecurity Fundamentals", "EASY", "Phishing is...", ["A network topology", "Deceptive messages to steal credentials", "A backup method", "An encryption standard"], 1, "Phishing uses deceptive messages to steal information."),
    ("Cybersecurity Fundamentals", "MEDIUM", "Which practice improves account security most?", ["Reusing strong passwords", "Unique passwords plus MFA", "Sharing passwords with IT", "Writing passwords on paper"], 1, "Unique passwords plus MFA materially reduce risk."),
    ("Cybersecurity Fundamentals", "MEDIUM", "HTTPS primarily provides...", ["Faster downloads", "Encrypted transport", "Anonymous access", "Database backups"], 1, "HTTPS encrypts traffic in transit."),
    ("Cybersecurity Fundamentals", "HARD", "Broken access control belongs to which OWASP Top 10 (2021) category?", ["A01", "A05", "A07", "A10"], 0, "Broken Access Control is A01 in the 2021 list."),
    ("UI/UX Design", "EASY", "UX primarily focuses on...", ["Server uptime", "The user's experience", "Database design", "Network speed"], 1, "UX concerns the whole user experience."),
    ("UI/UX Design", "MEDIUM", "WCAG 2.2 AA normal-text contrast ratio is at least...", ["1.5:1", "3:1", "4.5:1", "7:1"], 2, "Normal text needs 4.5:1 under WCAG 2.2 AA."),
    ("UI/UX Design", "MEDIUM", "A wireframe is...", ["A finished visual design", "A low-fidelity layout plan", "A database schema", "A test suite"], 1, "A wireframe is a low-fidelity layout plan."),
    ("UI/UX Design", "HARD", "The consistency usability heuristic means...", ["Every page uses different controls", "Similar actions should look and behave similarly", "Users must memorise shortcuts", "Colours carry all meaning"], 1, "Consistency means similar things work similarly."),
    ("Communication", "EASY", "Active listening includes...", ["Interrupting quickly", "Focusing and confirming understanding", "Preparing a reply only", "Changing the topic"], 1, "Active listening requires focus and confirmation."),
    ("Communication", "MEDIUM", "Constructive feedback should be...", ["Vague and general", "Specific and actionable", "Only positive", "Public and personal"], 1, "Specific, actionable feedback is most useful."),
    ("Communication", "MEDIUM", "Explaining a technical idea to a non-technical audience works best by...", ["Using every technical term", "Using analogies and plain language", "Skipping the context", "Showing only code"], 1, "Analogies and plain language improve understanding."),
    ("Communication", "HARD", "A productive way to handle team disagreement is to...", ["Avoid the topic", "Focus on evidence and the shared goal", "Escalate immediately", "Let the loudest person decide"], 1, "Evidence and shared goals keep disagreement productive."),
    ("Problem Solving", "EASY", "The first step in solving a problem is to...", ["Pick a tool", "Understand the problem", "Write code", "Deploy"], 1, "Understand the problem before choosing a solution."),
    ("Problem Solving", "MEDIUM", "The 5 Whys technique helps to...", ["Estimate cost", "Find root causes", "Improve UI", "Write tests"], 1, "Repeatedly asking why helps find root causes."),
    ("Problem Solving", "MEDIUM", "Decomposition means...", ["Combining everything", "Breaking a problem into smaller parts", "Ignoring constraints", "Testing in production"], 1, "Decomposition breaks problems into manageable parts."),
    ("Problem Solving", "HARD", "A trade-off analysis compares...", ["Colours", "Benefits against costs", "Passwords", "Server names"], 1, "Trade-off analysis weighs benefits against costs."),
]

MILESTONES = [
    "Complete the baseline assessment",
    "Finish the first learning phase",
    "Pass two skill checks at 70% or higher",
    "Publish and submit a portfolio project",
]


def _seed_catalog(db) -> None:
    if db["skills"].count_documents({}) == 0:
        for name, category, description in SKILLS:
            db["skills"].insert_one(
                {
                    "_id": __import__("uuid").uuid4().hex,
                    "name": name,
                    "category": category,
                    "description": description,
                    "created_at": now_utc(),
                }
            )

    skill_ids = {doc["name"]: doc["_id"] for doc in db["skills"].find({})}

    if db["career_roles"].count_documents({}) == 0:
        for name, description, experience, required, preferred, project in CAREERS:
            db["career_roles"].insert_one(
                {
                    "_id": __import__("uuid").uuid4().hex,
                    "name": name,
                    "description": description,
                    "experience_level": experience,
                    "required_skills": [
                        {
                            "skill_id": skill_ids.get(skill_name),
                            "skill_name": skill_name,
                            "min_proficiency": min_prof,
                            "weight": weight,
                        }
                        for skill_name, min_prof, weight in required
                    ],
                    "preferred_skills": [
                        {
                            "skill_id": skill_ids.get(skill_name),
                            "skill_name": skill_name,
                            "min_proficiency": min_prof,
                            "weight": 1,
                        }
                        for skill_name, min_prof in preferred
                    ],
                    "certifications": [],
                    "project_expectations": project,
                    "milestones": MILESTONES,
                    "is_active": True,
                    "created_at": now_utc(),
                    "updated_at": now_utc(),
                }
            )

    if db["learning_resources"].count_documents({}) == 0:
        for title, provider, url, resource_type, skill_names, difficulty, hours in RESOURCES:
            db["learning_resources"].insert_one(
                {
                    "_id": __import__("uuid").uuid4().hex,
                    "title": title,
                    "provider": provider,
                    "url": url,
                    "resource_type": resource_type,
                    "skill_names": skill_names,
                    "difficulty": difficulty,
                    "duration_hours": hours,
                    "description": f"{title} from {provider}.",
                    "is_trusted": True,
                    "created_by": "system",
                    "created_at": now_utc(),
                }
            )

    if db["courses"].count_documents({}) == 0:
        for title, provider, url, resource_type, skill_names, difficulty, hours in RESOURCES:
            if resource_type != "COURSE":
                continue
            db["courses"].insert_one(
                {
                    "_id": __import__("uuid").uuid4().hex,
                    "title": title,
                    "provider": provider,
                    "description": f"{title} from {provider}.",
                    "url": url,
                    "difficulty": difficulty,
                    "duration_hours": hours,
                    "skill_names": skill_names,
                    "modules": [
                        {"id": __import__("uuid").uuid4().hex, "title": "Getting started", "position": 1},
                        {"id": __import__("uuid").uuid4().hex, "title": "Core concepts", "position": 2},
                        {"id": __import__("uuid").uuid4().hex, "title": "Hands-on project", "position": 3},
                    ],
                    "is_active": True,
                    "created_by": "system",
                    "created_at": now_utc(),
                    "updated_at": now_utc(),
                }
            )

    if db["assessment_questions"].count_documents({}) == 0:
        for skill_name, difficulty, prompt, options, correct, explanation in QUESTIONS:
            db["assessment_questions"].insert_one(
                {
                    "_id": __import__("uuid").uuid4().hex,
                    "skill_name": skill_name,
                    "difficulty": difficulty,
                    "question_type": "FACTUAL" if difficulty != "MEDIUM" else "SCENARIO",
                    "prompt": prompt,
                    "options": options,
                    "correct_option": correct,
                    "correct_keywords": [],
                    "explanation": explanation,
                    "points": 2 if difficulty == "HARD" else 1,
                    "created_at": now_utc(),
                }
            )


def ensure_super_admin(app) -> dict | None:
    email = app.config.get("SUPER_ADMIN_EMAIL") or ""
    demo_mode = app.extensions.get("db_mode") == "memory" or app.config.get("SEED_DEMO_ON_START")
    if not email and demo_mode:
        email = "superadmin@eip.local"
    if not email:
        return None
    existing = users_repo.find_by_email(email)
    if existing:
        return existing

    password = app.config.get("SUPER_ADMIN_PASSWORD")
    if not password:
        if not demo_mode:
            return None
        password = "Demo@12345"
    return users_repo.create_user(
        {
            "full_name": app.config.get("SUPER_ADMIN_NAME", "Platform Owner"),
            "email": email.lower(),
            "password_hash": hash_password(password),
            "role": "SUPER_ADMIN",
            "account_status": "APPROVED",
            "email_verified": True,
            "approved_at": now_utc(),
        }
    )


def _demo_user(name: str, email: str, role: str, org_id: str, department_id: str | None, **extra) -> dict:
    return users_repo.create_user(
        {
            "full_name": name,
            "email": email,
            "password_hash": hash_password("Demo@12345"),
            "role": role,
            "organization_id": org_id,
            "department_id": department_id,
            "account_status": "APPROVED",
            "email_verified": True,
            "approved_at": now_utc(),
            **extra,
        }
    )


def _seed_demo(app) -> None:
    if users_repo.count({"role": "SUPER_ADMIN"}) == 0:
        ensure_super_admin(app)

    university = organizations_repo.create_org(
        {
            "name": "Rathinam Technical Campus",
            "organization_type": "UNIVERSITY",
            "subtype": "Engineering College",
            "location": {"country": "India", "state": "Tamil Nadu", "district": "Coimbatore", "city": "Coimbatore"},
            "official_email": "office@rathinam.demo",
            "website": "https://www.rathinamcollege.edu.in/",
            "contact_number": "+91 422 000 0000",
            "address": "Coimbatore, Tamil Nadu, India",
            "registration_identifier": "DEMO-UNI-001",
            "approval_status": "APPROVED",
            "approved_at": now_utc(),
        }
    )
    cse = organizations_repo.create_department(university["_id"], "Computer Science and Engineering", "CSE")
    organizations_repo.create_department(university["_id"], "Information Technology", "IT")
    organizations_repo.create_department(university["_id"], "Electronics and Communication", "ECE")

    uni_admin = _demo_user(
        "Priya Raman",
        "rathinam.admin@eip.local",
        "UNIVERSITY_ADMIN",
        university["_id"],
        cse["_id"],
        designation="Placement Director",
        phone="+91 90000 00001",
    )

    company = organizations_repo.create_org(
        {
            "name": "Nova Systems",
            "organization_type": "COMPANY",
            "subtype": "Private Limited",
            "industry": "Software Development",
            "location": {"country": "India", "state": "Karnataka", "district": "Bengaluru Urban", "city": "Bengaluru"},
            "official_email": "people@novasystems.demo",
            "website": "https://www.novasystems.example",
            "contact_number": "+91 80 0000 0000",
            "address": "Bengaluru, Karnataka, India",
            "registration_identifier": "DEMO-ORG-001",
            "approval_status": "APPROVED",
            "approved_at": now_utc(),
        }
    )
    engineering = organizations_repo.create_department(company["_id"], "Engineering", "ENG")
    data_dept = organizations_repo.create_department(company["_id"], "Data", "DATA")

    _demo_user(
        "Daniel Mathew",
        "nova.admin@eip.local",
        "ORGANIZATION_ADMIN",
        company["_id"],
        engineering["_id"],
        designation="People Development Lead",
        phone="+91 90000 00002",
    )
    employee = _demo_user(
        "Meera Shah",
        "employee@eip.local",
        "EMPLOYEE",
        company["_id"],
        data_dept["_id"],
        designation="Software Engineer",
        phone="+91 90000 00003",
        is_expert=True,
    )
    student = _demo_user(
        "Aarav Kumar",
        "aarav@eip.local",
        "STUDENT",
        university["_id"],
        cse["_id"],
        phone="+91 90000 00004",
    )
    profiles_repo.create_profile(student["_id"], university["_id"], "STUDENT")

    profiles_repo.update_profile(
        student["_id"],
        {
            "education": {
                "degree": "B.E. Computer Science",
                "academic_year": "2023-2027",
                "year_of_study": "3",
                "roll_number": "21CSE001",
                "department_name": cse["name"],
            },
            "soft_skills": ["Communication"],
            "interests": ["Web development", "Product building"],
            "learning_style": "Hands-on projects",
            "weekly_hours": 8,
            "onboarding_complete": True,
        },
    )
    full_stack = catalog_repo.find_career_by_name("Full Stack Developer")
    profiles_repo.update_profile(student["_id"], {"target_career_id": full_stack["_id"] if full_stack else None})

    for name, level in [("Python", "ADVANCED"), ("SQL", "ADVANCED"), ("HTML", "BEGINNER"), ("Communication", "INTERMEDIATE")]:
        skill_service.add_self_skill(student["_id"], university["_id"], name, level)

    project_one = profiles_repo.add_project(
        {
            "user_id": student["_id"],
            "organization_id": university["_id"],
            "name": "Campus Event Finder",
            "description": "A Flask web application that helps students discover and register for campus events. It uses SQL for event storage and role-based access for organisers.",
            "technologies": ["Python", "Flask", "SQL"],
            "repo_url": "https://github.com/example/campus-event-finder",
            "skills": ["Python", "SQL"],
        }
    )
    profiles_repo.add_project(
        {
            "user_id": student["_id"],
            "organization_id": university["_id"],
            "name": "Personal Portfolio Website",
            "description": "A responsive personal portfolio built with semantic HTML and CSS, including accessible navigation and a contact section.",
            "technologies": ["HTML", "CSS"],
            "repo_url": "https://github.com/example/portfolio",
            "skills": ["HTML", "CSS"],
        }
    )
    profiles_repo.add_certification(
        {
            "user_id": student["_id"],
            "organization_id": university["_id"],
            "name": "Python for Data Science",
            "issuer": "Demo Certification Body",
            "issued_on": "2025-06-01",
            "skills": ["Python", "SQL"],
            "status": "PENDING_VERIFICATION",
        }
    )
    for skill in project_one["skills"]:
        skill_service.add_evidence(
            student["_id"], university["_id"], skill, "PROJECT", 55,
            title=project_one["name"], source_id=project_one["_id"], verified=False,
        )

    profiles_repo.create_profile(employee["_id"], company["_id"], "EMPLOYEE")
    profiles_repo.update_profile(
        employee["_id"],
        {
            "employment": {
                "designation": "Software Engineer",
                "employment_type": "Full-time",
                "years_experience": "2",
                "department_name": data_dept["name"],
            },
            "soft_skills": ["Communication"],
            "interests": ["Cloud", "Reliability"],
            "learning_style": "Short focused sessions",
            "weekly_hours": 5,
            "onboarding_complete": True,
            "target_career_id": (catalog_repo.find_career_by_name("Cloud Engineer") or {}).get("_id"),
        },
    )
    for name, level in [("Python", "INTERMEDIATE"), ("SQL", "INTERMEDIATE"), ("Cloud Fundamentals", "BEGINNER"), ("Communication", "INTERMEDIATE")]:
        skill_service.add_self_skill(employee["_id"], company["_id"], name, level)

    operations_repo.create_assignment(employee["_id"], student["_id"], university["_id"], uni_admin["_id"])

    if full_stack:
        learning_repo.record_activity(
            {
                "user_id": student["_id"],
                "organization_id": university["_id"],
                "activity_type": "NOTE",
                "status": "COMPLETED",
                "task_title": "Demo profile prepared",
                "skill_name": "Python",
                "self_reported": True,
            }
        )

    for account, message in [
        (student, "Welcome to EIP. Complete your baseline assessment to unlock your personalised plan."),
        (employee, "Welcome to EIP. Complete your baseline assessment to start your professional development plan."),
    ]:
        operations_repo.create_notification(
            account["_id"], account["organization_id"], "Welcome to EIP", message, "INFO", "/app/assessments"
        )


def ensure_seed(app) -> None:
    db = app.extensions["mongo_db"]
    _seed_catalog(db)

    demo_enabled = app.config.get("SEED_DEMO_ON_START", False)
    is_empty = users_repo.count() == 0
    if demo_enabled and is_empty:
        _seed_demo(app)
    else:
        ensure_super_admin(app)
