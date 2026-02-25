# 06 - GenAI Service Specification

## Overview

The genai-service provides an AI-powered chatbot for the Spring Petclinic application. It uses Spring AI to integrate with OpenAI (or Azure OpenAI) for natural language interaction with the clinic's data. The chatbot can answer questions about owners, pets, vets, and visits, and can perform actions like adding owners and pets through LLM function/tool calling.

**Java Source Module:** `spring-petclinic-genai-service`
**Port:** 8081
**Spring Application Name:** `genai-service`
**Web Application Type:** Reactive (configured in application.yml, though uses WebMVC starter)

---

## Architecture

```
+------------------+       +------------------+       +--------------------+
|   Browser Chat   | --->  |  API Gateway     | --->  |  GenAI Service     |
|   Widget (JS)    |       |  /api/genai/**   |       |  POST /chatclient  |
+------------------+       +------------------+       +----+----------+----+
                                                           |          |
                                                      +----v---+ +---v---------+
                                                      | OpenAI | | Tool Calls  |
                                                      | API    | | (functions) |
                                                      +--------+ +---+---------+
                                                                      |
                                                           +----------v----------+
                                                           | AIDataProvider      |
                                                           | (RestClient calls   |
                                                           |  to customers-svc)  |
                                                           | (VectorStore for    |
                                                           |  vet similarity)    |
                                                           +---------------------+
```

### Key Components

| Java Class | Role | Python Equivalent |
|---|---|---|
| `PetclinicChatClient` | REST controller, chat endpoint | FastAPI route handler |
| `PetclinicTools` | Tool/function definitions for LLM | OpenAI function definitions |
| `AIDataProvider` | Data access layer (REST + vector store) | Service class using httpx + vector store |
| `AIBeanConfiguration` | Vector store and WebClient beans | Module-level configuration |
| `VectorStoreController` | Loads vet data into vector store on startup | Startup event handler |

---

## Chat Endpoint

### POST /chatclient

**Java Source:** `PetclinicChatClient.java`

Accepts a user message as a raw string body (JSON-encoded string) and returns the LLM response as plain text.

**Request:**
```
POST /chatclient
Content-Type: application/json

"What owners do you have?"
```

**Response:**
```
Content-Type: text/plain

Here are the owners in the clinic:
1. George Franklin - 110 W. Liberty St., Madison (608-555-1023)
...
```

**Error Handling:** On any exception, returns the string `"Chat is currently unavailable. Please try again later."`

### Gateway Routing

The API gateway routes `/api/genai/**` to this service, so the browser calls `/api/genai/chatclient`.

---

## System Prompt

The system prompt is hardcoded in `PetclinicChatClient`:

```
You are a friendly AI assistant designed to help with the management of a veterinarian pet clinic
called Spring Petclinic. Your job is to answer questions about and to perform actions on the user's
behalf, mainly around veterinarians, owners, owners' pets and owners' visits.
You are required to answer an a professional manner. If you don't know the answer, politely tell
the user you don't know the answer, then ask the user a followup question to try and clarify the
question they are asking.
If you do know the answer, provide the answer but do not provide any additional followup questions.
When dealing with vets, if the user is unsure about the returned results, explain that there may be
additional data that was not returned.
Only if the user is asking about the total number of all vets, answer that there are a lot and ask
for some additional criteria.
For owners, pets or visits - provide the correct data.
```

---

## Chat Memory

**Java:** `MessageChatMemoryAdvisor` with order 10, using a `ChatMemory` bean.

The chat memory maintains context for the conversation. Spring AI's default `ChatMemory` implementation keeps up to 10 previous messages in context.

**Python Equivalent:** Maintain a list of message dicts (`{"role": "user"/"assistant", "content": "..."}`) in an in-memory store (dict keyed by session), passing the last 10 messages in each OpenAI API call.

---

## Tool/Function Calling

**Java Source:** `PetclinicTools.java`

The LLM is configured with 4 tools that it can invoke to interact with the petclinic data. Each tool is annotated with `@Tool` and has a description that the LLM uses to decide when to call it.

### Tool 1: listOwners

```java
@Tool(description = "List the owners that the pet clinic has")
public List<OwnerDetails> listOwners()
```

- **Parameters:** None
- **Returns:** List of all owners with their pets
- **Backend Call:** `GET {customers-service}/owners`

### Tool 2: addOwnerToPetclinic

```java
@Tool(description = """
    Add a new pet owner to the pet clinic. The Owner must include a first name and a last name
    as two separate words, plus an address and a 10-digit phone number
    """)
public OwnerDetails addOwnerToPetclinic(OwnerRequest ownerRequest)
```

- **Parameters:** `OwnerRequest` record:
  - `firstName` (String, @NotBlank)
  - `lastName` (String, @NotBlank)
  - `address` (String, @NotBlank)
  - `city` (String, @NotBlank)
  - `telephone` (String, @NotBlank, @Digits(fraction=0, integer=12))
- **Returns:** Created `OwnerDetails`
- **Backend Call:** `POST {customers-service}/owners` with OwnerRequest body

### Tool 3: listVets

```java
@Tool(description = "List the veterinarians that the pet clinic has")
public List<String> listVets(@ToolParam(required = false) Vet vetRequest)
```

- **Parameters:** Optional `Vet` object (id, firstName, lastName, specialties) for filtering
- **Returns:** List of formatted document strings from vector store similarity search
- **Backend:** Uses **vector store similarity search** (not direct REST call)
  - If `vetRequest` is null: `topK = 50`
  - If `vetRequest` is provided: `topK = 20`
  - Serializes the vet request to JSON, uses it as the search query
  - Returns `Document.getFormattedContent()` for each match

### Tool 4: addPetToOwner

```java
@Tool(description = """
    Add a pet with the specified petTypeId, to an owner identified by the ownerId.
    The allowed Pet types IDs are only: 1 = cat, 2 = dog, 3 = lizard, 4 = snake, 5 = bird,
    6 - hamster
    """)
public PetDetails addPetToOwner(
    @ToolParam(description = "Pet's owner identifier") int ownerId,
    PetRequest petRequest)
```

- **Parameters:**
  - `ownerId` (int) - owner identifier
  - `petRequest`:
    - `id` (int)
    - `birthDate` (Date, format: yyyy-MM-dd)
    - `name` (String)
    - `typeId` (int) - 1=cat, 2=dog, 3=lizard, 4=snake, 5=bird, 6=hamster
- **Returns:** Created `PetDetails`
- **Backend Call:** `POST {customers-service}/owners/{ownerId}/pets` with PetRequest body

---

## AI Data Provider

**Java Source:** `AIDataProvider.java`

The data provider is a `@Service` that bridges the LLM tools to actual backend services. It uses:

1. **RestClient** (synchronous) for direct HTTP calls to the customers-service
2. **VectorStore** for vet similarity search
3. **DiscoveryClient** to resolve `customers-service` hostname via Eureka

### Service Discovery

```java
private URI getCustomerServiceUri() {
    return discoveryClient.getInstances("customers-service").get(0).getUri();
}
```

### Methods

| Method | HTTP Call | Description |
|---|---|---|
| `getAllOwners()` | `GET {customers-service}/owners` | Returns `List<OwnerDetails>` |
| `addOwnerToPetclinic(OwnerRequest)` | `POST {customers-service}/owners` | Returns `OwnerDetails` |
| `addPetToOwner(int, PetRequest)` | `POST {customers-service}/owners/{id}/pets` | Returns `PetDetails` |
| `getVets(Vet)` | Vector store similarity search | Returns `List<String>` |

---

## Vector Store for Vet Search

**Java Source:** `VectorStoreController.java`, `AIBeanConfiguration.java`

### Configuration

The vector store uses Spring AI's `SimpleVectorStore` backed by an `EmbeddingModel` (provided by the OpenAI starter).

```java
@Bean
VectorStore vectorStore(EmbeddingModel embeddingModel) {
    return SimpleVectorStore.builder(embeddingModel).build();
}
```

### Data Loading (Startup)

On `ApplicationStartedEvent`, the `VectorStoreController` loads vet data:

1. **Check for pre-embedded data:** Look for `vectorstore.json` on the classpath
   - If found, load directly from file (saves API credits for embeddings)
   - The project ships with a pre-computed `vectorstore.json`
2. **If no file exists:** Fetch vets from the vets-service and embed them:
   - Call `GET http://vets-service/vets` via WebClient (load-balanced)
   - Convert vet list to JSON using `JsonReader`
   - Add documents to vector store
   - Save the vector store to a temp file for future use

### Similarity Search Flow

When `listVets` is called:
1. The vet request (or null) is serialized to JSON
2. A `SearchRequest` is created with the JSON as query and appropriate `topK`
3. `vectorStore.similaritySearch(sr)` returns matching `Document` objects
4. Each document's formatted content is returned as a string

---

## DTOs

### OwnerDetails
```python
@dataclass
class OwnerDetails:
    id: int
    first_name: str
    last_name: str
    address: str
    city: str
    telephone: str
    pets: list[PetDetails]
```

### PetDetails
```python
@dataclass
class PetDetails:
    id: int
    name: str
    birth_date: str  # "yyyy-MM-dd"
    type: PetType
    visits: list[VisitDetails]
```

### PetRequest
```python
@dataclass
class PetRequest:
    id: int
    birth_date: date  # yyyy-MM-dd format
    name: str
    type_id: int
```

### PetType
```python
@dataclass
class PetType:
    name: str
```

### Vet
```python
@dataclass
class Vet:
    id: int | None
    first_name: str | None
    last_name: str | None
    specialties: set[Specialty] | None
```

### Specialty
```python
@dataclass
class Specialty:
    id: int | None
    name: str | None
```

### VisitDetails
```python
@dataclass
class VisitDetails:
    id: int | None
    pet_id: int | None
    date: str | None
    description: str | None
```

---

## OpenAI / Azure OpenAI Configuration

**Java Source:** `application.yml`

### OpenAI (default)
```yaml
spring:
  ai:
    openai:
      api-key: ${OPENAI_API_KEY:demo}
      chat:
        options:
          temperature: 0.7
          model: gpt-4o-mini
```

### Azure OpenAI (alternative)
```yaml
spring:
  ai:
    azure:
      openai:
        api-key: ${AZURE_OPENAI_KEY}
        endpoint: ${AZURE_OPENAI_ENDPOINT}
        chat:
          options:
            temperature: 0.7
            deployment-name: gpt-4o
```

The active provider is selected by Maven dependency:
- `spring-ai-starter-model-openai` for OpenAI (default, active in pom.xml)
- `spring-ai-starter-model-azure-openai` for Azure (commented out in pom.xml)

### Logging
```yaml
logging:
  level:
    org.springframework.ai.chat.client.advisor: DEBUG
```

---

## Python Equivalent Implementation

### Recommended Stack

| Concern | Python Library |
|---|---|
| LLM Client | `openai` (official SDK) |
| Function/Tool Calling | OpenAI function calling API |
| Vector Store | `chromadb` or `faiss-cpu` with `openai` embeddings |
| Chat Memory | In-memory dict with message history |
| HTTP Client | `httpx` (async) |
| Service Discovery | Direct URL config or Consul via `python-consul2` |

### Python Implementation Structure

```python
# genai_service/main.py
from fastapi import FastAPI
from genai_service.chat import router as chat_router

app = FastAPI(title="GenAI Service")
app.include_router(chat_router)

@app.on_event("startup")
async def load_vet_vector_store():
    """Load vet data into vector store on startup."""
    await vet_store.initialize()
```

### Chat Endpoint

```python
# genai_service/chat.py
from fastapi import APIRouter
from openai import OpenAI

router = APIRouter()
client = OpenAI()

SYSTEM_PROMPT = """You are a friendly AI assistant designed to help with the management of a
veterinarian pet clinic called Spring Petclinic. Your job is to answer questions about and to
perform actions on the user's behalf, mainly around veterinarians, owners, owners' pets and
owners' visits.
You are required to answer in a professional manner. If you don't know the answer, politely tell
the user you don't know the answer, then ask the user a followup question to try and clarify the
question they are asking.
If you do know the answer, provide the answer but do not provide any additional followup questions.
When dealing with vets, if the user is unsure about the returned results, explain that there may be
additional data that was not returned.
Only if the user is asking about the total number of all vets, answer that there are a lot and ask
for some additional criteria.
For owners, pets or visits - provide the correct data."""

# In-memory chat history (per-session or global for simplicity)
chat_history: list[dict] = []

@router.post("/chatclient")
async def chat(query: str) -> str:
    chat_history.append({"role": "user", "content": query})

    # Keep last 10 messages for context
    recent_history = chat_history[-10:]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.7,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *recent_history,
            ],
            tools=TOOL_DEFINITIONS,
        )

        # Handle tool calls in a loop
        message = response.choices[0].message
        while message.tool_calls:
            message = await handle_tool_calls(message, recent_history)

        assistant_reply = message.content
        chat_history.append({"role": "assistant", "content": assistant_reply})
        return assistant_reply

    except Exception:
        return "Chat is currently unavailable. Please try again later."
```

### Tool Definitions

```python
# genai_service/tools.py
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "listOwners",
            "description": "List the owners that the pet clinic has",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "addOwnerToPetclinic",
            "description": (
                "Add a new pet owner to the pet clinic. The Owner must include a first name "
                "and a last name as two separate words, plus an address and a 10-digit phone number"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "firstName": {"type": "string"},
                    "lastName": {"type": "string"},
                    "address": {"type": "string"},
                    "city": {"type": "string"},
                    "telephone": {"type": "string"},
                },
                "required": ["firstName", "lastName", "address", "city", "telephone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listVets",
            "description": "List the veterinarians that the pet clinic has",
            "parameters": {
                "type": "object",
                "properties": {
                    "firstName": {"type": "string"},
                    "lastName": {"type": "string"},
                    "specialties": {
                        "type": "array",
                        "items": {"type": "object", "properties": {"name": {"type": "string"}}},
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "addPetToOwner",
            "description": (
                "Add a pet with the specified petTypeId, to an owner identified by the ownerId. "
                "The allowed Pet types IDs are only: 1 = cat, 2 = dog, 3 = lizard, 4 = snake, "
                "5 = bird, 6 = hamster"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ownerId": {"type": "integer", "description": "Pet's owner identifier"},
                    "name": {"type": "string"},
                    "birthDate": {"type": "string", "description": "yyyy-MM-dd format"},
                    "typeId": {"type": "integer"},
                },
                "required": ["ownerId", "name", "birthDate", "typeId"],
            },
        },
    },
]
```

### Tool Call Handler

```python
# genai_service/tool_handler.py
import json
import httpx

CUSTOMERS_SERVICE_URL = "http://customers-service:8080"  # or from service discovery

async def handle_tool_calls(message, history):
    """Process tool calls from the LLM and return the next response."""
    tool_results = []

    for tool_call in message.tool_calls:
        args = json.loads(tool_call.function.arguments)
        result = await dispatch_tool(tool_call.function.name, args)
        tool_results.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result),
        })

    # Send tool results back to LLM
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.7,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            message.model_dump(),
            *tool_results,
        ],
        tools=TOOL_DEFINITIONS,
    )
    return response.choices[0].message


async def dispatch_tool(name: str, args: dict):
    async with httpx.AsyncClient() as client:
        if name == "listOwners":
            resp = await client.get(f"{CUSTOMERS_SERVICE_URL}/owners")
            return resp.json()

        elif name == "addOwnerToPetclinic":
            resp = await client.post(f"{CUSTOMERS_SERVICE_URL}/owners", json=args)
            return resp.json()

        elif name == "listVets":
            # Use vector store similarity search
            return await search_vets(args)

        elif name == "addPetToOwner":
            owner_id = args.pop("ownerId")
            resp = await client.post(
                f"{CUSTOMERS_SERVICE_URL}/owners/{owner_id}/pets",
                json=args,
            )
            return resp.json()
```

### Vector Store

```python
# genai_service/vet_store.py
import json
import chromadb
from openai import OpenAI

openai_client = OpenAI()
chroma_client = chromadb.Client()  # In-memory
collection = chroma_client.create_collection("vets")

async def initialize():
    """Load vet data into vector store on startup."""
    # Try loading pre-embedded data first
    try:
        with open("vectorstore.json") as f:
            data = json.load(f)
            # Load pre-computed embeddings
            collection.add(
                documents=[item["content"] for item in data],
                ids=[str(i) for i in range(len(data))],
            )
            return
    except FileNotFoundError:
        pass

    # Fetch from vets-service and embed
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get("http://vets-service:8080/vets")
        vets = resp.json()

    documents = [json.dumps(vet) for vet in vets]
    collection.add(
        documents=documents,
        ids=[str(i) for i in range(len(documents))],
    )


async def search_vets(vet_filter: dict) -> list[str]:
    """Similarity search for vets based on filter criteria."""
    query = json.dumps(vet_filter) if vet_filter else "{}"
    top_k = 20 if vet_filter else 50

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
    )
    return results["documents"][0] if results["documents"] else []
```

---

## Dependencies

### Java (from pom.xml)

| Dependency | Version | Purpose |
|---|---|---|
| `spring-ai-starter-model-openai` | 2.0.0-M1 (BOM) | OpenAI LLM integration |
| `spring-ai-vector-store` | 2.0.0-M1 (BOM) | SimpleVectorStore for embeddings |
| `spring-boot-starter-webmvc` | 4.0.1 | REST controller |
| `spring-cloud-starter-netflix-eureka-client` | 2025.1.0 | Service discovery |
| `spring-cloud-starter-config` | 2025.1.0 | External configuration |
| `spring-cloud-starter-circuitbreaker-reactor-resilience4j` | 2025.1.0 | Circuit breaker |

### Python Equivalents

| Python Package | Purpose |
|---|---|
| `openai>=1.0` | OpenAI API client with function calling |
| `chromadb` | Vector store for vet similarity search |
| `fastapi` | REST framework |
| `httpx` | Async HTTP client for inter-service calls |
| `pydantic` | Request/response models |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | `demo` | OpenAI API key |
| `AZURE_OPENAI_KEY` | (none) | Azure OpenAI API key (if using Azure) |
| `AZURE_OPENAI_ENDPOINT` | (none) | Azure OpenAI endpoint (if using Azure) |
| `CONFIG_SERVER_URL` | `http://localhost:8888/` | Spring Cloud Config server URL |

---

## Eureka Registration

The service registers with Eureka as `genai-service` and uses the `DiscoveryClient` to resolve `customers-service` for REST calls and the `WebClient` (load-balanced) to resolve `vets-service` for vector store loading.

---

## Advisors

The `ChatClient` is configured with two advisors:

1. **MessageChatMemoryAdvisor** (order 10) - Maintains conversation history
2. **SimpleLoggerAdvisor** - Logs chat interactions at DEBUG level

In Python, these map to:
- Chat memory: Maintain a message list, pass last N messages to each API call
- Logging: Standard Python `logging` module with debug-level log of each request/response
