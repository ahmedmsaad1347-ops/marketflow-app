import { creativeEscape as e } from './creativeView.js';

const options=(values,current)=>values.map(([value,label])=>`<option value="${value}" ${String(current)===String(value)?'selected':''}>${label}</option>`).join('');
const input=(name,label,value='',help='',max=1000000000000,step='0.01',min=0)=>`<label>${label}<input name="${name}" type="number" min="${min}" max="${max}" step="${step}" value="${e(value??'')}">${help?`<small>${help}</small>`:''}</label>`;
export function budgetExtraFields(prefix='',value={}) {
  return `<div class="budget-planner-grid">${input(prefix+'target_results','<span data-budget-target-label>Test target: outcomes / impressions</span>',value.target_results??'', 'Leave blank for 10 outcomes, or 10,000 impressions for Awareness. These are planning targets.',10000000,'1',1)}${input(prefix+'cost_per_result','<span data-budget-cost-label>Known / assumed cost per outcome</span>',value.cost_per_result||'', 'Optional with positive business economics. Traffic uses CPC; Awareness uses CPM.',1000000000,'any')}${input(prefix+'spend_ceiling','Maximum affordable test spend',value.spend_ceiling||'', 'Optional ceiling. A smaller budget will show a funding gap.')}
    <label>Ad language<select name="${prefix}creative_language"><option value="">Choose language</option>${options([['ar-EG','العربية · مصري'],['ar','العربية · فصحى'],['en','English']],value.creative_language)}</select></label></div>
    <p class="budget-planner-note">MarketFlow uses your cost assumption or 70% of contribution per sale, adjusted for your real close rate for leads/messages. It does not invent a market price. For property agents, use your commission/revenue per closed deal and its margin.</p>`;
}

export function campaignPlannerView(snapshot=null) {
  const v=snapshot?.input||{};
  return `<section class="budget-planner" id="campaignBudgetPlanner" data-saved-plan="${e(JSON.stringify(snapshot))}"><p class="workspace-eyebrow">LET MARKETFLOW PLAN THE FIRST TEST</p><h2>A budget and an ad idea, together.</h2><p>Your goal is set. Add a cost assumption or your business economics, and see a daily and total test budget before saving.</p>
    <label>Brand / business name<input name="planner_business_name" maxlength="120" value="${e(v.business_name||'')}" placeholder="Uses the campaign name if left blank"></label>
    <div class="budget-planner-grid"><label>Currency<select name="planner_currency">${options([...new Set(['EGP','USD','SAR','AED','EUR','GBP',...(v.currency?[v.currency]:[])])].map(x=>[x,x]),v.currency||'EGP')}</select></label><label>Test duration<select name="planner_campaign_days">${options([...new Set([7,14,30,60,90,...(v.campaign_days?[v.campaign_days]:[])])].map(x=>[x,x+' days']),v.campaign_days||14)}</select></label></div>
    <label>Where should the customer take action?<select name="planner_sales_channel">${options([['website','Website / landing page'],['whatsapp','WhatsApp / messages'],['phone','Phone call'],['store','Store / in person']],v.sales_channel||'website')}</select></label>
    <div class="mf-campaign-readiness"><label><input type="checkbox" name="planner_has_website" ${v.has_website?'checked':''}> I have a usable website / landing page</label><label><input type="checkbox" name="planner_has_tracking" ${v.has_tracking?'checked':''}> Conversion tracking is verified</label></div>
    ${budgetExtraFields('planner_',v)}
    <details class="budget-planner-economics"><summary>Use my business economics instead of a cost assumption</summary><div class="budget-planner-grid">${input('planner_price','Revenue / commission per closed sale',v.price||'')}${input('planner_gross_margin_percent','Gross margin %',v.gross_margin_percent||'','',100)}${input('planner_extra_variable_cost_per_order','Extra variable cost per sale',v.extra_variable_cost_per_order||'')}${input('planner_lead_to_sale_rate_percent','Lead / message → sale rate %',v.lead_to_sale_rate_percent||'','Use the same qualification definition as the campaign goal.',100)}</div></details>
    <label>Main benefit<textarea name="planner_benefit" maxlength="1000" rows="2" placeholder="Use a benefit you can support">${e(v.benefit||'')}</textarea></label><label>Offer / exact terms<textarea name="planner_offer" maxlength="500" rows="2" placeholder="Prices and terms to preserve">${e(v.offer||'')}</textarea></label><label class="budget-checkbox"><input type="checkbox" name="planner_has_video_creatives" ${v.has_video_creatives?'checked':''}> I have usable vertical video</label>
    <button type="button" id="campaignPlanGenerate" class="workspace-mint-button">Suggest my budget & ad idea</button><p id="campaignPlanNotice" role="status" aria-live="polite"></p><div id="campaignPlanResult"></div></section>`;
}

export function budgetAdviceView(plan,concept=null) {
  if(!plan&&!concept)return '';
  const fmt=value=>value==null?'—':Number(value).toLocaleString(undefined,{maximumFractionDigits:2});
  const fmtCost=value=>value==null?'—':Number(value).toLocaleString(undefined,{maximumFractionDigits:6});
  const ar=concept?.language&&concept.language!=='en';
  return `<div class="budget-advice" data-budget-advice>${plan?`<div class="budget-advice-heading"><span class="workspace-eyebrow">BUDGET ADVISOR · PLANNING SCENARIO</span><h3>${plan.recommended_total==null?'A little more information is needed':`${fmt(plan.recommended_total)} ${e(plan.currency)} for this test`}</h3>${plan.recommended_daily!=null?`<p>${fmt(plan.recommended_daily)} ${e(plan.currency)} / day on average · ${e(plan.campaign_days)} days</p>`:''}</div>
    ${plan.recommended_total==null?'<p>Add a comparable cost per result, or positive sale contribution and the lead/message-to-sale rate. Traffic needs CPC; Awareness needs CPM. Your ad idea is available below.</p>':`<p>Planning target: <strong>${e(plan.target_results)} ${e(plan.result_label)}</strong>. Cost basis: ${fmtCost(plan.reference_cost)} ${e(plan.currency)} ${e(plan.cost_unit)}.</p>`}
    ${plan.basis_explanation?`<p class="budget-planner-note">${e(plan.basis_explanation)}</p>`:''}
    <p class="budget-planner-note">Planning scenario only. Actual advertising costs and results are not guaranteed.</p>
    ${plan.total_budget!=null?`<div class="budget-advice-selected"><span>${plan.display_mode==='reference'?'Reference scenario budget':'Proposed test budget'}</span><strong>${fmt(plan.total_budget)} ${e(plan.currency)}</strong><small>${fmt(plan.daily_budget)} / day on average</small></div>`:''}
    ${plan.funding_gap>0&&plan.display_mode!=='reference'?`<p class="budget-funding-gap" role="note">Funding gap: ${fmt(plan.funding_gap)} ${e(plan.currency)} against the stated planning target. Your ceiling is respected.</p>`:''}
    ${plan.scenarios?.length?`<div class="budget-scenarios">${plan.scenarios.map(item=>`<article><small>${e({lean:'Lean test',recommended:'Recommended test',broader:'Broader test'}[item.key])}</small><strong>${fmt(item.total_budget)} ${e(plan.currency)}</strong><span>${e(item.target_results)} ${e(plan.result_label)}</span>${!item.within_ceiling?'<small>Above your ceiling</small>':''}</article>`).join('')}</div>`:''}
    <details><summary>How this budget was calculated</summary><p>${e(plan.basis_explanation)}</p><p>${e(plan.formula)}</p>${(plan.warnings||[]).map(text=>`<p>${e(text)}</p>`).join('')}<p>Confirm campaign eligibility and current platform minimums before launch.</p></details>`:''}
    ${concept?`<article class="budget-ad-concept"><p class="workspace-eyebrow">YOUR PROPOSED AD · ${e(concept.funnel_stage?.toUpperCase())}</p><p>${e(concept.format)}</p><div dir="${ar?'rtl':'ltr'}"><h3>${e(concept.headline)}</h3><strong>${e(concept.hook)}</strong><p class="budget-ad-copy">${e(concept.body)}</p><p><strong>${e(concept.cta)}</strong></p><p>${e(concept.visual_idea)}</p></div><small>Local writing from your supplied facts. Review copy and terms before use.</small></article>`:''}</div>`;
}

export function savedCampaignPlanView(campaign) {
  let saved;try{saved=JSON.parse(campaign.planning_json||'null');}catch{}
  return saved?`<section class="budget-planner"><h2>Your saved campaign plan</h2>${!saved.applied_budget?'<p>The campaign uses your manually entered budget. The advisor below is retained as a reference.</p>':''}${budgetAdviceView(saved.output?.budget?{...saved.output.budget,display_mode:saved.applied_budget?'selected':'reference'}:null,saved.output?.ad_concept)}${recommendedStepsView(saved.output?.recommendations)}</section>`:'';
}

export function recommendedStepsView(items=[]) {
 return items?.length?`<section class="mf-campaign-suggestions"><p class="workspace-eyebrow">RECOMMENDED NEXT STEPS</p>${items.map(item=>`<article><strong>${e(item.title)}</strong><p>${e(item.detail)}</p></article>`).join('')}</section>`:'';
}
