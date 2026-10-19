import { previewCampaignPlan } from '../services/api.js';
import { budgetAdviceView, recommendedStepsView } from '../views/budgetPlannerView.js';
const goals={'Sales':'sales','Leads':'leads','Messages':'messages','Website traffic':'traffic','Brand awareness':'awareness'};
export function attachCampaignPlanner(form) {
  const root=form.querySelector('#campaignBudgetPlanner');
  if(!root)return ()=>({});
  let saved;try{saved=JSON.parse(root.dataset.savedPlan||'null');}catch{}
  let selected=saved?.input?.creative_language?saved.input:null, applied=Boolean(selected&&saved?.applied_budget);
  let preview=selected&&saved?.output?{input:selected,plan:saved.output}:null;
  const note=text=>{root.querySelector('#campaignPlanNotice').textContent=text;};
  const data=()=>{
    const read=key=>form.elements['planner_'+key]?.value||'';
    const number=key=>Number(read(key)||0);
    return {business_name:read('business_name')||form.elements.name.value, product:form.elements.product.value,
      audience:form.elements.audience.value,country:form.elements.country.value,platform:form.elements.platform.value,
      objective:goals[form.elements.goal.value],budget_mode:'recommend',currency:read('currency'),campaign_days:number('campaign_days'),
      target_results:read('target_results')?number('target_results'):null,cost_per_result:number('cost_per_result'),spend_ceiling:number('spend_ceiling'),
      price:number('price'),gross_margin_percent:number('gross_margin_percent'),extra_variable_cost_per_order:number('extra_variable_cost_per_order'),
      lead_to_sale_rate_percent:number('lead_to_sale_rate_percent'),creative_language:read('creative_language'),benefit:read('benefit'),offer:read('offer'),
      has_video_creatives:form.elements.planner_has_video_creatives.checked,sales_channel:read('sales_channel')||'website',
      has_website:form.elements.planner_has_website.checked,has_tracking:form.elements.planner_has_tracking.checked};
  };
  const show=plan=>{
    const result=root.querySelector('#campaignPlanResult');
    result.innerHTML=budgetAdviceView(plan.budget,plan.ad_concept)+recommendedStepsView(plan.recommendations);
    if(plan.budget?.status==='ready'){
      const button=document.createElement('button');button.type='button';button.className='workspace-mint-button';button.id='campaignPlanApply';button.textContent='Use this budget & ad idea';
      button.onclick=()=>{
        if(!preview)return;
        selected=preview.input;applied=true;
        const budget=preview.plan.budget;
        form.elements.budget.value=`${budget.total_budget.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})} ${budget.currency} / ${budget.campaign_days} days`;
        note('Budget and ad idea applied. Saving this campaign keeps both as a draft.');
      };result.append(button);
    }
  };
  if(saved?.output)show(saved.output);
  root.querySelector('#campaignPlanGenerate').onclick=async()=>{
    for(const name of ['name','product','audience','country','platform','goal'])if(!form.elements[name].reportValidity())return;
    for(const field of root.querySelectorAll('input,select,textarea'))if(!field.reportValidity())return;
    const input=data();
    if(!input.creative_language){note('Choose the language for your proposed ad.');form.elements.planner_creative_language.focus();return;}
    const button=root.querySelector('#campaignPlanGenerate');button.disabled=true;note('Calculating your test budget and preparing an ad idea…');
    try{
      const response=await previewCampaignPlan(input);
      if(!root.isConnected)return;
      if(JSON.stringify(data())!==JSON.stringify(input)){note('Your brief changed. Suggest the budget again to use the latest details.');return;}
      preview={input,plan:response.plan};show(response.plan);
      selected=input;applied=false;
      note(response.plan.budget.status==='ready'?'Review your budget and idea, then apply them. No API key was used.':'Your ad idea is ready. Add a cost assumption or business economics to calculate a budget.');
    }catch(error){if(root.isConnected)note(error.message||'Could not prepare this plan. Your campaign is unchanged.');}
    finally{if(button.isConnected)button.disabled=false;}
  };
  form.addEventListener('input',event=>{
    if(event.target.name==='budget'&&selected){applied=false;note('Your budget was edited manually. The ad idea and reference scenario will still be saved.');return;}
    if(event.target.name&&event.target.name!=='budget'&&selected){selected=null;preview=null;applied=false;root.querySelector('#campaignPlanResult').innerHTML='';note('Details changed. Suggest a fresh budget and ad idea for this brief.');}
  });
  form.addEventListener('change',event=>{if(event.target.matches('select,[type=checkbox]'))event.target.dispatchEvent(new Event('input',{bubbles:true}));});
  const context=()=>selected?{planner:selected,planner_apply_budget:applied}:{};
  context.currentPlan=()=>{
    if(!selected)return null;
    const plan=preview?.plan||saved?.output;
    return plan?{...plan,budget:plan.budget?{...plan.budget,display_mode:applied?'selected':'reference'}:null}:null;
  };
  return context;
}
