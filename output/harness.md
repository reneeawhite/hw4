# Campus Customs Database Harness

`data/campus_customs.db` is a SQLite database for the Campus Customs shop and chatbot. The application tables are connected through user and product IDs.

## `catalogue`

The `catalogue` table stores the products the shop sells.

| Field | Why it matters |
|---|---|
| `product_id` | Uniquely identifies a product and lets other tables refer to it. |
| `name` | Gives the shop and chatbot a readable product name to display. |
| `garment_type` | Helps classify products as T-shirts, hoodies, crewnecks, and so on. |
| `description` | Gives the chatbot detailed information for product explanations and matching. |
| `colors` | Helps the chatbot search for products by color and describe what is available. |
| `search_tags` | Provides keywords for product search and recommendation. |
| `image_file_path` | Connects a catalogue record to the product image shown to shoppers or analyzed by the chatbot. |
| `price` | Lets the shop display the cost and lets the chatbot answer price questions. |

## `inventory`

The `inventory` table tracks how many items are available in each size.

| Field | Why it matters |
|---|---|
| `id` | Uniquely identifies each inventory record. |
| `product_id` | Connects stock information to the correct product in `catalogue`. |
| `size` | Tells the shop which clothing size the stock record describes. |
| `quantity` | Shows whether an item is in stock and how many are available. |

## `users`

The `users` table stores customer account information.

| Field | Why it matters |
|---|---|
| `id` | Uniquely identifies a customer and connects the customer to chat messages. |
| `name` | Provides the customer’s display name for the shop or chatbot. |
| `email` | Identifies the account and provides a contact or login address. |
| `password_hash` | Stores a protected password representation for authentication without storing the original password. |
| `created_at` | Records when the account was created. |
| `first_name` | Stores the customer’s first name when available for personalization. |
| `last_name` | Stores the customer’s last name when available for personalization. |

## Authentication

Problem 4 uses `POST /api/auth/register` to create accounts and `POST /api/auth/login` to authenticate existing users. Registration requires first name, last name, email, password, and matching password confirmation. Emails are normalized to lowercase and duplicate addresses are rejected.

The `users` table stores the account name, email, first name, last name, creation time, and a `password_hash`. It never stores the original password. Passwords are protected with Python’s built-in `scrypt` password-hashing function using:

- a new random 16-byte salt for every account;
- work factor `N=16384`, `r=8`, and `p=1`; and
- a 64-byte derived key encoded in the stored `scrypt$...` value.

During login, the submitted password is hashed with the stored salt and compared using a constant-time comparison. The browser stores only a temporary access token and the returned user profile in `sessionStorage`; it never stores the password. Prototype session tokens are held in backend memory and become invalid when the API server restarts.

The supplied test account is supported with:

```text
Email: test@campuscustoms.yale.edu
Password: password
```

The seed test account was migrated from its older placeholder hash to the same salted `scrypt` format used for new accounts. This is suitable for the homework prototype; a production deployment would also require HTTPS, a persistent session store, rate limiting, and account recovery controls.

## `chat_messages`

The `chat_messages` table stores the conversation between customers and the chatbot.

| Field | Why it matters |
|---|---|
| `id` | Uniquely identifies each message and preserves message history. |
| `user_id` | Connects each message to the customer who had the conversation. |
| `role` | Identifies whether the message came from the user or the assistant. |
| `content` | Stores the actual question, answer, or other message text. |
| `products_json` | Stores product recommendations or search results associated with a response. |
| `created_at` | Records when the message was sent and helps preserve conversation order. |

## `sqlite_sequence`

`sqlite_sequence` is an internal SQLite table. It tracks automatic ID values for tables that use `AUTOINCREMENT`; it does not contain shop or chatbot business data.

## Table relationships

```text
users ───────────────< chat_messages

catalogue ───────────< inventory
```

One user can have many chat messages, and one catalogue product can have multiple inventory records—typically one for each size.

## Problem 5: PydanticAI shopping assistant

The front-end chat widget sends `POST /api/chat` to `http://127.0.0.1:8000` with the current `message` and page context. For a logged-in shopper, FastAPI loads the latest eight messages from `chat_messages` as agent context; the browser does not resend that history. Guests may send up to eight recent in-memory messages because their chats are not stored. The route returns a JSON object with the assistant `reply` and a `products` array. The widget renders returned products as links to their existing single-product pages. It shows a loading state while waiting and a readable error if the API or model is unavailable.

The agent is split into `backend/agent.py` (provider setup and agent execution), `backend/tools.py` (SQLite catalogue search and exact product lookup), `backend/models.py` (request, response, product, and structured agent-output types), and `backend/prompts/prompt.md` (Campus Customs voice, grounding, privacy, and safety rules). `main.py` exposes the chat route along with the existing catalogue, image, registration, and login routes.

The agent reads the system prompt from `backend/prompts/prompt.md`. It uses PydanticAI's OpenAI Responses model through Portkey's OpenAI-compatible endpoint. The default model is `gpt-5.6-luna`; `PORTKEY_MODEL` and `PORTKEY_BASE_URL` can override that default. The API key is loaded from the repository-root `.env` file (`PORTKEY_API_KEY`) and is not sent to the browser or committed. The agent is created lazily when the first chat request arrives, so product and auth endpoints remain available if the key is missing; chat then returns HTTP 503 with a setup message.

Product search, related-product search, and exact lookup tools read the local `catalogue` and `inventory` tables. Before cards are sent to the browser, the API resolves selected product IDs against SQLite and only includes IDs returned by a tool in that request. Consequently product names, descriptions, images, prices, colors, and size stock on cards come from the database rather than model-generated values. The prompt instructs the model to use these tools for product-specific answers and to be transparent when information is unavailable.

Guest turns stay in front-end memory and up to eight recent messages are sent with each guest chat request. For a signed-in shopper, the backend writes new user and assistant messages to `chat_messages`, using the authenticated user's `user_id`; assistant rows store returned product IDs in `products_json`. FastAPI loads the latest eight saved messages directly from SQLite as agent context for each signed-in request. `GET /api/chat/history` restores the same latest eight messages, including canonical product cards, for display when the shopper opens the chat again. Older messages remain stored in SQLite but are not loaded into the widget or resent to the agent. The browser keeps the access token in session storage and sends it as a Bearer token; the prototype's in-memory sessions expire when the API restarts, so the shopper must log in again after a backend restart.

Run the backend from `homework/hw4/backend/` with the homework virtual environment activated:

```bash
cd homework/hw4
source .venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
```

The Vite development server should be started separately from `homework/hw4/frontend/` with `npm run dev`.

If the terminal prompt already ends in `backend %`, activate Homework 4's environment from that directory and run the required command directly:

```bash
source ../.venv/bin/activate
command -v uvicorn
uvicorn main:app --reload --port 8000
```

`command -v uvicorn` should point to `homework/hw4/.venv/bin/uvicorn`. A prompt that merely says `(.venv)` does not identify which virtual environment is active; the workspace-root environment may not contain Uvicorn. Run one API server on port 8000 at a time.

## Problem 6: Product information, price, and stock tools

The agent uses the existing `backend/prompts/prompt.md` file to choose tools. The catalogue has no separate main-color, accent-color, clothing-category, or sleeve-length columns, so `product_description` derives those fields from `catalogue.colors`, `garment_type`, the name, and the description. Price and inventory counts are read directly from SQLite on each lookup.

| Agent tool | Return model and fields | Why these fields are returned |
|---|---|---|
| `search_products(query)` | `ProductSearchHit`: `product_id`, `name`, `garment_type`, `main_color` | Finds IDs and the pictured main color without giving the agent unchecked price or stock. Broad color searches hard-filter on the first catalogue color before ranking; when several colors are requested, a product may match any one of them. A specifically named item's later listed colors can still answer questions about that item's options. If a search returns no products, the API uses a clear no-match reply rather than allowing unsupported claims. |
| `related_products(product_id, requested_type?)` | `ProductSearchHit`: `product_id`, `name`, `garment_type` | Finds separate products with a related college/design identity and requested garment type(s). Multiple types can be passed together; omitting the optional type searches all related listings. Full-zip and T-shirt are recognized categories, and returned IDs are resolved into canonical product cards from SQLite. |
| `product_description(product_id)` | `ProductDescriptionResult`: `product_id`, `name`, `description`, `garment_type`, `clothing_type`, `main_color`, `accent_colors`, `sleeve_length`, `sleeve_length_source` | Identifies the item and gives its original catalogue wording plus the requested appearance fields. The first entry in the ordered `colors` list is the pictured main color; `accent_colors` holds later listed colors, which may be alternate options rather than accents shown in the photo. Sleeve length comes from explicit catalogue wording where possible, otherwise from a clothing-type inference marked by `sleeve_length_source`; it is `null` if unsupported. |
| `price(product_id)` | `PriceResult`: `product_id`, `name`, `price` | Ties the exact `catalogue.price` value to the right item. No price is inferred from similar products. |
| `stock(product_id, size?)` | `StockResult`: `product_id`, `name`, `total_stock`, `inventory_by_size`, `requested_size`, `requested_size_quantity`, `size_status` | Gives the exact `inventory.quantity` rows and their sum. For a requested size, `size_status` distinguishes `in_stock`, a recorded zero quantity (`out_of_stock`), and a size with no inventory row (`not_listed`). The size-specific quantity is `null` when no row exists. |

Each exact lookup returns `ProductLookupError` with `product_not_found` if the ID is absent. The system prompt requires `price()` for price questions and `stock()` for stock or size questions, and it tells the agent to state zero-stock sizes clearly. Product cards in API replies are still re-read from SQLite before reaching the browser.

Verification: a live agent question about the Berkeley Sweater Fleece Jacket called `search_products`, `product_description`, `price`, and `stock`. It correctly reported that size S has quantity 0 and is out of stock, quoted the database price of $98, and labeled its long sleeves as an inference from the clothing type.

## Problem 7: Chat search that updates the page

The chat API is the contract between the agent and the React page. The front end sends `POST /api/chat` with the shopper's message and page context; logged-in history is loaded by FastAPI, while guest history is a short in-memory client slice. FastAPI runs the PydanticAI agent, and `search_products(query)` returns typed `ProductSearchHit` values containing catalogue product IDs, names, and garment types. The agent places relevant IDs in `AgentChatReply.product_ids`. The backend then resolves those IDs against SQLite and returns canonical `Product` objects in the `ChatResponse.products` array. Images, names, descriptions, prices, colors, and inventory therefore come from the database.

When the response arrives, the chat widget keeps the assistant message and sends its `products` array to the page layout. The layout displays a `Found through chat` product section above the current route. Each result uses the same `ProductCard` component as the main Products page, including the image, name, short description, garment type, and price. Each card links to `/products/:productId`, so a card returned by chat opens the same single-item page with the large image, full description, colors, price, and size stock.

For a category request such as `What hoodies do you have?`, the search tool records matching IDs in the request dependencies. The related-products tool also records its results so the API can include those cards even if the model omits an ID while formatting its final answer. A new chat response replaces the previous page-level results; an API error clears them and is shown in the chat conversation.

Search detects explicit product categories in both the shopper's original message and the agent's tool query (including T-shirts, sweaters, hoodies, sweatshirts, fleece, jackets, and quarter-zips), then filters candidates to those categories before ranking. This prevents a broad matching word such as `Yale` from causing a T-shirt to appear for a sweater request, even if the agent broadens its own query. The agent prompt also tells the model to preserve the requested category.

## Problem 8: Customer memory

Logged-in chat uses the existing `chat_messages` table. Each new turn creates two rows for the authenticated user's `user_id`: one `role='user'` row containing the shopper's message and one `role='assistant'` row containing the agent reply. The assistant row's `products_json` stores the product IDs that were returned as cards. The `/api/chat/history` route reads those rows in conversation order and rehydrates product IDs into current database-backed product cards. Guests can still call `POST /api/chat`, and their messages are never written to the database. If a chat request contains an expired or invalid bearer token, the backend treats that request as guest chat rather than blocking it. If loading saved history returns 401, the front end clears the stale token and cached user and tells the shopper they can continue as a guest. Loading saved history itself still requires a valid login.

The backend resolves the Bearer token from the existing login/register session and puts a `CustomerContext` in agent dependencies with the customer's `user_id`, name, and email. The request-scoped instruction gives the agent the signed-in shopper's name; it gives the verified email only when that shopper explicitly asks for their own email. The customer ID stays in server-side dependencies. The backend does not add passwords or access tokens to agent dependencies or its prompt; shoppers should not paste secrets into chat themselves. The prompt tells the agent to use a shopper's name only when useful and protect their email and customer ID.

The React widget sends a `page_context` object with the current browser path and, when the path is `/products/:productId`, that product ID. The backend verifies the ID against the catalogue and gives the agent the canonical product name, garment type, and catalogue colors. When the current message refers to `this`, `that`, or `it`, factual product lookups resolve to the current page item, so older product cards in chat history cannot override the open page. If the shopper asks for another product type, `related_products(product_id, requested_type)` anchors the search on the current item's distinctive name terms and filters for every requested type. It recognizes full-zip and T-shirt categories; if no type is specified, it can find all same-design listings. Its results are separate catalogue products, not asserted variants of the current item. The same page context is sent for guests and logged-in shoppers.

## Problem 9: Usability improvements

The Products page provides a name/description/keyword search, garment-type and main-color filters, an availability filter, and name/price sorting. Main color is the first value in each product's ordered `colors` list; later listed colors are not included in the color filter. The result count updates with the filters, and an empty state offers a clear reset action. Stock availability is based on size inventory totals. Broad chat requests such as “white apparel” also use the pictured main color, so a gray garment that merely lists white as another option is not shown as a white product. For a question about a specific item, the agent may still discuss all of its listed color options. The API checks the returned cards against the same rule before sending them to the page.

The chat panel shows its current scope: the product name and garment type on a product-detail page, catalogue browsing on the Products page, or general shopping elsewhere. For each new reply made from a product page, cards are split into separately titled “Current item” and “Related options” groups; replies elsewhere use “Products from this answer.” This keeps the anchor product distinct from suggestions. Restored older chat cards are not misidentified as the product currently open.

The agent's `related_products(product_id, requested_type)` tool uses the current product's distinctive identity terms and filters results to the requested garment type(s). For example, from the Benjamin Franklin 1 4 Zip page, asking for “full-zip and T-shirt” options can return the separate Benjamin Franklin Fleece Jacket (catalogued as a full-zip fleece jacket) and Benjamin Franklin T Shirt. The Morse Logo T Shirt is another example of a separate related product, not a variant of the Morse 4 Zip.

For logged-in chat, FastAPI reads the latest eight saved messages from `chat_messages` when each request arrives. The browser does not send authenticated chat history repeatedly, and `/api/chat/history` restores only the same recent eight messages to the widget. Older rows remain in SQLite. Guest conversations remain in browser memory and send at most eight recent messages per request; guest history is not saved to SQLite.

## Problem 10: Website styling and product image presentation

The shared header has a light/dark theme toggle. The choice is saved in browser `localStorage` and applied to all routes. A tiled inline-SVG wallpaper repeats Yale wordmarks, Y marks, pennants, and Bulldog line art in subdued theme colors. The Dan cursor is a custom SVG pointer with a clear arrow tip and Bulldog badge; text inputs keep the normal text-selection cursor. While the chat request is pending, the status reads “Handsome Dan is checking the catalogue” and a rounder Bulldog illustration trots across the box once every eight seconds, with a pause between crossings. It no longer reverses direction. Reduced-motion settings show Dan standing still. The chat panel is capped to the viewport height, its message list scrolls independently, and it automatically scrolls to the newest message or loading status so Dan stays visible above the input.

Light-garment outlines are selected from the first catalogue color (the main color): `white`, `ivory`, `cream`, and `off-white`. A secondary color does not cause a gray or navy garment to be outlined, and the outline follows the image's alpha silhouette.

In `backend/main.py`, `/media/...` removes large, neutral near-white or near-black background regions connected to transparent margins or the image edges, then caches transformed bytes in memory. For cutouts with a matching source photo on a uniform white background, it also grows a mask from the known garment pixels into connected photo pixels that differ from the backdrop, then closes tiny gaps. This repairs missing white fabric (including the Yale Bowl T-shirt and Hype & Vice premium crewneck) without making the exterior opaque or leaving transparent speckles inside the garment. The Benjamin Franklin T-shirt remains intact. Source images and the database are not modified.

## Problem 12: Audit trail, safety, and final system specification

### Model fields and why they exist

The API and agent share the typed contracts in `backend/models.py`. These types keep model-generated language separate from database-backed product facts.

| Model | Fields | Why these fields were chosen |
|---|---|---|
| `InventoryItem` | `size`, `quantity` | Represents one exact `inventory` row, so an unavailable size is not confused with another size. |
| `Product` | `product_id`, `name`, `garment_type`, `description`, `colors`, `search_tags`, `image_file_path`, `image_url`, `price`, `inventory`, `total_stock` | Carries the canonical catalogue record to product pages/cards; `inventory` holds size rows and `total_stock` is their sum. `image_file_path` is the database path and `image_url` is the served path. |
| `ProductSearchHit` | `product_id`, `name`, `garment_type`, `main_color` | Lets search select an item and check its pictured main color without treating search as a source of price or quantity. |
| `ProductLookupError` | `product_id`, `error="product_not_found"` | Gives the agent an explicit, typed not-found result instead of an invented item. |
| `ProductDescriptionResult` | `product_id`, `name`, `description`, `garment_type`, `clothing_type`, `main_color`, `accent_colors`, `sleeve_length`, `sleeve_length_source` | Supplies requested appearance details and marks whether sleeve length came from catalogue text, clothing-type inference, or could not be determined. Later `colors` values may be alternate options rather than visible accents. |
| `PriceResult` | `product_id`, `name`, `price` | Keeps an exact database price tied to the correct product. |
| `StockResult` | `product_id`, `name`, `total_stock`, `inventory_by_size`, `requested_size`, `requested_size_quantity`, `size_status` | Shows counts by size and distinguishes a recorded zero (`out_of_stock`) from a size with no row (`not_listed`). |
| `CustomerContext` | `user_id`, `name`, `email` | Associates logged-in chat with a verified account. The agent sees the name by default, gets the email only for an explicit own-email question, and never needs the ID in its prompt. |
| `PageContext` | `path`, `current_product_id` | Resolves “this item” to the open product page; the backend verifies the ID against SQLite. |
| `ChatTurn` / `ChatRequest` | `role`, `content`, `product_ids`; request `message`, `history`, `page_context` | Identifies who said what, remembers which cards were shown, and carries the current question and page context. Request validation rejects blank messages; guest history is bounded to eight turns. |
| `AgentChatReply` / `ChatResponse` | Agent `reply`, `product_ids`; API `reply`, `products` | The model proposes text and IDs; FastAPI checks the IDs and returns full, current SQLite `Product` objects instead of trusting model-written product facts. |
| `StoredChatTurn` / `ChatHistoryResponse` | Saved turn plus `products`; response `messages` | Restores recent logged-in chat with current product cards while older rows remain in SQLite. |
| `AgentDependencies` | `database_path`, `data_dir`, `original_user_message`, `catalogue_search_performed`, `matched_product_ids`, `search_result_ids`, `customer`, `page_context` | Gives each run read-only lookup context and tracks whether a catalogue search ran and which IDs tools actually found, so the model cannot insert arbitrary product cards or claim search matches when none exist. |
| `AuditEvent` | UTC `time`, `request_id`, `event`, `tool_name`, `args_summary`, `result_summary`, `stop_reason`, `model_finish_reason`, `model_requests`, `tool_calls` | Makes tool calls and the end of each run traceable without storing the shopper's message, identity, token, or full model output. |

### Tools and abilities

`search_products(query, limit)` searches the catalogue by words, category, and pictured main color, returning at most eight typed hits. `related_products(product_id, requested_type)` finds same-design alternatives as separate products. `product_description(product_id)` supplies description, clothing type, colors, and carefully sourced sleeve length. `price(product_id)` reads `catalogue.price` for the exact ID. `stock(product_id, size?)` reads the size rows in `inventory` and calculates the total. These are the five agent tools; all are read-only. A not-found lookup returns `ProductLookupError`.

The shopper can browse/filter/sort products, open a product detail page, create an account or log in, and ask the agent product questions as a guest or signed-in user. `POST /api/chat` returns `ChatResponse`; its canonical cards appear both in the widget and in the page-level “Found through chat” section. `GET /api/chat/history` restores only a logged-in shopper's recent conversation. FastAPI also serves products and images; React/Vite calls it at `http://127.0.0.1:8000`.

### Append-only audit trail

`output/audit_trail.json` is an append-only **JSON Lines** file: each non-empty line is one complete JSON object, although the requested filename ends in `.json`. It starts empty and is populated by chat requests; it is never reset on server restart. After a successful PydanticAI run, the backend pairs that run's function-tool call and return messages and records their UTC time, tool name, short arguments/results, and a random per-request ID. A final `run_end` record has a `stop_reason` such as `completed`, `configuration_error`, `limit_reached`, `cancelled`, or `error`; successful runs also include the provider finish reason and model-request count. An unmatched tool call in a completed run is marked `interrupted`. If a model run fails before returning its messages, its end reason is still logged, but partial tool steps cannot be reconstructed from that failed run.

The writer opens the file with append-only mode, locks it while writing, and never truncates earlier lines. Search arguments are reduced to a small allowlist of catalogue terms; only verified catalogue product IDs, recognized sizes, result counts, prices, and stock counts are logged. Raw shopper text, names, emails, passwords, access tokens, API keys, and full model replies are not logged. To inspect records after a chat, run `tail -n 20 output/audit_trail.json` from `homework/hw4/`. Each line can be parsed separately as JSON. The offline tests exercise real PydanticAI function-tool calls, append across two runs, and check that private text does not appear in the records. If the audit file cannot be written, chat fails rather than silently running without an audit record.

### Safety rules

`backend/prompts/prompt.md` tells the agent to use the database tools for price, stock, size, and product facts on the current turn; admit missing information; and never invent stock, prices, products, shipping promises, or store policy. It distinguishes zero stock from an unlisted size and treats shopper messages, saved history, and catalogue text as untrusted data, not new instructions. It rejects attempts to reveal hidden prompts, credentials, or other shoppers' information. It does not ask for or echo passwords, API keys, tokens, or payment details, and cannot authenticate, take payment, place orders, or access private account records. Only the authenticated shopper's own account context may be used; email is provided to the model only when that shopper asks for their own email. Passwords in `users` are salted `scrypt` hashes, and session tokens remain in backend memory.

This is a homework prototype, not a production security system: logged-in chat saves user-entered messages in `chat_messages`, so shoppers should not paste secrets into chat. Production use would also need HTTPS, persistent sessions, rate limiting, and stronger privacy controls.

### Limits, model, and how to run

The PydanticAI model is `OpenAIResponsesModel` through Portkey, defaulting to `gpt-5.6-luna`; `PORTKEY_MODEL` and `PORTKEY_BASE_URL` can override it. `PORTKEY_API_KEY` comes from the repository-root `.env`, not the browser. The agent is created on the first chat request. The prompt file is read when the backend process starts, so restart the backend after changing `prompts/prompt.md`.

One chat turn has explicit limits of **8 model requests**, **12 function-tool calls**, and **2 PydanticAI retries**. Catalogue searches default to 5 hits and cap at 8; the API sends at most 8 product cards. Logged-in context and restored display use the latest 8 saved messages; guests send at most 8 in-memory turns. `ChatRequest.message` allows up to 1,200 characters. These limits control latency, cost, and irrelevant older context.

On a fresh checkout, restore the supplied `data/` pack and create the local dependencies first (from the `AI Foundations` workspace root):

```bash
cd homework/hw4
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cd frontend
npm install
```

With dependencies installed, run the backend in one terminal:

```bash
cd homework/hw4
source .venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
```

Run the front end in another terminal:

```bash
cd homework/hw4/frontend
npm run dev
```

Open `http://127.0.0.1:5173`; the API is at `http://127.0.0.1:8000/docs`. If the checkout root is already `hw4`, skip the `cd homework/hw4` command and use `cd frontend` for the front-end terminal. The submitted public repository must omit `data/campus_customs.db`, source product images, generated cutouts, local `.env` secrets, virtual environments, and `node_modules`; the supplied local data pack must be restored under `data/` before the full shop can run.
