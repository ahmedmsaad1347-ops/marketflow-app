"""Local paid-media planning from explicit costs or business economics, never market forecasts."""
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
from typing import Literal, Optional

from pydantic import BaseModel, Field, root_validator, validator
from backend.content_engine import compose


class BudgetInputs(BaseModel):
    class Config:
        allow_inf_nan = False
        anystr_strip_whitespace = True

    budget_mode: Literal['manual', 'recommend'] = 'manual'
    total_budget: float = Field(default=0, ge=0, le=1_000_000_000_000)
    currency: str = Field(default='EGP', regex=r'^[A-Z]{3}$')
    campaign_days: int = Field(default=14, ge=1, le=365)
    target_results: Optional[int] = Field(default=None, ge=1, le=10_000_000)
    cost_per_result: float = Field(default=0, ge=0, le=1_000_000_000)
    spend_ceiling: float = Field(default=0, ge=0, le=1_000_000_000_000)
    price: float = Field(default=0, ge=0, le=1_000_000_000_000)
    gross_margin_percent: float = Field(default=0, ge=0, le=100)
    extra_variable_cost_per_order: float = Field(default=0, ge=0, le=1_000_000_000_000)
    lead_to_sale_rate_percent: float = Field(default=0, ge=0, le=100)

    @validator('target_results', pre=True)
    def whole_targets(cls, value):
        if value is None:return None
        if isinstance(value, bool) or int(value) != float(value):raise ValueError('Use a whole positive outcome target.')
        return int(value)

    @validator('total_budget','spend_ceiling')
    def currency_precision(cls, value):
        if Decimal(str(value)).quantize(Decimal('.01')) != Decimal(str(value)):
            raise ValueError('Budget and ceiling amounts support two decimal places.')
        return value

    @validator('currency')
    def currency_code(cls,value):
        value=value.strip().upper()
        if len(value)!=3 or not value.isascii() or not value.isalpha():raise ValueError('Use a three-letter currency code.')
        return value

    @root_validator
    def manual_budget_required(cls, values):
        if values.get('budget_mode') == 'manual' and values.get('total_budget', 0) <= 0:
            raise ValueError('Enter your budget, or choose Recommend a budget.')
        return values


class CampaignPlanInput(BudgetInputs):
    budget_mode: Literal['manual', 'recommend'] = 'recommend'
    business_name: str = Field(min_length=2, max_length=120)
    product: str = Field(min_length=3, max_length=1000)
    audience: str = Field(min_length=3, max_length=500)
    country: str = Field(min_length=2, max_length=120)
    objective: Literal['sales', 'leads', 'messages', 'traffic', 'awareness']
    platform: Literal['Facebook', 'Instagram', 'TikTok', 'Google', 'Multiple platforms', 'Meta'] = 'Facebook'
    creative_language: Literal['ar-EG', 'ar', 'en']
    benefit: str = Field(default='', max_length=1000)
    offer: str = Field(default='', max_length=500)
    has_video_creatives: bool = False
    sales_channel: Literal['website','whatsapp','phone','store'] = 'website'
    has_website: bool = False
    has_tracking: bool = False


def money(value):
    return float(Decimal(str(value)).quantize(Decimal('.01'), rounding=ROUND_HALF_UP))


def budget_label(plan):
    return f"{plan['total_budget']:,.2f} {plan['currency']} / {plan['campaign_days']} days"


def plan_budget(data):
    d = data.dict() if hasattr(data, 'dict') else data
    objective = d.get('objective', 'sales')
    unit = {'sales':'sales', 'leads':'qualified leads', 'messages':'conversations',
            'traffic':'clicks', 'awareness':'impressions'}[objective]
    target = d.get('target_results') or (10000 if objective == 'awareness' else 10)
    decimal = lambda value: Decimal(str(value))
    amount = decimal(d.get('cost_per_result', 0))
    contribution = max(Decimal(0), decimal(d.get('price', 0)) * decimal(d.get('gross_margin_percent', 0)) / 100 - decimal(d.get('extra_variable_cost_per_order', 0)))
    basis, explanation, missing = None, '', []
    warnings = ['This is a planning scenario, not a market price, guaranteed result or platform minimum. Media spend excludes creative production, agency fees and taxes.']
    if amount > 0:
        basis = 'supplied_result_cost'
        explanation = 'Your supplied cost assumption. Use a comparable recent campaign or a provider estimate; MarketFlow has not independently verified it.'
    elif objective in ('sales', 'leads', 'messages') and contribution > 0:
        if objective == 'sales' or d.get('lead_to_sale_rate_percent', 0) > 0:
            amount = contribution * Decimal('.70')
            if objective != 'sales':amount *= decimal(d['lead_to_sale_rate_percent']) / 100
            basis = 'economics_allowance'
            explanation = '70% of contribution per sale' + (' × your lead/message-to-sale rate' if objective != 'sales' else '') + '. This is an affordable planning allowance, not an expected auction cost.'
            warnings.append('The 70% allowance is a MarketFlow planning rule, not an advertising-platform learning requirement. Validate actual costs with a small test.')
        else:missing = ['lead_to_sale_rate_percent', 'cost_per_result']
    else:
        missing = ['cost_per_result'] if objective in ('traffic', 'awareness') else ['price', 'gross_margin_percent', 'cost_per_result']
    break_even = contribution * (decimal(d.get('lead_to_sale_rate_percent', 0)) / 100 if objective in ('leads','messages') else 1)
    if basis == 'supplied_result_cost' and objective in ('sales','leads','messages') and break_even > 0 and amount > break_even:
        warnings.append('Your cost assumption exceeds contribution per outcome. This scenario would not break even on the stated economics.')
    if contribution <= 0 and d.get('price', 0) > 0 and d.get('gross_margin_percent', 0) > 0:
        warnings.append('Contribution after variable costs is not positive. Review your offer economics before paid acquisition.')
    divisor = 1000 if objective == 'awareness' else 1
    days = d['campaign_days']
    recommended = money(Decimal(str(amount)) * Decimal(target) / divisor) if amount > 0 else None
    if recommended is not None and not .01 <= recommended <= 1_000_000_000_000:
        recommended = None
        missing = ['cost_per_result', 'target_results']
        warnings.append('The scenario is outside supported budget bounds. Review the cost and target inputs.')
    manual = d.get('budget_mode', 'manual') == 'manual'
    chosen = d.get('total_budget', 0) if manual else recommended
    cap = d.get('spend_ceiling', 0) if not manual else 0
    if chosen is not None and cap > 0:chosen = min(chosen, cap)
    gap = money(max(0, recommended - chosen)) if recommended is not None and chosen is not None else None
    if gap:
        warnings.append('Your selected budget is below the scenario needed for the stated test target. Reduce the target or increase the budget; the target is not a performance promise.')
    scenarios = []
    if recommended is not None:
        for key, count in [('lean', max(1, target // 2)), ('recommended', target), ('broader', target + max(1, target // 2))]:
            total = money(Decimal(str(amount)) * count / divisor)
            scenarios.append({'key':key, 'target_results':count, 'total_budget':total, 'daily_budget':money(total / days),
                              'within_ceiling':not cap or total <= cap})
    return {'status':'ready' if chosen is not None and chosen > 0 else 'needs_inputs',
        'mode':d.get('budget_mode', 'manual'), 'currency':d['currency'], 'campaign_days':days,
        'target_results':target, 'result_label':unit, 'cost_unit':'per 1,000 impressions (CPM)' if divisor == 1000 else 'per '+unit,
        'reference_cost':float(amount) if amount > 0 else None, 'basis':basis, 'basis_explanation':explanation,
        'contribution_per_sale':money(contribution), 'recommended_total':recommended,
        'recommended_daily':money(recommended / days) if recommended is not None else None,
        'total_budget':money(chosen) if chosen is not None else None,
        'daily_budget':money(chosen / days) if chosen is not None else None,
        'spend_ceiling':cap or None, 'funding_gap':gap,
        'missing_inputs':missing, 'scenarios':scenarios, 'warnings':warnings,
        'formula':f"{target:,} {unit} × reference cost" + (' ÷ 1,000' if divisor == 1000 else ''),
        'provider_budget_validation_required':True, 'is_performance_forecast':False}


def ad_concept(data):
    d = data.dict() if hasattr(data, 'dict') else data
    language = d['creative_language']
    ar = language != 'en'
    stage = 'tofu' if d['objective'] == 'awareness' else 'mofu' if d['objective'] == 'traffic' else 'bofu'
    ctas = {'sales':('اطلب التفاصيل', 'Explore the offer'), 'leads':('اطلب التفاصيل وحدد موعدًا للتواصل', 'Ask about the details'),
            'messages':('ابعتلنا رسالة لمعرفة التفاصيل', 'Message us for details'),
            'traffic':('اعرف التفاصيل', 'Explore the details'), 'awareness':('اكتشف الفكرة', 'Discover the idea')}
    brief = dict(brand=d['business_name'], product=d['product'], audience=d['audience'],
        benefit=d.get('benefit') or d['product'], offer=d.get('offer', ''), cta=ctas[d['objective']][0 if ar else 1],
        language=language, tone='friendly', channel={'Facebook':'meta', 'Meta':'meta', 'Instagram':'instagram', 'TikTok':'tiktok', 'Google':'google'}.get(d.get('platform'),'meta'),
        domain='auto', content_length='standard', funnel_stage=stage, proof='')
    seed = int(sha256(json.dumps(brief, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16],16)
    variant = compose(brief, seed)[0]
    return {**variant, 'language':language, 'format':('Short vertical video' if d.get('has_video_creatives') or d.get('platform')=='TikTok' else 'Image / carousel with a clear headline'),
            'engine':'local', 'review_required':True}


def campaign_plan(data):
    budget = plan_budget(data)
    d = data.dict() if hasattr(data, 'dict') else data
    suggestions = []
    if d['objective'] in ('leads','messages'):
        suggestions.append({'title':'Define a useful enquiry', 'detail':'Agree what qualifies a lead or conversation and record closed outcomes. An enquiry does not automatically count as a sale.'})
    if d.get('sales_channel') == 'website' and not d.get('has_website'):
        suggestions.append({'title':'Prepare the conversion destination', 'detail':'Build a usable landing page before a website campaign. For eligible Meta lead campaigns, consider a native lead form while you prepare it.'})
    if d.get('sales_channel') == 'website' and d['objective'] in ('sales','leads') and not d.get('has_tracking'):
        suggestions.append({'title':'Verify conversion measurement', 'detail':'Check the conversion event and reporting before optimizing for website outcomes.'})
    if d.get('platform') == 'Multiple platforms':
        suggestions.append({'title':'Keep the first test focused', 'detail':'This budget is one test pool, not a separate budget for each platform. Begin with one primary channel before splitting limited spend.'})
    if not d.get('has_video_creatives'):
        suggestions.append({'title':'Prepare the first creative', 'detail':'Use real product or property images. For TikTok or a video-first test, film the proposed vertical sequence before launch.'})
    if budget['funding_gap']:
        suggestions.append({'title':'Match the target to your spending limit', 'detail':'Your ceiling is kept. Reduce the test target or expand funding before relying on the larger scenario.'})
    if budget['status'] == 'needs_inputs':
        suggestions.append({'title':'Add one defensible cost basis', 'detail':'Use a comparable recent cost per outcome, or business contribution and close-rate inputs. No market benchmark has been guessed.'})
    if d['objective'] == 'awareness':
        suggestions.append({'title':'Measure awareness as awareness', 'detail':'Review reach, impressions and attention against the stated message. Do not treat views as guaranteed leads or sales.'})
    return {'budget':budget, 'ad_concept':ad_concept(data), 'recommendations':suggestions, 'engine':'local',
            'note':'Review the scenario and product facts before saving a draft. Nothing is published and no API key is used.'}
