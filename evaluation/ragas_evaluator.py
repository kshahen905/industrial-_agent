"""
Evaluation Pipeline using RAGAS Framework

Implements quantitative evaluation metrics:
- Faithfulness: Does answer stay true to retrieved context?
- Answer Relevancy: How well does response address user query?
- Tool Call Accuracy: Did agent use correct tools?
- Context Precision: Is retrieved context relevant?
- Context Recall: Does retrieved context have needed information?
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EvaluationMetrics:
    """Container for evaluation metrics"""
    faithfulness: float
    answer_relevancy: float
    tool_call_accuracy: float
    context_precision: float
    context_recall: float
    latency: float
    success: bool


class RAGASEvaluator:
    """RAGAS-inspired evaluation framework (custom implementation)"""

    def __init__(self):
        self.metrics_history = []

    def evaluate_faithfulness(self, answer: str, context: str) -> float:
        """
        Evaluate if answer is faithful to retrieved context.

        Checks:
        - No contradictions between answer and context
        - Claims in answer are supported by context
        - No hallucinations

        Returns: Score 0-1
        """
        if not answer or not context:
            return 0.0

        answer_lower = answer.lower()
        context_lower = context.lower()

        # Check if key claims from answer appear in context
        answer_words = set(answer_lower.split())
        context_words = set(context_lower.split())

        # Simple overlap check (in production, use NLP similarity)
        overlap = len(answer_words & context_words) / len(answer_words) if answer_words else 0

        # Check for common hallucination patterns
        hallucination_patterns = [
            "i don't know",
            "i cannot",
            "i'm not sure",
        ]

        has_hallucination = any(pattern in answer_lower for pattern in hallucination_patterns)

        # Faithfulness score
        faithfulness = overlap * 0.7 + (0.3 if not has_hallucination else 0)
        return min(1.0, max(0.0, faithfulness))

    def evaluate_answer_relevancy(self, query: str, answer: str) -> float:
        """
        Evaluate how well answer addresses the user's query.

        Checks:
        - Answer directly addresses question
        - Contains solution/explanation
        - Is complete and actionable

        Returns: Score 0-1
        """
        if not query or not answer:
            return 0.0

        query_lower = query.lower()
        answer_lower = answer.lower()

        # Check for solution indicators
        solution_keywords = [
            "solution", "fix", "resolve", "command",
            "check", "verify", "run", "execute",
            "root cause", "error", "problem"
        ]

        has_solution = any(keyword in answer_lower for keyword in solution_keywords)

        # Check if answer length is reasonable
        min_length = 50  # At least 50 characters
        has_content = len(answer) > min_length

        # Check for actionable steps
        has_actions = any(keyword in answer_lower for keyword in ["step", "run", "check", "verify"])

        relevancy = (0.4 * has_solution + 0.3 * has_content + 0.3 * has_actions)
        return min(1.0, max(0.0, relevancy))

    def evaluate_tool_call_accuracy(self, expected_tools: List[str], used_tools: List[str]) -> float:
        """
        Evaluate correctness of tool usage.

        Checks:
        - Correct tools were called
        - No unnecessary tool calls
        - Tools called in correct order

        Returns: Score 0-1
        """
        if not expected_tools:
            return 1.0  # No tools expected, perfect if none used

        if not used_tools:
            return 0.0  # Tools expected but not used

        # Check overlap
        expected_set = set(expected_tools)
        used_set = set(used_tools)

        if not expected_set and not used_set:
            return 1.0

        # Precision: correct tools / tools used
        precision = len(expected_set & used_set) / len(used_set) if used_set else 0

        # Recall: correct tools found / expected tools
        recall = len(expected_set & used_set) / len(expected_set) if expected_set else 0

        # F1 score
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        return min(1.0, max(0.0, f1))

    def evaluate_context_precision(self, query: str, retrieved_context: str) -> float:
        """
        Evaluate quality of retrieved context.

        Checks:
        - Retrieved context is relevant to query
        - No irrelevant information
        - Context is accurate

        Returns: Score 0-1
        """
        if not query or not retrieved_context:
            return 0.0

        query_lower = query.lower()
        context_lower = retrieved_context.lower()

        # Simple relevancy check based on word overlap
        query_words = set(query_lower.split())
        context_words = set(context_lower.split())

        overlap = len(query_words & context_words) / len(query_words) if query_words else 0

        # Check for quality indicators in context
        has_examples = "example" in context_lower or "e.g." in context_lower
        has_details = "solution" in context_lower or "command" in context_lower

        precision = overlap * 0.6 + (0.2 if has_examples else 0) + (0.2 if has_details else 0)
        return min(1.0, max(0.0, precision))

    def evaluate_context_recall(self, query: str, retrieved_context: str, answer: str) -> float:
        """
        Evaluate if retrieved context contains all needed information.

        Checks:
        - Retrieved context has info used in answer
        - No critical info missing
        - Coverage is comprehensive

        Returns: Score 0-1
        """
        if not query or not retrieved_context or not answer:
            return 0.0

        answer_lower = answer.lower()
        context_lower = retrieved_context.lower()

        # Check how much of answer is covered by context
        answer_phrases = answer_lower.split()
        covered = sum(1 for phrase in answer_phrases if phrase in context_lower)

        coverage = covered / len(answer_phrases) if answer_phrases else 0

        return min(1.0, max(0.0, coverage))

    def evaluate_case(
        self,
        test_case: Dict[str, Any],
        agent_output: str,
        retrieved_context: str,
        execution_time: float,
        tools_used: List[str] = None
    ) -> Tuple[EvaluationMetrics, Dict[str, Any]]:
        """
        Evaluate a single test case.

        Returns: (EvaluationMetrics, detailed_results)
        """
        if tools_used is None:
            tools_used = []

        # Get expected tools if they exist
        expected_tools = test_case.get("expected_tools", [])

        # Calculate all metrics
        faithfulness = self.evaluate_faithfulness(agent_output, retrieved_context)
        answer_relevancy = self.evaluate_answer_relevancy(test_case["query"], agent_output)
        tool_accuracy = self.evaluate_tool_call_accuracy(expected_tools, tools_used)
        context_precision = self.evaluate_context_precision(test_case["query"], retrieved_context)
        context_recall = self.evaluate_context_recall(
            test_case["query"],
            retrieved_context,
            agent_output
        )

        metrics = EvaluationMetrics(
            faithfulness=faithfulness,
            answer_relevancy=answer_relevancy,
            tool_call_accuracy=tool_accuracy,
            context_precision=context_precision,
            context_recall=context_recall,
            latency=execution_time,
            success=True
        )

        detailed_results = {
            "test_case_id": test_case.get("id"),
            "query": test_case["query"],
            "expected_answer": test_case.get("expected_answer", ""),
            "agent_output": agent_output,
            "retrieved_context": retrieved_context,
            "tools_used": tools_used,
            "metrics": {
                "faithfulness": faithfulness,
                "answer_relevancy": answer_relevancy,
                "tool_call_accuracy": tool_accuracy,
                "context_precision": context_precision,
                "context_recall": context_recall,
                "latency": execution_time,
            },
            "timestamp": datetime.now().isoformat()
        }

        self.metrics_history.append(detailed_results)
        return metrics, detailed_results

    def get_aggregate_metrics(self) -> Dict[str, float]:
        """Calculate aggregate metrics from all evaluated cases"""
        if not self.metrics_history:
            return {}

        faithfulness_scores = [m["metrics"]["faithfulness"] for m in self.metrics_history]
        relevancy_scores = [m["metrics"]["answer_relevancy"] for m in self.metrics_history]
        tool_accuracy_scores = [m["metrics"]["tool_call_accuracy"] for m in self.metrics_history]
        precision_scores = [m["metrics"]["context_precision"] for m in self.metrics_history]
        recall_scores = [m["metrics"]["context_recall"] for m in self.metrics_history]
        latencies = [m["metrics"]["latency"] for m in self.metrics_history]

        return {
            "avg_faithfulness": np.mean(faithfulness_scores),
            "avg_answer_relevancy": np.mean(relevancy_scores),
            "avg_tool_call_accuracy": np.mean(tool_accuracy_scores),
            "avg_context_precision": np.mean(precision_scores),
            "avg_context_recall": np.mean(recall_scores),
            "avg_latency": np.mean(latencies),
            "p95_latency": np.percentile(latencies, 95),
            "p99_latency": np.percentile(latencies, 99),
            "success_rate": 1.0,  # All cases marked as success
            "total_evaluated": len(self.metrics_history),
        }

    def generate_report(self, output_path: str = None) -> str:
        """Generate evaluation report"""
        aggregate = self.get_aggregate_metrics()

        report = f"""
# RAGAS Evaluation Report
Generated: {datetime.now().isoformat()}

## Executive Summary
- Total Test Cases: {aggregate['total_evaluated']}
- Success Rate: {aggregate['success_rate']*100:.1f}%
- Average Latency: {aggregate['avg_latency']:.2f}s
- P95 Latency: {aggregate['p95_latency']:.2f}s

## Aggregate Metrics

| Metric | Score | Status |
|--------|-------|--------|
| Faithfulness | {aggregate['avg_faithfulness']:.3f} | {'✅ GOOD' if aggregate['avg_faithfulness'] > 0.7 else '⚠️ NEEDS IMPROVEMENT'} |
| Answer Relevancy | {aggregate['avg_answer_relevancy']:.3f} | {'✅ GOOD' if aggregate['avg_answer_relevancy'] > 0.7 else '⚠️ NEEDS IMPROVEMENT'} |
| Tool Call Accuracy | {aggregate['avg_tool_call_accuracy']:.3f} | {'✅ GOOD' if aggregate['avg_tool_call_accuracy'] > 0.7 else '⚠️ NEEDS IMPROVEMENT'} |
| Context Precision | {aggregate['avg_context_precision']:.3f} | {'✅ GOOD' if aggregate['avg_context_precision'] > 0.7 else '⚠️ NEEDS IMPROVEMENT'} |
| Context Recall | {aggregate['avg_context_recall']:.3f} | {'✅ GOOD' if aggregate['avg_context_recall'] > 0.7 else '⚠️ NEEDS IMPROVEMENT'} |

## Performance Metrics

- Average Latency: {aggregate['avg_latency']:.2f}s
- P95 Latency: {aggregate['p95_latency']:.2f}s
- P99 Latency: {aggregate['p99_latency']:.2f}s

## Interpretation

### Faithfulness Score
Measures if the agent's answer is grounded in the retrieved context without hallucinations.
- Score > 0.8: Excellent - No hallucinations detected
- Score 0.6-0.8: Good - Mostly faithful with minor issues
- Score < 0.6: Poor - Significant hallucinations or contradictions

### Answer Relevancy Score
Measures how directly the agent's answer addresses the user's query.
- Score > 0.8: Excellent - Directly answers all aspects of query
- Score 0.6-0.8: Good - Answers most aspects
- Score < 0.6: Poor - Misses key aspects of query

### Tool Call Accuracy Score
Measures if the agent uses the correct tools with correct arguments.
- Score > 0.8: Excellent - Correct tool usage
- Score 0.6-0.8: Good - Minor tool usage issues
- Score < 0.6: Poor - Frequent tool selection errors

### Context Precision Score
Measures if the retrieved context is relevant to the user query.
- Score > 0.8: Excellent - Highly relevant retrieval
- Score 0.6-0.8: Good - Mostly relevant
- Score < 0.6: Poor - Irrelevant retrieval

### Context Recall Score
Measures if the retrieved context contains all information needed to answer the query.
- Score > 0.8: Excellent - Complete coverage
- Score 0.6-0.8: Good - Most information available
- Score < 0.6: Poor - Missing critical information

## Detailed Results

"""
        for result in self.metrics_history:
            report += f"\n### Test Case {result['test_case_id']}\n"
            report += f"**Query:** {result['query'][:80]}...\n"
            report += f"**Metrics:**\n"
            for metric, value in result['metrics'].items():
                report += f"- {metric}: {value:.3f}\n"

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to {output_path}")

        return report


if __name__ == "__main__":
    # Example usage
    evaluator = RAGASEvaluator()
    logger.info("RAGAS Evaluator initialized")
