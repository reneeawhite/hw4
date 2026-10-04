# Problem 9: Usability improvements

## Front-end improvements

### 1. Catalogue search, filters, and sorting

**Why it was added:** The catalogue contains many products, so scrolling through every item makes it harder to find a particular garment, color, or price.

**How it helps shoppers and the business:** Shoppers can search product names and descriptions, narrow the catalogue by garment type, each product's main color, and in-stock status, then sort by name or price. The color filter uses only the first catalogue color (the main color), not accent colors, making color-based browsing more direct and predictable.

### 3. Visible chat product context

**Why it was added:** A shopper may ask about “this” while viewing a product, while older recommendations in chat history can make the reference unclear.

**How it helps shoppers and the business:** The chat panel displays the product it is using as context. Related-product suggestions are labeled separately from the current item, so shoppers can tell whether an answer describes the item they opened or a different recommendation. This reduces confusion and makes product follow-ups easier.

## Search accuracy correction: strict color matching

**Why it was added:** The original catalogue search ranked any matching query word, allowing a generic tag such as “apparel” to add products that did not match a requested color. It also accepted white when white appeared only as a later listed option, even though the product photo showed a gray or navy garment.

**How it helps shoppers and the business:** Broad color searches use the first database color, which matches the pictured item. For example, “white apparel” no longer shows gray or navy product photos just because white appears later in their color lists. Specific item questions can still use the full list of available colors. If no pictured items match, the assistant can say so instead of showing misleading alternatives.

When a shopper requests several colors, matching treats them as alternatives: an item is included if its pictured main color matches any requested color. If the database returns no products, the API replaces a contradictory assistant claim with a clear no-match message.

## Agent and backend improvements

### 1. Related-products lookup

**Why it was added:** Free-form search can miss a matching alternative or return unrelated items when a shopper asks for the current design in another garment type.

**How it helps shoppers and the business:** A typed related-products tool receives the current product and one or more requested types, then searches for catalogue items sharing distinctive product or college terms. It recognizes full-zips and T-shirts, and can search all same-design forms when the shopper asks generally for other options. For example, a Benjamin Franklin 1 4 Zip request for “full-zip and T-shirt” can return the separate Benjamin Franklin Fleece Jacket and Benjamin Franklin T Shirt. This gives shoppers grounded alternatives without implying that the original item has a variant the database does not record.

### 4. Server-side recent chat context

**Why it was added:** The chat widget was restoring up to 40 saved messages even though the agent uses a much shorter recent context, leaving old recommendations visible and sending more history than needed.

**How it helps shoppers and the business:** Load only the most relevant recent turns from the database instead of repeatedly sending a large history from the browser. This can reduce request size and keep older product cards from distracting the agent. FastAPI uses the same latest eight message rows for agent context and restored chat display; older messages remain safely stored in `chat_messages`. Guest chat remains available with a small, bounded in-memory history, and guest turns are not saved to the database.
