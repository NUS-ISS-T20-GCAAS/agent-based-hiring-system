```text
/Users/isaactan/Projects/agent-based-hiring-system
├── Makefile
├── README.md
├── SYSTEM_WORKFLOW.md
├── TREE.md
├── db
│   ├── init_db.sql
│   ├── migrate.sh
│   └── migrations
│       ├── 001_extensions.sql
│       ├── 002_jobs_candidates.sql
│       ├── 003_workflow_artifacts.sql
│       ├── 004_indexes.sql
│       ├── 005_job_requirements.sql
│       └── 006_candidate_review_state.sql
├── frontend
│   ├── Dockerfile
│   ├── index.html
│   ├── nginx.conf
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.js
│   ├── src
│   │   ├── App.css
│   │   ├── App.jsx
│   │   ├── components
│   │   ├── index.css
│   │   ├── main.jsx
│   │   ├── services
│   │   └── utils
│   ├── tailwind.config.js
│   └── vite.config.js
├── infra
│   ├── .env.example
│   ├── docker-compose.yml
│   └── terraform
│       ├── README.md
│       ├── ecr.tf
│       ├── eks-fargate.tf
│       ├── eks.tf
│       ├── iam.tf
│       ├── k8s
│       │   └── secrets.yaml.example
│       ├── outputs.tf
│       ├── rds.tf
│       ├── terraform.tfvars.example
│       ├── variables.tf
│       ├── versions.tf
│       └── vpc.tf
└── services
    ├── NEXT_STEPS.md
    ├── PROGRESS.md
    ├── README.md
    ├── audit-agent
    │   ├── Dockerfile
    │   ├── app
    │   ├── requirements.txt
    │   └── tests
    ├── coordinator-agent
    │   ├── Dockerfile
    │   ├── app
    │   ├── requirements.txt
    │   └── tests
    ├── docker-compose.yml
    ├── ranking-agent
    │   ├── Dockerfile
    │   ├── app
    │   ├── requirements.txt
    │   └── tests
    ├── resume-intake-agent
    │   ├── Dockerfile
    │   ├── app
    │   ├── requirements.txt
    │   └── tests
    └── screening-agent
        ├── Dockerfile
        ├── app
        ├── requirements.txt
        └── tests
```
