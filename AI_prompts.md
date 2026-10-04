# AI Prompts — Homework 4

This file records the prompts used while completing Homework 4. Add each problem in the format below as work progresses.

## Problem [number]: [title]

### First prompt

> [Paste the first prompt exactly as typed, word-for-word.]

### What was lacking after the first prompt

[Write one sentence explaining what was missing, unclear, or needed improvement after the first prompt.]

### Follow-up prompt

> [Paste the follow-up prompt exactly as typed, word-for-word, if one was needed.]

## Problem 2: Analyze the database

### First prompt

> In a new file output/harness.md write down each table and its fields, and one short line on why each field matters for the shop or the chatbot

### What was lacking after the first prompt

Nothing was lacking after the first prompt; it specified the output file, the database information to include, and the required explanation for each field.

### Follow-up prompt

None.

## Problem 3: Build the Campus Customs website

### First prompt

> Now I’mm working on “Problem 3: Build the Campus Customs website” I need to scaffold a React + Vite + TypeScript front end for Campus Customs. I will need to put a nav bar at the top of the site that links to the main pages 
>
> - Home
> - Products
> - About Us
> - Log in
> - Create Account
>
> Pull from Customs-style wording from [https://yalebulldogblue.com](https://yalebulldogblue.com) for Home and About Us, but write these pages in your own voice (do not copy the original site text). On the products page, show product images from the catalogue (use the image paths in the database) with basic product information (name, price, short description). Make each product open a single-item page (large image on one side, full product text on the other - description, price, size/stock when you have them). Clicking a card on Products should take the shopper there. Also, add a chat interface in the bottom right of the site (a floating chat panel is fine). It does not need to talk to an agent yet - please just create a stub that will call my backend later for this problem. I will also need a small API soon to read the database. It is fine to start a simple FastAPI app in backend/main.py just to serve products and images, then I will grow it into the agent backend in problem 5. Is there anything outside of this prompt that I need to download to build these pages?

### What was lacking after the first prompt

The prompt provided the page requirements and data source; the remaining work was to choose the project structure, visual direction, and development dependencies.

### Follow-up prompt

> ok it works now thanks. Can you make a more more stylish frontent that looks like the attached image while not changing the the tabs and page layout and only using different shades of blue and black for the text and icons. Also, change the layers and clue narrative it is confusing. Be more direct about what the site is for

> ok can you do it?

> ok manually, "Berkeley Sweater Fleece Jacket" has gray  · red · white, "Benjamin Frank T-shirt" has gray · blue · red · white, and "Timothy Dwight College Crewneck" has grey red white. please update and hid the vision block text

## Problem 4: Create account and login

### First prompt

> Now I’m working on “Problem 4: Create account and login”. Build a normal create-account / login flow.
>
> - Create account: first name, last name, email, password (confirm password is a nice touch)
> - Log in: email and password.
>
> New accounts will go into the users table. Make sure to store passwords securely so hackers (human or AI) cannot access them. The seed database already has a test user you can use while building:
>
> - Email: [test@campuscustoms.yale.edu](mailto:test@campuscustoms.yale.edu)
> - Password: password
>
> Confirm you can log in as that user, and that a brand new-account you create also works. Update output/harness.md with how auth works (what you store for a user and how passwords are protected)

### What was lacking after the first prompt

The first prompt did not specify a session strategy or a password-hashing format, so those choices still needed to be made and implemented after the prompt.

### Follow-up prompt

None yet.

## Problem 5: PydanticAI agent backend

### First prompt

> Now I’m working on “Problem 5: PydanticAI agent backend”. Build the shop chatbot as a PydanticAI agent behind FastAPI, plugged into the front-end chat widget. Put the API app in backend/main.py — this is the file that I will run with Uvicorn. Keep the agent as these four files next to it (same idea as Homework 3):
>
> - Backend/prompts/prompt.md — system prompt (grow this same file later)
> - Backend/agent.py — (agent entry / wiring)
> - Backend/tools.py — tools the agent can call
> - Backend/models.py — Pydantic / PydanticAI structured types
>
> In main.py, expose a chat route so a message from the website returns a reply from the agent (and whatever else you need for prodcuts/auth). I will need my AI model API key for the agent. Also, put Campus Customs voice and safety basics into prompts/prompt.md (I will expand tools and safety later). Start or update types in models.py for chat replies / product cards as needed. In output/harness.md, note how the front end talks to FastAPI and how the agent is loaded (prompt file + model). The backend bus run from the backend/ folder like this “uvicorn main:app --reload --port 8000”

### What was lacking after the first prompt

The agent code was complete, but I still needed terminal instructions that selected Homework 4's virtual environment so the required `uvicorn` command would work.

### Follow-up prompt

> I need to be able to run this in the terminal or I will get all points off for my homework. Why isn't it working?

## Problem 6: Tools: product info and stock

### First prompt

> Ok now I’m working in “Problem 6: Tools: product info and stock”.  Now I need to give the agent tools to look up real information from campus_customs.db
>
> - product_description()
>   - Main color
>   - Accent colors
>   - Sleeve_length(short or long)
>   - clothing_type(hoodie, fleece, t-shirt, sweater, etc.)
> - price()
> - stock()
>   - How many are in stock (by size when the customer asks)
>
> The agent must use the database — it should not invent prices or quantities. If a size is out of stock, make sure to say so clearly. Update these tools in prompts/prompts.md for the agent, so it knows to call these tools for price and stock questions. Add or update return types in models.py. In output/harness.md, list each tool and explain which model fields you chose for lookup results and why

### What was lacking after the first prompt

The database lacked separate columns for main color, accent colors, and sleeve length, so the lookup rules needed to derive those fields carefully and show when sleeve length was inferred.

### Follow-up prompt

> are there any products on this site that can't determine sleeve length? 

## Problem 7: Chat search that updates the page

### First prompt

> Now I’m working in “Problem 7: Chat search that updates the page”.  Now, I’m going to add a really cool feature to the site! When a customer asks about a type of item (e.g. “What hoodies do you have?”), the agent will search the catalogue and the website should dynamically show those matching items as product cards (image, name, price, short info). This will be an API contract: the agent returns structured product matches and then the front end renders them on the website. Let’s make sure this looks really cool. After we finish this and the dynamic product cards are loaded by the new feature, make sure the same single-item page behavior that was created in Problem 3 still works: each product card, including the ones the chat just put on the page, should still open that detail view (large image + full info) when clicked. Update prompts/prompt.md and output/harness.md, so it is clear how search results reach the page.

### What was lacking after the first prompt

The existing chat response had product cards only inside the floating chat panel, so the page needed shared state and a page-level results section to display search matches dynamically.

### Follow-up prompt

None yet.

## Problem 8: Customer memory

### First prompt

> Now I’m working in “Problem 8: Customer memory”. When a shopper is logged in, save their chat history in the database in an appropriate table answer reload it when they return. The agent should know who is chatting (name, email); put that in agent deps (or an equivalent clear pattern) and/or tools the agent can call. Also, pass enough page context that if someone is on a product page and asks “do you have this in orange?”, the agent knows which item they mean. To help accomplish this task you can put code into the agent context. Also, guests can still chat, however there is only history saved for logged-in users. Document these updates in output/harness.md: how the chat history is stored, what customer fields the agent sees, and how page context is passed

### What was lacking after the first prompt

The API passed current-page context to the agent, but the search behavior did not distinguish factual questions about the open item from requests for a related product type. Pinning every “this” search to the open item prevented a request for a T-shirt alternative from finding the separate Morse T-shirt listing.

### Follow-up prompts

> how do it make it so that there is enough page context that if someone is on a product page and asks "do you have this in white", the agent knows which item I mean

> why can't the agent identity the t-shirt option

> can you fix this for me

> I'm not logged in but the chatbot should still be able to answer me

## Problem 9: Usability improvements

### First prompt

> Ok, now I’m working in “Problem 9: Usability improvements”. The core shop works, thanks! Now I want to make it even better. Please give me some options to choose and implement for:
>
> - Front-end usability improvements, and
> - Agent / backend usability improvements
>
> Front-end improvements are things that will make the site look better and make it easier to use. Agent / backend improvements are things that men the agent output better, more accurate, or safer. These could be new agent tools or things that make the agent run faster or cheaper. Do do anything yet, just give me some ideas

### What was lacking after the first prompt

The first request asked for ideas only and did not select which improvements to implement; the follow-up chose two front-end and two backend improvements and specified the required documentation and running-app outcome.

### Follow-up prompt

> For front-end improvements do #1 and #3. For agent and backend improvements do #1 and #4. Write output/usability.md before you build. For each improvement, say:
>
> - Why it was added,
> - how it helps a campus customs shopper or business
>
> Then make sure all improvements actually show up in the running app

## Problem 10: Style the website

### First prompt

> Now I’m working on “Problem 10: Style the website”. Give the option that the shopper can turn on dark or light mode for the website and make the cursor on the page a little dan the bulldog. Also, in the chat box when it is thinking, show dan the bulldog running across the chat. Also, for the white apparel on this page outline only the clothing item in black so it is easier to view. Overall for the site’s background add an illustrated wallpaper of bulldogs. Make sure everything looks neat and modern though and is not overwhelming

### What was lacking after the first prompt

The first styling pass used a faint generic Bulldog motif and a mascot-face cursor, and it outlined products whenever white appeared anywhere in the color list without removing baked-in image backdrops; it needed to match the reference more closely and distinguish white garments from the surrounding image background. The loading Bulldog also moved back and forth too quickly for comfortable viewing.

### Follow-up prompt

> make the background look more like this and male the cursor look better. Also, fix the black box around some of the items (see attached), and get rid of the white boxes around some the items when in dark in mode (see attached). Also, for the white t-shirts like the one attached keep it white, dont make the item's content itself be transparent

## Problem 11: Site testing (app check)

### First prompt

> Now I’m working in “Problem 11: Site testing (app check)”. Test the live site and document it in output/app_check.html (a page you can double-click open). Include clear screenshots and short captions for: (don’t make the screenshots and add the captions just create the outline for now)
>
> 1. Chat checking the inventory level of an item (honest stock/price from the DB)
> 2. The dynamic search-result cards appearing after a category question (e.g. hoodies)
> 3. One of the usability features you added in Problem 9
>
> Make sure the HTML is easy to grade: heading for each check, screenshot, one or two sentences on what the screenshot proves. Put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example, app_check_images/inventory.png)

### What was lacking after the first prompt

The first prompt requested only an outline, so the actual screenshots and proof captions still needed to be added after the evidence was ready.

### Follow-up prompts

> For Check #1 add the attached image (rename to inventory.png) and add the following caption. Also, put the screenshot image file in output/app_check_images/ and link them from app_check.html with relative paths:
> I asked the chatbot, “What is the cost and stock for the Yale Mom crewneck?” And it told me the cost, total stock, and size options and their respective stocks

> For Check #2 add the following caption. Also, link dyanmic_search_results_card from app_check.html with relative paths:
> I asked the chatbot, “can you show me all the hoodies you have?” and it showed all the possibilities in the chat and added a “Found Through Chat: Products that match your question” section on the site

> For Check #3 add the following caption. Also, link usability_improvement from app_check.html with relative paths:
> I added a filter section to the site so it is easier for shoppers to locate products of interests out of 102 total products. The screenshot shows filtering the items by “dusty coral”

> can you make check #1 a little smaller, more comparable to the check #2 and #3 size?

## Problem 12: Audit trail, safety, finish harness

### First prompt

> Now I’m working in “Problem 12: Audit trail, safety, finish harness”. Keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/results, stop reason). Do not wipe it between runs. Also, add some important safety rules to give the agent (e.g. don’t invent data, don’t use a person’s personal data without their permission - keep passwords safe, etc.) and put them in prompts/prompt.md. Finish output/harness.md so it is clear how the system works, explaining clearly the following:
>
> - Model fields in models.py and why they were chosen
> - Tools and abilities
> - Safety rules
>
> Specs (loop limits, result caps, models, how to run front + back)

### What was lacking after the first prompt

The first prompt covered the audit trail, safety rules, and harness documentation, but did not ask for regression checks that multi-color searches treat requested colors as alternatives or that the assistant's answer matches an empty search result.

### Follow-up prompts

> what is happening?

> can you fix this?
