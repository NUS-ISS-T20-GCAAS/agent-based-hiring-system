```
.
├── Makefile
├── README.md
├── TREE.md
├── db
│   └── init_db.sql
├── frontend
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package-lock.json
│   └── package.json
├── infra
│   ├── db
│   │   └── init_db.sql
│   ├── docker-compose.yml
│   └── k8s
└── services
    ├── README.md
    ├── coordinator-agent
    │   ├── Dockerfile
    │   ├── app
    │   │   ├── agents.py
    │   │   ├── base_agent.py
    │   │   ├── bootstrap.py
    │   │   ├── config.py
    │   │   ├── coordinator.py
    │   │   ├── events.py
    │   │   ├── logger.py
    │   │   ├── main.py
    │   │   ├── routes.py
    │   │   ├── schemas.py
    │   │   ├── shared_memory.py
    │   │   └── state.py
    │   └── requirements.txt
    ├── docker-compose.yml
    └── resume-intake-agent
        ├── Dockerfile
        ├── app
        │   ├── agent.py
        │   ├── health.py
        │   ├── main.py
        │   ├── schemas.py
        │   └── worker.py
        └── requirements.txt

12 directories, 32 files

```
