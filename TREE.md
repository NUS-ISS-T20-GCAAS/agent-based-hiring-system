```
.
├── Makefile
├── README.md
├── TREE.md
├── db
│   └── init_db.sql
├── frontend
│   ├── index.html
│   ├── src
│   │   ├── components
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Candidates.jsx
│   │   │   ├── AgentActivity.jsx
│   │   │   ├── CandidateDetailModal.jsx
│   │   │   └── StatsCard.jsx
│   │   ├── services
│   │   │   └── api.js
│   │   ├── utils
│   │   │   └── helpers.js
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── main.jsx
│   │   └── index.css
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package-lock.json
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
├── infra
│   ├── db
│   │   └── init_db.sql
│   ├── docker-compose.yml
│   └── k8s
└── services
    ├── README.md
    ├── coordinator-agent
    │   ├── Dockerfile
    │   ├── app
    │   │   ├── agents.py
    │   │   ├── base_agent.py
    │   │   ├── bootstrap.py
    │   │   ├── config.py
    │   │   ├── coordinator.py
    │   │   ├── events.py
    │   │   ├── logger.py
    │   │   ├── main.py
    │   │   ├── routes.py
    │   │   ├── schemas.py
    │   │   ├── shared_memory.py
    │   │   └── state.py
    │   └── requirements.txt
    ├── docker-compose.yml
    └── resume-intake-agent
        ├── Dockerfile
        ├── app
        │   ├── agent.py
        │   ├── health.py
        │   ├── main.py
        │   ├── schemas.py
        │   └── worker.py
        └── requirements.txt


14 directories, 48 files

```
