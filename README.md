# 🐋 ORCA - Marine Decision Intelligence Platform

An **Agentic AI-powered** marine decision intelligence platform that coordinates specialized AI agents to analyze ocean, weather, satellite, and geospatial data — providing fishermen and marine stakeholders with explainable safety and operational recommendations.

Built for the **Smart India Hackathon (SIH)**.

---

## 💡 IDEA / SOLUTION

**Ask ORCA 🎤**
Fishermen ask questions using voice or text in their local language.
*Example: “Can I go fishing tomorrow?”*

**Collect Ocean Data 🌊**
ORCA collects information about weather, waves, tides, sea temperature, chlorophyll, cyclones and satellites.

**AI Thinks Together 🤖**
Different AI agents analyze the data to identify good fishing areas, dangerous areas and safe routes.

**Give a Simple Answer ✅**
ORCA converts all the complex analysis into a simple decision:
- 🟢 **GO** – Safe/good conditions
- 🔴 **AVOID** – Dangerous conditions
- 🟡 **WAIT** – Conditions may improve later

**Show & Warn 🗺️🔔**
A map shows Potential Fishing Zones (PFZs), safe routes and danger zones. ORCA also sends voice/text alerts about cyclones, rough seas and other hazards.

> **Ocean Data → AI Agents → Analyze → GO/AVOID/WAIT → Map + Alert**

---

## 🚀 Features

- **Agentic Orchestration:** A LangGraph-inspired state machine that delegates complex natural language queries to specialized agents.
- **Zero Mock Data:** 100% live integrations with Open-Meteo (Marine & Weather) and geographic math for EEZ/MPA calculation.
- **Deterministic Risk Engine:** Safety scoring is calculated using absolute mathematical thresholds (not LLM hallucinations).
- **Explainable AI:** Uses Google Gemini to translate raw JSON risk profiles into local-language advice (Bengali, Hindi, English).
- **Real-Time Visualization:** Interactive React-Leaflet map with dynamic routes, risk zones, and PFZ (Potential Fishing Zone) heatmaps.

---

## 🔬 Technical Approach

Our solution moves away from the traditional, fragile "chatbot wrapper" by implementing a **Multi-Agent State Machine**. 

1. **LangGraph-Inspired Orchestration:** 
   Instead of relying on a single LLM to guess answers, we use a central Orchestrator that breaks down user queries (e.g., *"Is it safe near Digha?"*) and fans out execution to parallel, specialized domain agents (Weather, Ocean, PFZ, Geospatial).
   
2. **Deterministic Risk Engine (Zero Hallucinations):** 
   LLMs are notoriously bad at math and safety-critical reasoning. To ensure fishermen's safety, ORCA uses a purely mathematical Risk Assessment Agent. It grades live oceanic data against hardcoded threshold matrices. For example, a wave height > 4.0 meters immediately triggers an *Extreme Risk (100)* score, bypassing AI unpredictability.

3. **Live Marine Data Integration (Zero Mock Data):** 
   The platform integrates with Open-Meteo Marine and OpenWeatherMap APIs, passing spatial coordinates directly to extract precise, real-time wind speed, swell height, sea surface temperature (SST), and precipitation probabilities.

4. **Explainable AI (XAI) with Local Language Support:** 
   Only *after* the deterministic Risk Engine calculates safety scores does the Explainability Agent (powered by Google Gemini) step in. It translates the raw JSON risk profile into easy-to-understand, empathetic advice in the user's native language (Bengali, Hindi, English).

---

## 🧠 System Architecture

ORCA is built on a decoupled, modular architecture that emphasizes specialized intelligence over a single monolithic LLM.

```mermaid
graph TD
    %% Styling
    classDef frontend fill:#0f1535,stroke:#4a5a8a,stroke-width:2px,color:#e2e8f0
    classDef backend fill:#1a2144,stroke:#3498db,stroke-width:2px,color:#e2e8f0
    classDef agent fill:#252d55,stroke:#00d4aa,stroke-width:2px,color:#e2e8f0
    classDef external fill:#0a0e27,stroke:#e94560,stroke-width:2px,color:#e2e8f0
    classDef engine fill:#334173,stroke:#f39c12,stroke-width:2px,color:#e2e8f0

    subgraph Frontend ["Client Layer (React + Vite)"]
        UI["Web Dashboard"]:::frontend
        Map["Leaflet Marine Map"]:::frontend
        Dash["Risk Dashboard"]:::frontend
        Trace["Real-time Reasoning Trace"]:::frontend
    end

    subgraph Backend ["Intelligence Layer (FastAPI)"]
        Orchestrator{"Orchestrator Agent<br/>Intent & Routing"}:::engine
        WS["WebSocket Manager<br/>Progress Streaming"]:::backend
        
        subgraph Agents ["Specialized Domain Agents"]
            Weather["Weather Agent"]:::agent
            Ocean["Ocean Agent"]:::agent
            Geo["Geospatial Agent"]:::agent
            PFZ["PFZ Discovery Agent"]:::agent
            Route["Route Planning Agent"]:::agent
        end
        
        Risk["Risk Assessment Agent<br/>Deterministic Engine"]:::engine
        Explain["Explainability Agent<br/>Gemini LLM"]:::agent
    end

    subgraph External ["External APIs & Data"]
        OM["Open-Meteo API<br/>Marine & Weather"]:::external
        OWM["OpenWeatherMap API"]:::external
        Gemini["Google Gemini API"]:::external
    end

    %% Data Flow
    UI -->|"HTTP POST Query"| Orchestrator
    Orchestrator -.->|"Agent Status Updates"| WS
    WS -.->|"WebSocket Stream"| Trace
    
    Orchestrator --> Weather
    Orchestrator --> Ocean
    Orchestrator --> Geo
    Orchestrator --> PFZ
    Orchestrator --> Route
    
    Weather --> OM
    Ocean --> OM
    PFZ --> OM
    Weather -.-> OWM
    Explain --> Gemini
    Orchestrator --> Gemini
    
    Weather --> Risk
    Ocean --> Risk
    Geo --> Risk
    
    Risk --> Explain
    Explain --> UI
    Risk --> Dash
    Route --> Map
    PFZ --> Map
```

---

## ⚡ Agentic Workflow

How ORCA processes a complex user request in parallel:

```mermaid
sequenceDiagram
    participant User
    participant Orch as Orchestrator Agent
    participant Domain as Domain Agents (Parallel)
    participant API as External APIs
    participant Risk as Risk Assessment Agent
    participant Explain as Explainability Agent
    
    User->>Orch: "Is it safe to fish near Digha?"
    activate Orch
    
    Orch->>Orch: Intent Detection (LLM)
    Note over Orch: Extracts:<br/>Intent: SAFETY_CHECK<br/>Location: Digha (21.6°N, 87.5°E)
    
    Orch-->>User: WS Event: "Analyzing query..."
    
    par Parallel Data Gathering
        Orch->>Domain: Invoke Weather Agent
        Orch->>Domain: Invoke Ocean Agent
        Orch->>Domain: Invoke Geospatial Agent
    end
    
    activate Domain
    Domain->>API: Fetch Live Data (HTTP/REST)
    API-->>Domain: Raw marine/weather JSON
    Domain-->>Orch: Standardized Data Reports
    deactivate Domain
    
    Orch-->>User: WS Event: "Marine data fetched."
    
    Orch->>Risk: Pass all marine data
    activate Risk
    Note over Risk: Deterministic scoring<br/>(e.g., Wave > 4m = Score 100)
    Risk-->>Orch: Final Risk Score (0-100) & Profile
    deactivate Risk
    
    Orch->>Explain: Pass marine data + Risk Profile
    activate Explain
    Note over Explain: Generates human-readable advice<br/>in local language (Bengali/English)
    Explain-->>Orch: Formatted Explanation
    deactivate Explain
    
    Orch-->>User: Final Response (JSON)
    Note over User: UI updates Map, Risk Dashboard,<br/>and displays Chat response.
    deactivate Orch
```

## 🛠 Tech Stack

**1. Frontend & Core Framework**
- **Framework:** React + Vite
- **Language:** TypeScript
- **Global State Management:** React Hooks & Context
- **Deployment:** Local / Vercel-ready

**2. UI / UX & Visualization**
- **Styling:** Tailwind CSS v4 (Custom Dark Ocean Glassmorphic Design Token System)
- **Icons & Animations:** Native CSS Animations
- **Data Visualization (Charts/Graphs):** Recharts
- **Geospatial Mapping:** React Leaflet / Leaflet.js

**3. Agentic AI & Intelligence**
- **Orchestration Engine:** LangGraph-inspired State Machine
- **AI Models:** Google Gemini (3.1 Pro / 2.0 Flash)
- **Natural Language Interface:** Multilingual LLM Translation (Bengali, Hindi, English)

**4. External Data Integrations (Feeds)**
- **Oceanographic & Meteorological Data:** Open-Meteo Marine & Weather APIs
- **Geospatial Data:** Mathematical Haversine geofencing & static coordinate bounding boxes
- **Weather Validation Data:** OpenWeatherMap API

## 🏁 Getting Started
### Backend
```bash
cd backend
cp .env.example .env # Add your Gemini API Key
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
