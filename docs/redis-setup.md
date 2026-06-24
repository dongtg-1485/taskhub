# Redis — Tích hợp và Vận hành trong TaskHub

Tài liệu này tổng hợp toàn bộ kiến thức về việc tích hợp Redis vào project TaskHub: từ lý do thiết kế, cấu hình từng file, đến cách dùng trong code.

---

## Mục lục

1. [Các file đã thay đổi / tạo mới](#1-các-file-đã-thay-đổi--tạo-mới)
2. [Dependency](#2-dependency)
3. [Cấu hình Settings](#3-cấu-hình-settings)
4. [Redis Client — `app/core/redis.py`](#4-redis-client--appcoreredis-py)
5. [Cache Key Management — `app/core/cache_keys.py`](#5-cache-key-management--appcorecache_keyspy)
6. [FastAPI Dependency — `RedisDep`](#6-fastapi-dependency--redisdep)
7. [App Lifespan — Dọn dẹp khi shutdown](#7-app-lifespan--dọn-dẹp-khi-shutdown)
8. [Docker Compose](#8-docker-compose)
9. [Biến môi trường `.env`](#9-biến-môi-trường-env)
10. [Cách dùng trong route](#10-cách-dùng-trong-route)
11. [Các câu hỏi thường gặp](#11-các-câu-hỏi-thường-gặp)

---

## 1. Các file đã thay đổi / tạo mới

| File | Thay đổi |
|------|----------|
| `backend/pyproject.toml` | Thêm `redis[hiredis]>=5.0.0` |
| `backend/app/core/config.py` | Thêm `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, computed `REDIS_URL` |
| `backend/app/core/redis.py` | **Tạo mới** — connection pool, `get_redis()`, `close_redis()` |
| `backend/app/core/cache_keys.py` | **Tạo mới** — quản lý cache key tập trung |
| `backend/app/api/deps.py` | Thêm `RedisDep` |
| `backend/app/main.py` | Thêm `lifespan` context manager để close pool khi shutdown |
| `.env` | Thêm block `# Redis` |
| `compose.yml` | Thêm service `redis`, volume `redis-data`, wire backend |
| `compose.override.yml` | Expose port `6379` cho local dev |

---

## 2. Dependency

```toml
# backend/pyproject.toml
"redis[hiredis]>=5.0.0"
```

- **`redis`**: thư viện client chính thức của Redis cho Python, có hỗ trợ async (`redis.asyncio`).
- **`[hiredis]`**: C extension tăng tốc parse response từ Redis ~10×. Được cài thêm tự động khi có dấu ngoặc vuông.

---

## 3. Cấu hình Settings

```python
# backend/app/core/config.py

REDIS_HOST: str = "localhost"
REDIS_PORT: int = 6379
REDIS_DB: int = 0
REDIS_PASSWORD: str | None = None

@computed_field
@property
def REDIS_URL(self) -> str:
    if self.REDIS_PASSWORD:
        return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
```

### Giải thích từng field

**`REDIS_HOST = "localhost"`**

Giá trị mặc định dùng khi chạy API trực tiếp trên máy (ngoài Docker). Khi chạy trong Docker Compose, biến này bị override thành `redis` (tên service), vì Docker DNS tự resolve tên service thành IP nội bộ container.

| Môi trường | `REDIS_HOST` | Redis nằm ở đâu |
|---|---|---|
| Local (ngoài Docker) | `localhost` | Cùng máy dev |
| Docker Compose | `redis` | Container riêng, cùng network |
| Production cloud | Endpoint của managed Redis | Server/cluster riêng biệt |

**`REDIS_PORT = 6379`**

Port mặc định của Redis — được IANA assign. Chỉ thay đổi nếu chạy nhiều Redis instance trên cùng server hoặc có policy bảo mật.

**`REDIS_DB = 0`**

Redis hỗ trợ nhiều **logical database** đánh số `0–15` trong cùng một instance. Chúng hoàn toàn tách biệt namespace. Dùng để phân tách môi trường trên cùng Redis server:

| DB | Dùng cho |
|---|---|
| `0` | Production / default |
| `1` | Staging |
| `2` | Testing (tránh pollute data thật) |

> Trên ElastiCache Cluster mode, multiple DB bị disable — khi đó dùng Redis instance riêng cho mỗi môi trường.

**`REDIS_URL` — `@computed_field` + `@property`**

- `@property` (Python built-in): biến method thành attribute, gọi `settings.REDIS_URL` thay vì `settings.REDIS_URL()`.
- `@computed_field` (Pydantic v2): báo Pydantic đây là field được tính toán, không đọc từ `.env`, nhưng vẫn xuất hiện trong `model_dump()`, JSON schema và được validate kiểu trả về.
- Nếu chỉ dùng `@property` thuần — Pydantic v2 bỏ qua, không đưa vào model schema.

**Lý do tách `REDIS_HOST/PORT/DB` thay vì một biến `REDIS_URL`:**
1. Dễ override từng phần trong Compose (`REDIS_HOST=redis`) mà không cần rewrite toàn bộ URL.
2. Password không bị ghép vào URL trong file `.env` plain-text.
3. Nhất quán với pattern `POSTGRES_SERVER`, `POSTGRES_PORT`, `POSTGRES_DB` đã có.
4. Dễ map 1:1 với CI/CD secrets.

---

## 4. Redis Client — `app/core/redis.py`

```python
import redis.asyncio as aioredis
from app.core.config import settings

redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    decode_responses=True,
)

def get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=redis_pool)

async def close_redis() -> None:
    await redis_pool.aclose()
```

### Connection pool

Tạo một pool dùng chung toàn ứng dụng thay vì tạo connection mới cho mỗi request.

**`max_connections=20`**: Giới hạn số connection đồng thời tới Redis.
- Quá thấp → request xếp hàng chờ → latency tăng.
- Quá cao → Redis quá tải, tốn RAM (~1 MB/connection).
- 20 là điểm khởi đầu an toàn cho ứng dụng vừa.

Khi scale lên nhiều worker, tính lại:

$$\text{max\_connections} = \left\lceil \frac{\text{Redis maxclients}}{\text{số worker process}} \right\rceil$$

Redis mặc định `maxclients = 10000`.

**`decode_responses=True`**: Tự decode bytes → str, không cần gọi `.decode()` thủ công sau mỗi lần `redis.get()`.

---

## 5. Cache Key Management — `app/core/cache_keys.py`

Quản lý tập trung tất cả cache key. **Không được khai báo key string trực tiếp trong router.**

### Quy ước đặt tên

| Pattern | Dùng cho |
|---|---|
| `{entity}:{id}` | Chi tiết một object |
| `{entity}:list:{scope}:{id}` | Danh sách thuộc một scope |
| `{entity}:members:{id}` | Danh sách thành viên |

### TTL constants

| Constant | Giá trị | Dùng cho |
|---|---|---|
| `TTL_SHORT` | 60s | Task list, comment (thay đổi thường xuyên) |
| `TTL_MEDIUM` | 300s | Project, label |
| `TTL_LONG` | 3600s | Workspace detail (ít thay đổi) |

### Danh sách hàm

```python
# Workspace
cache_keys.workspace_detail(workspace_id)     # "workspace:{id}"
cache_keys.workspace_list(user_id)            # "workspace:list:user:{id}"
cache_keys.workspace_members(workspace_id)    # "workspace:members:{id}"

# Project
cache_keys.project_detail(project_id)         # "project:{id}"
cache_keys.project_list(workspace_id)         # "project:list:workspace:{id}"

# Task
cache_keys.task_detail(task_id)               # "task:{id}"
cache_keys.task_list(project_id)              # "task:list:project:{id}"

# Label
cache_keys.label_list(project_id)             # "label:list:project:{id}"

# Comment
cache_keys.comment_list(task_id)              # "comment:list:task:{id}"
```

---

## 6. FastAPI Dependency — `RedisDep`

```python
# backend/app/api/deps.py
import redis.asyncio as aioredis
from app.core.redis import get_redis

RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]
```

Dùng trong route giống `AsyncSessionDep`:

```python
from app.api.deps import AsyncSessionDep, RedisDep

@router.get("/projects/{project_id}/tasks")
async def list_tasks(
    project_id: UUID,
    session: AsyncSessionDep,
    redis: RedisDep,
) -> list[TaskResponse]:
    ...
```

---

## 7. App Lifespan — Dọn dẹp khi shutdown

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from app.core.redis import close_redis

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await close_redis()

app = FastAPI(..., lifespan=lifespan)
```

`close_redis()` drain toàn bộ connection trong pool khi app shutdown — tránh connection leak.

---

## 8. Docker Compose

### Service `redis` trong `compose.yml`

```yaml
redis:
  image: redis:7-alpine
```
Redis 7.x trên Alpine Linux (~30 MB). Không dùng `redis:latest` để tránh upgrade ngoài ý muốn.

```yaml
  restart: always
```
Tự restart nếu crash hoặc Docker daemon restart.

```yaml
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    retries: 5
    start_period: 10s
    timeout: 5s
```
`redis-cli ping` → Redis trả `PONG` khi healthy. Backend có `depends_on: redis: condition: service_healthy` → Docker đợi Redis healthy trước khi start backend.

```yaml
  volumes:
    - redis-data:/data
```
Named volume để AOF file tồn tại qua container restart.

```yaml
  command: >
    redis-server
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
    --appendonly yes
```

| Option | Ý nghĩa |
|--------|---------|
| `--maxmemory 256mb` | Giới hạn RAM. Không set → Redis dùng hết RAM → OOM kill |
| `--maxmemory-policy allkeys-lru` | Khi đầy RAM: xóa key ít dùng nhất (LRU). Phù hợp cho cache thuần |
| `--appendonly yes` | Bật AOF — ghi mọi write operation ra file, phục hồi sau restart |

**So sánh eviction policy:**

| Policy | Hành vi |
|---|---|
| `noeviction` | Từ chối write khi đầy (default — không dùng cho cache) |
| `volatile-lru` | Chỉ xóa key có TTL theo LRU |
| `allkeys-lru` | Xóa bất kỳ key nào ít dùng nhất ✓ |
| `allkeys-random` | Xóa ngẫu nhiên |

### Backend `depends_on` Redis

```yaml
backend:
  depends_on:
    redis:
      condition: service_healthy
      restart: true
  environment:
    - REDIS_HOST=redis   # ← tên service, Docker DNS resolve thành IP nội bộ
    - REDIS_PORT=${REDIS_PORT}
    - REDIS_DB=${REDIS_DB}
    - REDIS_PASSWORD=${REDIS_PASSWORD}
```

### Override cho local dev (`compose.override.yml`)

`compose.yml` **không expose port 6379** ra ngoài — trong production Redis chỉ cần reachable bên trong Docker network. Expose ra internet là lỗ hổng bảo mật.

`compose.override.yml` được Docker Compose **tự động merge** khi chạy `docker compose up` ở local (không cần chỉ định `-f`):

```yaml
redis:
  restart: "no"   # không auto-restart khi dev
  ports:
    - "6379:6379" # expose để dùng redis-cli, RedisInsight khi debug
```

---

## 9. Biến môi trường `.env`

```env
# Redis
REDIS_HOST=localhost   # override thành "redis" bởi compose.yml khi chạy Docker
REDIS_PORT=6379
REDIS_DB=0
# REDIS_PASSWORD=      # bỏ comment khi Redis có auth
```

---

## 10. Cách dùng trong route

### Cache-aside pattern (lazy loading)

```
Request đến
    ↓
Kiểm tra key trong Redis
    ├── HIT  → trả về ngay từ cache
    └── MISS → query DB → lưu vào Redis → trả về
```

```python
import json
from uuid import UUID
from app.api.deps import AsyncSessionDep, RedisDep
from app.core import cache_keys
from app.repositories import tasks as task_repo
from app.schemas.task import TaskResponse

@router.get("/projects/{project_id}/tasks")
async def list_tasks(
    project_id: UUID,
    session: AsyncSessionDep,
    redis: RedisDep,
) -> list[TaskResponse]:
    key = cache_keys.task_list(project_id)

    # 1. Cache hit
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)

    # 2. Cache miss — query DB
    tasks = await task_repo.list_by_project(session, project_id)
    result = [t.model_dump() for t in tasks]

    # 3. Lưu vào cache
    await redis.set(key, json.dumps(result, default=str), ex=cache_keys.TTL_SHORT)
    return result
```

### Cache invalidation

Gọi khi tạo / sửa / xóa dữ liệu:

```python
@router.post("/projects/{project_id}/tasks", status_code=201)
async def create_task(
    project_id: UUID,
    body: CreateTaskRequest,
    session: AsyncSessionDep,
    redis: RedisDep,
) -> TaskResponse:
    task = await task_repo.create(session, ...)

    # Xóa cache danh sách để lần sau lấy dữ liệu mới
    await redis.delete(cache_keys.task_list(project_id))

    return task
```

---

## 11. Các câu hỏi thường gặp

**Q: Làm thế nào biết API đang dùng bao nhiêu worker?**

Kiểm tra process trong container:
```bash
docker exec <container> ps aux | grep uvicorn
docker compose logs backend | grep "workers"
```
`fastapi run` (Uvicorn đơn) mặc định **1 worker**. Multi-worker cần Gunicorn:
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```
Rule of thumb: `2 × CPU_cores + 1` worker. `--reload` (dev mode) không tương thích multi-worker.

---

**Q: Production dùng Redis như thế nào?**

| Quy mô | Mô hình | Config |
|---|---|---|
| Small (1 VPS) | Redis container cùng Compose | `REDIS_HOST=redis` |
| Medium (nhiều server) | Redis server riêng | `REDIS_HOST=10.0.1.50` (private IP) |
| Large / Cloud | Managed Redis (ElastiCache, Memorystore) | `REDIS_HOST=<endpoint từ provider>` |

Trên production: Redis **phải có password** (`REDIS_PASSWORD`), **không expose port ra internet**, và **nằm trên private network** cùng với API server.

---

**Q: `REDIS_HOST=redis` trong Docker hoạt động thế nào?**

Docker Compose tạo một bridge network nội bộ. Mỗi service name trở thành hostname DNS có thể resolve từ các container khác trong cùng network:

```
backend container → redis://redis:6379
Docker DNS        → redis = 172.18.0.X (IP nội bộ redis container)
```

Redis container không cần expose port ra host machine — giao tiếp diễn ra hoàn toàn trong network nội bộ.
