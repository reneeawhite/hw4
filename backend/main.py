"""FastAPI app for the Campus Customs storefront and shopping assistant."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import secrets
import sqlite3
from collections import deque
from functools import lru_cache
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageChops, ImageFilter, ImageOps
from pydantic import BaseModel, Field, model_validator

if __package__:
    from .agent import AgentConfigurationError, run_chat
    from .models import (
        ChatHistoryResponse,
        ChatRequest,
        ChatResponse,
        ChatTurn,
        CustomerContext,
        Product,
        StoredChatTurn,
    )
    from .tools import read_products
else:  # Supports `uvicorn main:app` when launched from backend/.
    from agent import AgentConfigurationError, run_chat
    from models import (
        ChatHistoryResponse,
        ChatRequest,
        ChatResponse,
        ChatTurn,
        CustomerContext,
        Product,
        StoredChatTurn,
    )
    from tools import read_products


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "campus_customs.db"
RECENT_CHAT_MESSAGE_LIMIT = 8
logger = logging.getLogger(__name__)

app = FastAPI(title="Campus Customs API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    first_name: str | None = None
    last_name: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


SESSIONS: dict[str, UserResponse] = {}


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))


def hash_password(password: str) -> str:
    """Hash a password with scrypt and a fresh random salt."""
    salt = secrets.token_bytes(16)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=64,
    )
    return "scrypt$16384$8$1$" + _encode(salt) + "$" + _encode(derived_key)


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify only the supported scrypt format; never compare plaintext passwords."""
    try:
        algorithm, n_value, r_value, p_value, salt_value, key_value = stored_hash.split("$")
        if algorithm != "scrypt":
            return False
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_decode(salt_value),
            n=int(n_value),
            r=int(r_value),
            p=int(p_value),
            dklen=len(_decode(key_value)),
        )
        return hmac.compare_digest(candidate, _decode(key_value))
    except (ValueError, TypeError):
        return False


def _user_response(row: sqlite3.Row) -> UserResponse:
    return UserResponse(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        first_name=row["first_name"],
        last_name=row["last_name"],
    )


def _start_session(user: UserResponse) -> AuthResponse:
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = user
    return AuthResponse(access_token=token, user=user)


def _authenticated_user(authorization: str | None) -> UserResponse | None:
    """Resolve the in-memory bearer token without exposing it to the agent."""
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.casefold() != "bearer" or not token or token not in SESSIONS:
        raise HTTPException(status_code=401, detail="Your session has expired; please log in again")
    return SESSIONS[token]


def _customer_context(user: UserResponse) -> CustomerContext:
    return CustomerContext(user_id=user.id, name=user.name, email=user.email)


def _product_ids_json(products: list[Product]) -> str | None:
    if not products:
        return None
    return json.dumps([product.product_id for product in products])


def _save_chat_turns(user: UserResponse, request: ChatRequest, response: ChatResponse) -> None:
    """Persist the new authenticated turn so later requests can load context from SQLite."""
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        connection.executemany(
            """
            INSERT INTO chat_messages (user_id, role, content, products_json)
            VALUES (?, ?, ?, ?)
            """,
            [
                (user.id, "user", request.message, None),
                (user.id, "assistant", response.reply, _product_ids_json(response.products)),
            ],
        )
        connection.commit()
    finally:
        connection.close()


def _product_ids_from_json(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return [item for item in parsed if isinstance(item, str)][:8] if isinstance(parsed, list) else []


def _load_recent_chat_context(
    user_id: int,
    limit: int = RECENT_CHAT_MESSAGE_LIMIT,
) -> list[ChatTurn]:
    """Load only the latest saved messages for agent context, oldest first."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT role, content, products_json
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    finally:
        connection.close()

    return [
        ChatTurn(
            role=row["role"],
            content=row["content"],
            product_ids=_product_ids_from_json(row["products_json"]),
        )
        for row in reversed(rows)
    ]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "campus-customs-api"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    authorization: str | None = Header(default=None),
) -> ChatResponse:
    """Send a shopper message to the PydanticAI agent and return DB-backed cards."""
    try:
        user = _authenticated_user(authorization)
    except HTTPException as error:
        if error.status_code != 401:
            raise
        # Chat is available to guests. A stale browser token must not block it.
        logger.info("Chat request has an invalid session; continuing as a guest")
        user = None
    try:
        history = (
            _load_recent_chat_context(user.id)
            if user
            else request.history[-8:]
        )
        response = await run_chat(
            request.message,
            history,
            DATABASE_PATH,
            customer=_customer_context(user) if user else None,
            page_context=request.page_context,
        )
        if user:
            _save_chat_turns(user, request, response)
        return response
    except AgentConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except asyncio.CancelledError:
        raise
    except Exception as error:
        logger.exception("Campus Customs chat request failed")
        raise HTTPException(
            status_code=502,
            detail="The shopping assistant is temporarily unavailable. Please try again.",
        ) from error


@app.get("/api/chat/history", response_model=ChatHistoryResponse)
def chat_history(authorization: str | None = Header(default=None)) -> ChatHistoryResponse:
    """Return the signed-in customer's saved turns, including saved product cards."""
    user = _authenticated_user(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="Log in to load saved chat history")

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT role, content, products_json
            FROM chat_messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user.id, RECENT_CHAT_MESSAGE_LIMIT),
        ).fetchall()
    finally:
        connection.close()

    messages: list[StoredChatTurn] = []
    for row in reversed(rows):
        product_ids = _product_ids_from_json(row["products_json"])
        products = [
            product
            for product_id in product_ids
            for product in read_products(DATABASE_PATH, DATA_DIR, product_id)
        ]
        messages.append(
            StoredChatTurn(
                role=row["role"],
                content=row["content"],
                product_ids=product_ids,
                products=products,
            )
        )
    return ChatHistoryResponse(messages=messages)


@app.post("/api/auth/register", response_model=AuthResponse, status_code=201)
def register(request: RegisterRequest) -> AuthResponse:
    first_name = request.first_name.strip()
    last_name = request.last_name.strip()
    email = request.email.strip().lower()
    if not first_name or not last_name or "@" not in email:
        raise HTTPException(status_code=400, detail="Enter a valid first name, last name, and email")

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        if connection.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise HTTPException(status_code=409, detail="An account with that email already exists")
        cursor = connection.execute(
            """
            INSERT INTO users (name, email, password_hash, first_name, last_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (f"{first_name} {last_name}", email, hash_password(request.password), first_name, last_name),
        )
        connection.commit()
        row = connection.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return _start_session(_user_response(row))
    except sqlite3.IntegrityError as error:
        connection.rollback()
        raise HTTPException(status_code=409, detail="An account with that email already exists") from error
    finally:
        connection.close()


@app.post("/api/auth/login", response_model=AuthResponse)
def login(request: LoginRequest) -> AuthResponse:
    email = request.email.strip().lower()
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        row = connection.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        connection.close()
    if row is None or not verify_password(request.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return _start_session(_user_response(row))


@app.get("/api/products", response_model=list[Product])
def products() -> list[Product]:
    return read_products(DATABASE_PATH, DATA_DIR)


@app.get("/api/products/{product_id}", response_model=Product)
def product(product_id: str) -> Product:
    matches = read_products(DATABASE_PATH, DATA_DIR, product_id)
    if not matches:
        raise HTTPException(status_code=404, detail="Product not found")
    return matches[0]


def _candidate_background_mask(image: Image.Image, *, light: bool) -> Image.Image:
    red, green, blue, alpha = image.split()
    darkest = ImageChops.darker(red, ImageChops.darker(green, blue))
    brightest = ImageChops.lighter(red, ImageChops.lighter(green, blue))
    color_spread = ImageChops.subtract(brightest, darkest)
    neutral = color_spread.point(lambda value: 255 if value <= 16 else 0)
    if light:
        shade = darkest.point(lambda value: 255 if value >= 244 else 0)
    else:
        shade = brightest.point(lambda value: 255 if value <= 18 else 0)
    opaque = alpha.point(lambda value: 255 if value > 0 else 0)
    return ImageChops.multiply(ImageChops.multiply(shade, neutral), opaque)


def _touches_transparency(alpha: Image.Image) -> Image.Image:
    width, height = alpha.size
    transparent = alpha.point(lambda value: 255 if value == 0 else 0)
    padded = ImageOps.expand(transparent, border=1, fill=0)
    neighbors = (
        padded.crop((1, 0, width + 1, height)),
        padded.crop((1, 2, width + 1, height + 2)),
        padded.crop((0, 1, width, height + 1)),
        padded.crop((2, 1, width + 2, height + 1)),
    )
    adjacent = neighbors[0]
    for neighbor in neighbors[1:]:
        adjacent = ImageChops.lighter(adjacent, neighbor)
    return adjacent


def _background_component(image: Image.Image, kind: str) -> bytearray:
    alpha = image.getchannel("A")
    candidate = _candidate_background_mask(image, light=kind == "light")
    if candidate.getbbox() is None:
        return bytearray(image.width * image.height)

    edge = Image.new("L", image.size, 0)
    edge_pixels = edge.load()
    for x in range(image.width):
        edge_pixels[x, 0] = 255
        edge_pixels[x, image.height - 1] = 255
    for y in range(image.height):
        edge_pixels[0, y] = 255
        edge_pixels[image.width - 1, y] = 255
    exterior = ImageChops.lighter(_touches_transparency(alpha), edge)
    seed_mask = ImageChops.multiply(candidate, exterior)
    seed_box = seed_mask.getbbox()
    if seed_box is None:
        return bytearray(image.width * image.height)
    seed_left, seed_top, seed_right, _ = seed_box
    seed_width = seed_right - seed_left
    seeds = seed_mask.crop(seed_box).tobytes()
    candidates = candidate.tobytes()
    visited = bytearray(len(candidates))
    queue: deque[int] = deque()
    count = 0
    for local_index, seed in enumerate(seeds):
        if not seed:
            continue
        x = seed_left + local_index % seed_width
        y = seed_top + local_index // seed_width
        index = y * image.width + x
        visited[index] = 1
        queue.append(index)
        count += 1

    width, height = image.size
    while queue:
        index = queue.popleft()
        x = index % width
        if x > 0 and not visited[index - 1] and candidates[index - 1]:
            visited[index - 1] = 1
            queue.append(index - 1)
            count += 1
        if x + 1 < width and not visited[index + 1] and candidates[index + 1]:
            visited[index + 1] = 1
            queue.append(index + 1)
            count += 1
        if index >= width and not visited[index - width] and candidates[index - width]:
            visited[index - width] = 1
            queue.append(index - width)
            count += 1
        if index + width < width * height and not visited[index + width] and candidates[index + width]:
            visited[index + width] = 1
            queue.append(index + width)
            count += 1

    # Small white logos and edge highlights belong to the item, not its backdrop.
    minimum_backdrop = max(128, (image.width * image.height) // 12)
    return visited if count >= minimum_backdrop else bytearray(len(candidates))


def _grow_photo_foreground(
    source: Image.Image, alpha: Image.Image, backdrop: tuple[int, int, int]
) -> Image.Image:
    """Recover missing garment pixels while keeping the uniform photo backdrop clear."""
    red, green, blue = source.split()
    differences = [
        ImageChops.difference(channel, Image.new("L", source.size, backdrop[index]))
        for index, channel in enumerate((red, green, blue))
    ]
    distance = ImageChops.lighter(differences[0], ImageChops.lighter(differences[1], differences[2]))
    candidate = distance.point(lambda value: 255 if value > 8 else 0).tobytes()
    seeds = alpha.tobytes()
    width, height = source.size
    pixel_count = width * height
    visited = bytearray(pixel_count)
    queue: deque[int] = deque()
    for index, seed in enumerate(seeds):
        if seed:
            visited[index] = 1
            queue.append(index)

    # Existing cutout alpha establishes the garment's full silhouette bounds. Stay
    # inside them so a connected studio shadow cannot grow the shape outward.
    bounds = alpha.getbbox()
    if bounds is None:
        return alpha
    left, top, right, bottom = bounds
    while queue:
        index = queue.popleft()
        x, y = index % width, index // width
        neighbors = (
            index - 1 if x > left else -1,
            index + 1 if x + 1 < right else -1,
            index - width if y > top else -1,
            index + width if y + 1 < bottom else -1,
        )
        for neighbor in neighbors:
            if neighbor >= 0 and not visited[neighbor] and candidate[neighbor]:
                visited[neighbor] = 1
                queue.append(neighbor)

    grown = Image.frombytes("L", source.size, bytes(255 if value else 0 for value in visited))
    # Close only tiny mask gaps; preserve the alpha silhouette at its outer edge.
    closed = grown.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3))
    return ImageChops.lighter(alpha, closed)


@lru_cache(maxsize=24)
def _clean_cutout_backdrop(
    path: str,
    modified_ns: int,
    source_modified_ns: int = 0,
) -> bytes | None:
    """Clean photo backdrops and recover pale fabric from the untouched catalogue photo."""
    # Both timestamps are part of the cache key so either updated image is reprocessed.
    del modified_ns, source_modified_ns
    with Image.open(path) as source:
        image = source.convert("RGBA")
    alpha = bytearray(image.getchannel("A").tobytes())

    changed = False
    for kind in ("light", "dark"):
        background = _background_component(image, kind)
        for index, remove in enumerate(background):
            if remove and alpha[index]:
                alpha[index] = 0
                changed = True

    source_path = Path(path).parent.parent / "products" / f"{Path(path).stem}.jpg"
    if source_path.is_file():
        with Image.open(source_path) as source:
            original = source.convert("RGB")
        if original.size != image.size:
            original = original.resize(image.size, Image.Resampling.LANCZOS)

        corners = [
            original.getpixel((0, 0)),
            original.getpixel((image.width - 1, 0)),
            original.getpixel((0, image.height - 1)),
            original.getpixel((image.width - 1, image.height - 1)),
        ]
        if all(min(pixel) >= 245 and max(pixel) - min(pixel) <= 12 for pixel in corners):
            backdrop = tuple(
                sorted(pixel[channel] for pixel in corners)[len(corners) // 2]
                for channel in range(3)
            )
            restored = _grow_photo_foreground(
                original, Image.frombytes("L", image.size, bytes(alpha)), backdrop
            )
            restored_alpha = restored.tobytes()
            if restored_alpha != bytes(alpha):
                alpha = bytearray(restored_alpha)
                changed = True
    if not changed:
        return None

    image.putalpha(Image.frombytes("L", image.size, bytes(alpha)))
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


@app.get("/media/{file_path:path}")
def media(file_path: str) -> Response:
    requested = (DATA_DIR / file_path).resolve()
    if DATA_DIR.resolve() not in requested.parents or not requested.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    if "product_cutouts" in requested.relative_to(DATA_DIR.resolve()).parts and requested.suffix.lower() == ".png":
        original = DATA_DIR / "products" / f"{requested.stem}.jpg"
        source_modified_ns = original.stat().st_mtime_ns if original.is_file() else 0
        cleaned = _clean_cutout_backdrop(
            str(requested), requested.stat().st_mtime_ns, source_modified_ns
        )
        if cleaned is not None:
            return Response(
                content=cleaned,
                media_type="image/png",
                headers={"Cache-Control": "public, max-age=3600"},
            )
    return FileResponse(requested)
