# Redis Tutorial: Cài đặt và Sử dụng với FastAPI & Docker

Tài liệu này hướng dẫn tích hợp Redis vào project TaskHub — từ khái niệm cơ bản đến triển khai caching thực tế với FastAPI và Docker Compose.

---

## Mục lục

1. [Redis là gì?](#1-redis-là-gì)
2. [Các kiểu dữ liệu cơ bản](#2-các-kiểu-dữ-liệu-cơ-bản)
3. [Thêm Redis vào Docker Compose](#3-thêm-redis-vào-docker-compose)
4. [Kết nối Redis từ FastAPI](#4-kết-nối-redis-từ-fastapi)
5. [Caching pattern với FastAPI](#5-caching-pattern-với-fastapi)
6. [Cache Invalidation](#6-cache-invalidation)
7. [Áp dụng vào TaskHub: Cache danh sách Task](#7-áp-dụng-vào-taskhub-cache-danh-sách-task)
8. [Các lưu ý quan trọng](#8-các-lưu-ý-quan-trọng)
9. [Redis trên môi trường thực tế (Production)](#9-redis-trên-môi-trường-thực-tế-production)

---

## 1. Redis là gì?

**Redis** (Remote Dictionary Server) là một **in-memory data store** — lưu dữ liệu trực tiếp trên RAM thay vì đĩa cứng, nên tốc độ đọc/ghi cực kỳ nhanh (sub-millisecond).

### Các use case phổ biến

| Use case | Mô tả |
|----------|-------|
| **Caching** | Lưu kết quả query DB tốn kém, trả về ngay từ RAM |
| **Session store** | Lưu session người dùng (stateless JWT thay thế một phần) |
| **Rate limiting** | Đếm số request theo IP / user trong sliding window |
| **Pub/Sub** | Message broker đơn giản giữa các service |
| **Job queue** | Hàng đợi background task (kết hợp Celery hoặc ARQ) |
| **Leaderboard** | Sorted Set để xếp hạng realtime |

### Tại sao dùng Redis thay vì cache trong bộ nhớ ứng dụng?

- **Chia sẻ giữa nhiều worker**: Khi chạy nhiều process FastAPI (Gunicorn, K8s replicas), cache trong RAM mỗi process là riêng biệt → miss liên tục.
- **TTL tự động**: Redis tự xóa key hết hạn, không cần cron job.
- **Persistence tuỳ chọn**: RDB snapshot hoặc AOF log để phục hồi sau restart.

---

## 2. Các kiểu dữ liệu cơ bản

Redis không chỉ là key-value đơn thuần — mỗi value có thể là một trong các kiểu sau:

### String
```bash
SET user:1:name "Alice"
GET user:1:name          # "Alice"
SETEX session:abc 3600 "user_id=42"  # TTL 3600 giây
TTL session:abc          # còn bao nhiêu giây
DEL user:1:name
```

### Hash (như dict/object)
```bash
HSET task:42 title "Fix bug" status "TODO" priority "HIGH"
HGET task:42 title        # "Fix bug"
HGETALL task:42           # toàn bộ fields
HDEL task:42 priority
```

### List (queue / stack)
```bash
LPUSH notifications:user:1 "New comment on task #5"
RPOP notifications:user:1  # lấy từ đuôi (FIFO)
LRANGE notifications:user:1 0 -1  # toàn bộ
```

### Set (tập hợp không trùng)
```bash
SADD project:1:members 10 20 30
SISMEMBER project:1:members 20   # 1 (tồn tại)
SMEMBERS project:1:members        # {10, 20, 30}
```

### Sorted Set (có điểm số, tự sắp xếp)
```bash
ZADD leaderboard 100 "alice" 85 "bob" 120 "carol"
ZRANGE leaderboard 0 -1 WITHSCORES  # từ thấp đến cao
ZREVRANK leaderboard "alice"         # thứ hạng từ cao xuống
```

---

## 3. Thêm Redis vào Docker Compose

Mở `compose.yml` ở root project, thêm service `redis`:

```yaml
services:
  # ... các service hiện có (db, adminer, prestart, backend) ...

  redis:
    image: redis:7-alpine
    restart: always
    ports:
      - "6379:6379"          # expose ra localhost để debug với redis-cli
    volumes:
      - redis-data:/data
    command: >
      redis-server
      --maxmemory 256mb
      --maxmemory-policy allkeys-lru
      --appendonly yes

volumes:
  app-db-data:
  redis-data:               # thêm volume mới
```

**Giải thích các option:**

| Option | Ý nghĩa |
|--------|---------|
| `redis:7-alpine` | Image nhỏ gọn (~30MB), Redis 7.x |
| `maxmemory 256mb` | Giới hạn RAM, tránh OOM kill |
| `maxmemory-policy allkeys-lru` | Khi đầy RAM: xóa key ít dùng nhất (LRU) |
| `appendonly yes` | Bật AOF — phục hồi dữ liệu sau restart container |

Thêm `REDIS_URL` vào file `.env`:
```env
REDIS_URL=redis://redis:6379/0
```

> **Lưu ý:** Trong Docker network, backend kết nối Redis qua hostname `redis` (tên service), không phải `localhost`.

---

## 4. Kết nối Redis từ FastAPI

### Cài thư viện

```bash
# Thêm vào backend/requirements.txt hoặc pyproject.toml
redis[hiredis]>=5.0.0
```

`hiredis` là C extension giúp parse response nhanh hơn ~10×.

### Tạo Redis client (connection pool)

Tạo file `backend/app/core/redis.py`:

```python
import redis.asyncio as aioredis
from app.core.config import settings

# Connection pool — dùng chung toàn bộ ứng dụng
redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    decode_responses=True,  # tự decode bytes → str
)


def get_redis() -> aioredis.Redis:
    """Trả về Redis client từ pool (không cần async context manager)."""
    return aioredis.Redis(connection_pool=redis_pool)
```

Thêm `REDIS_URL` vào `backend/app/core/config.py`:

```python
class Settings(BaseSettings):
    # ... các field hiện có ...
    REDIS_URL: str = "redis://localhost:6379/0"
```

### Dependency injection cho FastAPI

```python
# backend/app/api/deps.py
from typing import Annotated
import redis.asyncio as aioredis
from fastapi import Depends
from app.core.redis import get_redis

RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]
```

### Dùng trong route

```python
from app.api.deps import RedisDep

@router.get("/ping-redis")
async def ping_redis(redis: RedisDep) -> dict:
    await redis.set("hello", "world", ex=60)
    value = await redis.get("hello")
    return {"value": value}
```

---

## 5. Caching Pattern với FastAPI

Pattern chuẩn cho **cache-aside** (lazy loading):

```
Request đến
    ↓
Kiểm tra key trong Redis
    ├── HIT  → trả về ngay từ cache
    └── MISS → query DB → lưu vào Redis → trả về
```

### Ví dụ cơ bản

```python
import json
from fastapi import APIRouter
from app.api.deps import AsyncSessionDep, RedisDep

router = APIRouter()

CACHE_TTL = 300  # 5 phút

@router.get("/projects/{project_id}/tasks")
async def list_tasks(
    project_id: int,
    session: AsyncSessionDep,
    redis: RedisDep,
) -> list[dict]:
    cache_key = f"tasks:project:{project_id}"

    # 1. Thử lấy từ cache
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # 2. Cache miss — query DB
    tasks = await task_repo.list_by_project(session, project_id)
    result = [t.model_dump() for t in tasks]

    # 3. Lưu vào cache
    await redis.set(cache_key, json.dumps(result, default=str), ex=CACHE_TTL)

    return result
```

### Tách logic thành helper để tái sử dụng

```python
# backend/app/services/cache.py
import json
from typing import Any, Callable, Awaitable
import redis.asyncio as aioredis


async def get_or_set(
    redis: aioredis.Redis,
    key: str,
    ttl: int,
    fetch: Callable[[], Awaitable[Any]],
) -> Any:
    """
    Cache-aside helper.
    Nếu key tồn tại → trả về giá trị đã cache.
    Nếu không → gọi fetch(), cache kết quả, rồi trả về.
    """
    cached = await redis.get(key)
    if cached is not None:
        return json.loads(cached)

    data = await fetch()
    await redis.set(key, json.dumps(data, default=str), ex=ttl)
    return data
```

Dùng trong route:

```python
from app.services.cache import get_or_set

@router.get("/projects/{project_id}/tasks")
async def list_tasks(
    project_id: int,
    session: AsyncSessionDep,
    redis: RedisDep,
) -> list[dict]:
    async def fetch():
        tasks = await task_repo.list_by_project(session, project_id)
        return [t.model_dump() for t in tasks]

    return await get_or_set(
        redis,
        key=f"tasks:project:{project_id}",
        ttl=300,
        fetch=fetch,
    )
```

---

## 6. Cache Invalidation

Dữ liệu cache sẽ stale nếu không xóa đúng lúc. Có hai chiến lược:

### A. TTL đơn giản (eventual consistency)

Cache tự hết hạn sau `TTL` giây. Phù hợp khi dữ liệu không yêu cầu real-time:

```python
await redis.set(key, value, ex=300)  # tự xóa sau 5 phút
```

### B. Explicit invalidation (strong consistency)

Xóa cache ngay khi có thay đổi dữ liệu — phù hợp với TaskHub vì task thay đổi thường xuyên:

```python
@router.post("/projects/{project_id}/tasks")
async def create_task(
    project_id: int,
    data: TaskCreate,
    session: AsyncSessionDep,
    redis: RedisDep,
) -> Task:
    task = await task_repo.create(session, data)

    # Xóa cache của project này
    await redis.delete(f"tasks:project:{project_id}")

    return task


@router.patch("/tasks/{task_id}")
async def update_task(
    task_id: int,
    data: TaskUpdate,
    session: AsyncSessionDep,
    redis: RedisDep,
) -> Task:
    task = await task_repo.update(session, task_id, data)

    # Xóa cache
    await redis.delete(f"tasks:project:{task.project_id}")

    return task
```

### C. Pattern-based invalidation (dùng SCAN)

Khi cache key có nhiều biến thể (pagination, filter), dùng `SCAN` để xóa theo pattern:

```python
async def invalidate_pattern(redis: aioredis.Redis, pattern: str) -> int:
    """Xóa tất cả key khớp pattern. Dùng SCAN thay KEYS để không block Redis."""
    count = 0
    async for key in redis.scan_iter(match=pattern, count=100):
        await redis.delete(key)
        count += 1
    return count

# Xóa tất cả cache liên quan đến project 5
await invalidate_pattern(redis, "tasks:project:5:*")
```

> **Tránh dùng `KEYS *`** trong production — nó block Redis cho đến khi quét xong toàn bộ keyspace. Dùng `SCAN` thay thế.

---

## 7. Áp dụng vào TaskHub: Cache danh sách Task

Theo yêu cầu `docs/requirement.md`, TaskHub cần cache `GET /projects/{id}/tasks` với Redis và invalidate khi có thay đổi.

### Cấu trúc key đề xuất

```
tasks:project:{project_id}                    # danh sách không filter
tasks:project:{project_id}:status:{status}   # filter theo status
tasks:project:{project_id}:page:{page}       # có pagination
```

### Ví dụ hoàn chỉnh với filter và pagination

```python
# backend/app/api/routes/tasks.py
import hashlib
import json
from fastapi import APIRouter, Query
from app.api.deps import AsyncSessionDep, RedisDep
from app.repositories import tasks as task_repo
from app.schemas.task import TaskRead, TaskListParams

router = APIRouter()
CACHE_TTL = 300


def make_cache_key(project_id: int, params: TaskListParams) -> str:
    """Tạo cache key duy nhất từ project_id + tham số filter/pagination."""
    param_str = json.dumps(params.model_dump(), sort_keys=True)
    param_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
    return f"tasks:project:{project_id}:{param_hash}"


@router.get("/projects/{project_id}/tasks", response_model=list[TaskRead])
async def list_tasks(
    project_id: int,
    session: AsyncSessionDep,
    redis: RedisDep,
    status: str | None = Query(None),
    priority: str | None = Query(None),
    assignee_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> list[TaskRead]:
    params = TaskListParams(
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        page=page,
        limit=limit,
    )
    cache_key = make_cache_key(project_id, params)

    # Cache hit
    cached = await redis.get(cache_key)
    if cached:
        return [TaskRead.model_validate(t) for t in json.loads(cached)]

    # Cache miss
    tasks = await task_repo.list_by_project(session, project_id, params)
    result = [t.model_dump() for t in tasks]

    await redis.set(cache_key, json.dumps(result, default=str), ex=CACHE_TTL)
    return tasks


@router.post("/projects/{project_id}/tasks", response_model=TaskRead)
async def create_task(
    project_id: int,
    data: TaskCreate,
    session: AsyncSessionDep,
    redis: RedisDep,
) -> TaskRead:
    task = await task_repo.create(session, project_id, data)

    # Invalidate toàn bộ cache của project này
    await invalidate_project_task_cache(redis, project_id)

    return task


async def invalidate_project_task_cache(redis: aioredis.Redis, project_id: int) -> None:
    """Xóa tất cả cache variant của project."""
    async for key in redis.scan_iter(match=f"tasks:project:{project_id}:*"):
        await redis.delete(key)
    # Xóa cả key không có suffix
    await redis.delete(f"tasks:project:{project_id}")
```

---

## 8. Các lưu ý quan trọng

### Serialization

Redis chỉ lưu string/bytes. Cần serialize/deserialize khi làm việc với object phức tạp:

```python
# ĐÚNG: dùng json.dumps với default=str để handle datetime
await redis.set(key, json.dumps(data, default=str), ex=ttl)
data = json.loads(await redis.get(key))

# SAI: không thể set trực tiếp dict hoặc Pydantic model
await redis.set(key, my_dict)         # TypeError
await redis.set(key, my_model)        # TypeError
```

### Connection pool

Không tạo mới connection mỗi request — dùng pool dùng chung:

```python
# ĐÚNG: tạo pool một lần, inject vào mọi route
redis_pool = aioredis.ConnectionPool.from_url(...)

# SAI: tạo client mới mỗi request — tốn tài nguyên
async def get_redis():
    return aioredis.from_url(settings.REDIS_URL)  # tạo connection mới
```

### Graceful degradation

Cache chỉ là tầng tối ưu — không được để Redis down làm hỏng toàn bộ API:

```python
@router.get("/projects/{project_id}/tasks")
async def list_tasks(
    project_id: int,
    session: AsyncSessionDep,
    redis: RedisDep,
) -> list[TaskRead]:
    try:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        # Redis không khả dụng → bỏ qua cache, query DB bình thường
        pass

    tasks = await task_repo.list_by_project(session, project_id)

    try:
        await redis.set(cache_key, json.dumps(...), ex=CACHE_TTL)
    except Exception:
        pass  # Lỗi khi set cache không ảnh hưởng response

    return tasks
```

### Thiết kế key

Dùng dấu `:` làm separator, prefix theo domain để dễ quản lý:

```
# Pattern gợi ý
{domain}:{entity}:{id}:{variant}

tasks:project:42:page:1
user:profile:10
workspace:members:5
```

### Debug với redis-cli

```bash
# Kết nối vào container Redis
docker compose exec redis redis-cli

# Các lệnh debug thường dùng
KEYS tasks:*                  # Liệt kê key (chỉ dùng khi dev)
TTL tasks:project:42          # Còn bao lâu hết hạn
GET tasks:project:42          # Xem giá trị
MONITOR                       # Stream real-time mọi command (debug)
INFO stats                    # Hit/miss ratio, memory, connections
```

Kiểm tra hit rate:
```bash
INFO stats | grep keyspace_hits
INFO stats | grep keyspace_misses
```

---

## 9. Redis trên môi trường thực tế (Production)

Redis nằm ở **tầng giữa** (middle tier) — giữa application server và database:

```
Client (Browser / Mobile)
        ↓
  Load Balancer (Nginx / ALB)
        ↓
  ┌─────────────────────────┐
  │   Application Servers   │  ← FastAPI workers (nhiều instance)
  │  (Pod 1 | Pod 2 | Pod 3)│
  └─────────────────────────┘
        ↓           ↓
    Redis           PostgreSQL
  (Cache /        (Source of
  Session)          Truth)
```

### Mô hình 1: Cùng server — nhỏ / cá nhân

```
┌─────────────────────────┐
│       1 VPS / EC2       │
│                         │
│  FastAPI (port 8000)    │
│  PostgreSQL (port 5432) │
│  Redis (port 6379)      │
│                         │
└─────────────────────────┘
```

- **Ưu:** rẻ nhất, đơn giản, latency ~0 (cùng máy)
- **Nhược:** Redis và App tranh nhau RAM/CPU; 1 server chết → tất cả chết
- **Khi nào dùng:** side project, MVP, traffic < vài nghìn req/ngày

### Mô hình 2: Server riêng — production thực tế

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  App Server(s)   │     │  Redis Server    │     │  DB Server       │
│                  │────▶│                  │     │                  │
│  FastAPI         │     │  Redis :6379     │     │  PostgreSQL      │
│  (EC2 t3.medium) │     │  (EC2 t3.small)  │     │  (RDS)           │
└──────────────────┘     └──────────────────┘     └──────────────────┘
        tất cả nằm trong cùng 1 VPC / private network
```

- **Ưu:** App scale độc lập, Redis không bị ảnh hưởng khi deploy app
- **Nhược:** thêm chi phí 1 server, cần config network / security group
- **Khi nào dùng:** production thật, team có vài người

### Mô hình 3: Managed Redis — phổ biến nhất hiện nay

```
┌──────────────────┐     ┌───────────────────────────┐
│  App Server(s)   │     │  Managed Redis             │
│                  │────▶│                            │
│  FastAPI trên    │     │  AWS ElastiCache            │
│  EC2 / ECS /     │     │  hoặc Upstash               │
│  Railway / Fly   │     │  (bạn không cần biết        │
│                  │     │   nó chạy máy vật lý nào)  │
└──────────────────┘     └───────────────────────────┘
```

Bạn chỉ nhận được 1 URL kiểu `redis://xxx.cache.amazonaws.com:6379` — nhà cung cấp tự lo server vật lý, failover, backup.

- **Ưu:** không cần ops, HA sẵn, bảo mật tốt
- **Nhược:** đắt hơn tự host, vendor lock-in
- **Khi nào dùng:** hầu hết production hiện đại

| Platform deploy app | Redis đặt ở đâu |
|---------------------|-----------------|
| **Railway** | Thêm Redis plugin → cùng project, khác container |
| **Render** | Thêm Redis service → cùng region |
| **Fly.io** | Upstash Redis addon hoặc deploy Redis app riêng |
| **AWS EC2/ECS** | ElastiCache (khuyên dùng) hoặc EC2 riêng |
| **VPS (DigitalOcean, Vultr)** | Cùng VPS (nhỏ) hoặc droplet riêng (lớn hơn) |

### Các mô hình HA (High Availability) theo scale

#### Redis Sentinel — tránh downtime

```
          App Server
         ↙    ↓    ↘
  Sentinel  Sentinel  Sentinel   ← giám sát, bầu leader
       ↓
  Master → Replica → Replica    ← Replica dùng để read scaling
```

Sentinel tự **failover** khi Master chết — promote Replica lên làm Master mới. Phù hợp production vừa.

#### Redis Cluster — large scale

```
App Server
   ↓
Cluster Proxy
   ↙         ↓         ↘
Shard 1    Shard 2    Shard 3   ← mỗi shard = 1 master + N replica
(slot 0–5460) (5461–10922) (10923–16383)
```

Dữ liệu được **sharding** tự động theo 16384 hash slot. Dùng khi single node không đủ RAM hoặc write throughput quá cao.

### Bảo mật: Redis không bao giờ expose ra internet

```
Internet
   ↓
[Load Balancer]  ← public subnet
   ↓
[App Servers]    ← private subnet
   ↓
[Redis]          ← private subnet, KHÔNG có public IP
[PostgreSQL]     ← private subnet, KHÔNG có public IP
```

> Port `6379` chỉ mở trong Docker Compose local để debug. Trên production, Redis chỉ nhận kết nối từ các service trong cùng VPC / security group.

### Tóm tắt chọn mô hình

| Scale | Mô hình |
|-------|---------|
| Dev / Staging | Single node trong Docker Compose |
| Production nhỏ / MVP | Single node hoặc Sentinel trên VPS / EC2 |
| Production vừa | Managed Redis (ElastiCache, Memorystore, Railway) |
| Production lớn | Redis Cluster hoặc Managed Cluster mode |

Với TaskHub ở giai đoạn hiện tại: **Managed Redis (Upstash hoặc Railway Redis)** là lựa chọn thực tế nhất — không tốn công vận hành, có HA sẵn, tích hợp qua 1 biến môi trường `REDIS_URL`.

---

## Tóm tắt checklist tích hợp

- [ ] Thêm `redis:7-alpine` service vào `compose.yml`
- [ ] Thêm `REDIS_URL` vào `.env`
- [ ] Cài `redis[hiredis]` vào `requirements.txt`
- [ ] Tạo `app/core/redis.py` với connection pool
- [ ] Thêm `REDIS_URL` vào `Settings` trong `config.py`
- [ ] Tạo `RedisDep` trong `app/api/deps.py`
- [ ] Implement cache-aside trong `GET /projects/{id}/tasks`
- [ ] Invalidate cache trong `POST`, `PATCH`, `DELETE` tasks
- [ ] Thêm graceful degradation (try/except) cho mọi Redis call
- [ ] Kiểm tra hit rate bằng `redis-cli INFO stats`
