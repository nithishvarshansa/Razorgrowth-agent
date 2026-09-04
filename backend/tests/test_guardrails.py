from backend.services.guardrails import evaluate_recommendation

def valid(): return {"agent_run_id":"run-1","opportunity_type":"cross_sell","recommended_product":"sku-b","evidence":["test fixture evidence"],"confidence":"medium","estimated_revenue_impact":None}
def test_valid_recommendation_requires_approval():
    result=evaluate_recommendation(valid()); assert result.decision=="allowed_for_approval" and result.status=="pending_approval"
def test_missing_evidence_fails_closed():
    item=valid(); item["evidence"]=[]; assert evaluate_recommendation(item).decision=="insufficient_evidence"
def test_unknown_action_and_missing_product_are_blocked():
    item=valid(); item["opportunity_type"]="unknown"; item["recommended_product"]=None; assert evaluate_recommendation(item).decision=="blocked"
def test_excessive_value_is_blocked():
    item=valid(); item["estimated_revenue_impact"]=100001; assert evaluate_recommendation(item).decision=="blocked"
