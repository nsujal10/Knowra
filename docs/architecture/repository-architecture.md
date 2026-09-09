

# Phase 5: Repository Architecture & Dependency Strategy

## 1. Repository Structure Overview
Our repository strictly adheres to a modular, decoupled architecture designed for scale. To maintain velocity and system integrity as the platform grows, the repository is divided into distinct, isolated domains. This ensures that infrastructure changes, frontend overhauls, or AI model swaps do not cascade into breaking changes across the broader system.

## 2. Backend Layers
The backend follows a layered architecture, abstracting the complexities of data persistence and business logic away from the entry points. 
* **API Layer:** Handles HTTP routing, payload validation, and POST request orchestration.
* **Service Layer:** Contains the core business logic, orchestrating calls between the database, external APIs, and AI modules.
* **Repository Layer:** Abstract interfaces for data access, ensuring the service layer remains unaware of specific SQL dialects.
* **Database Models:** Represents the strictly normalized schema of the underlying database, ensuring efficient and structured metadata storage.

## 3. AI Separation
AI components are treated as independent, swappable engines rather than tightly coupled utility functions. The core logic does not interact with specific AI vendors directly. Instead, it interacts with standard internal AI Module interfaces, which then utilize Provider Adapters to communicate with external APIs or local models. This prevents vendor lock-in and allows seamless failover mechanisms.

## 4. Frontend Separation
The frontend application (typically structured with modern frameworks like Next.js, utilizing TypeScript and Tailwind CSS for generative AI interfaces) operates completely independently from the backend ecosystem. It acts strictly as a consumer of the API, adhering to the contract defined by the OpenAPI specification. It maintains no awareness of the underlying backend architecture, task queues, or AI orchestration.

## 5. Infrastructure Separation
Infrastructure components such as PostgreSQL, Redis, and MinIO are fully abstracted. The application interacts with these services through generic interfaces (e.g., a standard Object Storage interface rather than a MinIO-specific client). This allows for seamless migration to cloud-managed equivalents without rewriting application logic.

## 6. Dependency Direction
To maintain a clean architecture, dependencies must flow strictly inward toward the core domain logic, or downward through defined layers. Upward or cyclical dependencies are strictly prohibited.

**Core Application Flow:**
`API` ↓ `Services` ↓ `Repositories` ↓ `Database Models`

**Asynchronous & Background Task Flow:**
`Workers/Tasks` ↓ `Services` ↓ `AI Modules` ↓ `Repositories`

**AI Orchestration Flow:**
`AI Modules` ↓ `Provider Adapters` ↓ `Specific Models (e.g., OpenAI / Azure / Local Model)`

*(Example: Summarization Engine ↓ LLM Provider Interface ↓ Azure OpenAI)*

## 7. Forbidden Dependencies
Enforcing strict boundaries is critical to preventing spaghetti code and unmaintainable technical debt. The following architectural constraints are mandatory:

**API Constraints:**
The API layer must NOT directly contain:
* SQL queries or database session executions
* Direct LLM calls or prompt engineering
* Whisper, pyannote, or other ML model calls
* FFmpeg execution or native audio processing commands

**AI Constraints:**
AI modules must NOT directly depend on:
* FastAPI request/response objects
* HTTP routing configurations
* Frontend code or UI components

**Frontend Constraints:**
The frontend must NOT know about or communicate with:
* PostgreSQL (no direct DB queries)
* Redis (no direct queue manipulation)
* MinIO internals (all storage access must route through API presigned URLs)
* Whisper or underlying ML libraries

**The standard communication flow must always be:**
`Frontend` ↓ `API` ↓ `Backend`

## 8. Naming Conventions
* **Files & Directories:** `snake_case` for Python backend files, `kebab-case` for Markdown documentation and frontend components.
* **Classes:** `PascalCase` (e.g., `AudioProcessingService`).
* **Functions & Variables:** `snake_case` (e.g., `generate_summary()`).
* **Interfaces/Adapters:** Append `Interface` or `Adapter` to clarify intent (e.g., `LLMProviderInterface`, `MinioStorageAdapter`).

## 9. Future Expansion Strategy
This modular monolith is designed to comfortably scale. As specific domains require independent scaling, their isolated Service and AI Modules can be cleanly sheared off into dedicated microservices. The strict dependency rules ensure that this transition requires only rewriting the API transport layer, leaving the core business and AI logic completely untouched.