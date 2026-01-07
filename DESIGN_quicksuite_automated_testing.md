# QuickSuite Automated Testing - Implementation Design

This document describes the implementation of standalone automated testing for QuickSuite Knowledge Base retrieval accuracy.

## Overview

The automated testing system evaluates Knowledge Base retrieval quality by running a suite of predefined queries against ground truth data, measuring precision, recall, faithfulness, and other metrics.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Automated Test Pipeline                       │
│                                                                  │
│  Ground Truth    Test Runner      Evaluator       Reporter      │
│  ┌─────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │ Queries │───▶│  pytest  │───▶│ Accuracy │───▶│  JSON +  │   │
│  │ Expected│    │   CLI    │    │ Metrics  │    │ Console  │   │
│  │ Results │    └──────────┘    └──────────┘    └──────────┘   │
│  └─────────┘           │               │               │        │
│                        ▼               ▼               ▼        │
│                   KB API          LLM Judge       test_results/ │
└─────────────────────────────────────────────────────────────────┘
```

## Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         Test Execution Flow                         │
└────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────┐
                    │   run_tests.py      │
                    │   (Entry Point)     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
     │ ground_truth│  │  evaluator  │  │   reporter  │
     │   .py       │  │   .py       │  │   .py       │
     │             │  │             │  │             │
     │ Test cases  │  │ Metrics:    │  │ Output:     │
     │ with        │  │ - Precision │  │ - JSON      │
     │ expected    │  │ - Recall    │  │ - Console   │
     │ results     │  │ - F1, MRR   │  │ - HTML      │
     └─────────────┘  │ - Faith.    │  └─────────────┘
                      │ - Relevance │
                      └──────┬──────┘
                             │
                    ┌────────┴────────┐
                    ▼                 ▼
           ┌─────────────┐   ┌─────────────┐
           │ Bedrock KB  │   │ Bedrock LLM │
           │ retrieve()  │   │ (Judge)     │
           │ RAG()       │   │ Faithfulness│
           └─────────────┘   └─────────────┘
```

## Project Structure

```
knowledgeDB/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # pytest fixtures
│   ├── requirements.txt            # test dependencies
│   ├── run_tests.py                # CLI entry point
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   └── ground_truth.py         # test dataset
│   │
│   ├── evaluators/
│   │   ├── __init__.py
│   │   └── retrieval_accuracy.py   # metrics calculations
│   │
│   ├── reporters/
│   │   ├── __init__.py
│   │   ├── json_reporter.py        # JSON output
│   │   └── console_reporter.py     # terminal output
│   │
│   └── test_retrieval.py           # pytest test cases
│
└── test_results/                   # output directory
    ├── accuracy_report.json
    └── screenshots/                # optional visual evidence
```

## Implementation Files

### 1. Test Dependencies

**File: `tests/requirements.txt`**

```
boto3>=1.34.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
rich>=13.0.0           # pretty console output
```

### 2. Ground Truth Dataset

**File: `tests/data/ground_truth.py`**

```python
"""
Ground truth dataset for QuickSuite Knowledge Base accuracy testing.

Each test case includes:
- query: The search query to test
- expected_sources: Documents that should be retrieved
- expected_chunks: Specific text that should appear in results
- expected_answer_contains: Keywords expected in RAG response
- marketplace: CN, US, or BOTH
- category: Test category for grouping results
"""

from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TestCase:
    id: str
    query: str
    expected_sources: List[str]
    expected_chunks: List[str]
    expected_answer_contains: List[str]
    marketplace: str
    category: str
    description: Optional[str] = None

GROUND_TRUTH_DATASET: List[TestCase] = [
    TestCase(
        id="q001",
        query="What are the seller registration requirements for China marketplace?",
        expected_sources=["seller-guide-cn.md"],
        expected_chunks=[
            "Chinese business license",
            "Chinese bank account",
            "Legal representative ID card"
        ],
        expected_answer_contains=["business license", "bank account", "registration"],
        marketplace="CN",
        category="registration",
        description="Basic CN registration requirements"
    ),
    TestCase(
        id="q002",
        query="What is the monthly fee for professional sellers in the US?",
        expected_sources=["seller-guide-us.md"],
        expected_chunks=["Professional Seller: $39.99/month"],
        expected_answer_contains=["$39.99", "month"],
        marketplace="US",
        category="pricing",
        description="US professional seller pricing"
    ),
    TestCase(
        id="q003",
        query="How many FBA warehouses are there in America?",
        expected_sources=["seller-guide-us.md"],
        expected_chunks=["175+ fulfillment centers across the US"],
        expected_answer_contains=["175", "fulfillment"],
        marketplace="US",
        category="fulfillment",
        description="US FBA warehouse count"
    ),
    TestCase(
        id="q004",
        query="What certifications are required for selling electronics in China?",
        expected_sources=["seller-guide-cn.md"],
        expected_chunks=["CCC Certification"],
        expected_answer_contains=["CCC", "certification"],
        marketplace="CN",
        category="compliance",
        description="CN electronics compliance"
    ),
    TestCase(
        id="q005",
        query="Compare seller fees between CN and US marketplaces",
        expected_sources=["seller-guide-cn.md", "seller-guide-us.md"],
        expected_chunks=["¥300/month", "$39.99/month"],
        expected_answer_contains=["¥300", "$39.99"],
        marketplace="BOTH",
        category="pricing",
        description="Cross-marketplace fee comparison"
    ),
    TestCase(
        id="q006",
        query="What are the peak shopping days for US sellers?",
        expected_sources=["seller-guide-us.md"],
        expected_chunks=["Prime Day, Black Friday, Cyber Monday"],
        expected_answer_contains=["Prime Day", "Black Friday"],
        marketplace="US",
        category="marketing",
        description="US peak shopping events"
    ),
    TestCase(
        id="q007",
        query="Double 11 shopping festival requirements",
        expected_sources=["seller-guide-cn.md"],
        expected_chunks=["11.11 (Double 11): Largest shopping event"],
        expected_answer_contains=["11.11", "November"],
        marketplace="CN",
        category="marketing",
        description="CN Double 11 event"
    ),
    TestCase(
        id="q008",
        query="Alipay payment integration",
        expected_sources=["seller-guide-cn.md"],
        expected_chunks=["Alipay"],
        expected_answer_contains=["Alipay", "payment"],
        marketplace="CN",
        category="payments",
        description="CN payment methods"
    ),
]

def get_test_cases_by_category(category: str) -> List[TestCase]:
    """Filter test cases by category."""
    return [tc for tc in GROUND_TRUTH_DATASET if tc.category == category]

def get_test_cases_by_marketplace(marketplace: str) -> List[TestCase]:
    """Filter test cases by marketplace."""
    return [tc for tc in GROUND_TRUTH_DATASET if tc.marketplace == marketplace]
```

### 3. Retrieval Accuracy Evaluator

**File: `tests/evaluators/retrieval_accuracy.py`**

```python
"""
Retrieval accuracy evaluator for QuickSuite Knowledge Base.

Metrics:
- Precision: % of retrieved docs that are relevant
- Recall: % of relevant docs that were retrieved
- F1 Score: Harmonic mean of precision & recall
- MRR: Mean Reciprocal Rank
- Faithfulness: Is the answer grounded in retrieved docs? (LLM-judged)
- Relevance: Does the response contain expected information?
"""

import boto3
import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

@dataclass
class RetrievalResult:
    """Result from a knowledge base query."""
    query: str
    retrieved_chunks: List[Dict]
    generated_answer: str
    sources: List[str]
    latency_ms: float

@dataclass
class AccuracyScore:
    """Accuracy metrics for a single test case."""
    precision: float
    recall: float
    f1_score: float
    mrr: float
    faithfulness: float
    relevance: float
    passed: bool
    details: Dict = field(default_factory=dict)

class RetrievalAccuracyEvaluator:
    """Evaluate knowledge base retrieval accuracy."""
    
    # Thresholds for pass/fail
    THRESHOLDS = {
        'f1_score': 0.70,
        'faithfulness': 0.80,
        'relevance': 0.70,
    }
    
    def __init__(
        self, 
        kb_id: str, 
        region: str = "us-west-2",
        model_arn: str = "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
        judge_model: str = "anthropic.claude-3-haiku-20240307-v1:0"
    ):
        self.kb_id = kb_id
        self.region = region
        self.model_arn = model_arn
        self.judge_model = judge_model
        
        self.bedrock_agent = boto3.client('bedrock-agent-runtime', region_name=region)
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        
    def query_knowledge_base(self, query: str, num_results: int = 5) -> RetrievalResult:
        """Query the knowledge base and get retrieved chunks + generated answer."""
        start = time.time()
        
        # Retrieve documents
        retrieve_response = self.bedrock_agent.retrieve(
            knowledgeBaseId=self.kb_id,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': num_results
                }
            }
        )
        
        # Get RAG response
        rag_response = self.bedrock_agent.retrieve_and_generate(
            input={'text': query},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': self.kb_id,
                    'modelArn': self.model_arn
                }
            }
        )
        
        latency = (time.time() - start) * 1000
        
        # Extract chunks and sources
        chunks = []
        sources = set()
        for result in retrieve_response.get('retrievalResults', []):
            chunk = {
                'content': result.get('content', {}).get('text', ''),
                'score': result.get('score', 0),
                'source': self._extract_source(result)
            }
            chunks.append(chunk)
            sources.add(chunk['source'])
            
        return RetrievalResult(
            query=query,
            retrieved_chunks=chunks,
            generated_answer=rag_response.get('output', {}).get('text', ''),
            sources=list(sources),
            latency_ms=latency
        )
    
    def _extract_source(self, result: Dict) -> str:
        """Extract source filename from retrieval result."""
        location = result.get('location', {})
        s3_location = location.get('s3Location', {})
        uri = s3_location.get('uri', '')
        # Extract filename from s3://bucket/path/filename.md
        if '/' in uri:
            return uri.split('/')[-1]
        return uri
        
    def evaluate_precision(self, result: RetrievalResult, expected_sources: List[str]) -> float:
        """Calculate precision: relevant retrieved / total retrieved."""
        if not result.retrieved_chunks:
            return 0.0
            
        relevant_count = 0
        for chunk in result.retrieved_chunks:
            for expected in expected_sources:
                if expected in chunk['source']:
                    relevant_count += 1
                    break
                    
        return relevant_count / len(result.retrieved_chunks)
        
    def evaluate_recall(self, result: RetrievalResult, expected_chunks: List[str]) -> float:
        """Calculate recall: found chunks / expected chunks."""
        if not expected_chunks:
            return 1.0
            
        retrieved_text = ' '.join([c['content'] for c in result.retrieved_chunks]).lower()
        found_count = sum(1 for exp in expected_chunks if exp.lower() in retrieved_text)
        
        return found_count / len(expected_chunks)
        
    def evaluate_mrr(self, result: RetrievalResult, expected_sources: List[str]) -> float:
        """Calculate Mean Reciprocal Rank."""
        for i, chunk in enumerate(result.retrieved_chunks):
            for expected in expected_sources:
                if expected in chunk['source']:
                    return 1.0 / (i + 1)
        return 0.0
        
    def evaluate_faithfulness(self, result: RetrievalResult) -> float:
        """Use LLM judge to evaluate if answer is grounded in retrieved docs."""
        context = '\n\n'.join([f"[Source {i+1}]: {c['content'][:500]}" 
                               for i, c in enumerate(result.retrieved_chunks[:3])])
        
        prompt = f"""Evaluate if the following answer is faithfully grounded in the provided context.

CONTEXT:
{context}

ANSWER:
{result.generated_answer}

Scoring criteria:
- 1.0 = Answer is completely grounded in context, all claims supported
- 0.7-0.9 = Answer is mostly grounded, minor additions or interpretations
- 0.4-0.6 = Answer is partially grounded, some claims not in context
- 0.1-0.3 = Answer has little basis in context
- 0.0 = Answer contradicts context or is completely fabricated

Return ONLY a JSON object: {{"score": <float>, "reasoning": "<brief explanation>"}}"""

        try:
            response = self.bedrock.invoke_model(
                modelId=self.judge_model,
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 200
                })
            )
            
            result_body = json.loads(response['body'].read())
            llm_output = result_body['content'][0]['text']
            
            parsed = json.loads(llm_output)
            return float(parsed.get('score', 0.0))
        except Exception as e:
            logger.warning(f"Faithfulness evaluation failed: {e}")
            return 0.0
            
    def evaluate_relevance(self, result: RetrievalResult, expected_contains: List[str]) -> float:
        """Check if answer contains expected information."""
        if not expected_contains:
            return 1.0
            
        answer_lower = result.generated_answer.lower()
        found = sum(1 for exp in expected_contains if exp.lower() in answer_lower)
        
        return found / len(expected_contains)
        
    def evaluate(self, test_case) -> AccuracyScore:
        """Run full accuracy evaluation for a single test case."""
        result = self.query_knowledge_base(test_case.query)
        
        precision = self.evaluate_precision(result, test_case.expected_sources)
        recall = self.evaluate_recall(result, test_case.expected_chunks)
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        mrr = self.evaluate_mrr(result, test_case.expected_sources)
        faithfulness = self.evaluate_faithfulness(result)
        relevance = self.evaluate_relevance(result, test_case.expected_answer_contains)
        
        # Determine pass/fail
        passed = (
            f1 >= self.THRESHOLDS['f1_score'] and
            faithfulness >= self.THRESHOLDS['faithfulness'] and
            relevance >= self.THRESHOLDS['relevance']
        )
        
        return AccuracyScore(
            precision=round(precision, 3),
            recall=round(recall, 3),
            f1_score=round(f1, 3),
            mrr=round(mrr, 3),
            faithfulness=round(faithfulness, 3),
            relevance=round(relevance, 3),
            passed=passed,
            details={
                'query': test_case.query,
                'query_id': test_case.id,
                'category': test_case.category,
                'marketplace': test_case.marketplace,
                'retrieved_sources': result.sources,
                'expected_sources': test_case.expected_sources,
                'answer_preview': result.generated_answer[:300],
                'latency_ms': round(result.latency_ms, 1)
            }
        )
```

### 4. Console Reporter

**File: `tests/reporters/console_reporter.py`**

```python
"""Pretty console output for test results using Rich library."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from typing import List, Dict

console = Console()

def print_test_result(test_id: str, query: str, score, index: int, total: int):
    """Print a single test result."""
    status = "[green]PASS[/green]" if score.passed else "[red]FAIL[/red]"
    console.print(
        f"[{index}/{total}] {status} "
        f"F1={score.f1_score:.2f} Faith={score.faithfulness:.2f} Rel={score.relevance:.2f} "
        f"| {query[:50]}..."
    )

def print_summary(report: Dict):
    """Print test summary report."""
    console.print()
    console.rule("[bold blue]RETRIEVAL ACCURACY TEST REPORT[/bold blue]")
    
    # Overview
    console.print(f"\n[bold]Knowledge Base:[/bold] {report['knowledge_base_id']}")
    console.print(f"[bold]Timestamp:[/bold] {report['timestamp']}")
    console.print(f"[bold]Results:[/bold] {report['passed']}/{report['total_tests']} passed")
    
    # Aggregate metrics table
    console.print("\n[bold]Aggregate Metrics:[/bold]")
    metrics_table = Table(show_header=True)
    metrics_table.add_column("Metric")
    metrics_table.add_column("Value", justify="right")
    metrics_table.add_column("Target", justify="right")
    metrics_table.add_column("Status", justify="center")
    
    targets = {'avg_precision': 0.80, 'avg_recall': 0.70, 'avg_f1': 0.75, 
               'avg_mrr': 0.80, 'avg_faithfulness': 0.90, 'avg_relevance': 0.85}
    
    for metric, value in report['aggregate_metrics'].items():
        target = targets.get(metric, 0.70)
        status = "[green]✓[/green]" if value >= target else "[red]✗[/red]"
        metrics_table.add_row(metric, f"{value:.3f}", f"≥{target:.2f}", status)
    
    console.print(metrics_table)
    
    # By category
    console.print("\n[bold]By Category:[/bold]")
    cat_table = Table(show_header=True)
    cat_table.add_column("Category")
    cat_table.add_column("Tests", justify="right")
    cat_table.add_column("F1", justify="right")
    cat_table.add_column("Pass Rate", justify="right")
    
    for cat, metrics in report['by_category'].items():
        pass_pct = f"{metrics['pass_rate']*100:.0f}%"
        cat_table.add_row(cat, str(metrics['count']), f"{metrics['avg_f1']:.2f}", pass_pct)
    
    console.print(cat_table)
    
    # By marketplace
    console.print("\n[bold]By Marketplace:[/bold]")
    mp_table = Table(show_header=True)
    mp_table.add_column("Marketplace")
    mp_table.add_column("Tests", justify="right")
    mp_table.add_column("F1", justify="right")
    mp_table.add_column("Relevance", justify="right")
    
    for mp, metrics in report['by_marketplace'].items():
        mp_table.add_row(mp, str(metrics['count']), 
                         f"{metrics['avg_f1']:.2f}", f"{metrics['avg_relevance']:.2f}")
    
    console.print(mp_table)
    console.print()
```

### 5. Test Runner CLI

**File: `tests/run_tests.py`**

```python
#!/usr/bin/env python3
"""
QuickSuite Knowledge Base Accuracy Test Runner

Usage:
    python run_tests.py --kb-id OYBA7PFNNQ
    python run_tests.py --kb-id OYBA7PFNNQ --category pricing
    python run_tests.py --kb-id OYBA7PFNNQ --marketplace CN
"""

import argparse
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

from data.ground_truth import GROUND_TRUTH_DATASET, get_test_cases_by_category, get_test_cases_by_marketplace
from evaluators.retrieval_accuracy import RetrievalAccuracyEvaluator
from reporters.console_reporter import print_test_result, print_summary

def run_accuracy_tests(
    kb_id: str,
    region: str = "us-west-2",
    category: Optional[str] = None,
    marketplace: Optional[str] = None,
    output_dir: str = "test_results"
) -> Dict:
    """Run accuracy tests and generate report."""
    
    # Filter test cases
    test_cases = GROUND_TRUTH_DATASET
    if category:
        test_cases = get_test_cases_by_category(category)
    if marketplace:
        test_cases = get_test_cases_by_marketplace(marketplace)
    
    if not test_cases:
        print(f"No test cases found for filters: category={category}, marketplace={marketplace}")
        return {}
    
    evaluator = RetrievalAccuracyEvaluator(kb_id=kb_id, region=region)
    results = []
    
    print(f"\nRunning {len(test_cases)} accuracy tests...\n")
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            score = evaluator.evaluate(test_case)
            
            result = {
                'id': test_case.id,
                'query': test_case.query,
                'category': test_case.category,
                'marketplace': test_case.marketplace,
                'precision': score.precision,
                'recall': score.recall,
                'f1_score': score.f1_score,
                'mrr': score.mrr,
                'faithfulness': score.faithfulness,
                'relevance': score.relevance,
                'passed': score.passed,
                'details': score.details
            }
            results.append(result)
            
            print_test_result(test_case.id, test_case.query, score, i, len(test_cases))
            
        except Exception as e:
            print(f"[{i}/{len(test_cases)}] ERROR: {test_case.query[:50]}... - {e}")
            results.append({
                'id': test_case.id,
                'query': test_case.query,
                'error': str(e),
                'passed': False
            })
    
    # Aggregate metrics
    valid_results = [r for r in results if 'error' not in r]
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'knowledge_base_id': kb_id,
        'region': region,
        'filters': {'category': category, 'marketplace': marketplace},
        'total_tests': len(test_cases),
        'passed': sum(1 for r in results if r.get('passed')),
        'failed': sum(1 for r in results if not r.get('passed')),
        'aggregate_metrics': _calculate_aggregates(valid_results),
        'by_category': _aggregate_by_field(valid_results, 'category'),
        'by_marketplace': _aggregate_by_field(valid_results, 'marketplace'),
        'detailed_results': results
    }
    
    # Print summary
    print_summary(report)
    
    # Save report
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, 'accuracy_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Detailed report saved to: {report_path}")
    
    return report

def _calculate_aggregates(results: List[Dict]) -> Dict:
    """Calculate aggregate metrics."""
    if not results:
        return {}
    
    metrics = ['precision', 'recall', 'f1_score', 'mrr', 'faithfulness', 'relevance']
    return {
        f'avg_{m}': round(sum(r[m] for r in results) / len(results), 3)
        for m in metrics
    }

def _aggregate_by_field(results: List[Dict], field: str) -> Dict:
    """Aggregate metrics by a grouping field."""
    groups = {}
    for r in results:
        key = r.get(field, 'unknown')
        if key not in groups:
            groups[key] = []
        groups[key].append(r)
    
    aggregated = {}
    for key, items in groups.items():
        aggregated[key] = {
            'count': len(items),
            'avg_f1': round(sum(r['f1_score'] for r in items) / len(items), 3),
            'avg_faithfulness': round(sum(r['faithfulness'] for r in items) / len(items), 3),
            'avg_relevance': round(sum(r['relevance'] for r in items) / len(items), 3),
            'pass_rate': round(sum(1 for r in items if r['passed']) / len(items), 3)
        }
    return aggregated

def main():
    parser = argparse.ArgumentParser(description='QuickSuite KB Accuracy Test Runner')
    parser.add_argument('--kb-id', required=True, help='Knowledge Base ID')
    parser.add_argument('--region', default='us-west-2', help='AWS region')
    parser.add_argument('--category', help='Filter by category (e.g., pricing, registration)')
    parser.add_argument('--marketplace', help='Filter by marketplace (CN, US, BOTH)')
    parser.add_argument('--output-dir', default='test_results', help='Output directory')
    
    args = parser.parse_args()
    
    report = run_accuracy_tests(
        kb_id=args.kb_id,
        region=args.region,
        category=args.category,
        marketplace=args.marketplace,
        output_dir=args.output_dir
    )
    
    # Exit with error code if tests failed
    if report.get('failed', 0) > 0:
        exit(1)

if __name__ == '__main__':
    main()
```

### 6. Pytest Integration

**File: `tests/conftest.py`**

```python
"""Pytest fixtures for QuickSuite KB testing."""

import pytest
import os

@pytest.fixture
def kb_id():
    """Get Knowledge Base ID from environment or default."""
    return os.environ.get('KB_ID', 'OYBA7PFNNQ')

@pytest.fixture
def region():
    """Get AWS region from environment or default."""
    return os.environ.get('AWS_REGION', 'us-west-2')

@pytest.fixture
def evaluator(kb_id, region):
    """Create evaluator instance."""
    from evaluators.retrieval_accuracy import RetrievalAccuracyEvaluator
    return RetrievalAccuracyEvaluator(kb_id=kb_id, region=region)
```

**File: `tests/test_retrieval.py`**

```python
"""Pytest test cases for KB retrieval accuracy."""

import pytest
from data.ground_truth import GROUND_TRUTH_DATASET

class TestRetrievalAccuracy:
    """Test retrieval accuracy for all ground truth cases."""
    
    @pytest.mark.parametrize("test_case", GROUND_TRUTH_DATASET, ids=lambda tc: tc.id)
    def test_retrieval_accuracy(self, evaluator, test_case):
        """Test that retrieval meets accuracy thresholds."""
        score = evaluator.evaluate(test_case)
        
        assert score.f1_score >= 0.70, f"F1 score {score.f1_score} below threshold"
        assert score.faithfulness >= 0.80, f"Faithfulness {score.faithfulness} below threshold"
        assert score.relevance >= 0.70, f"Relevance {score.relevance} below threshold"

class TestRetrievalByCategory:
    """Test retrieval accuracy by category."""
    
    @pytest.mark.parametrize("category", ["pricing", "registration", "fulfillment", "compliance"])
    def test_category_accuracy(self, evaluator, category):
        """Test that each category meets minimum pass rate."""
        from data.ground_truth import get_test_cases_by_category
        
        test_cases = get_test_cases_by_category(category)
        if not test_cases:
            pytest.skip(f"No test cases for category: {category}")
        
        passed = sum(1 for tc in test_cases if evaluator.evaluate(tc).passed)
        pass_rate = passed / len(test_cases)
        
        assert pass_rate >= 0.80, f"Category {category} pass rate {pass_rate:.0%} below 80%"
```

## Test Execution

### CLI Usage

```bash
# Run all tests
python tests/run_tests.py --kb-id OYBA7PFNNQ

# Filter by category
python tests/run_tests.py --kb-id OYBA7PFNNQ --category pricing

# Filter by marketplace  
python tests/run_tests.py --kb-id OYBA7PFNNQ --marketplace CN

# Custom output directory
python tests/run_tests.py --kb-id OYBA7PFNNQ --output-dir results/
```

### Pytest Usage

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_retrieval.py::TestRetrievalAccuracy -v

# Run with custom KB ID
KB_ID=OYBA7PFNNQ pytest tests/ -v

# Generate JUnit XML report
pytest tests/ -v --junitxml=test_results/junit.xml
```

## Metrics and Thresholds

| Metric | Pass Threshold | Alert | Critical |
|--------|---------------|-------|----------|
| Precision | ≥ 0.75 | < 0.70 | < 0.50 |
| Recall | ≥ 0.70 | < 0.60 | < 0.40 |
| F1 Score | ≥ 0.70 | < 0.65 | < 0.50 |
| MRR | ≥ 0.75 | < 0.60 | < 0.40 |
| Faithfulness | ≥ 0.80 | < 0.70 | < 0.50 |
| Relevance | ≥ 0.70 | < 0.60 | < 0.40 |

## Sample Output

```
Running 8 accuracy tests...

[1/8] PASS F1=0.92 Faith=0.95 Rel=1.00 | What are the seller registration requirements f...
[2/8] PASS F1=1.00 Faith=0.98 Rel=1.00 | What is the monthly fee for professional selle...
[3/8] PASS F1=0.85 Faith=0.90 Rel=0.67 | How many FBA warehouses are there in America?...
[4/8] PASS F1=0.88 Faith=0.92 Rel=1.00 | What certifications are required for selling e...
[5/8] PASS F1=0.80 Faith=0.85 Rel=1.00 | Compare seller fees between CN and US marketpl...
[6/8] PASS F1=0.95 Faith=0.98 Rel=1.00 | What are the peak shopping days for US sellers...
[7/8] PASS F1=0.90 Faith=0.88 Rel=0.67 | Double 11 shopping festival requirements...
[8/8] PASS F1=0.82 Faith=0.91 Rel=1.00 | Alipay payment integration...

─────────────────── RETRIEVAL ACCURACY TEST REPORT ───────────────────

Knowledge Base: OYBA7PFNNQ
Timestamp: 2026-01-04T10:45:00
Results: 8/8 passed

Aggregate Metrics:
┌──────────────────┬───────┬────────┬────────┐
│ Metric           │ Value │ Target │ Status │
├──────────────────┼───────┼────────┼────────┤
│ avg_precision    │ 0.890 │ ≥0.80  │   ✓    │
│ avg_recall       │ 0.875 │ ≥0.70  │   ✓    │
│ avg_f1           │ 0.890 │ ≥0.75  │   ✓    │
│ avg_mrr          │ 0.938 │ ≥0.80  │   ✓    │
│ avg_faithfulness │ 0.921 │ ≥0.90  │   ✓    │
│ avg_relevance    │ 0.917 │ ≥0.85  │   ✓    │
└──────────────────┴───────┴────────┴────────┘

Detailed report saved to: test_results/accuracy_report.json
```

## Next Steps

1. **Implement test files** in `tests/` directory
2. **Expand ground truth dataset** with more test cases
3. **Add regression testing** to track accuracy over time
4. **Integrate with CI/CD** for automated testing on document updates

---

**Status**: Design Complete | **Date**: January 4, 2026

