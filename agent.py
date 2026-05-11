

# --- CONFIGURATION ---
GROQ_API_KEY = "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"  # 👈 Paste your key here
TAVILY_API_KEY = "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"

import os
import asyncio
from typing import TypedDict, List
from pydantic import BaseModel, Field
from celery import Celery

from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END

# --- CONFIGURATION ---
GROQ_API_KEY = "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"  # 👈 Paste your key here
TAVILY_API_KEY = "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"

os.environ["GROQ_API_KEY"] = GROQ_API_KEY
os.environ["TAVILY_API_KEY"] = TAVILY_API_KEY

# --- 2. STATE DEFINITION ---
class AgentState(TypedDict):
    query: str
    abstracts: str
    sources: List[str]      # Stores the URLs for citations
    draft: str
    review_feedback: str
    is_accurate: bool
    retry_count: int

# --- 3. MODELS & TOOLS ---
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
tavily_tool = TavilySearch(max_results=3)

class ReviewResult(BaseModel):
    is_accurate: bool = Field(description="True if the draft matches the abstracts perfectly.")
    feedback: str = Field(description="Instructions to fix hallucinations or missing info.")

# --- 4. NODES (The Brain Logic) ---

async def research_node(state: AgentState):
    """Fetch abstracts from trusted medical sources and save URLs."""
    print("🔍 Fetching clinical abstracts...")
    
    search_response = await tavily_tool.ainvoke({
        "query": state["query"],
        "include_domains": ["mayoclinic.org", "heart.org", "cdc.gov", "nih.gov", "health.harvard.edu"]
    })
    
    # Handle response format safely
    results = search_response.get("results", []) if isinstance(search_response, dict) else search_response
    
    abstract_list = []
    source_urls = []
    
    if isinstance(results, list):
        for r in results:
            if isinstance(r, dict):
                url = r.get('url', 'Unknown Source')
                content = r.get('content', r.get('snippet', 'No content'))
                abstract_list.append(f"Source: {url}\nContent: {content}")
                source_urls.append(url)
    
    return {
        "abstracts": "\n\n".join(abstract_list) if abstract_list else "No data found.",
        "sources": source_urls
    }

async def generation_node(state: AgentState):
    print(f"👩‍🍳 Drafting response...")
    
    # We still give the LLM the abstracts, but we REMOVE the rule 
    # that tells it to list the URLs in the text.
    prompt = f"""You are Cardia, a helpful health assistant. 
    Use the following clinical abstracts to answer the user query.
    
    ABSTRACTS: 
    {state['abstracts']}
    
    RULES:
    1. Only use information from the provided abstracts.
    2. Be warm, professional, and clear.
    3. DO NOT include any URL links or a source list in your response. 
    Just provide the helpful medical advice.
    """
    
    res = await llm.ainvoke([SystemMessage(content=prompt), HumanMessage(content=state["query"])])
    return {"draft": res.content}
    

async def reviewer_node(state: AgentState):
    """Compare draft against abstracts for medical accuracy."""
    print("🔬 Reviewing for accuracy...")
    critic_llm = llm.with_structured_output(ReviewResult)
    
    prompt = f"""Compare this DRAFT against the provided ABSTRACTS.
    DRAFT: {state['draft']}
    ABSTRACTS: {state['abstracts']}
    
    Verify that the draft does not hallucinate info outside the abstracts and includes the source list."""
    
    review = await critic_llm.ainvoke(prompt)
    return {
        "is_accurate": review.is_accurate, 
        "review_feedback": review.feedback, 
        "retry_count": state.get("retry_count", 0) + 1
    }

# --- 5. GRAPH CONSTRUCTION ---

def should_continue(state: AgentState):
    if state["is_accurate"] or state["retry_count"] >= 3:
        return END
    return "generate"

workflow = StateGraph(AgentState)
workflow.add_node("research", research_node)
workflow.add_node("generate", generation_node)
workflow.add_node("review", reviewer_node)

workflow.add_edge(START, "research")
workflow.add_edge("research", "generate")
workflow.add_edge("generate", "review")
workflow.add_conditional_edges("review", should_continue)

agent_graph = workflow.compile()

# --- 6. CELERY SETUP ---

app = Celery(
    'cardia_tasks', 
    broker='redis://localhost:6379/0', 
    backend='redis://localhost:6379/0'
)

@app.task(name="run_health_agent")
def run_agent_task(user_query: str):
    result = asyncio.run(agent_graph.ainvoke({
        "query": user_query, 
        "retry_count": 0,
        "sources": [],
        "is_accurate": False
    }))
    
    # 👈 Return a dictionary containing BOTH
    return {
        "answer": result["draft"],
        "sources": result["sources"] 
    }

