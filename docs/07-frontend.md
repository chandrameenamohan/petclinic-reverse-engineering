# 07 - Frontend Specification

## Overview

The Spring Petclinic frontend is an AngularJS 1.x Single Page Application (SPA) served as static files from the API Gateway. It uses UI-Router for client-side routing, Bootstrap for styling, and communicates with backend services through the gateway's API proxy endpoints.

**Location:** `spring-petclinic-api-gateway/src/main/resources/static/`
**Framework:** AngularJS 1.x with UI-Router
**CSS Framework:** Bootstrap (loaded via WebJars)
**Icons:** Font Awesome (loaded via WebJars)

---

## Application Structure

```
static/
  index.html                          # Main SPA shell
  css/
    petclinic.css                     # Custom styles (compiled from SCSS)
    header.css                        # Navbar styles
    responsive.css                    # Responsive breakpoints
    typography.css                    # Font definitions
  scss/                               # SCSS sources (not served)
  fonts/                              # Montserrat and Varela Round web fonts
  images/
    favicon.png
    pets.png                          # Welcome page hero image
    spring-pivotal-logo.png           # Footer logo
    platform-bg.png                   # Background
    spring-logo-dataflow.png          # Logo variants
  scripts/
    app.js                            # Main AngularJS module + routing
    genai/
      chat.js                         # Chatbot widget logic
    fragments/
      nav.html                        # Navigation bar template
      welcome.html                    # Welcome/home page template
      footer.html                     # Footer template
    owner-list/                       # Owners list view
    owner-details/                    # Owner detail view
    owner-form/                       # Add/edit owner view
    pet-form/                         # Add/edit pet view
    vet-list/                         # Veterinarians list view
    visits/                           # Add visit view
    infrastructure/                   # HTTP error interceptor
```

### AngularJS Module Structure

Each view is an AngularJS module with three files:
- `{name}.js` - Module definition and UI-Router state configuration
- `{name}.controller.js` - Controller with data fetching and form handling
- `{name}.component.js` - Component registration (binds template to controller)

Main module (`app.js`):
```javascript
var petClinicApp = angular.module('petClinicApp', [
    'ui.router', 'infrastructure', 'layoutNav', 'layoutFooter', 'layoutWelcome',
    'ownerList', 'ownerDetails', 'ownerForm', 'petForm', 'visits', 'vetList'
]);
```

Layout components (nav, footer, welcome) are auto-registered from `scripts/fragments/`.

---

## Routing Table

| State Name | URL Pattern | Component | Description |
|---|---|---|---|
| `welcome` | `/welcome` (default) | `<layout-welcome>` | Home page |
| `owners` | `/owners` | `<owner-list>` | List all owners |
| `ownerDetails` | `/owners/details/:ownerId` | `<owner-details>` | Owner detail with pets/visits |
| `ownerNew` | `/owners/new` | `<owner-form>` | Create new owner |
| `ownerEdit` | `/owners/:ownerId/edit` | `<owner-form>` | Edit existing owner |
| `petNew` | `/owners/:ownerId/new-pet` | `<pet-form>` | Add pet to owner |
| `petEdit` | `/owners/:ownerId/pets/:petId` | `<pet-form>` | Edit existing pet |
| `visits` | `/owners/:ownerId/pets/:petId/visits` | `<visits>` | Add visit to pet |
| `vets` | `/vets` | `<vet-list>` | List all veterinarians |

URL hash prefix: `!` (e.g., `#!/owners`)

Default route: `/welcome`

---

## Navigation Bar

**Template:** `scripts/fragments/nav.html`

Bootstrap dark navbar with 4 links:

| Label | Icon | Target | Description |
|---|---|---|---|
| Home | `fa-home` | `/` (root) | Home page |
| Find owners | `fa-search` | `ui-sref="owners"` | Owners list |
| Register owner | `fa-plus` | `ui-sref="ownerNew"` | New owner form |
| Veterinarians | `fa-th-list` | `ui-sref="vets"` | Vets list |

Active link highlighting via `ui-sref-active="active"`.

---

## Pages / Views

### 1. Welcome Page (Home)

**State:** `welcome`
**URL:** `#!/welcome`
**Template:** `scripts/fragments/welcome.html`
**API Calls:** None

```
+----------------------------------------------------------+
| [Navbar: Home | Find owners | Register | Veterinarians] |
+----------------------------------------------------------+
|                                                          |
|               Welcome to Petclinic                       |
|                                                          |
|              [  pets.png hero image  ]                   |
|                                                          |
+----------------------------------------------------------+
|              [Spring/Pivotal logo footer]                 |
+----------------------------------------------------------+
```

### 2. Owners List

**State:** `owners`
**URL:** `#!/owners`
**Controller:** `OwnerListController`
**API Call:** `GET api/customer/owners`

```
+----------------------------------------------------------+
| [Navbar]                                                  |
+----------------------------------------------------------+
|                                                          |
|  Owners                                                  |
|                                                          |
|  [____Search Filter____]                                 |
|                                                          |
|  +------+----------+----------+-----------+--------+     |
|  | Name | Address  | City     | Telephone | Pets   |     |
|  +------+----------+----------+-----------+--------+     |
|  | George Franklin  | 110 W...| Madison  | 608... | Leo  |
|  | (link to detail) |         |          |        |      |
|  | Betty Davis      | 638 C...| Sun Pr.. | 608... | Basil|
|  +------+----------+----------+-----------+--------+     |
|                                                          |
+----------------------------------------------------------+
```

**Features:**
- Client-side search filter (`ng-model="$ctrl.query"`) that filters across all columns
- Owner name is a link to `ownerDetails` state
- Pets column shows pet names (space-separated)
- Address column hidden on small/extra-small screens (`hidden-sm hidden-xs`)
- Pets column hidden on extra-small screens (`hidden-xs`)

### 3. Owner Details

**State:** `ownerDetails`
**URL:** `#!/owners/details/:ownerId`
**Controller:** `OwnerDetailsController`
**API Call:** `GET api/gateway/owners/{ownerId}`

Note: This calls the **gateway's aggregation endpoint** (not customer service directly) which merges owner data with visit data.

```
+----------------------------------------------------------+
| [Navbar]                                                  |
+----------------------------------------------------------+
|                                                          |
|  Owner Information                                       |
|                                                          |
|  +------------+---------------------------+              |
|  | Name       | George Franklin           |              |
|  | Address    | 110 W. Liberty St.        |              |
|  | City       | Madison                   |              |
|  | Telephone  | 6085551023                |              |
|  +------------+---------------------------+              |
|  | [Edit Owner]  [Add New Pet]            |              |
|  +----------------------------------------+              |
|                                                          |
|  Pets and Visits                                         |
|                                                          |
|  +---------------------------+------------------+        |
|  | Name: Leo (link to edit)  | Visit Date | Desc|        |
|  | Birth Date: 2010 Sep 07   | 2013 Jan 01|rabies|       |
|  | Type: cat                 |            |      |        |
|  |                           | [Edit Pet] | [Add Visit]  |
|  +---------------------------+------------------+        |
|  | Name: ...                 | ...              |        |
|  +---------------------------+------------------+        |
|                                                          |
+----------------------------------------------------------+
```

**Features:**
- Owner info displayed in a striped table
- "Edit Owner" button links to `ownerEdit` state
- "Add New Pet" button links to `petNew` state
- Each pet shown with name (link to `petEdit`), birth date (formatted `yyyy MMM dd`), type
- Visit history per pet: date + description
- "Edit Pet" and "Add Visit" links per pet

### 4. Owner Form (Add / Edit)

**State:** `ownerNew` (URL: `#!/owners/new`) or `ownerEdit` (URL: `#!/owners/:ownerId/edit`)
**Controller:** `OwnerFormController`
**API Calls:**
- **Edit mode:** `GET api/customer/owners/{ownerId}` to pre-populate form
- **Create:** `POST api/customer/owners` with owner data
- **Update:** `PUT api/customer/owners/{ownerId}` with owner data
- **After submit:** Navigate to `ownerDetails` (edit) or `owners` list (create)

```
+----------------------------------------------------------+
| [Navbar]                                                  |
+----------------------------------------------------------+
|                                                          |
|  Owner                                                   |
|                                                          |
|  First name  [________________]                          |
|              First name is required.                     |
|                                                          |
|  Last name   [________________]                          |
|              Last name is required.                      |
|                                                          |
|  Address     [________________]                          |
|              Address is required.                        |
|                                                          |
|  City        [________________]                          |
|              City is required.                           |
|                                                          |
|  Telephone   [________________]  (pattern: 12 digits)   |
|              Telephone is required.                      |
|                                                          |
|  [Submit]                                                |
|                                                          |
+----------------------------------------------------------+
```

**Form Fields:**

| Field | ng-model | Validation | Input Attributes |
|---|---|---|---|
| First name | `$ctrl.owner.firstName` | required | - |
| Last name | `$ctrl.owner.lastName` | required | - |
| Address | `$ctrl.owner.address` | required | - |
| City | `$ctrl.owner.city` | required | - |
| Telephone | `$ctrl.owner.telephone` | required, pattern `[0-9]{12}` | maxlength=12, placeholder="905554443322" |

**Validation:** Inline error messages shown via `ng-show` when field is required and empty. Telephone pattern requires exactly 12 digits.

### 5. Pet Form (Add / Edit)

**State:** `petNew` (URL: `#!/owners/:ownerId/new-pet`) or `petEdit` (URL: `#!/owners/:ownerId/pets/:petId`)
**Controller:** `PetFormController`
**API Calls:**
- `GET api/customer/petTypes` - load pet type dropdown options
- **Edit mode:** `GET api/customer/owners/{ownerId}/pets/{petId}` - pre-populate
- **New mode:** `GET api/customer/owners/{ownerId}` - get owner name display
- **Create:** `POST api/customer/owners/{ownerId}/pets` with pet data
- **Update:** `PUT api/customer/owners/{ownerId}/pets/{petId}` with pet data
- **After submit:** Navigate to `ownerDetails`

```
+----------------------------------------------------------+
| [Navbar]                                                  |
+----------------------------------------------------------+
|                                                          |
|  Pet                                                     |
|                                                          |
|  Owner       George Franklin (read-only display)         |
|                                                          |
|  Name        [________________]                          |
|              Name is required.                           |
|                                                          |
|  Birth date  [____date picker____]                       |
|              birth date is required.                     |
|                                                          |
|  Type        [v cat          ]                           |
|              (dropdown: cat, dog, lizard, snake,         |
|               bird, hamster)                             |
|                                                          |
|  [Submit]                                                |
|                                                          |
+----------------------------------------------------------+
```

**Form Fields:**

| Field | Type | ng-model | Validation |
|---|---|---|---|
| Owner | Static text | `$ctrl.pet.owner` | Read-only (displayed as `firstName + " " + lastName`) |
| Name | text input | `$ctrl.pet.name` | required |
| Birth date | date input | `$ctrl.pet.birthDate` | required |
| Type | select dropdown | `$ctrl.petTypeId` | Required (defaults to "1" for new pets) |

**Submit Payload:**
```json
{
    "id": 0,
    "name": "Rex",
    "birthDate": "2020-01-15T00:00:00.000Z",
    "typeId": "2"
}
```

### 6. Add Visit

**State:** `visits`
**URL:** `#!/owners/:ownerId/pets/:petId/visits`
**Controller:** `VisitsController`
**API Calls:**
- `GET api/visit/owners/{ownerId}/pets/{petId}/visits` - load previous visits
- `POST api/visit/owners/{ownerId}/pets/{petId}/visits` - create visit
- **After submit:** Navigate to `ownerDetails`

```
+----------------------------------------------------------+
| [Navbar]                                                  |
+----------------------------------------------------------+
|                                                          |
|  Visits                                                  |
|                                                          |
|  Date        [____date picker____]  (defaults to today)  |
|                                                          |
|  Description [________________________]                  |
|              [________________________]  (textarea,      |
|              [________________________]   required)      |
|                                                          |
|  [Add New Visit]                                         |
|                                                          |
|  Previous Visits                                         |
|  +------------+---------------------------+              |
|  | 2013-01-01 | rabies shot               |              |
|  | 2013-01-04 | spayed                    |              |
|  +------------+---------------------------+              |
|                                                          |
+----------------------------------------------------------+
```

**Form Fields:**

| Field | Type | ng-model | Validation |
|---|---|---|---|
| Date | date input | `$ctrl.date` | Defaults to `new Date()` (today) |
| Description | textarea | `$ctrl.desc` | required, vertical resize |

**Submit Payload:**
```json
{
    "date": "2024-01-15",
    "description": "Annual checkup"
}
```

Date is formatted with `$filter('date')(self.date, "yyyy-MM-dd")` before submission.

### 7. Veterinarians List

**State:** `vets`
**URL:** `#!/vets`
**Controller:** `VetListController`
**API Call:** `GET api/vet/vets`

```
+----------------------------------------------------------+
| [Navbar]                                                  |
+----------------------------------------------------------+
|                                                          |
|  Veterinarians                                           |
|                                                          |
|  +----------------------------+----------------+         |
|  | Name                       | Specialties    |         |
|  +----------------------------+----------------+         |
|  | James Carter               |                |         |
|  | Helen Leary                | radiology      |         |
|  | Linda Douglas              | surgery dentistry|       |
|  | Rafael Ortega              | surgery        |         |
|  | Henry Stevens              | radiology      |         |
|  | Sharon Jenkins             |                |         |
|  +----------------------------+----------------+         |
|                                                          |
+----------------------------------------------------------+
```

**Features:**
- Simple striped table with name and specialties columns
- Specialties shown as space-separated names
- Read-only view (no edit/delete actions)

---

## Chatbot Widget

**Source:** `scripts/genai/chat.js` and inline in `index.html`

A floating chatbox widget overlaid on every page (not routed, always present).

```
+----------------------------------------------------------+
|                                                          |
|                   [Page Content]                         |
|                                                          |
|                                      +--Chat with Us!--+ |
|                                      | [bot] Hello!    | |
|                                      | [user] List vets| |
|                                      | [bot] Here are..| |
|                                      |                 | |
|                                      | [____msg___][Send]|
|                                      +-----------------+ |
+----------------------------------------------------------+
```

**Features:**
- Toggle expand/collapse by clicking "Chat with Us!" header
- Messages styled as chat bubbles (`.chat-bubble.user` and `.chat-bubble.bot`)
- Markdown rendering via `marked.js` library
- Chat history persisted in `localStorage` across page reloads
- Enter key sends message
- API call: `POST /api/genai/chatclient` with JSON string body
- Error fallback: displays "Chat is currently unavailable"

**Implementation:**

```javascript
function sendMessage() {
    const query = document.getElementById('chatbox-input').value;
    if (!query.trim()) return;
    document.getElementById('chatbox-input').value = '';
    appendMessage(query, 'user');

    fetch('/api/genai/chatclient', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(query),
    })
    .then(response => response.text())
    .then(responseText => appendMessage(responseText, 'bot'))
    .catch(error => appendMessage('Chat is currently unavailable', 'bot'));
}
```

---

## API Calls Summary

All API calls go through the gateway proxy. The gateway routes:
- `/api/customer/**` -> customers-service
- `/api/visit/**` -> visits-service
- `/api/vet/**` -> vets-service
- `/api/genai/**` -> genai-service
- `/api/gateway/**` -> gateway's own aggregation controller

| View | Method | API Endpoint | Purpose |
|---|---|---|---|
| Owner List | GET | `api/customer/owners` | Fetch all owners |
| Owner Details | GET | `api/gateway/owners/{id}` | Fetch owner + merged visits |
| Owner Form (edit) | GET | `api/customer/owners/{id}` | Fetch owner for editing |
| Owner Form (create) | POST | `api/customer/owners` | Create new owner |
| Owner Form (update) | PUT | `api/customer/owners/{id}` | Update existing owner |
| Pet Form (types) | GET | `api/customer/petTypes` | Fetch pet type options |
| Pet Form (edit) | GET | `api/customer/owners/{oid}/pets/{pid}` | Fetch pet for editing |
| Pet Form (owner) | GET | `api/customer/owners/{id}` | Fetch owner name for display |
| Pet Form (create) | POST | `api/customer/owners/{id}/pets` | Create new pet |
| Pet Form (update) | PUT | `api/customer/owners/{oid}/pets/{pid}` | Update existing pet |
| Visits (list) | GET | `api/visit/owners/{oid}/pets/{pid}/visits` | Fetch previous visits |
| Visits (create) | POST | `api/visit/owners/{oid}/pets/{pid}/visits` | Create new visit |
| Vet List | GET | `api/vet/vets` | Fetch all veterinarians |
| Chat | POST | `api/genai/chatclient` | Send chat message to LLM |

---

## HTTP Error Handling

**Source:** `scripts/infrastructure/httpErrorHandlingInterceptor.js`

Global `$http` interceptor that catches response errors and shows an alert:

```javascript
responseError: function (response) {
    var error = response.data;
    alert(error.error + "\r\n" + error.errors.map(function (e) {
        return e.field + ": " + e.defaultMessage;
    }).join("\r\n"));
    return response;
}
```

Expects error response format:
```json
{
    "error": "Validation Failed",
    "errors": [
        { "field": "firstName", "defaultMessage": "must not be blank" }
    ]
}
```

A `Cache-Control: no-cache` header is set on all requests to prevent Safari caching issues.

---

## External Dependencies (WebJars)

Loaded via WebJar paths:
- `/webjars/bootstrap/css/bootstrap.min.css` - Bootstrap CSS
- `/webjars/bootstrap/js/bootstrap.min.js` - Bootstrap JS
- `/webjars/angularjs/angular.min.js` - AngularJS core
- `/webjars/angular-ui-router/angular-ui-router.min.js` - UI-Router
- `/webjars/font-awesome/css/font-awesome.min.css` - Font Awesome icons
- `/webjars/marked/marked.min.js` - Markdown parser (for chat)

---

## Python Frontend Recommendation

### Option A: Jinja2 + HTMX (Recommended for Simplicity)

Replace the AngularJS SPA with server-side rendered HTML using Jinja2 templates and HTMX for dynamic interactions. This eliminates the need for a JavaScript build step and aligns with the Python/FastAPI stack.

```
templates/
  base.html              # Layout with navbar, footer, chatbox
  welcome.html           # Home page
  owners/
    list.html            # Owners table with search
    detail.html          # Owner info + pets + visits
    form.html            # Add/edit owner form
  pets/
    form.html            # Add/edit pet form
  visits/
    form.html            # Add visit form with previous visits
  vets/
    list.html            # Vets table
  partials/
    chat.html            # Chat widget
static/
  css/petclinic.css      # Custom styles
  js/chat.js             # Chat widget JS (keep as vanilla JS)
  images/                # Static images
```

**FastAPI Routes for Pages:**
```python
@app.get("/", response_class=HTMLResponse)
async def welcome(request: Request):
    return templates.TemplateResponse("welcome.html", {"request": request})

@app.get("/owners", response_class=HTMLResponse)
async def owner_list(request: Request):
    owners = await customers_client.get_owners()
    return templates.TemplateResponse("owners/list.html", {
        "request": request, "owners": owners
    })
```

**HTMX for Dynamic Behavior:**
- Search filter: `hx-get="/owners?q=..." hx-trigger="keyup changed delay:300ms" hx-target="#owner-table"`
- Form submission: `hx-post="/owners" hx-target="body"`

### Option B: Static SPA (Vue.js or React)

If an SPA is preferred, use a lightweight framework:
- **Vue.js 3** with Vue Router (closest to AngularJS component model)
- **React** with React Router

The SPA would be built separately and served as static files from the gateway/API service.

### Recommendation

**Option A (Jinja2 + HTMX)** is recommended because:
1. No separate build step or Node.js toolchain needed
2. Server-side rendering works naturally with FastAPI
3. HTMX provides sufficient interactivity for this application
4. Simpler deployment (templates are part of the Python service)
5. The original app's interactivity is minimal (forms, tables, filtering)

The chat widget can remain as vanilla JavaScript since it's a self-contained component that communicates with a single API endpoint.
