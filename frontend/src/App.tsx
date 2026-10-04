import { FormEvent, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  Link,
  NavLink,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
} from "react-router-dom";
import { ApiError, fetchChatHistory, fetchProduct, fetchProducts, loginUser, productImageUrl, registerUser, sendChatMessage } from "./api";
import type { Product } from "./types";

type ChatMessage = {
  from: "assistant" | "user";
  text: string;
  products?: Product[];
  contextProductId?: string;
};

function formatPrice(price: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(price);
}

function cleanProductDescription(product: Product): string {
  if (/vision blocked|filename-based stub/i.test(product.description)) {
    return `${product.name} from the Campus Customs catalogue.`;
  }
  return product.description;
}

function hasLightGarmentColor(product: Product): boolean {
  const mainColor = product.colors[0]?.trim().toLocaleLowerCase();
  return ["white", "ivory", "cream", "off-white"].includes(mainColor ?? "");
}

type ThemeMode = "light" | "dark";

function savedTheme(): ThemeMode {
  try {
    return localStorage.getItem("campus_customs_theme") === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

function productCategory(product: Product): string {
  const type = `${product.garment_type} ${product.name}`.toLocaleLowerCase();
  if (/\bt\s?-?\s?shirt\b|\bt-?shirt\b|\btees?\b/.test(type)) return "T-shirt";
  if (/hoodie|hooded/.test(type)) return "Hoodie";
  if (/quarter[ -]?zip|1[ /-]?4[ -]?zip/.test(type)) return "Quarter-zip";
  if (/crew ?neck|sweatshirt/.test(type)) return "Sweatshirt";
  if (/sweater/.test(type)) return "Sweater";
  if (/fleece/.test(type)) return "Fleece";
  if (/jacket/.test(type)) return "Jacket";
  if (/shirt/.test(type)) return "Shirt";
  return product.garment_type || "Other";
}

function LoadingMessage({ label = "Loading products" }: { label?: string }) {
  return <p className="status-message">{label}<span className="loading-dots">...</span></p>;
}

function BulldogWallpaper() {
  return (
    <svg className="bulldog-wallpaper" aria-hidden="true" focusable="false" viewBox="0 0 320 240" preserveAspectRatio="xMidYMid slice">
      <defs>
        <pattern id="bulldog-wallpaper-pattern" width="320" height="240" patternUnits="userSpaceOnUse">
          <text className="wallpaper-word" x="9" y="36" fontSize="35" transform="rotate(7 9 36)">YALE</text>
          <text className="wallpaper-y" x="224" y="112" fontSize="106">Y</text>
          <g className="wallpaper-dog" transform="translate(47 58) scale(.82)">
            <path d="M22 26C14 20 10 10 13 3c9 2 15 7 18 14 8-4 19-4 27 0 3-7 9-12 18-14 4 8 0 17-8 23 5 10 4 23-2 32-6 9-15 13-25 13S21 65 16 56c-6-10-5-22 6-30Z" />
            <path d="M27 35c3-3 7-3 10 0m13 0c3-3 7-3 10 0M31 48c6-7 23-7 29 0-2 8-8 12-15 12S33 56 31 48Z" />
            <path d="M39 47c2-3 11-3 13 0l-2 4H41l-2-4Zm7 5v4m-6 3c4 3 8 3 12 0M30 65l-3 5m28-5 3 5" />
          </g>
          <text className="wallpaper-word" x="156" y="171" fontSize="27" transform="rotate(-29 156 171)">YALE</text>
          <g className="wallpaper-pennant" transform="rotate(-8 240 198)">
            <path d="M205 176 296 185 205 222Z" />
            <text className="wallpaper-pennant-text" x="212" y="196" fontSize="13">YALE</text>
          </g>
          <g className="wallpaper-dog" transform="translate(39 170) rotate(-10) scale(.42)">
            <path d="M22 26C14 20 10 10 13 3c9 2 15 7 18 14 8-4 19-4 27 0 3-7 9-12 18-14 4 8 0 17-8 23 5 10 4 23-2 32-6 9-15 13-25 13S21 65 16 56c-6-10-5-22 6-30Z" />
            <path d="M27 35c3-3 7-3 10 0m13 0c3-3 7-3 10 0M31 48c6-7 23-7 29 0-2 8-8 12-15 12S33 56 31 48Z" />
            <path d="M39 47c2-3 11-3 13 0l-2 4H41l-2-4Zm7 5v4m-6 3c4 3 8 3 12 0" />
          </g>
        </pattern>
      </defs>
      <rect className="wallpaper-base" width="100%" height="100%" />
      <rect width="100%" height="100%" fill="url(#bulldog-wallpaper-pattern)" />
    </svg>
  );
}

function DanRunner() {
  return (
    <svg className="dan-runner" aria-hidden="true" focusable="false" viewBox="0 0 112 64">
      <path className="runner-tail" d="M25 31c-10-2-16-10-12-17 7 2 12 6 15 13" />
      <path className="runner-body" d="M24 28c11-9 35-10 52-4 8 5 10 16 3 22-13 8-37 9-53 2-9-4-12-13-2-20Z" />
      <path className="runner-spot" d="M37 27c5-2 12-2 18-1-4 5-6 10-5 16-8 1-13-4-13-15Z" />
      <path className="runner-leg runner-leg-back" d="M37 47 31 59m19-9-2 10" />
      <path className="runner-leg" d="M66 48 73 59m-29-10-4 11" />
      <path className="runner-ear" d="M79 22c-5-6-6-14-1-18 7 3 11 10 10 18m11 1c2-8 7-12 12-10 1 8-2 14-8 18" />
      <path className="runner-head" d="M75 19c9-7 22-6 30 2 6 6 8 18 3 27-4 7-12 10-22 8-13-2-20-11-19-22 0-6 3-12 8-15Z" />
      <path className="runner-collar" d="M75 24c-5 6-6 13-4 20" />
      <circle className="runner-tag" cx="72" cy="45" r="3" />
      <path className="runner-muzzle" d="M78 39c4-5 9-7 15-6 6-1 12 2 15 7-1 9-6 14-15 14-10 0-15-6-15-15Z" />
      <circle className="runner-eye" cx="84" cy="31" r="2.2" />
      <circle className="runner-eye" cx="100" cy="31" r="2.2" />
      <circle className="runner-eye-shine" cx="84.5" cy="30.5" r=".7" />
      <circle className="runner-eye-shine" cx="100.5" cy="30.5" r=".7" />
      <path className="runner-nose" d="M89 40c2-3 8-3 10 0-1 3-3 4-5 4s-4-1-5-4Z" />
      <path className="runner-mouth" d="M94 44v3m-7 0c3 4 11 4 14 0" />
    </svg>
  );
}

function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="error-message">
      <strong>The catalogue is unavailable.</strong>
      <span>{message}</span>
      <small>Start the FastAPI server and refresh this page.</small>
    </div>
  );
}

function Header({ theme, onToggleTheme }: { theme: ThemeMode; onToggleTheme: () => void }) {
  const navItems = [
    ["Home", "/"],
    ["Products", "/products"],
    ["About Us", "/about"],
    ["Log in", "/login"],
    ["Create Account", "/create-account"],
  ];

  return (
    <header className="site-header">
      <Link className="brand" to="/" aria-label="Campus Customs home">
        <span className="brand-mark">CC</span>
        <span>
          <strong>Campus Customs</strong>
          <small>Yale apparel, clearly organized</small>
        </span>
      </Link>
      <nav className="main-nav" aria-label="Main navigation">
        {navItems.map(([label, path]) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}
            end={path === "/"}
          >
            {label}
          </NavLink>
        ))}
        <button
          className="theme-toggle"
          type="button"
          onClick={onToggleTheme}
          aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
        >
          <span aria-hidden="true">{theme === "light" ? "◐" : "☼"}</span>
          {theme === "light" ? "Dark" : "Light"}
        </button>
      </nav>
    </header>
  );
}

function Footer() {
  return (
    <footer className="site-footer">
      <div>
        <strong>Campus Customs</strong>
        <p>Yale apparel, without the guesswork.</p>
      </div>
      <span>Prototype storefront · Yale apparel catalogue</span>
    </footer>
  );
}

function ChatWidget({ onProducts }: { onProducts: (products: Product[]) => void }) {
  const messagesRef = useRef<HTMLDivElement>(null);
  const location = useLocation();
  const productPageMatch = location.pathname.match(/^\/products\/([^/]+)$/);
  const currentProductId = productPageMatch
    ? decodeURIComponent(productPageMatch[1])
    : undefined;
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [loadedToken, setLoadedToken] = useState<string | null>(null);
  const [chatNotice, setChatNotice] = useState("");
  const [contextProduct, setContextProduct] = useState<Product | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { from: "assistant", text: "Hi! I’m the Campus Customs shopping assistant. Ask me about a product, size, or color." },
  ]);

  useLayoutEffect(() => {
    if (open && messagesRef.current) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [open, messages, busy]);

  useEffect(() => {
    let cancelled = false;
    setContextProduct(null);
    if (!currentProductId) return;
    fetchProduct(currentProductId)
      .then((product) => {
        if (!cancelled) setContextProduct(product);
      })
      .catch(() => {
        if (!cancelled) setContextProduct(null);
      });
    return () => {
      cancelled = true;
    };
  }, [currentProductId]);

  useEffect(() => {
    if (!open) return;
    const accessToken = sessionStorage.getItem("campus_customs_access_token");
    if (!accessToken || accessToken === loadedToken) return;
    setLoadedToken(accessToken);
    fetchChatHistory(accessToken)
      .then((history) => {
        setChatNotice("");
        const latestProducts = [...history.messages]
          .reverse()
          .find((message) => message.products && message.products.length > 0)?.products ?? [];
        onProducts(latestProducts);
        if (history.messages.length === 0) return;
        setMessages([
          { from: "assistant", text: "Welcome back. Here is your saved Campus Customs conversation." },
          ...history.messages.map((message) => ({
            from: message.role,
            text: message.content,
            products: message.products,
          })),
        ]);
      })
      .catch((reason: unknown) => {
        if (reason instanceof ApiError && reason.status === 401) {
          if (sessionStorage.getItem("campus_customs_access_token") === accessToken) {
            sessionStorage.removeItem("campus_customs_access_token");
            sessionStorage.removeItem("campus_customs_user");
          }
          setChatNotice("Your saved session expired. You can keep chatting as a guest; log in again to reload saved messages.");
          return;
        }
        setMessages((current) => [
          ...current,
          { from: "assistant", text: "I could not load your saved chat history. You can still start a new conversation." },
        ]);
      });
  }, [open, loadedToken]);

  const pageContext = {
    path: location.pathname,
    ...(currentProductId
      ? { current_product_id: currentProductId }
      : {}),
  };

  function productGroups(message: ChatMessage): { label: string; products: Product[] }[] {
    if (!message.products?.length) return [];
    const currentItem = message.contextProductId
      ? message.products.filter((product) => product.product_id === message.contextProductId)
      : [];
    const related = message.contextProductId
      ? message.products.filter((product) => product.product_id !== message.contextProductId)
      : message.products;
    return [
      ...(currentItem.length ? [{ label: "Current item", products: currentItem }] : []),
      ...(related.length
        ? [{ label: message.contextProductId ? "Related options" : "Products from this answer", products: related }]
        : []),
    ];
  }

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = draft.trim();
    if (!trimmed || busy) return;
    const accessToken = sessionStorage.getItem("campus_customs_access_token") ?? undefined;
    const history = accessToken ? undefined : messages.map((message) => ({
      role: message.from,
      content: message.text,
      product_ids: (message.products ?? []).map((product) => product.product_id),
    })).slice(-8);
    setMessages((current) => [
      ...current,
      { from: "user", text: trimmed },
    ]);
    setDraft("");
    setBusy(true);
    try {
      const response = await sendChatMessage({
        message: trimmed,
        ...(history ? { history } : {}),
        page_context: pageContext,
      }, accessToken);
      onProducts(response.products);
      setMessages((current) => [
        ...current,
        {
          from: "assistant",
          text: response.reply,
          products: response.products,
          contextProductId: currentProductId,
        },
      ]);
    } catch (reason) {
      onProducts([]);
      const detail = reason instanceof Error ? reason.message : "Please try again in a moment.";
      setMessages((current) => [
        ...current,
        { from: "assistant", text: `I couldn't get an answer just now. ${detail}` },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={open ? "chat-widget open" : "chat-widget"}>
      {open && (
        <section className="chat-panel" aria-label="Campus Customs chat">
          <div className="chat-header">
            <div>
              <span className="online-dot" />
              <strong>Shopping assistant</strong>
            </div>
            <button className="icon-button" onClick={() => setOpen(false)} aria-label="Close chat">×</button>
          </div>
          <div className="chat-context">
            <div className="chat-context-copy">
              <small>{currentProductId ? "ASKING ABOUT" : "SHOPPING CONTEXT"}</small>
              <strong>
                {currentProductId
                  ? contextProduct?.name ?? "Loading product details…"
                  : location.pathname === "/products" ? "Browsing the catalogue" : "General shopping"}
              </strong>
              {contextProduct && <span>{contextProduct.garment_type}</span>}
            </div>
            {contextProduct && (
              <Link className="chat-context-link" to={`/products/${encodeURIComponent(contextProduct.product_id)}`}>
                View item
              </Link>
            )}
          </div>
          {chatNotice && <p className="chat-session-notice" role="status">{chatNotice}</p>}
          <div className="chat-messages" ref={messagesRef}>
            {messages.map((message, index) => (
              <div key={`${message.from}-${index}`} className={`chat-message ${message.from}`}>
                <p className={`chat-bubble ${message.from}`}>{message.text}</p>
                {productGroups(message).map((group) => (
                  <div className="chat-product-group" key={group.label}>
                    <small className="chat-products-label">{group.label}</small>
                    <div className="chat-products" aria-label={group.label}>
                      {group.products.map((product) => (
                        <Link
                          className="chat-product-card"
                          key={product.product_id}
                          to={`/products/${encodeURIComponent(product.product_id)}`}
                          onClick={() => setOpen(false)}
                        >
                          <img className={hasLightGarmentColor(product) ? "white-apparel-image" : undefined} src={productImageUrl(product.image_url)} alt="" />
                          <span><strong>{product.name}</strong><small>{formatPrice(product.price)}</small></span>
                        </Link>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ))}
            {busy && (
              <div className="chat-thinking" role="status" aria-live="polite">
                <div className="dan-run-track"><DanRunner /></div>
                <span><strong>Handsome Dan</strong> is checking the catalogue…</span>
              </div>
            )}
          </div>
          <form className="chat-form" onSubmit={sendMessage}>
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask a question..."
              aria-label="Chat message"
              disabled={busy}
            />
            <button className="send-button" type="submit" disabled={busy || !draft.trim()} aria-label="Send message">↑</button>
          </form>
          <small className="stub-note">Answers use the current product catalogue and inventory.</small>
        </section>
      )}
      {!open && (
        <button className="chat-launcher" onClick={() => setOpen(true)}>
          <span className="chat-spark">✦</span>
          Chat with us
        </button>
      )}
    </div>
  );
}

function ChatResults({ products }: { products: Product[] }) {
  if (products.length === 0) return null;
  return (
    <section className="chat-results page-width" aria-live="polite" aria-label="Products found by the shopping assistant">
      <div className="chat-results-heading">
        <div>
          <p className="eyebrow">Found through chat</p>
          <h2>Products that match your question.</h2>
        </div>
        <p>Click any card to open its full product page with description, colors, price, and size stock.</p>
      </div>
      <div className="product-grid">
        {products.map((product) => <ProductCard key={product.product_id} product={product} />)}
      </div>
    </section>
  );
}

function PageLayout({ children }: { children: React.ReactNode }) {
  const [chatProducts, setChatProducts] = useState<Product[]>([]);
  const [theme, setTheme] = useState<ThemeMode>(savedTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("campus_customs_theme", theme);
    } catch {
      // The theme still works for this visit when browser storage is unavailable.
    }
  }, [theme]);

  return (
    <>
      <BulldogWallpaper />
      <Header theme={theme} onToggleTheme={() => setTheme((current) => current === "light" ? "dark" : "light")} />
      <main>
        <ChatResults products={chatProducts} />
        {children}
      </main>
      <Footer />
      <ChatWidget onProducts={setChatProducts} />
    </>
  );
}

function HomePage() {
  return (
    <div>
      <section className="hero page-width">
        <div className="hero-copy">
          <p className="eyebrow">Campus Customs · Yale apparel</p>
          <h1>Yale merchandise, all in one place.</h1>
          <p className="hero-text">
            Campus Customs is an online shop for Yale apparel. Browse shirts,
            hoodies, crewnecks, and other campus favorites, then compare the
            details, sizes, prices, and available stock before you buy.
          </p>
          <div className="button-row">
            <Link className="button primary" to="/products">Shop products</Link>
            <Link className="button secondary" to="/about">About Campus Customs</Link>
          </div>
        </div>
        <div className="hero-card" aria-label="Campus Customs apparel collection">
          <span className="hero-sticker">YALE GEAR</span>
          <div className="hero-orbit orbit-one" />
          <div className="hero-orbit orbit-two" />
          <div className="hero-card-content">
            <span className="hero-card-label">The Yale apparel shop</span>
            <strong>Find your<br />Yale gear.</strong>
            <span className="hero-card-footer">Browse · Compare · Choose</span>
          </div>
        </div>
      </section>

      <section className="feature-strip page-width">
        <article><span>01</span><h2>Shop Yale merchandise</h2><p>Find shirts, hoodies, crewnecks, jackets, and other apparel in one easy-to-browse catalogue.</p></article>
        <article><span>02</span><h2>Compare the details</h2><p>See product images, descriptions, prices, sizes, and stock before choosing what belongs in your bag.</p></article>
        <article><span>03</span><h2>Get help when you need it</h2><p>Ask the shopping assistant about products, colors, prices, and current size availability.</p></article>
      </section>
    </div>
  );
}

function ProductCard({ product }: { product: Product }) {
  return (
    <Link className="product-card" to={`/products/${encodeURIComponent(product.product_id)}`}>
      <div className="product-image-wrap">
        <img className={hasLightGarmentColor(product) ? "white-apparel-image" : undefined} src={productImageUrl(product.image_url)} alt={product.name} />
        <span className="product-type">{product.garment_type}</span>
      </div>
      <div className="product-card-body">
        <div>
          <h2>{product.name}</h2>
          <p>{cleanProductDescription(product)}</p>
        </div>
        <strong>{formatPrice(product.price)}</strong>
      </div>
    </Link>
  );
}

function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [colorFilter, setColorFilter] = useState("all");
  const [availabilityFilter, setAvailabilityFilter] = useState("all");
  const [sortBy, setSortBy] = useState("name");

  useEffect(() => {
    fetchProducts().then(setProducts).catch((reason: Error) => setError(reason.message));
  }, []);

  const categories = [...new Set(products.map(productCategory))].sort((a, b) => a.localeCompare(b));
  const colors = [...new Set(products.flatMap((product) => product.colors[0] ? [product.colors[0]] : []))]
    .sort((a, b) => a.localeCompare(b));
  const normalizedSearch = search.trim().toLocaleLowerCase();
  const filteredProducts = products
    .filter((product) => {
      const searchableText = [
        product.name,
        product.description,
        product.garment_type,
        ...product.search_tags,
        ...product.colors,
      ].join(" ").toLocaleLowerCase();
      if (normalizedSearch && !searchableText.includes(normalizedSearch)) return false;
      if (typeFilter !== "all" && productCategory(product) !== typeFilter) return false;
      if (colorFilter !== "all" && product.colors[0]?.toLocaleLowerCase() !== colorFilter) return false;
      if (availabilityFilter === "in-stock" && product.total_stock <= 0) return false;
      if (availabilityFilter === "out-of-stock" && product.total_stock > 0) return false;
      return true;
    })
    .sort((left, right) => {
      if (sortBy === "price-low") return left.price - right.price || left.name.localeCompare(right.name);
      if (sortBy === "price-high") return right.price - left.price || left.name.localeCompare(right.name);
      return left.name.localeCompare(right.name);
    });

  function clearFilters() {
    setSearch("");
    setTypeFilter("all");
    setColorFilter("all");
    setAvailabilityFilter("all");
    setSortBy("name");
  }

  return (
    <section className="page-width page-section">
      <div className="section-heading">
        <div><p className="eyebrow">The catalogue</p><h1>Browse Yale merchandise.</h1></div>
        <p>Search, filter, and compare. Open any card for full product details and size stock.</p>
      </div>
      {error && <ErrorMessage message={error} />}
      {!error && products.length === 0 && <LoadingMessage />}
      {products.length > 0 && (
        <>
          <div className="catalogue-controls" aria-label="Catalogue search and filters">
            <label className="catalogue-search">
              <span>Search products</span>
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Name, college, or keyword"
              />
            </label>
            <label>
              <span>Item type</span>
              <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
                <option value="all">All types</option>
                {categories.map((category) => <option key={category} value={category}>{category}</option>)}
              </select>
            </label>
            <label>
              <span>Main color</span>
              <select value={colorFilter} onChange={(event) => setColorFilter(event.target.value)}>
                <option value="all">All colors</option>
                {colors.map((color) => <option key={color} value={color.toLocaleLowerCase()}>{color}</option>)}
              </select>
            </label>
            <label>
              <span>Availability</span>
              <select value={availabilityFilter} onChange={(event) => setAvailabilityFilter(event.target.value)}>
                <option value="all">All items</option>
                <option value="in-stock">In stock</option>
                <option value="out-of-stock">Out of stock</option>
              </select>
            </label>
            <label>
              <span>Sort by</span>
              <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
                <option value="name">Name, A–Z</option>
                <option value="price-low">Price, low to high</option>
                <option value="price-high">Price, high to low</option>
              </select>
            </label>
          </div>
          <div className="catalogue-results-summary" aria-live="polite">
            <span>Showing {filteredProducts.length} of {products.length} products</span>
            <button type="button" className="text-button" onClick={clearFilters}>Clear filters</button>
          </div>
        </>
      )}
      <div className="product-grid">
        {filteredProducts.map((product) => <ProductCard key={product.product_id} product={product} />)}
      </div>
      {products.length > 0 && filteredProducts.length === 0 && (
        <div className="catalogue-empty">
          <strong>No products match those filters.</strong>
          <span>Try a different keyword or clear the filters to browse the full catalogue.</span>
          <button type="button" className="button secondary" onClick={clearFilters}>Clear filters</button>
        </div>
      )}
    </section>
  );
}

function ProductDetailPage() {
  const { productId } = useParams();
  const [product, setProduct] = useState<Product | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!productId) return;
    fetchProduct(productId).then(setProduct).catch((reason: Error) => setError(reason.message));
  }, [productId]);

  if (error) return <section className="page-width page-section"><ErrorMessage message={error} /></section>;
  if (!product) return <section className="page-width page-section"><LoadingMessage label="Opening the product file" /></section>;

  const availableSizes = product.inventory.filter((item) => item.quantity > 0);
  return (
    <section className="page-width page-section detail-page">
      <Link className="back-link" to="/products">← Back to products</Link>
      <div className="detail-layout">
        <div className="detail-image-wrap"><img className={hasLightGarmentColor(product) ? "white-apparel-image" : undefined} src={productImageUrl(product.image_url)} alt={product.name} /></div>
        <div className="detail-copy">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>
          <p className="detail-description">{cleanProductDescription(product)}</p>
          <div className="detail-block"><span className="detail-label">Colors</span><p>{product.colors.join(" · ") || "See product image"}</p></div>
          <div className="detail-block"><span className="detail-label">Size & stock</span>
            {availableSizes.length ? <div className="size-list">{availableSizes.map((item) => <span key={item.size}>{item.size} <b>{item.quantity}</b></span>)}</div> : <p>Currently out of stock</p>}
          </div>
          <button className="button primary wide" type="button">Add to bag <span>→</span></button>
          <small className="stub-note">Cart and checkout will be connected in a later problem.</small>
        </div>
      </div>
    </section>
  );
}

function AboutPage() {
  return (
    <section className="page-width page-section about-page">
      <div className="about-intro"><p className="eyebrow">About Campus Customs</p><h1>A straightforward shop for Yale apparel.</h1><p>Campus Customs makes it easier to find Yale shirts, sweatshirts, hoodies, jackets, and other campus merchandise. The catalogue brings product information and stock together so shoppers can make a confident choice.</p></div>
      <div className="about-grid"><article><span className="number-badge">01</span><h2>A clear catalogue</h2><p>Browse the collection with product images, names, descriptions, prices, and search-friendly details in one place.</p></article><article><span className="number-badge">02</span><h2>Useful information</h2><p>Open any product to check its full description, available sizes, and current inventory before you decide.</p></article><article><span className="number-badge">03</span><h2>Helpful shopping support</h2><p>Ask the Campus Customs assistant to find items and answer questions using the current catalogue and inventory.</p></article></div>
    </section>
  );
}

function AuthPage({ mode }: { mode: "login" | "create" }) {
  const navigate = useNavigate();
  const isLogin = mode === "login";
  const [submitted, setSubmitted] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted("");
    setError("");
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "").trim();
    const password = String(form.get("password") ?? "");
    setBusy(true);
    try {
      const result = isLogin
        ? await loginUser({ email, password })
        : await registerUser({
            first_name: String(form.get("first_name") ?? "").trim(),
            last_name: String(form.get("last_name") ?? "").trim(),
            email,
            password,
            confirm_password: String(form.get("confirm_password") ?? ""),
          });
      sessionStorage.setItem("campus_customs_access_token", result.access_token);
      sessionStorage.setItem("campus_customs_user", JSON.stringify(result.user));
      setSubmitted(`${isLogin ? "Logged in" : "Account created"} for ${result.user.name}.`);
      if (isLogin) navigate("/");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to complete authentication");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page-width page-section auth-page">
      <div className="auth-card"><p className="eyebrow">{isLogin ? "Welcome back" : "Create an account"}</p><h1>{isLogin ? "Log in to your account." : "Create your Campus Customs account."}</h1><p className="muted">{isLogin ? "Your saved products and account details are waiting." : "Save favorites and make your next Yale apparel search easier."}</p>
        {submitted && <div className="success-message">{submitted}</div>}
        {error && <div className="error-message"><strong>Authentication could not be completed.</strong><span>{error}</span></div>}
        <form onSubmit={handleSubmit} className="auth-form">
          {!isLogin && <><label>First name<input name="first_name" required type="text" autoComplete="given-name" placeholder="Ada" /></label><label>Last name<input name="last_name" required type="text" autoComplete="family-name" placeholder="Lovelace" /></label></>}
          <label>Email<input name="email" required type="email" autoComplete="email" placeholder="you@yale.edu" /></label>
          <label>Password<input name="password" required minLength={8} type="password" autoComplete={isLogin ? "current-password" : "new-password"} placeholder="••••••••" /></label>
          {!isLogin && <label>Confirm password<input name="confirm_password" required minLength={8} type="password" autoComplete="new-password" placeholder="••••••••" /></label>}
          <button className="button primary wide" disabled={busy} type="submit">{busy ? "Working..." : isLogin ? "Log in" : "Create account"} <span>→</span></button>
        </form>
      </div>
    </section>
  );
}

function App() {
  return (
    <PageLayout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/products/:productId" element={<ProductDetailPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/create-account" element={<AuthPage mode="create" />} />
        <Route path="*" element={<HomePage />} />
      </Routes>
    </PageLayout>
  );
}

export default App;
