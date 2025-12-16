"""
Evaluation framework for Life Admin Assistant.
Tests agent responses for quality, accuracy, and helpfulness.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import LifeAdminAgent
from src.config import Config


class ResponseEvaluator:
    """
    Custom code-based evaluator for response quality.
    Checks if responses are helpful and complete.
    """
    
    def __init__(self):
        pass
    
    def __call__(self, *, response: str, expected_behavior: str, **kwargs) -> dict:
        """Evaluate response quality based on expected behavior."""
        score = 0
        reasons = []
        
        # Check if response is not empty
        if response and len(response.strip()) > 0:
            score += 1
            reasons.append("Response is not empty")
        else:
            reasons.append("Response is empty")
            return {"response_quality_score": 0, "response_quality_reason": "Empty response"}
        
        # Check if response contains relevant keywords from expected behavior
        expected_lower = expected_behavior.lower()
        response_lower = response.lower()
        
        # Extract key concepts from expected behavior
        key_concepts = {
            "add": ["added", "saved", "created", "tracked", "✅"],
            "show": ["showing", "here", "list", "found"],
            "list": ["showing", "here", "list", "found", "total"],
            "delete": ["deleted", "removed", "✅"],
            "mark": ["marked", "complete", "✅", "progress"],
            "send": ["sent", "email", "notification"],
            "checklist": ["tasks", "progress", "%", "items"],
            "expir": ["days", "expir", "warning", "urgent"],
            "spending": ["$", "month", "year", "total"],
        }
        
        matched_concepts = 0
        for concept, keywords in key_concepts.items():
            if concept in expected_lower:
                if any(kw in response_lower for kw in keywords):
                    matched_concepts += 1
        
        if matched_concepts > 0:
            score += min(matched_concepts, 3)  # Max 3 points for concept matching
            reasons.append(f"Matched {matched_concepts} expected concepts")
        
        # Check for error indicators
        if "❌" in response or "error" in response_lower:
            if "should" not in expected_lower or "error" not in expected_lower:
                score -= 1
                reasons.append("Response contains unexpected error")
        
        # Normalize score to 1-5 scale
        normalized_score = max(1, min(5, score + 1))
        
        return {
            "response_quality_score": normalized_score,
            "response_quality_reason": "; ".join(reasons)
        }


class ToolUsageEvaluator:
    """
    Custom code-based evaluator for tool usage accuracy.
    Checks if the agent would call the correct tool.
    """
    
    # Map of tool names to response indicators
    TOOL_INDICATORS = {
        "add_document": ["saved", "document", "expir", "reminder"],
        "list_documents": ["documents", "total", "expir"],
        "get_expiring_documents": ["expir", "days", "urgent", "warning"],
        "delete_document": ["deleted", "removed", "document"],
        "add_subscription": ["subscription", "saved", "$", "month"],
        "list_subscriptions": ["subscriptions", "total", "$"],
        "get_spending_summary": ["spending", "monthly", "yearly", "$"],
        "get_trial_alerts": ["trial", "ending", "free"],
        "delete_subscription": ["deleted", "removed", "subscription"],
        "start_life_event": ["event", "created", "checklist", "tasks"],
        "get_checklist": ["checklist", "tasks", "progress", "%"],
        "mark_task_complete": ["complete", "marked", "progress"],
        "list_life_events": ["events", "life", "active"],
        "delete_life_event": ["deleted", "event"],
        "add_task_to_checklist": ["added", "task", "checklist"],
        "send_expiry_reminder": ["email", "sent", "reminder"],
        "get_daily_digest": ["digest", "urgent", "upcoming"],
    }
    
    def __init__(self):
        pass
    
    def __call__(self, *, response: str, expected_tool: str, **kwargs) -> dict:
        """Check if response indicates correct tool was used."""
        if not response:
            return {
                "tool_accuracy_score": 0,
                "tool_accuracy_reason": "Empty response"
            }
        
        response_lower = response.lower()
        indicators = self.TOOL_INDICATORS.get(expected_tool, [])
        
        matches = sum(1 for ind in indicators if ind in response_lower)
        total = len(indicators) if indicators else 1
        
        accuracy = matches / total if total > 0 else 0
        
        # Convert to 1-5 scale
        score = max(1, min(5, int(accuracy * 4) + 1))
        
        return {
            "tool_accuracy_score": score,
            "tool_accuracy_reason": f"Matched {matches}/{total} tool indicators for {expected_tool}"
        }


async def collect_agent_responses(
    test_data: list,
    output_path: str = "evaluation/responses.jsonl"
) -> str:
    """
    Run the agent on test queries and collect responses.
    Returns path to the JSONL file with responses.
    """
    print("🤖 Initializing agent...")
    agent = LifeAdminAgent()
    
    results = []
    
    print(f"📝 Running {len(test_data)} test queries...")
    for i, item in enumerate(test_data):
        query = item["query"]
        print(f"  [{i+1}/{len(test_data)}] {query[:50]}...")
        
        try:
            # Reset conversation for each test
            agent.reset_conversation()
            
            # Get response
            response = await agent.chat(query)
            
            results.append({
                "query": query,
                "response": response,
                "expected_tool": item.get("expected_tool", ""),
                "expected_behavior": item.get("expected_behavior", "")
            })
        except Exception as e:
            print(f"    ❌ Error: {e}")
            results.append({
                "query": query,
                "response": f"Error: {str(e)}",
                "expected_tool": item.get("expected_tool", ""),
                "expected_behavior": item.get("expected_behavior", "")
            })
    
    # Save to JSONL
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w") as f:
        for result in results:
            f.write(json.dumps(result) + "\n")
    
    print(f"✅ Saved {len(results)} responses to {output_path}")
    return str(output_file)


def run_evaluation(responses_path: str, output_path: str = "evaluation/results.json"):
    """
    Run evaluation on collected responses.
    Uses custom evaluators for response quality and tool usage.
    """
    print("📊 Running evaluation...")
    
    # Load responses
    responses = []
    with open(responses_path, "r") as f:
        for line in f:
            responses.append(json.loads(line))
    
    # Initialize evaluators
    response_evaluator = ResponseEvaluator()
    tool_evaluator = ToolUsageEvaluator()
    
    # Run evaluation
    results = []
    total_response_score = 0
    total_tool_score = 0
    
    for item in responses:
        response_result = response_evaluator(
            response=item["response"],
            expected_behavior=item["expected_behavior"]
        )
        
        tool_result = tool_evaluator(
            response=item["response"],
            expected_tool=item["expected_tool"]
        )
        
        combined = {
            **item,
            **response_result,
            **tool_result
        }
        results.append(combined)
        
        total_response_score += response_result["response_quality_score"]
        total_tool_score += tool_result["tool_accuracy_score"]
    
    # Calculate aggregates
    count = len(results)
    summary = {
        "total_evaluations": count,
        "avg_response_quality": round(total_response_score / count, 2) if count > 0 else 0,
        "avg_tool_accuracy": round(total_tool_score / count, 2) if count > 0 else 0,
        "overall_score": round((total_response_score + total_tool_score) / (count * 2), 2) if count > 0 else 0
    }
    
    # Save results
    output_file = Path(output_path)
    with open(output_file, "w") as f:
        json.dump({
            "summary": summary,
            "detailed_results": results
        }, f, indent=2)
    
    print(f"\n📈 **Evaluation Summary**")
    print(f"   Total evaluations: {summary['total_evaluations']}")
    print(f"   Avg response quality: {summary['avg_response_quality']}/5")
    print(f"   Avg tool accuracy: {summary['avg_tool_accuracy']}/5")
    print(f"   Overall score: {summary['overall_score']}/5")
    print(f"\n✅ Full results saved to {output_path}")
    
    return summary


async def main():
    """Run complete evaluation pipeline."""
    # Load test dataset
    test_data_path = Path(__file__).parent / "test_dataset.json"
    
    if not test_data_path.exists():
        print(f"❌ Test dataset not found at {test_data_path}")
        return
    
    with open(test_data_path) as f:
        test_data = json.load(f)
    
    print(f"📂 Loaded {len(test_data)} test cases")
    
    # Step 1: Collect responses
    responses_path = await collect_agent_responses(
        test_data,
        output_path="evaluation/responses.jsonl"
    )
    
    # Step 2: Run evaluation
    summary = run_evaluation(
        responses_path,
        output_path="evaluation/results.json"
    )
    
    return summary


if __name__ == "__main__":
    asyncio.run(main())
