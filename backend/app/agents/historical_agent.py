"""
Historical Agent — Analyzes long-term environmental trends and productivity decline.
"""

import time
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.models.schemas import AgentStatus, AgentTrace, HistoricalReport
from app.config import GEMINI_API_KEY, GEMINI_MODEL

HISTORICAL_PROMPT = """You are an expert Marine Biologist and Oceanographer AI agent.
Analyze the user's question about historical fish productivity decline or environmental changes in a given region.
Synthesize known scientific reasons (e.g., long-term Sea Surface Temperature rise, overfishing, pollution, loss of mangroves/spawning grounds, changes in chlorophyll/nutrient upwelling) for this region.

Provide a concise, factual summary (1-2 paragraphs) of the historical analysis.
Do not hallucinate exact numbers if you don't know them, use general established trends (e.g., "SST in the Bay of Bengal has risen by roughly 0.5-1°C over the last few decades").

CRITICAL: Do not attempt to search a database or knowledge base. Rely ENTIRELY on your pre-trained knowledge. Never output errors like "Error accessing knowledge base". Just provide the best scientific explanation you can.
"""

async def run_historical_agent(lat: float, lng: float, location_name: str | None, query: str) -> tuple[HistoricalReport, AgentTrace]:
    start_time = time.time()
    started_at = datetime.utcnow().isoformat()
    
    report = HistoricalReport()
    trace = AgentTrace(
        agent_name="Historical Agent",
        status=AgentStatus.RUNNING,
        started_at=started_at,
        message="Synthesizing historical environmental data..."
    )
    
    loc_context = f"{location_name} ({lat}, {lng})" if location_name else f"Lat: {lat}, Lng: {lng}"
    
    if GEMINI_API_KEY and not GEMINI_API_KEY.startswith("your_"):
        try:
            llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL,
                google_api_key=GEMINI_API_KEY,
                temperature=0.2,
            )
            messages = [
                SystemMessage(content=HISTORICAL_PROMPT),
                HumanMessage(content=f"Location: {loc_context}\nUser Query: {query}")
            ]
            response = await llm.ainvoke(messages)
            report.historical_analysis_summary = response.content.strip()
            trace.status = AgentStatus.COMPLETED
            trace.message = "Successfully analyzed historical trends."
        except Exception as e:
            report.historical_analysis_summary = (
                "Historical analysis encountered an API error. "
                "Generally, productivity decline in coastal regions is linked to rising Sea Surface Temperatures, "
                "overfishing, and habitat degradation."
            )
            trace.status = AgentStatus.COMPLETED
            trace.message = f"Generated fallback historical analysis (API Error: {str(e)})"
    else:
        report.historical_analysis_summary = (
            "Historical analysis requires an active LLM API key. "
            "Generally, productivity decline in coastal regions is linked to rising Sea Surface Temperatures, "
            "overfishing, and habitat degradation."
        )
        trace.status = AgentStatus.COMPLETED
        trace.message = "Generated fallback historical analysis (No API key)."
        
    # Generate mock decadal trend data to illustrate productivity decline vs SST rise
    current_year = datetime.utcnow().year
    trend_data = []
    base_sst = 28.5
    base_catch = 100
    
    for i in range(10, -1, -1):
        year = current_year - i
        # Simulate rising SST and declining catch with slight variance
        sst = base_sst + (10 - i) * 0.12
        catch = base_catch - (10 - i) * 4.5
        trend_data.append({
            "year": year,
            "sst_c": round(sst, 2),
            "catch_index": max(0, round(catch, 1))
        })
        
    report.trend_data = trend_data
    report.sst_trend_c = 1.2
    
    trace.completed_at = datetime.utcnow().isoformat()
    trace.duration_ms = int((time.time() - start_time) * 1000)
    trace.data = {"analysis": report.historical_analysis_summary}
    
    return report, trace
