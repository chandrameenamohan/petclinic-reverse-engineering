"""OpenAI function/tool definitions for the GenAI service.

Defines the 4 LLM tools matching the Spring Petclinic Java @Tool annotations:
  - listOwners: list all owners
  - addOwnerToPetclinic: add a new owner
  - listVets: search vets (vector similarity)
  - addPetToOwner: add a pet to an owner
"""

from __future__ import annotations

TOOL_DEFINITIONS: list[dict[str, object]] = [
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
                "5 = bird, 6 - hamster"
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
