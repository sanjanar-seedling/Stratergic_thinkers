# System Data Flow Diagram

This document illustrates the data flow architecture of the Strategic Thinkers (Seedlings) system, detailing how data moves between ingestion workers, backing infrastructure, backend services, and front-end clients.

```mermaid
graph TD
    %% External Inputs
    subgraph Data Sources
        DS_Slack[Slack]
        DS_Email[Email]
        DS_Google[Google Workspace]
        DS_Voice[Voice Memos]
        DS_Doc[Documents / OCR]
    end

    %% Ingestion Workers
    subgraph Ingestion Workers [Data Ingestion Layer]
        W_Slack[Slack Worker]
        W_Email[Email Worker]
        W_Google[Google Worker]
        W_Voice[Voice Worker]
        W_OCR[OCR Worker]
    end

    %% Message Broker
    subgraph Message Queue
        RedisStream[(Redis Stream\n'seedlings:events')]
    end

    %% Backend Services
    subgraph Backend [FastAPI Backend]
        API[API Gateway / Routes]
        EventProc[Event Processor]
        PatternEng[Pattern Engine]
        RAG[RAG Pipeline]
        Router[Inference / Personalized Router]
        Lora[LoRA Worker]
    end

    %% Datastores & Infra
    subgraph Infrastructure [Data Storage & Infrastructure]
        PG[(PostgreSQL / pgvector\nStructured Data & Embeddings)]
        MinIO[(MinIO\nObject Storage)]
        RedisCache[(Redis\nCache & PubSub)]
    end

    %% External LLM
    ExtLLM[LLM Provider\nOpenAI / Anthropic / Local]

    %% Frontend App
    subgraph Client Application
        WebApp[Frontend React App\nVite / TS]
    end

    %% ---------------- FLOWS ----------------

    %% Ingestion Flow
    DS_Slack -->|Webhooks| W_Slack
    DS_Email -->|Imap/SMTP| W_Email
    DS_Google -->|APIs| W_Google
    DS_Voice -->|Audio files| W_Voice
    DS_Doc -->|Files/Images| W_OCR

    W_Slack -->|Pushes FounderEvents| RedisStream
    W_Email -->|Pushes FounderEvents| RedisStream
    W_Google -->|Pushes FounderEvents| RedisStream
    W_Voice -->|Pushes FounderEvents| RedisStream
    W_OCR -->|Pushes FounderEvents| RedisStream

    %% Processing Flow
    RedisStream -->|Consumes Events| EventProc
    EventProc -->|Stores Metadata/Vectors| PG
    EventProc -->|Stores Raw Assets| MinIO
    EventProc -->|Triggers Async Analysis| PatternEng

    %% Client / App Flow
    WebApp <-->|HTTP/REST / WebSocket| API
    API -->|Reads/Writes Data| PG
    API -->|Caches| RedisCache
    
    %% AI / Logic Flow
    API <-->|Generates Insights| RAG
    RAG <-->|Vector Search Context| PG
    RAG <-->|Generates Response| Router
    PatternEng <-->|Analyzes events| Router
    Router <-->|Inference Calls| ExtLLM
    
    %% Training Flow
    Lora -.->|Fine-tunes models\nfrom parsed events| ExtLLM
    EventProc -.->|Queues Training Data| Lora

    classDef worker fill:#f9f0ff,stroke:#d0bfff,stroke-width:2px,color:#333
    classDef datastore fill:#e6f7ff,stroke:#91d5ff,stroke-width:2px,color:#333
    classDef backend fill:#f6ffed,stroke:#b7eb8f,stroke-width:2px,color:#333
    classDef ext fill:#fffbe6,stroke:#ffe58f,stroke-width:2px,color:#333
    
    class W_Slack,W_Email,W_Google,W_Voice,W_OCR worker
    class PG,MinIO,RedisStream,RedisCache datastore
    class API,EventProc,PatternEng,RAG,Router,Lora backend
    class ExtLLM,DS_Slack,DS_Email,DS_Google,DS_Voice,DS_Doc ext
```
