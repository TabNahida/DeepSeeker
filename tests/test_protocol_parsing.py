from deepseeker.schema import ControllerDecision, ReaderReport

CTRL_JSON = {
  "role": "controller_decision",
  "decision_id": "123e4567-e89b-12d3-a456-426614174000",
  "stage": "initial",
  "action": "search",
  "search_plan": {
    "queries": [{"q": "test", "recency_days": 30}],
    "per_query_limit": 8
  }
}

READ_JSON = {
  "role": "reader_report",
  "doc_id": "abc",
  "source_url": "https://example.com",
  "title": "hello",
  "verdict": "relevant",
  "reliability": {"rating": 0.7, "reasons": "ok"},
  "key_points": ["a", "b"],
  "mini_summary": "short",
  "citation": "https://example.com"
}

def test_ctrl():
    ControllerDecision(**CTRL_JSON)

def test_read():
    ReaderReport(**READ_JSON)