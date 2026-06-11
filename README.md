# Task Hub

Project with FastAPI

## Installation
From the repo root:
```bash
cd /Users/trinh.giang.dong/SunAsterisk/taskhub
docker compose watch
```

Then open:
* Frontend: http://localhost:5173
* Backend API: http://localhost:8000
* Swagger docs: http://localhost:8000/docs
* Adminer: http://localhost:8080
* Mailcatcher: http://localhost:1080
* Traefik dashboard: http://localhost:8090

Useful checks:
```bash
docker compose logs
docker compose logs backend
docker compose ps
```

Stop everything:
```bash
docker compose down
```

If you want volumes removed too:
```bash
docker compose down -v
```