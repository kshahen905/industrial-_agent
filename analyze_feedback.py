import os
import json
from feedback_db import get_negative_feedback
from langchain_ollama import OllamaLLM
from config import DEFAULT_MODEL, OLLAMA_BASE_URL

# Define categories
CATEGORIES = [
    "Hallucination",
    "Tool Misuse / Tool Error",
    "Incorrect Reasoning",
    "Wrong Tone / Style",
    "Incomplete Answer",
    "Dangerous Advice"
]

PROMPT_TEMPLATE = """You are a Judge LLM analyzing negative feedback on an AI assistant.
Your task is to classify the failure into ONE of the following categories:
{categories}

User Input: {user_input}
Agent Response: {agent_response}
User Comment: {optional_comment}

Analyze the interaction and the user's comment, then output ONLY the category name that best describes the failure. No explanation.
"""

def analyze_feedback():
    print("Fetching negative feedback from database...")
    negative_records = get_negative_feedback()
    
    if not negative_records:
        print("No negative feedback found in the database.")
        return
        
    print(f"Found {len(negative_records)} negative feedback records.")
    
    # Initialize the LLM
    print(f"Initializing LLM ({DEFAULT_MODEL})...")
    try:
        llm = OllamaLLM(model=DEFAULT_MODEL, base_url=OLLAMA_BASE_URL, temperature=0.1)
    except Exception as e:
        print(f"Failed to initialize LLM: {e}")
        return

    results = {category: 0 for category in CATEGORIES}
    analyzed_data = []

    print("Analyzing records...")
    for record in negative_records:
        prompt = PROMPT_TEMPLATE.format(
            categories="\n".join([f"- {c}" for c in CATEGORIES]),
            user_input=record['user_input'],
            agent_response=record['agent_response'],
            optional_comment=record['optional_comment']
        )
        
        try:
            # Call LLM
            response = llm.invoke(prompt).strip()
            
            # Map response to category
            matched_category = "Unknown"
            for cat in CATEGORIES:
                if cat.lower() in response.lower():
                    matched_category = cat
                    break
            
            if matched_category == "Unknown":
                # Fallback mapping if strict match fails
                if "hallucin" in response.lower(): matched_category = "Hallucination"
                elif "incomplete" in response.lower(): matched_category = "Incomplete Answer"
                elif "danger" in response.lower(): matched_category = "Dangerous Advice"
                elif "reasoning" in response.lower(): matched_category = "Incorrect Reasoning"
                else:
                    # Add unmapped category to results if needed or just mark as Incorrect Reasoning
                    matched_category = "Incorrect Reasoning"
                    
            results[matched_category] += 1
            
            analyzed_data.append({
                "user_input": record['user_input'],
                "category": matched_category,
                "comment": record['optional_comment']
            })
            print(f"Record {record['id']} classified as: {matched_category}")
            
        except Exception as e:
            print(f"Error analyzing record {record['id']}: {e}")

    # Calculate percentages and generate report
    total_failures = len(negative_records)
    
    report_content = f"""# Post-Deployment Drift & Failure Report

## Executive Summary
Total Negative Interactions Analyzed: {total_failures}

## Failure Categorization Breakdown
"""
    for cat, count in results.items():
        if count > 0:
            percentage = (count / total_failures) * 100
            report_content += f"- **{cat}**: {count} ({percentage:.1f}%)\n"
            
    report_content += "\n## Common Failure Patterns Identified\n\n"
    
    # Add patterns based on data
    for cat, count in results.items():
        if count > 0:
            report_content += f"### {cat}\n"
            for item in analyzed_data:
                if item["category"] == cat:
                    report_content += f"- *User Issue*: {item['user_input']}\n"
                    report_content += f"  *Feedback*: {item['comment']}\n\n"
                    
    # Recommendations
    report_content += """## Actionable Recommendations
1. **Address Dangerous Advice**: The system prompt must explicitly forbid the agent from suggesting destructive commands (like `rm -rf`, `kubectl delete all`, `git push --force`) without heavy warnings and verifying context.
2. **Reduce Hallucinations**: Ensure the agent relies ONLY on retrieved documentation or explicitly states when it doesn't know the exact fix. Reinstalling core components should be a last resort.
3. **Improve Completeness**: Agents should explain the 'why' alongside the 'how' instead of just restating the error.
"""

    with open("drift_report.md", "w") as f:
        f.write(report_content)
        
    print("Analysis complete! Report saved to drift_report.md")

if __name__ == "__main__":
    analyze_feedback()
