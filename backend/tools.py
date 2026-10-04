"""Database-backed catalogue tools for the Campus Customs agent."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Literal

from pydantic_ai import RunContext

if __package__:
    from .models import (
        AgentDependencies,
        InventoryItem,
        PriceResult,
        Product,
        ProductDescriptionResult,
        ProductLookupError,
        ProductSearchHit,
        StockResult,
    )
else:  # Supports `uvicorn main:app` when launched from backend/.
    from models import (
        AgentDependencies,
        InventoryItem,
        PriceResult,
        Product,
        ProductDescriptionResult,
        ProductLookupError,
        ProductSearchHit,
        StockResult,
    )


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [value]
    return parsed if isinstance(parsed, list) else [str(parsed)]


def _row_to_product(
    connection: sqlite3.Connection,
    row: sqlite3.Row,
    data_dir: Path,
) -> Product:
    inventory_rows = connection.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY id",
        (row["product_id"],),
    ).fetchall()
    inventory = [
        InventoryItem(size=item["size"], quantity=item["quantity"])
        for item in inventory_rows
    ]
    source_path = Path(row["image_file_path"])
    cutout_path = data_dir / "product_cutouts" / f"{source_path.stem}.png"
    image_url = (
        f"/media/product_cutouts/{source_path.stem}.png"
        if cutout_path.is_file()
        else f"/media/{row['image_file_path'].lstrip('/')}"
    )
    return Product(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=_json_list(row["colors"]),
        search_tags=_json_list(row["search_tags"]),
        image_file_path=row["image_file_path"],
        image_url=image_url,
        price=row["price"],
        inventory=inventory,
        total_stock=sum(item.quantity for item in inventory),
    )


def read_products(
    database_path: Path,
    data_dir: Path,
    product_id: str | None = None,
) -> list[Product]:
    """Read canonical products, including image URLs and size inventory, from SQLite."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        if product_id is None:
            rows = connection.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
            ).fetchall()
        return [_row_to_product(connection, row, data_dir) for row in rows]
    finally:
        connection.close()


_CATEGORY_ALIASES = {
    "t-shirt": ("t shirt", "t shirts", "tshirt", "tshirts", "tee", "tees"),
    "shirt": ("shirt", "shirts"),
    "sweater": ("sweater", "sweaters"),
    "hoodie": ("hoodie", "hoodies", "hooded sweatshirt"),
    "sweatshirt": ("sweatshirt", "sweatshirts", "crewneck", "crewnecks", "crew neck"),
    "fleece": ("fleece",),
    "jacket": ("jacket", "jackets"),
    "quarter-zip": ("quarter zip", "quarter zips", "1 4 zip"),
    "full-zip": ("full zip", "full zips", "zip up", "zip ups"),
}
_NONIDENTIFYING_PRODUCT_TERMS = {
    "apparel", "basic", "big", "campus", "chest", "college", "crew", "crewneck",
    "fleece", "hooded", "hoodie", "jacket", "left", "logo", "merchandise", "pullover",
    "quarter", "shirt", "sweater", "sweatshirt", "tee", "tshirt", "university", "vintage",
    "yale", "zip",
}
_COLOR_WORDS = {
    "aqua", "beige", "black", "blue", "brown", "bronze", "burgundy",
    "charcoal", "coral", "cream", "cyan", "gold", "gray", "green", "indigo",
    "ivory", "khaki", "lavender", "lilac", "magenta", "maroon", "multicolor",
    "navy", "olive", "orange", "peach", "pink", "purple", "red", "silver",
    "tan", "teal", "turquoise", "violet", "white", "yellow",
}
_COLOR_SYNONYMS = {"grey": "gray"}


def _normalized_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _requested_categories(query: str) -> set[str]:
    normalized_query = f" {_normalized_text(query)} "
    requested = {
        category
        for category, aliases in _CATEGORY_ALIASES.items()
        if any(f" {_normalized_text(alias)} " in normalized_query for alias in aliases)
    }
    if "t-shirt" in requested:
        without_t_shirt = normalized_query
        for alias in _CATEGORY_ALIASES["t-shirt"]:
            without_t_shirt = without_t_shirt.replace(f" {_normalized_text(alias)} ", " ")
        if not any(
            f" {_normalized_text(alias)} " in without_t_shirt
            for alias in _CATEGORY_ALIASES["shirt"]
        ):
            requested.discard("shirt")
    return requested


def _normalize_color(value: str) -> str:
    return " ".join(
        _COLOR_SYNONYMS.get(word, word) for word in _normalized_text(value).split()
    )


def _requested_colors(query: str, products: list[Product]) -> set[str]:
    """Extract explicit colors, preferring exact multiword catalogue colors."""
    words = [
        _COLOR_SYNONYMS.get(word, word) for word in _normalized_text(query).split()
    ]
    palette_phrases = sorted(
        {
            _normalize_color(color)
            for product in products
            for color in product.colors
            if len(_normalize_color(color).split()) > 1
        },
        key=lambda phrase: len(phrase.split()),
        reverse=True,
    )
    requested: set[str] = set()
    index = 0
    while index < len(words):
        phrase = next(
            (
                color
                for color in palette_phrases
                if words[index : index + len(color.split())] == color.split()
            ),
            None,
        )
        if phrase:
            requested.add(phrase)
            index += len(phrase.split())
            continue

        word = _COLOR_SYNONYMS.get(words[index], words[index])
        if word in _COLOR_WORDS:
            requested.add(word)
        index += 1
    return requested


def _product_matches_colors(
    product: Product, requested_colors: set[str], *, main_color_only: bool
) -> bool:
    """Match any requested color in the pictured color, or any listed option."""
    listed_colors = product.colors[:1] if main_color_only else product.colors
    product_colors = [_normalize_color(color) for color in listed_colors]
    return any(
        any(
            requested_color == product_color
            if " " in requested_color
            else requested_color in product_color.split()
            for product_color in product_colors
        )
        for requested_color in requested_colors
    )


def _product_matches_categories(product: Product, categories: set[str]) -> bool:
    searchable_text = _normalized_text(
        " ".join(
            [
                product.name,
                product.garment_type,
                product.description,
                *product.search_tags,
            ]
        )
    )
    return any(
        f" {_normalized_text(alias)} " in f" {searchable_text} "
        for category in categories
        for alias in _CATEGORY_ALIASES[category]
    )


def _product_identity_terms(product: Product) -> set[str]:
    """Return distinctive name words useful for finding a related product."""
    return {
        term
        for term in re.findall(r"[a-z0-9]+", product.name.casefold())
        if len(term) > 2
        and not term.isdigit()
        and term not in _NONIDENTIFYING_PRODUCT_TERMS
    }


_PAGE_PRODUCT_REFERENCE = re.compile(r"\b(?:this|that|it|these|those)\b", re.IGNORECASE)


def filter_color_recommendations(
    message: str,
    candidates: list[Product],
    catalogue: list[Product],
    *,
    page_product_id: str | None = None,
) -> list[Product]:
    """Show the pictured color in broad searches; keep listed variants for named items."""
    requested_colors = _requested_colors(message, catalogue)
    if not requested_colors:
        return candidates

    normalized_message = f" {_normalized_text(message)} "
    named_ids = {
        product.product_id
        for product in catalogue
        if f" {_normalized_text(product.name)} " in normalized_message
    }
    if page_product_id and _PAGE_PRODUCT_REFERENCE.search(message):
        named_ids.add(page_product_id)

    return [
        product
        for product in candidates
        if _product_matches_colors(
            product,
            requested_colors,
            main_color_only=product.product_id not in named_ids,
        )
    ]


def _current_page_product_reference(ctx: RunContext[AgentDependencies]) -> str | None:
    """Resolve product pronouns to the current page unless another item is named."""
    page_context = ctx.deps.page_context
    message = ctx.deps.original_user_message
    if (
        page_context is None
        or not page_context.current_product_id
        or not _PAGE_PRODUCT_REFERENCE.search(message)
    ):
        return None

    normalized_message = f" {_normalized_text(message)} "
    connection = sqlite3.connect(ctx.deps.database_path)
    try:
        other_products = connection.execute(
            "SELECT product_id, name FROM catalogue WHERE product_id != ?",
            (page_context.current_product_id,),
        ).fetchall()
    finally:
        connection.close()

    # A shopper may compare the page item with a different, explicitly named item.
    if any(
        f" {_normalized_text(name)} " in normalized_message
        for _, name in other_products
        if _normalized_text(name)
    ):
        return None
    return page_context.current_product_id


def search_catalogue(
    query: str,
    database_path: Path,
    data_dir: Path,
    limit: int = 5,
    category_context: str = "",
    required_categories: set[str] | None = None,
    required_anchor_terms: set[str] | None = None,
) -> list[Product]:
    """Rank catalogue rows against query terms; all fields remain sourced from SQLite."""
    stop_words = {
        "a", "an", "are", "can", "do", "for", "have", "i", "in", "is", "me",
        "of", "on", "please", "show", "some", "the", "to", "what", "with", "you",
    }
    search_text = f"{query} {category_context}"
    raw_terms = [
        term for term in re.findall(r"[a-z0-9]+", search_text.casefold()) if term not in stop_words
    ]
    expanded_terms = []
    for term in raw_terms:
        expanded_terms.append(term)
        if term.endswith("ies") and len(term) > 3:
            expanded_terms.append(term[:-3] + "y")
            expanded_terms.append(term[:-1])
        elif term.endswith("s") and not term.endswith("ss") and len(term) > 3:
            expanded_terms.append(term[:-1])
    terms = list(dict.fromkeys(expanded_terms))
    if not terms:
        return []

    # A broad term such as "Yale" must not make an unrelated item eligible
    # when the shopper also specified a product category such as "sweater".
    requested_categories = (
        required_categories
        if required_categories is not None
        else _requested_categories(query) | _requested_categories(category_context)
    )
    products = read_products(database_path, data_dir)
    # Prefer the original shopper message when provided; a model-generated tool
    # query must not invent a color constraint or erase the shopper's color.
    products = filter_color_recommendations(
        category_context.strip() or query, products, products
    )
    ranked: list[tuple[int, Product]] = []
    for product in products:
        if requested_categories and not _product_matches_categories(product, requested_categories):
            continue
        if required_anchor_terms:
            identity_text = _normalized_text(
                " ".join([product.name, product.description, *product.search_tags])
            )
            if not any(
                f" {term} " in f" {identity_text} " for term in required_anchor_terms
            ):
                continue
        fields = (
            (product.product_id.casefold(), 8),
            (product.name.casefold(), 6),
            (product.garment_type.casefold(), 4),
            (" ".join(product.colors).casefold(), 4),
            (" ".join(product.search_tags).casefold(), 2),
            (product.description.casefold(), 1),
        )
        score = sum(weight for term in terms for value, weight in fields if term in value)
        if score:
            ranked.append((score, product))

    ranked.sort(key=lambda item: (-item[0], item[1].name.casefold()))
    return [product for _, product in ranked[: max(1, min(limit, 8))]]


def search_products(
    ctx: RunContext[AgentDependencies],
    query: str,
    limit: int = 5,
) -> list[ProductSearchHit]:
    """Find IDs while enforcing requested categories and colors from the shopper's message."""
    ctx.deps.catalogue_search_performed = True
    page_product_id = _current_page_product_reference(ctx)
    if page_product_id:
        current_products = read_products(
            ctx.deps.database_path, ctx.deps.data_dir, page_product_id
        )
        if current_products:
            current_product = current_products[0]
            requested_categories = _requested_categories(ctx.deps.original_user_message)
            current_categories = _requested_categories(
                f"{current_product.name} {current_product.garment_type}"
            )
            alternative_categories = requested_categories - current_categories
        else:
            alternative_categories = set()

        if current_products and alternative_categories:
            # Use the current item as the search anchor, but restrict results to
            # the alternate product type the shopper asked for.
            matches = search_catalogue(
                f"{query[:240]} {current_products[0].name}",
                ctx.deps.database_path,
                ctx.deps.data_dir,
                limit=limit,
                category_context=ctx.deps.original_user_message,
                required_categories=alternative_categories,
                required_anchor_terms=_product_identity_terms(current_products[0]) or None,
            )
        elif current_products:
            matches = current_products
        else:
            matches = search_catalogue(
                query[:240],
                ctx.deps.database_path,
                ctx.deps.data_dir,
                limit=limit,
                category_context=ctx.deps.original_user_message,
            )
    else:
        matches = search_catalogue(
            query[:240],
            ctx.deps.database_path,
            ctx.deps.data_dir,
            limit=limit,
            category_context=ctx.deps.original_user_message,
        )
    ctx.deps.matched_product_ids.update(product.product_id for product in matches)
    for product in matches:
        if product.product_id not in ctx.deps.search_result_ids:
            ctx.deps.search_result_ids.append(product.product_id)
    return [
        ProductSearchHit(
            product_id=product.product_id,
            name=product.name,
            garment_type=product.garment_type,
            main_color=product.colors[0] if product.colors else None,
        )
        for product in matches
    ]


def _lookup_product(ctx: RunContext[AgentDependencies], product_id: str) -> Product | None:
    page_product_id = _current_page_product_reference(ctx)
    if page_product_id and product_id not in ctx.deps.search_result_ids:
        product_id = page_product_id
    matches = read_products(
        ctx.deps.database_path, ctx.deps.data_dir, product_id=product_id
    )
    if not matches:
        return None
    product = matches[0]
    ctx.deps.matched_product_ids.add(product.product_id)
    return product


def related_products(
    ctx: RunContext[AgentDependencies],
    product_id: str,
    requested_type: str = "",
    limit: int = 5,
) -> list[ProductSearchHit] | ProductLookupError:
    """Find same-design catalogue products of requested types, or all types if omitted."""
    anchor = _lookup_product(ctx, product_id)
    if anchor is None:
        return ProductLookupError(product_id=product_id)

    categories = _requested_categories(requested_type)
    if requested_type.strip() and not categories:
        return []

    matches = search_catalogue(
        f"{anchor.name} {requested_type}",
        ctx.deps.database_path,
        ctx.deps.data_dir,
        limit=limit,
        category_context=ctx.deps.original_user_message,
        # With no requested type, don't infer one from the anchor's own name
        # (e.g. "1/4 Zip" would otherwise restrict results to quarter-zips).
        required_categories=categories if requested_type.strip() else set(),
        required_anchor_terms=_product_identity_terms(anchor) or None,
    )
    matches = [product for product in matches if product.product_id != anchor.product_id]
    ctx.deps.matched_product_ids.update(product.product_id for product in matches)
    for product in matches:
        if product.product_id not in ctx.deps.search_result_ids:
            ctx.deps.search_result_ids.append(product.product_id)
    return [
        ProductSearchHit(
            product_id=product.product_id,
            name=product.name,
            garment_type=product.garment_type,
            main_color=product.colors[0] if product.colors else None,
        )
        for product in matches
    ]


def _clothing_type(product: Product) -> str:
    """Normalize the catalogue's garment type without replacing its original wording."""
    garment = product.garment_type.casefold()
    wording = f"{garment} {product.name.casefold()}"
    if "t-shirt" in garment:
        return "t-shirt"
    if "hood" in wording:
        return "hoodie"
    if "fleece" in wording:
        return "fleece"
    if "jacket" in wording:
        return "jacket"
    if "quarter-zip" in wording:
        return "quarter-zip"
    if "crewneck" in wording:
        return "crewneck"
    if "mockneck" in wording:
        return "mockneck"
    if "sweater" in wording:
        return "sweater"
    if "performance shirt" in garment:
        return "performance shirt"
    return product.garment_type


def _sleeve_info(
    product: Product, clothing_type: str
) -> tuple[
    Literal["short", "long"] | None,
    Literal["catalogue_text", "inferred_from_clothing_type", "unknown"],
]:
    for wording in (product.garment_type, product.description, product.name):
        has_short = bool(re.search(r"\bshort[ -]sleeves?\b", wording, re.IGNORECASE))
        has_long = bool(re.search(r"\blong[ -]sleeves?\b", wording, re.IGNORECASE))
        if has_short and has_long:
            return None, "unknown"
        if has_short:
            return "short", "catalogue_text"
        if has_long:
            return "long", "catalogue_text"

    if clothing_type in {
        "hoodie", "fleece", "jacket", "quarter-zip", "crewneck", "mockneck", "sweater"
    }:
        return "long", "inferred_from_clothing_type"
    return None, "unknown"


def product_description(
    ctx: RunContext[AgentDependencies], product_id: str
) -> ProductDescriptionResult | ProductLookupError:
    """Look up one item's description, main/accent colors, sleeve length, and clothing type."""
    product = _lookup_product(ctx, product_id)
    if product is None:
        return ProductLookupError(product_id=product_id)

    clothing_type = _clothing_type(product)
    sleeve_length, sleeve_source = _sleeve_info(product, clothing_type)
    return ProductDescriptionResult(
        product_id=product.product_id,
        name=product.name,
        description=product.description,
        garment_type=product.garment_type,
        clothing_type=clothing_type,
        main_color=product.colors[0] if product.colors else None,
        accent_colors=product.colors[1:],
        sleeve_length=sleeve_length,
        sleeve_length_source=sleeve_source,
    )


def price(
    ctx: RunContext[AgentDependencies], product_id: str
) -> PriceResult | ProductLookupError:
    """Look up one item's current price from catalogue.price by exact product ID."""
    product = _lookup_product(ctx, product_id)
    if product is None:
        return ProductLookupError(product_id=product_id)
    return PriceResult(product_id=product.product_id, name=product.name, price=product.price)


_SIZE_ALIASES = {
    "extra small": "XS",
    "x-small": "XS",
    "small": "S",
    "medium": "M",
    "large": "L",
    "extra large": "XL",
    "x-large": "XL",
    "2xl": "XXL",
    "extra extra large": "XXL",
}


def stock(
    ctx: RunContext[AgentDependencies], product_id: str, size: str | None = None
) -> StockResult | ProductLookupError:
    """Look up current inventory by size; pass a size to check its exact availability."""
    product = _lookup_product(ctx, product_id)
    if product is None:
        return ProductLookupError(product_id=product_id)

    requested_size = None
    requested_size_quantity = None
    size_status = None
    if size and size.strip():
        requested_size = _SIZE_ALIASES.get(size.strip().casefold(), size.strip().upper())
        matching_row = next(
            (item for item in product.inventory if item.size.casefold() == requested_size.casefold()),
            None,
        )
        if matching_row is None:
            size_status = "not_listed"
        else:
            requested_size = matching_row.size
            requested_size_quantity = matching_row.quantity
            size_status = "in_stock" if matching_row.quantity > 0 else "out_of_stock"

    return StockResult(
        product_id=product.product_id,
        name=product.name,
        total_stock=product.total_stock,
        inventory_by_size=product.inventory,
        requested_size=requested_size,
        requested_size_quantity=requested_size_quantity,
        size_status=size_status,
    )
