"""
Enhanced evaluation framework using Azure AI Evaluation SDK.
Uses built-in evaluators + custom evaluators for comprehensive assessment.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

# Add parent to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent import LifeAdminAgent
from src.config import Config


def check_azure_eval_available() -> bool:
    """Check if Azure AI Evaluation SDK is installed."""
    try:
        from azure.ai.evaluation import evaluate
        return True
    except ImportError:
        return False


# ============================================================
# CUSTOM CODE-BASED EVALUATORS
# ============================================================

class ResponseLengthEvaluator:
    """Evaluates if response length is appropriate (not too short, not too long)."""
    
    def __init__(self, min_length: int = 20, max_length: int = 2000):
        self.min_length = min_length
        self.max_length = max_length
    
    def __call__(self, *, response: str, **kwargs) -> dict:
        length = len(response)
        
        if length < self.min_length:
            score = 1
            reason = f"Response too short ({length} chars, min: {self.min_length})"
        elif length > self.max_length:
            score = 2
            reason = f"Response too long ({length} chars, max: {self.max_length})"
        else:
            # Optimal range: scale from 3-5
            ratio = (length - self.min_length) / (self.max_length - self.min_length)
            if 0.1 <= ratio <= 0.6:
                score = 5
                reason = "Response length is optimal"
            elif ratio < 0.1:
                score = 3
                reason = "Response is brief but acceptable"
            else:
                score = 4
                reason = "Response is detailed but acceptable"
        
        return {
            "response_length_score": score,
            "response_length_reason": reason,
            "response_length_chars": length
        }


class ToolIndicatorEvaluator:
    """Evaluates if response indicates correct tool was called based on keywords."""
    
    # Map of tool names to response indicators
    TOOL_INDICATORS = {
        "add_document": ["saved", "document", "added", "tracking", "reminder"],
        "list_documents": ["documents", "total", "showing", "list"],
        "get_expiring_documents": ["expir", "days", "urgent", "warning", "soon"],
        "delete_document": ["deleted", "removed", "document"],
        "add_subscription": ["subscription", "saved", "$", "added", "tracking"],
        "list_subscriptions": ["subscriptions", "total", "showing"],
        "get_spending_summary": ["spending", "monthly", "yearly", "$", "total"],
        "get_trial_alerts": ["trial", "ending", "free", "alert"],
        "delete_subscription": ["deleted", "removed", "subscription"],
        "start_life_event": ["event", "created", "checklist", "tasks", "✅"],
        "get_checklist": ["checklist", "tasks", "progress", "%"],
        "mark_task_complete": ["complete", "marked", "progress", "✅"],
        "list_life_events": ["events", "life", "active", "showing"],
        "delete_life_event": ["deleted", "event", "removed"],
        "add_task_to_checklist": ["added", "task", "checklist"],
        "send_expiry_reminder": ["email", "sent", "reminder", "notification"],
        "get_daily_digest": ["digest", "urgent", "upcoming", "summary"],
    }
    
    def __call__(self, *, response: str, expected_tool: str, **kwargs) -> dict:
        if not response:
            return {
                "tool_indicator_score": 1,
                "tool_indicator_reason": "Empty response"
            }
        
        response_lower = response.lower()
        indicators = self.TOOL_INDICATORS.get(expected_tool, [])
        
        if not indicators:
            return {
                "tool_indicator_score": 3,
                "tool_indicator_reason": f"No indicators defined for {expected_tool}"
            }
        
        matches = sum(1 for ind in indicators if ind in response_lower)
        total = len(indicators)
        
        match_ratio = matches / total
        
        if match_ratio >= 0.6:
            score = 5
        elif match_ratio >= 0.4:
            score = 4
        elif match_ratio >= 0.2:
            score = 3
        elif match_ratio > 0:
            score = 2
        else:
            score = 1
        
        return {
            "tool_indicator_score": score,
            "tool_indicator_reason": f"Matched {matches}/{total} indicators for {expected_tool}",
            "tool_indicator_matches": matches
        }


class ErrorDetectionEvaluator:
    """Detects if response contains error indicators."""
    
    ERROR_PATTERNS = ["❌", "error", "failed", "could not", "unable to", "exception"]
    
    def __call__(self, *, response: str, **kwargs) -> dict:
        response_lower = response.lower()
        
        errors_found = [p for p in self.ERROR_PATTERNS if p in response_lower]
        
        if errors_found:
            return {
                "error_free_score": 1,
                "error_free_reason": f"Error indicators found: {errors_found}"
            }
        else:
            return {
                "error_free_score": 5,
                "error_free_reason": "No error indicators found"
            }


class ActionConfirmationEvaluator:
    """Evaluates if the agent confirmed actions with appropriate indicators."""
    
    CONFIRMATION_PATTERNS = ["✅", "saved", "created", "added", "deleted", "marked", "sent"]
    
    def __call__(self, *, response: str, expected_behavior: str, **kwargs) -> dict:
        response_lower = response.lower()
        expected_lower = expected_behavior.lower()
        
        # Check if this was an action request
        action_keywords = ["add", "create", "delete", "save", "mark", "send", "start"]
        is_action_request = any(kw in expected_lower for kw in action_keywords)
        
        if not is_action_request:
            return {
                "action_confirmation_score": 5,
                "action_confirmation_reason": "Not an action request"
            }
        
        confirmations = sum(1 for p in self.CONFIRMATION_PATTERNS if p in response_lower)
        
        if confirmations >= 2:
            score = 5
            reason = "Strong action confirmation"
        elif confirmations == 1:
            score = 4
            reason = "Action confirmed"
        else:
            score = 2
            reason = "No clear action confirmation found"
        
        return {
            "action_confirmation_score": score,
            "action_confirmation_reason": reason
        }


# ============================================================
# RESPONSE COLLECTION
# ============================================================

async def collect_agent_responses(
    test_data: List[Dict],
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
            
            # Prepare result - JSONL format for Azure AI Evaluation
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
    
    # Save to JSONL format (required by Azure AI Evaluation SDK)
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    
    print(f"✅ Saved {len(results)} responses to {output_path}")
    return str(output_file)


# ============================================================
# EVALUATION EXECUTION
# ============================================================

def run_basic_evaluation(responses_path: str, output_path: str = "evaluation/results.json") -> Dict:
    """
    Run evaluation using custom code-based evaluators.
    Use this when Azure AI Evaluation SDK is not available.
    """
    print("📊 Running basic evaluation...")
    
    # Load responses
    responses = []
    with open(responses_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                responses.append(json.loads(line))
    
    # Initialize evaluators
    evaluators = {
        "response_length": ResponseLengthEvaluator(),
        "tool_indicator": ToolIndicatorEvaluator(),
        "error_detection": ErrorDetectionEvaluator(),
        "action_confirmation": ActionConfirmationEvaluator()
    }
    
    # Run evaluation
    results = []
    metrics = {name: [] for name in evaluators.keys()}
    
    for item in responses:
        row_result = {**item}
        
        for name, evaluator in evaluators.items():
            eval_result = evaluator(
                response=item["response"],
                expected_tool=item.get("expected_tool", ""),
                expected_behavior=item.get("expected_behavior", "")
            )
            row_result.update(eval_result)
            
            # Collect scores for aggregation
            score_key = f"{name}_score"
            if score_key in eval_result:
                metrics[name].append(eval_result[score_key])
        
        results.append(row_result)
    
    # Calculate aggregates
    summary = {
        "total_evaluations": len(results),
        "timestamp": datetime.now().isoformat()
    }
    
    for name, scores in metrics.items():
        if scores:
            summary[f"avg_{name}"] = round(sum(scores) / len(scores), 2)
    
    # Overall score (average of all metrics)
    all_averages = [v for k, v in summary.items() if k.startswith("avg_")]
    if all_averages:
        summary["overall_score"] = round(sum(all_averages) / len(all_averages), 2)
    
    # Save results
    output_file = Path(output_path)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "summary": summary,
            "detailed_results": results
        }, f, indent=2, ensure_ascii=False)
    
    _print_summary(summary)
    print(f"\n✅ Full results saved to {output_path}")
    
    return summary


def run_azure_evaluation(
    responses_path: str,
    output_path: str = "evaluation/azure_results.json"
) -> Dict:
    """
    Run comprehensive evaluation using Azure AI Evaluation SDK.
    Combines built-in evaluators with custom evaluators.
    """
    if not check_azure_eval_available():
        print("⚠️ Azure AI Evaluation SDK not installed. Using basic evaluation.")
        return run_basic_evaluation(responses_path, output_path)
    
    from azure.ai.evaluation import (
        evaluate,
        CoherenceEvaluator,
        FluencyEvaluator,
        RelevanceEvaluator,
        OpenAIModelConfiguration
    )
    
    print("📊 Running Azure AI Evaluation...")
    
    # Configure model for prompt-based evaluators
    model_config = OpenAIModelConfiguration(
        type="openai",
        model=Config.MODEL_NAME,
        base_url=Config.MODEL_ENDPOINT,
        api_key=Config.GITHUB_TOKEN
    )
    
    # Initialize evaluators
    evaluators = {
        # Built-in prompt-based evaluators
        "coherence": CoherenceEvaluator(model_config=model_config),
        "fluency": FluencyEvaluator(model_config=model_config),
        "relevance": RelevanceEvaluator(model_config=model_config),
        # Custom code-based evaluators
        "response_length": ResponseLengthEvaluator(),
        "tool_indicator": ToolIndicatorEvaluator(),
        "error_detection": ErrorDetectionEvaluator(),
        "action_confirmation": ActionConfirmationEvaluator()
    }
    
    # Run evaluation using evaluate() API
    result = evaluate(
        data=responses_path,
        evaluators=evaluators,
        evaluator_config={
            "coherence": {
                "column_mapping": {
                    "query": "${data.query}",
                    "response": "${data.response}"
                }
            },
            "fluency": {
                "column_mapping": {
                    "response": "${data.response}"
                }
            },
            "relevance": {
                "column_mapping": {
                    "query": "${data.query}",
                    "response": "${data.response}"
                }
            },
            "response_length": {
                "column_mapping": {
                    "response": "${data.response}"
                }
            },
            "tool_indicator": {
                "column_mapping": {
                    "response": "${data.response}",
                    "expected_tool": "${data.expected_tool}"
                }
            },
            "error_detection": {
                "column_mapping": {
                    "response": "${data.response}"
                }
            },
            "action_confirmation": {
                "column_mapping": {
                    "response": "${data.response}",
                    "expected_behavior": "${data.expected_behavior}"
                }
            }
        },
        output_path=output_path
    )
    
    print(f"\n✅ Azure AI Evaluation complete. Results saved to {output_path}")
    return result


def _print_summary(summary: Dict):
    """Print evaluation summary in a formatted way."""
    print(f"\n{'='*50}")
    print("📈 **Evaluation Summary**")
    print(f"{'='*50}")
    print(f"   Total evaluations: {summary.get('total_evaluations', 0)}")
    
    for key, value in summary.items():
        if key.startswith("avg_"):
            metric_name = key.replace("avg_", "").replace("_", " ").title()
            print(f"   {metric_name}: {value}/5")
    
    if "overall_score" in summary:
        print(f"\n   🏆 Overall Score: {summary['overall_score']}/5")


# ============================================================
# MAIN PIPELINE
# ============================================================

async def run_evaluation_pipeline(
    test_data_path: str = "evaluation/test_dataset.json",
    use_azure: bool = False
) -> Dict:
    """
    Run the complete evaluation pipeline.
    
    Args:
        test_data_path: Path to test dataset JSON
        use_azure: Whether to use Azure AI Evaluation SDK
    """
    test_path = Path(test_data_path)
    
    if not test_path.exists():
        print(f"❌ Test dataset not found at {test_data_path}")
        return {}
    
    with open(test_path, encoding="utf-8") as f:
        test_data = json.load(f)
    
    print(f"📂 Loaded {len(test_data)} test cases")
    
    # Step 1: Collect responses
    responses_path = await collect_agent_responses(
        test_data,
        output_path="evaluation/responses.jsonl"
    )
    
    # Step 2: Run evaluation
    if use_azure and check_azure_eval_available():
        summary = run_azure_evaluation(responses_path)
    else:
        summary = run_basic_evaluation(responses_path)
    
    return summary


async def main():
    """Run complete evaluation pipeline."""
    summary = await run_evaluation_pipeline(use_azure=True)
    return summary


if __name__ == "__main__":
    asyncio.run(main())
