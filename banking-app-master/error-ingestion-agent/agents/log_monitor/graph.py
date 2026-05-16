"""
Error Ingestion Agent — LangGraph Graph Definition
Wires parse → analyze → store into a compiled StateGraph.
"""
from langgraph.graph import StateGraph, END

from agents.log_monitor.nodes import IncidentState, parse_node, analyze_node, store_node


def build_graph():
    """Build and compile the incident processing graph."""
    graph = StateGraph(IncidentState)

    graph.add_node("parse",   parse_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("store",   store_node)

    graph.set_entry_point("parse")
    graph.add_edge("parse",   "analyze")
    graph.add_edge("analyze", "store")
    graph.add_edge("store",   END)

    return graph.compile()


# Singleton compiled graph
incident_graph = build_graph()


async def process_log_entry(raw_log: str, source: str = "db_watcher") -> IncidentState:
    """
    Run the full incident processing pipeline for a single log entry.

    Args:
        raw_log: Raw log text (single or multi-line)
        source:  'db_watcher' | 'datadog_webhook'

    Returns:
        Final graph state (IncidentState) with incident_id populated on success.
    """
    initial_state: IncidentState = {
        "raw_log":         raw_log,
        "source":          source,
        "parsed":          None,
        "error_type":      None,
        "message":         "",
        "severity":        "ERROR",
        "stack_trace":     None,
        "timestamp":       None,
        "gemini_summary":  None,
        "gemini_category": None,
        "incident_id":     None,
        "stored":          False,
        "error":           None,
    }
    return await incident_graph.ainvoke(initial_state)
