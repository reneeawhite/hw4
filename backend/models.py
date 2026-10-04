"""Shared API and agent models for the Campus Customs backend."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class InventoryItem(BaseModel):
    size: str
    quantity: int


class Product(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    search_tags: list[str]
    image_file_path: str
    image_url: str
    price: float
    inventory: list[InventoryItem]
    total_stock: int


class ProductSearchHit(BaseModel):
    product_id: str
    name: str
    garment_type: str
    main_color: str | None = None


class ProductLookupError(BaseModel):
    product_id: str
    error: Literal["product_not_found"] = "product_not_found"


class ProductDescriptionResult(BaseModel):
    product_id: str
    name: str
    description: str
    garment_type: str
    clothing_type: str
    main_color: str | None
    accent_colors: list[str]
    sleeve_length: Literal["short", "long"] | None
    sleeve_length_source: Literal[
        "catalogue_text", "inferred_from_clothing_type", "unknown"
    ]


class PriceResult(BaseModel):
    product_id: str
    name: str
    price: float


class StockResult(BaseModel):
    product_id: str
    name: str
    total_stock: int
    inventory_by_size: list[InventoryItem]
    requested_size: str | None = None
    requested_size_quantity: int | None = None
    size_status: Literal["in_stock", "out_of_stock", "not_listed"] | None = None


class CustomerContext(BaseModel):
    user_id: int
    name: str
    email: str


class PageContext(BaseModel):
    path: str | None = Field(default=None, max_length=500)
    current_product_id: str | None = Field(default=None, max_length=160)


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=3000)
    product_ids: list[str] = Field(default_factory=list, max_length=8)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1200)
    history: list[ChatTurn] = Field(default_factory=list, max_length=8)
    page_context: PageContext | None = None

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be blank")
        return value


class AgentChatReply(BaseModel):
    """Structured model output; product facts/cards are added from SQLite by the API."""

    reply: str = Field(description="A concise, helpful response to the shopper")
    product_ids: list[str] = Field(
        default_factory=list,
        description="IDs of relevant catalogue products returned by a product tool",
    )


class ChatResponse(BaseModel):
    reply: str
    products: list[Product] = Field(default_factory=list)


class StoredChatTurn(ChatTurn):
    products: list[Product] = Field(default_factory=list)


class ChatHistoryResponse(BaseModel):
    messages: list[StoredChatTurn] = Field(default_factory=list)


class AuditEvent(BaseModel):
    """One privacy-minimized JSON Lines record in the append-only audit trail."""

    time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    request_id: str
    event: Literal["tool_call", "run_end"]
    tool_name: str | None = None
    args_summary: dict[str, Any] = Field(default_factory=dict)
    result_summary: dict[str, Any] = Field(default_factory=dict)
    stop_reason: str | None = None
    model_finish_reason: str | None = None
    model_requests: int | None = None
    tool_calls: int | None = None


@dataclass
class AgentDependencies:
    database_path: Path
    data_dir: Path
    original_user_message: str = ""
    catalogue_search_performed: bool = False
    matched_product_ids: set[str] = field(default_factory=set)
    search_result_ids: list[str] = field(default_factory=list)
    customer: CustomerContext | None = None
    page_context: PageContext | None = None
