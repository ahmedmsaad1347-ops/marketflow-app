"""Meaningful budget arithmetic, privacy, immutable planning context and full draft flow."""
import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from dataclasses import replace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from auth_helpers import signup_verified, prepare_client
from backend.budget_planner import CampaignPlanInput, campaign_plan, plan_budget
from backend.strategy_engine import StrategyRequest, build_strategy, register_strategy_engine
from backend.strategy_agent import register_strategy_agent

BASE=dict(business_name='سكنك للعقارات',product='شقة 140 مترًا في الشروق، 3 غرف و2 حمام',
    audience='الباحثون عن شقة للسكن في الشروق',country='Egypt',objective='leads',currency='EGP',
    platform='Facebook',creative_language='ar-EG',campaign_days=14,target_results=10,
    cost_per_result=50,offer='السعر 2,400,000 جنيه. مقدم 600,000 جنيه والباقي على 5 سنوات.',
    benefit='فصل الاستقبال عن غرف النوم')


class BudgetMathTests(unittest.TestCase):
    def plan(self,**changes):return campaign_plan(CampaignPlanInput(**{**BASE,**changes}))

    def test_cost_basis_and_spend_ceiling_do_not_promise_results(self):
        result=self.plan(target_results=20,campaign_days=10,spend_ceiling=600)
        budget=result['budget']
        self.assertEqual(budget['recommended_total'],1000)
        self.assertEqual(budget['total_budget'],600)
        self.assertEqual(budget['daily_budget'],60)
        self.assertEqual(budget['funding_gap'],400)
        self.assertEqual(budget['target_results'],20)
        self.assertFalse(budget['is_performance_forecast'])
        self.assertEqual(budget['basis'],'supplied_result_cost')
        self.assertTrue(any(not item['within_ceiling'] for item in budget['scenarios']))
        self.assertIn(BASE['offer'],result['ad_concept']['body'])

    def test_financial_allowance_is_not_confused_with_market_cost(self):
        sales=self.plan(objective='sales',cost_per_result=0,price=1000,gross_margin_percent=70,extra_variable_cost_per_order=50)
        self.assertEqual(sales['budget']['contribution_per_sale'],650)
        self.assertEqual(sales['budget']['reference_cost'],455)
        self.assertEqual(sales['budget']['recommended_total'],4550)
        leads=self.plan(cost_per_result=0,price=1000,gross_margin_percent=70,extra_variable_cost_per_order=50,lead_to_sale_rate_percent=10)
        self.assertEqual(leads['budget']['reference_cost'],45.5)
        self.assertEqual(leads['budget']['recommended_total'],455)
        self.assertEqual(leads['budget']['basis'],'economics_allowance')
        self.assertIn('not an expected auction cost',leads['budget']['basis_explanation'])
        absent=self.plan(cost_per_result=0,price=1000,gross_margin_percent=70)
        self.assertEqual(absent['budget']['status'],'needs_inputs')
        self.assertIsNone(absent['budget']['recommended_total'])
        self.assertTrue(absent['ad_concept']['hook'])

    def test_clicks_and_impressions_use_different_units(self):
        traffic=self.plan(objective='traffic',cost_per_result=4,target_results=1000)
        awareness=self.plan(objective='awareness',cost_per_result=40,target_results=25000)
        self.assertEqual(traffic['budget']['recommended_total'],4000)
        self.assertEqual(awareness['budget']['recommended_total'],1000)
        self.assertEqual(traffic['ad_concept']['funnel_stage'],'mofu')
        self.assertEqual(awareness['ad_concept']['funnel_stage'],'tofu')
        self.assertNotIn(BASE['offer'],awareness['ad_concept']['body'])
        for objective in ('traffic','awareness'):
            missing=self.plan(objective=objective,cost_per_result=0,price=1000,gross_margin_percent=50)
            self.assertEqual(missing['budget']['status'],'needs_inputs')

    def test_loss_making_costs_are_flagged_and_no_profit_is_invented(self):
        result=self.plan(cost_per_result=100,price=1000,gross_margin_percent=50,lead_to_sale_rate_percent=10)
        self.assertTrue(any('not break even' in warning for warning in result['budget']['warnings']))
        bad=self.plan(cost_per_result=0,price=1000,gross_margin_percent=50,extra_variable_cost_per_order=600)
        self.assertEqual(bad['budget']['contribution_per_sale'],0)
        self.assertIsNone(bad['budget']['recommended_total'])

    def test_validation_rejects_nonfinite_fractional_targets_and_currency_confusion(self):
        for update in ({'cost_per_result':float('nan')},{'spend_ceiling':float('inf')},
            {'target_results':1.5},{'target_results':True},{'target_results':0},{'cost_per_result':-1},
            {'creative_language':'de'},{'currency':'EGP/USD'},{'spend_ceiling':.005},
            {'budget_mode':'manual','total_budget':0}):
            with self.subTest(update=update),self.assertRaises((ValidationError,ValueError)):
                CampaignPlanInput(**{**BASE,**update})

    def test_legacy_manual_budget_remains_authoritative(self):
        result=self.plan(budget_mode='manual',total_budget=3000)
        self.assertEqual(result['budget']['total_budget'],3000)
        self.assertEqual(result['budget']['recommended_total'],500)
        self.assertEqual(result['budget']['funding_gap'],0)
        self.assertEqual(result['ad_concept'],self.plan(budget_mode='manual',total_budget=3000)['ad_concept'])

    def test_excessive_scenario_and_rounding_do_not_create_unbounded_budget(self):
        result=self.plan(cost_per_result=1000000000,target_results=10000000)
        self.assertEqual(result['budget']['status'],'needs_inputs')
        tiny=self.plan(cost_per_result=.001,target_results=1)
        self.assertEqual(tiny['budget']['status'],'needs_inputs')
        fractional=self.plan(cost_per_result=1.005,target_results=10)['budget']
        self.assertEqual(fractional['total_budget'],10.05)
        self.assertEqual(fractional['reference_cost'],1.005)


class PlannerAPITests(unittest.TestCase):
    def setUp(self):
        self.main=importlib.import_module('backend.main')
        self.directory=tempfile.TemporaryDirectory(prefix='mf-budget-test-');self.addCleanup(self.directory.cleanup)
        self.dbpatch=patch.object(self.main,'DATABASE',str(Path(self.directory.name)/'app.db'));self.dbpatch.start();self.addCleanup(self.dbpatch.stop)
        config=patch.object(self.main.auth,'config',replace(self.main.auth.config,mail_mode='file',outbox=str(Path(self.directory.name)/'mail')))
        config.start();self.addCleanup(config.stop)
        self.main.init_db();self.main.auth.migrate()
        scratch=FastAPI();register_strategy_engine(scratch,self.main.get_db,self.main.get_current_user);register_strategy_agent(scratch,self.main.get_db,self.main.get_current_user)
        self.client=prepare_client(TestClient(self.main.app));self.addCleanup(self.client.close)
        signup_verified(self.client,self.main,json={'name':'Planner owner','email':'planner@example.com','password':'A thoughtful budget for my business!'})

    def payload(self,**changes):
        return dict(name='معاينات الشروق',product=BASE['product'],audience=BASE['audience'],country='Egypt',
            platform='Facebook',budget='client text is not trusted for auto mode',goal='Leads',planner=BASE,planner_apply_budget=True,**changes)

    def test_preview_save_reload_duplicate_and_manual_override_keep_concept(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'must-not-be-used'}),patch('backend.creative_studio.httpx.post') as external:
            response=self.client.post('/api/campaign-planner/preview',json=BASE)
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.headers['cache-control'],'no-store')
            self.assertEqual(response.json()['plan']['budget']['total_budget'],500)
            created=self.client.post('/api/campaigns',json=self.payload())
            self.assertEqual(created.status_code,200,created.text)
            item=created.json()['campaign'];self.assertEqual(item['status'],'Draft')
            self.assertEqual(item['budget'],'500.00 EGP / 14 days')
            saved=json.loads(item['planning_json'])
            self.assertEqual(saved['output']['ad_concept'],response.json()['plan']['ad_concept'])
            read=self.client.get(f"/api/campaigns/{item['id']}").json()['campaign']
            self.assertEqual(read['planning_json'],item['planning_json'])
            duplicate=self.client.post(f"/api/campaigns/{item['id']}/duplicate").json()['campaign']
            self.assertEqual(duplicate['planning_json'],item['planning_json'])
            changed=self.payload();changed.update(budget='300 EGP for a smaller test',planner_apply_budget=False)
            updated=self.client.put(f"/api/campaigns/{item['id']}",json=changed)
            self.assertEqual(updated.status_code,200,updated.text)
            self.assertEqual(updated.json()['campaign']['budget'],'300 EGP for a smaller test')
            self.assertFalse(json.loads(updated.json()['campaign']['planning_json'])['applied_budget'])
            external.assert_not_called()

    def test_missing_cost_returns_idea_but_cannot_apply_numeric_budget(self):
        brief={**BASE,'cost_per_result':0}
        preview=self.client.post('/api/campaign-planner/preview',json=brief)
        self.assertEqual(preview.status_code,200)
        self.assertEqual(preview.json()['plan']['budget']['status'],'needs_inputs')
        payload=self.payload();payload['planner']=brief
        self.assertEqual(self.client.post('/api/campaigns',json=payload).status_code,422)
        self.assertEqual(self.client.get('/api/campaigns').json()['campaigns'],[])

    def test_owner_isolation_and_csrf(self):
        item=self.client.post('/api/campaigns',json=self.payload()).json()['campaign']
        with prepare_client(TestClient(self.main.app)) as other:
            signup_verified(other,self.main,json={'name':'Other','email':'other-planner@example.com','password':'A separate budget planning account!'})
            self.assertEqual(other.get(f"/api/campaigns/{item['id']}").status_code,404)
            self.assertEqual(other.put(f"/api/campaigns/{item['id']}",json=self.payload()).status_code,404)
            other.headers.pop('X-CSRF-Token')
            self.assertEqual(other.post('/api/campaign-planner/preview',json=BASE).status_code,403)
        with TestClient(self.main.app) as stranger:
            self.assertEqual(stranger.post('/api/campaign-planner/preview',json=BASE).status_code,403)

    def test_strategy_recommends_and_accepts_same_budget_and_idea(self):
        data={key:value for key,value in BASE.items() if key!='platform'}
        data.update(budget_mode='recommend',has_website=True,has_tracking=True,sales_channel='website')
        generated=self.client.post('/api/strategy/generate',json=data)
        self.assertEqual(generated.status_code,200,generated.text)
        record=generated.json();strategy=record['strategy']
        self.assertEqual(strategy['budget_plan']['total_budget'],500)
        self.assertTrue(strategy['ad_concept']['hook'])
        accepted=self.client.post(f"/api/strategy/{record['strategy_id']}/accept")
        self.assertEqual(accepted.status_code,200,accepted.text)
        snapshot=json.loads(accepted.json()['campaign']['planning_json'])
        self.assertEqual(snapshot['output']['ad_concept'],strategy['ad_concept'])
        self.assertEqual(snapshot['output']['budget']['total_budget'],500)
        again=self.client.post(f"/api/strategy/{record['strategy_id']}/accept").json()
        self.assertEqual(again['campaign']['id'],accepted.json()['campaign']['id'])

    def test_agent_auto_budget_survives_resume_and_builds_from_economics(self):
        answers=dict(business_name='FlowDesk',product='Customer support software',offer='14-day paid trial',country='Egypt',
            audience='Store owners',objective='leads',demand_type='discovery',sales_channel='website',currency='EGP',total_budget='recommend',
            campaign_days=14,price=1000,gross_margin_percent=70,extra_variable_cost_per_order=50,lead_to_sale_rate_percent=10,
            has_website=True,has_tracking=True,has_previous_sales=False,has_video_creatives=False,target_results=10,spend_ceiling=300,creative_language='en')
        progress=self.client.post('/api/strategy-agent/start').json();sid=progress['session_id'];seen=set()
        while progress.get('question'):
            key=progress['question']['key'];self.assertNotIn(key,seen);seen.add(key)
            self.assertIn(key,answers,key)
            response=self.client.post(f'/api/strategy-agent/{sid}/answer',json={'value':answers[key]})
            self.assertEqual(response.status_code,200,response.text);progress=response.json()
        self.assertNotIn('cost_per_result',seen)
        resumed=self.client.get(f'/api/strategy-agent/{sid}/resume').json()
        self.assertEqual(resumed['answers']['budget_mode'],'recommend')
        with patch('backend.strategy_agent.research_business',return_value={'sources':[]}):
            built=self.client.post(f'/api/strategy-agent/{sid}/build')
        self.assertEqual(built.status_code,200,built.text)
        budget=built.json()['strategy']['budget_plan']
        self.assertEqual(budget['total_budget'],300)
        self.assertEqual(budget['recommendation']['recommended_total'],455)
        self.assertEqual(budget['recommendation']['funding_gap'],155)

    def test_suggestions_follow_real_setup_and_objective(self):
        response=self.client.post('/api/campaign-planner/preview',json={**BASE,'platform':'TikTok','objective':'awareness','cost_per_result':40,'target_results':10000})
        self.assertEqual(response.status_code,200,response.text)
        suggestions=' '.join(item['title'] for item in response.json()['plan']['recommendations'])
        self.assertIn('Measure awareness as awareness',suggestions)
        self.assertIn('Prepare the first creative',suggestions)
        self.assertNotIn('Define a useful enquiry',suggestions)
        invalid=self.payload();invalid.pop('planner')
        self.assertEqual(self.client.post('/api/campaigns',json=invalid).status_code,422)

    def test_schema_upgrade_preserves_existing_campaign(self):
        payload=self.payload();payload.pop('planner');payload.pop('planner_apply_budget');payload['budget']='1000 EGP'
        item=self.client.post('/api/campaigns',json=payload).json()['campaign']
        with self.main.get_db() as db:db.execute('ALTER TABLE campaigns DROP COLUMN planning_json')
        self.main.init_db()
        loaded=self.client.get(f"/api/campaigns/{item['id']}").json()['campaign']
        self.assertEqual(loaded['budget'],'1000 EGP')
        self.assertIsNone(loaded['planning_json'])


if __name__=='__main__':unittest.main()
