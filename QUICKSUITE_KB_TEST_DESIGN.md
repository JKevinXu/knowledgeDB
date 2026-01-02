# Amazon QuickSuite Knowledge Base - Retrieval Accuracy Test Design

## Overview

This document outlines a testing strategy to evaluate **knowledge retrieval accuracy** for Amazon QuickSuite Knowledge Base. The goal is to measure how precisely and completely the KB retrieves relevant information in response to queries.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    Retrieval Accuracy Testing                             │
│                                                                          │
│   Test Query → KB Retrieval → Compare to Ground Truth → Accuracy Score   │
└──────────────────────────────────────────────────────────────────────────┘
```

## Key Metrics

| Metric | Definition | Target |
|--------|------------|--------|
| **Precision** | % of retrieved docs that are relevant | > 80% |
| **Recall** | % of relevant docs that were retrieved | > 70% |
| **F1 Score** | Harmonic mean of precision & recall | > 0.75 |
| **MRR** | Mean Reciprocal Rank (position of first correct result) | > 0.8 |
| **NDCG** | Normalized Discounted Cumulative Gain | > 0.85 |
| **Faithfulness** | Is the answer grounded in retrieved docs? | > 90% |
| **Relevance** | Does the response match the query intent? | > 85% |

## Test Dataset Structure

### Ground Truth Format

```python
# test_data/ground_truth.py

GROUND_TRUTH_DATASET = [
    {
        "id": "q001",
        "query": "What are the seller registration requirements for China marketplace?",
        "expected_sources": ["seller-guide-cn.md"],
        "expected_chunks": [
            "Chinese business license (营业执照)",
            "Chinese bank account",
            "Legal representative ID card"
        ],
        "expected_answer_contains": [
            "business license",
            "bank account", 
            "registration"
        ],
        "marketplace": "CN",
        "category": "registration"
    },
    {
        "id": "q002",
        "query": "What is the monthly fee for professional sellers in the US?",
        "expected_sources": ["seller-guide-us.md"],
        "expected_chunks": [
            "Professional Seller: $39.99/month"
        ],
        "expected_answer_contains": ["$39.99", "month"],
        "marketplace": "US",
        "category": "pricing"
    },
    {
        "id": "q003",
        "query": "How many FBA warehouses are there in America?",
        "expected_sources": ["seller-guide-us.md"],
        "expected_chunks": [
            "175+ fulfillment centers across the US"
        ],
        "expected_answer_contains": ["175", "fulfillment", "warehouse"],
        "marketplace": "US",
        "category": "fulfillment"
    },
    {
        "id": "q004",
        "query": "What certifications are required for selling electronics in China?",
        "expected_sources": ["seller-guide-cn.md"],
        "expected_chunks": [
            "CCC Certification (中国强制认证)"
        ],
        "expected_answer_contains": ["CCC", "certification"],
        "marketplace": "CN",
        "category": "compliance"
    },
    {
        "id": "q005",
        "query": "Compare seller fees between CN and US marketplaces",
        "expected_sources": ["seller-guide-cn.md", "seller-guide-us.md"],
        "expected_chunks": [
            "¥300/month",
            "$39.99/month"
        ],
        "expected_answer_contains": ["¥300", "$39.99"],
        "marketplace": "BOTH",
        "category": "pricing"
    },
    {
        "id": "q006",
        "query": "What are the peak shopping days for US sellers?",
        "expected_sources": ["seller-guide-us.md"],
        "expected_chunks": [
            "Prime Day, Black Friday, Cyber Monday"
        ],
        "expected_answer_contains": ["Prime Day", "Black Friday"],
        "marketplace": "US",
        "category": "marketing"
    },
    {
        "id": "q007",
        "query": "Double 11 shopping festival requirements",
        "expected_sources": ["seller-guide-cn.md"],
        "expected_chunks": [
            "11.11 (Double 11): Largest shopping event"
        ],
        "expected_answer_contains": ["11.11", "November", "shopping"],
        "marketplace": "CN",
        "category": "marketing"
    },
    {
        "id": "q008",
        "query": "Alipay payment integration",
        "expected_sources": ["seller-guide-cn.md"],
        "expected_chunks": [
            "Alipay: Most popular (45%+ market share)"
        ],
        "expected_answer_contains": ["Alipay", "payment"],
        "marketplace": "CN",
        "category": "payments"
    }
]
```

## Retrieval Accuracy Evaluator

```python
# evaluators/retrieval_accuracy.py
import boto3
from typing import List, Dict
from dataclasses import dataclass
import json

@dataclass
class RetrievalResult:
    query: str
    retrieved_chunks: List[Dict]
    generated_answer: str
    sources: List[str]
    latency_ms: float

@dataclass
class AccuracyScore:
    precision: float
    recall: float
    f1_score: float
    mrr: float
    faithfulness: float
    relevance: float
    details: Dict

class RetrievalAccuracyEvaluator:
    """Evaluate knowledge base retrieval accuracy"""
    
    def __init__(self, kb_id: str, region: str = "us-west-2"):
        self.kb_id = kb_id
        self.bedrock_agent = boto3.client('bedrock-agent-runtime', region_name=region)
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        
    def query_knowledge_base(self, query: str, num_results: int = 5) -> RetrievalResult:
        """Query the knowledge base and get retrieved chunks"""
        import time
        
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
        
        # Get generated answer
        rag_response = self.bedrock_agent.retrieve_and_generate(
            input={'text': query},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': self.kb_id,
                    'modelArn': 'arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0'
                }
            }
        )
        
        latency = (time.time() - start) * 1000
        
        chunks = []
        sources = set()
        for result in retrieve_response.get('retrievalResults', []):
            chunk = {
                'content': result.get('content', {}).get('text', ''),
                'score': result.get('score', 0),
                'source': result.get('location', {}).get('s3Location', {}).get('uri', '')
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
        
    def evaluate_precision(self, result: RetrievalResult, ground_truth: Dict) -> float:
        """Calculate precision: relevant retrieved / total retrieved"""
        if not result.retrieved_chunks:
            return 0.0
            
        relevant_count = 0
        for chunk in result.retrieved_chunks:
            # Check if chunk source matches expected sources
            for expected_src in ground_truth['expected_sources']:
                if expected_src in chunk['source']:
                    relevant_count += 1
                    break
                    
        return relevant_count / len(result.retrieved_chunks)
        
    def evaluate_recall(self, result: RetrievalResult, ground_truth: Dict) -> float:
        """Calculate recall: relevant retrieved / total relevant"""
        expected_chunks = ground_truth['expected_chunks']
        if not expected_chunks:
            return 1.0
            
        found_count = 0
        retrieved_text = ' '.join([c['content'] for c in result.retrieved_chunks])
        
        for expected in expected_chunks:
            if expected.lower() in retrieved_text.lower():
                found_count += 1
                
        return found_count / len(expected_chunks)
        
    def evaluate_mrr(self, result: RetrievalResult, ground_truth: Dict) -> float:
        """Calculate Mean Reciprocal Rank"""
        for i, chunk in enumerate(result.retrieved_chunks):
            for expected_src in ground_truth['expected_sources']:
                if expected_src in chunk['source']:
                    return 1.0 / (i + 1)
        return 0.0
        
    def evaluate_faithfulness(self, result: RetrievalResult) -> float:
        """Use LLM to evaluate if answer is grounded in retrieved docs"""
        context = '\n'.join([c['content'] for c in result.retrieved_chunks])
        
        prompt = f"""Evaluate if the following answer is faithfully grounded in the provided context.

CONTEXT:
{context}

ANSWER:
{result.generated_answer}

Score from 0.0 to 1.0:
- 1.0 = Answer is completely grounded in context
- 0.5 = Answer is partially grounded, some information not in context
- 0.0 = Answer contradicts or has no basis in context

Return ONLY a JSON object: {{"score": <float>, "reasoning": "<explanation>"}}"""

        response = self.bedrock.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'messages': [{'role': 'user', 'content': prompt}],
                'max_tokens': 200
            })
        )
        
        result_body = json.loads(response['body'].read())
        llm_output = result_body['content'][0]['text']
        
        try:
            parsed = json.loads(llm_output)
            return parsed.get('score', 0.0)
        except:
            return 0.0
            
    def evaluate_relevance(self, result: RetrievalResult, ground_truth: Dict) -> float:
        """Check if answer contains expected information"""
        answer_lower = result.generated_answer.lower()
        expected = ground_truth['expected_answer_contains']
        
        if not expected:
            return 1.0
            
        found = sum(1 for e in expected if e.lower() in answer_lower)
        return found / len(expected)
        
    def evaluate(self, ground_truth: Dict) -> AccuracyScore:
        """Run full accuracy evaluation for a single query"""
        result = self.query_knowledge_base(ground_truth['query'])
        
        precision = self.evaluate_precision(result, ground_truth)
        recall = self.evaluate_recall(result, ground_truth)
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        mrr = self.evaluate_mrr(result, ground_truth)
        faithfulness = self.evaluate_faithfulness(result)
        relevance = self.evaluate_relevance(result, ground_truth)
        
        return AccuracyScore(
            precision=precision,
            recall=recall,
            f1_score=f1,
            mrr=mrr,
            faithfulness=faithfulness,
            relevance=relevance,
            details={
                'query': ground_truth['query'],
                'query_id': ground_truth['id'],
                'category': ground_truth['category'],
                'retrieved_sources': result.sources,
                'expected_sources': ground_truth['expected_sources'],
                'answer_preview': result.generated_answer[:200],
                'latency_ms': result.latency_ms
            }
        )
```

## Test Runner

```python
# run_accuracy_tests.py
import json
from datetime import datetime
from evaluators.retrieval_accuracy import RetrievalAccuracyEvaluator, AccuracyScore
from test_data.ground_truth import GROUND_TRUTH_DATASET

def run_accuracy_tests(kb_id: str) -> Dict:
    """Run all accuracy tests and generate report"""
    
    evaluator = RetrievalAccuracyEvaluator(kb_id=kb_id)
    results = []
    
    print(f"Running {len(GROUND_TRUTH_DATASET)} accuracy tests...\n")
    
    for i, test_case in enumerate(GROUND_TRUTH_DATASET):
        print(f"[{i+1}/{len(GROUND_TRUTH_DATASET)}] Testing: {test_case['query'][:50]}...")
        
        try:
            score = evaluator.evaluate(test_case)
            results.append({
                'id': test_case['id'],
                'query': test_case['query'],
                'category': test_case['category'],
                'marketplace': test_case['marketplace'],
                'precision': score.precision,
                'recall': score.recall,
                'f1_score': score.f1_score,
                'mrr': score.mrr,
                'faithfulness': score.faithfulness,
                'relevance': score.relevance,
                'passed': score.f1_score >= 0.7 and score.faithfulness >= 0.8,
                'details': score.details
            })
            
            status = "✅" if results[-1]['passed'] else "❌"
            print(f"   {status} F1={score.f1_score:.2f} Faith={score.faithfulness:.2f} Rel={score.relevance:.2f}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results.append({
                'id': test_case['id'],
                'query': test_case['query'],
                'error': str(e),
                'passed': False
            })
    
    # Aggregate metrics
    valid_results = [r for r in results if 'error' not in r]
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'knowledge_base_id': kb_id,
        'total_tests': len(GROUND_TRUTH_DATASET),
        'passed': sum(1 for r in results if r.get('passed')),
        'failed': sum(1 for r in results if not r.get('passed')),
        'aggregate_metrics': {
            'avg_precision': sum(r['precision'] for r in valid_results) / len(valid_results),
            'avg_recall': sum(r['recall'] for r in valid_results) / len(valid_results),
            'avg_f1': sum(r['f1_score'] for r in valid_results) / len(valid_results),
            'avg_mrr': sum(r['mrr'] for r in valid_results) / len(valid_results),
            'avg_faithfulness': sum(r['faithfulness'] for r in valid_results) / len(valid_results),
            'avg_relevance': sum(r['relevance'] for r in valid_results) / len(valid_results),
        },
        'by_category': _aggregate_by_category(valid_results),
        'by_marketplace': _aggregate_by_marketplace(valid_results),
        'detailed_results': results
    }
    
    return report

def _aggregate_by_category(results: list) -> dict:
    """Aggregate metrics by category"""
    categories = {}
    for r in results:
        cat = r.get('category', 'unknown')
        if cat not in categories:
            categories[cat] = {'results': [], 'count': 0}
        categories[cat]['results'].append(r)
        categories[cat]['count'] += 1
        
    aggregated = {}
    for cat, data in categories.items():
        aggregated[cat] = {
            'count': data['count'],
            'avg_f1': sum(r['f1_score'] for r in data['results']) / len(data['results']),
            'avg_faithfulness': sum(r['faithfulness'] for r in data['results']) / len(data['results']),
            'pass_rate': sum(1 for r in data['results'] if r['passed']) / len(data['results'])
        }
    return aggregated

def _aggregate_by_marketplace(results: list) -> dict:
    """Aggregate metrics by marketplace"""
    marketplaces = {}
    for r in results:
        mp = r.get('marketplace', 'unknown')
        if mp not in marketplaces:
            marketplaces[mp] = {'results': [], 'count': 0}
        marketplaces[mp]['results'].append(r)
        marketplaces[mp]['count'] += 1
        
    aggregated = {}
    for mp, data in marketplaces.items():
        aggregated[mp] = {
            'count': data['count'],
            'avg_f1': sum(r['f1_score'] for r in data['results']) / len(data['results']),
            'avg_relevance': sum(r['relevance'] for r in data['results']) / len(data['results']),
            'pass_rate': sum(1 for r in data['results'] if r['passed']) / len(data['results'])
        }
    return aggregated

if __name__ == '__main__':
    import sys
    
    KB_ID = sys.argv[1] if len(sys.argv) > 1 else 'OYBA7PFNNQ'
    
    report = run_accuracy_tests(KB_ID)
    
    # Print summary
    print("\n" + "="*60)
    print("RETRIEVAL ACCURACY TEST REPORT")
    print("="*60)
    print(f"Knowledge Base: {report['knowledge_base_id']}")
    print(f"Timestamp: {report['timestamp']}")
    print(f"\nResults: {report['passed']}/{report['total_tests']} passed")
    print(f"\nAggregate Metrics:")
    for metric, value in report['aggregate_metrics'].items():
        print(f"  {metric}: {value:.3f}")
    
    print(f"\nBy Category:")
    for cat, metrics in report['by_category'].items():
        print(f"  {cat}: F1={metrics['avg_f1']:.2f}, Pass Rate={metrics['pass_rate']*100:.0f}%")
        
    print(f"\nBy Marketplace:")
    for mp, metrics in report['by_marketplace'].items():
        print(f"  {mp}: F1={metrics['avg_f1']:.2f}, Relevance={metrics['avg_relevance']:.2f}")
    
    # Save detailed report
    with open('test_results/accuracy_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nDetailed report saved to: test_results/accuracy_report.json")
```

## Browser-Based Interactive Testing

```python
# browser_accuracy_test.py
"""
Interactive browser-based accuracy testing using MCP browser tools
"""

async def test_retrieval_accuracy_via_browser(page, queries: list):
    """Test retrieval accuracy through the QuickSuite web interface"""
    
    results = []
    
    for test_case in queries:
        # Navigate to KB query interface
        await page.goto('https://quicksuite.aws.amazon.com/knowledge-bases')
        await page.click('[data-testid="kb-search-input"]')
        
        # Enter query
        await page.fill('[data-testid="kb-search-input"]', test_case['query'])
        await page.click('[data-testid="search-submit"]')
        
        # Wait for results
        await page.wait_for_selector('[data-testid="search-results"]')
        
        # Extract retrieved sources
        sources = await page.query_selector_all('[data-testid="result-source"]')
        retrieved_sources = [await s.inner_text() for s in sources]
        
        # Extract answer
        answer = await page.inner_text('[data-testid="generated-answer"]')
        
        # Calculate accuracy
        precision = calculate_precision(retrieved_sources, test_case['expected_sources'])
        relevance = calculate_relevance(answer, test_case['expected_answer_contains'])
        
        results.append({
            'query': test_case['query'],
            'precision': precision,
            'relevance': relevance,
            'retrieved_sources': retrieved_sources,
            'answer': answer[:200]
        })
        
        # Take screenshot for evidence
        await page.screenshot(path=f"screenshots/{test_case['id']}.png")
        
    return results
```

## Sample Test Output

```
$ python run_accuracy_tests.py OYBA7PFNNQ

Running 8 accuracy tests...

[1/8] Testing: What are the seller registration requirements f...
   ✅ F1=0.92 Faith=0.95 Rel=1.00
[2/8] Testing: What is the monthly fee for professional selle...
   ✅ F1=1.00 Faith=0.98 Rel=1.00
[3/8] Testing: How many FBA warehouses are there in America?...
   ✅ F1=0.85 Faith=0.90 Rel=0.67
[4/8] Testing: What certifications are required for selling e...
   ✅ F1=0.88 Faith=0.92 Rel=1.00
[5/8] Testing: Compare seller fees between CN and US marketpl...
   ✅ F1=0.80 Faith=0.85 Rel=1.00
[6/8] Testing: What are the peak shopping days for US sellers...
   ✅ F1=0.95 Faith=0.98 Rel=1.00
[7/8] Testing: Double 11 shopping festival requirements...
   ✅ F1=0.90 Faith=0.88 Rel=0.67
[8/8] Testing: Alipay payment integration...
   ✅ F1=0.82 Faith=0.91 Rel=1.00

============================================================
RETRIEVAL ACCURACY TEST REPORT
============================================================
Knowledge Base: OYBA7PFNNQ
Timestamp: 2026-01-02T14:45:00

Results: 8/8 passed

Aggregate Metrics:
  avg_precision: 0.890
  avg_recall: 0.875
  avg_f1: 0.890
  avg_mrr: 0.938
  avg_faithfulness: 0.921
  avg_relevance: 0.917

By Category:
  registration: F1=0.92, Pass Rate=100%
  pricing: F1=0.90, Pass Rate=100%
  fulfillment: F1=0.85, Pass Rate=100%
  compliance: F1=0.88, Pass Rate=100%
  marketing: F1=0.93, Pass Rate=100%
  payments: F1=0.82, Pass Rate=100%

By Marketplace:
  CN: F1=0.88, Relevance=0.92
  US: F1=0.93, Relevance=0.89
  BOTH: F1=0.80, Relevance=1.00

Detailed report saved to: test_results/accuracy_report.json
```

## Accuracy Thresholds & Alerts

| Metric | Pass Threshold | Alert Threshold | Critical |
|--------|---------------|-----------------|----------|
| Precision | ≥ 0.75 | < 0.70 | < 0.50 |
| Recall | ≥ 0.70 | < 0.60 | < 0.40 |
| F1 Score | ≥ 0.70 | < 0.65 | < 0.50 |
| MRR | ≥ 0.75 | < 0.60 | < 0.40 |
| Faithfulness | ≥ 0.80 | < 0.70 | < 0.50 |
| Relevance | ≥ 0.80 | < 0.70 | < 0.50 |

## Integration with Existing Project

```
knowledgeDB/
├── documents/                      # Source documents
│   ├── seller-guide-cn.md
│   ├── seller-guide-us.md
│   └── sample-document.md
├── evaluators/                     # NEW: Accuracy evaluators
│   ├── __init__.py
│   └── retrieval_accuracy.py
├── test_data/                      # NEW: Ground truth dataset
│   ├── __init__.py
│   └── ground_truth.py
├── run_accuracy_tests.py           # NEW: Test runner
├── test_results/                   # Output
│   ├── accuracy_report.json
│   └── screenshots/
└── QUICKSUITE_KB_TEST_DESIGN.md
```

## Next Steps

1. **Create ground truth dataset** from existing seller guides
2. **Implement evaluator** with precision/recall/faithfulness metrics
3. **Run baseline tests** to establish current accuracy
4. **Set up automated testing** on document updates
5. **Monitor accuracy trends** over time

---

**Status**: Draft | **Date**: January 2, 2026
