import { creativeEscape as e } from '../views/creativeView.js';
import { budgetAdviceView, recommendedStepsView } from '../views/budgetPlannerView.js';
export function attachCampaignWizard(form,planning) {
  let step=1;
  const sections=[...form.querySelectorAll('[data-campaign-step]')];
  if(!sections.length)return;
  const next=form.querySelector('#campaignStepNext'),back=form.querySelector('#campaignStepBack'),save=form.querySelector('#campaignSave');
  const hints={Sales:'Count real purchases or closed sales. Check your contribution margin before deciding what acquisition can cost.',Leads:'Define a qualified lead and record which leads become customers. For property agents, use commission per closed deal in the budget inputs.',Messages:'A conversation is not a sale. Decide what a useful enquiry looks like, then follow it through to a real outcome.', 'Website traffic':'Use a working landing page and judge relevant visits. A click is not proof of a purchase.', 'Brand awareness':'Plan for reach and attention around a clear message. Awareness is measured differently from direct sales.'};
  const syncLabels=()=>{
    const goal=form.elements.goal.value;
    const targets={Sales:'Target sales for the test',Leads:'Target qualified leads',Messages:'Target conversations','Website traffic':'Target clicks','Brand awareness':'Target impressions'};
    const costs={Sales:'Known / assumed cost per sale',Leads:'Known / assumed cost per qualified lead',Messages:'Known / assumed cost per conversation','Website traffic':'Known / assumed CPC','Brand awareness':'Known / assumed CPM (per 1,000 impressions)'};
    form.querySelector('[data-budget-target-label]').textContent=targets[goal]||'Test target';
    form.querySelector('[data-budget-cost-label]').textContent=costs[goal]||'Known / assumed outcome cost';
  };
  const show=()=>{
    syncLabels();
    sections.forEach(section=>{section.hidden=Number(section.dataset.campaignStep)!==step;});
    form.querySelectorAll('[data-campaign-progress]').forEach(node=>{if(Number(node.dataset.campaignProgress)===step)node.setAttribute('aria-current','step');else node.removeAttribute('aria-current');});
    next.hidden=step===3;back.hidden=step===1;save.hidden=step!==3;
    next.innerHTML=step===1?'Budget & ideas →':'Review your plan →';
    form.querySelector('#campaignStepLabel').textContent=`Step ${step} of 3`;
    form.querySelector('#campaignGoalHint').textContent=hints[form.elements.goal.value]||'Choose an outcome so MarketFlow can suggest what to measure.';
    if(step===3){
      form.querySelector('#campaignWizardReview').innerHTML=`<div class="mf-campaign-summary">${[['Campaign',form.elements.name.value],['Product',form.elements.product.value],['Audience',form.elements.audience.value],['Market',form.elements.country.value],['Platform',form.elements.platform.value],['Outcome',form.elements.goal.value],['Selected media spend',form.elements.budget.value]].map(([label,value])=>`<div><small>${e(label)}</small><strong>${e(value)}</strong></div>`).join('')}</div>${planning.currentPlan?.()?budgetAdviceView(planning.currentPlan().budget,planning.currentPlan().ad_concept)+recommendedStepsView(planning.currentPlan().recommendations):'<p>You are saving a manually planned draft. You can add budget context and an ad idea later.</p>'}`;
    }
  };
  const valid=()=>{
    for(const field of sections[step-1].querySelectorAll('input,select,textarea'))if(!field.reportValidity())return false;
    return true;
  };
  next.onclick=()=>{if(!valid())return;step++;show();form.scrollIntoView({block:'start',behavior:'instant'});};
  back.onclick=()=>{step--;show();form.scrollIntoView({block:'start',behavior:'instant'});};
  let previousGoal=form.elements.goal.value;
  form.elements.goal.addEventListener('change',()=>{
    if(previousGoal&&previousGoal!==form.elements.goal.value){form.elements.planner_cost_per_result.value='';form.elements.planner_target_results.value='';}
    previousGoal=form.elements.goal.value;syncLabels();form.querySelector('#campaignGoalHint').textContent=hints[form.elements.goal.value]||'';
  });
  form.addEventListener('keydown',event=>{if(event.key==='Enter'&&event.target.tagName==='INPUT'&&step<3){event.preventDefault();next.click();}});
  form.addEventListener('submit',event=>{if(step<3){event.preventDefault();event.stopImmediatePropagation();next.click();}},true);
  show();
}
