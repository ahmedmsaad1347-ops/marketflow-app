import { ownerRequest } from '../services/api.js';
import {
  ownerShellView, ownerLoadingView, ownerOverviewView, ownerUsersView, ownerUserView,
  ownerRecordsView, ownerRecordView, ownerAuditView, ownerSettingsView, ownerDialogView,
} from '../views/ownerView.js';

export async function mountOwnerDashboard(container, currentUser) {
  if (currentUser?.platform_role !== 'owner' || currentUser?.account_status === 'suspended') {
    container.innerHTML = '<section class="page owner-console"><h1>Owner access required.</h1><p>This account does not have access to platform administration.</p></section>';
    return;
  }
  container.innerHTML = ownerShellView(currentUser);
  const root=container.querySelector('.owner-console'), panel=root.querySelector('#ownerPanel'), notice=root.querySelector('#ownerNotice');
  const state={tab:'overview',page:1,query:'',kind:'creative',detail:null};
  let generation=0, currentData=null, activeDialog=null;
  const announce=(message,error=false)=>{
    notice.textContent=message;notice.hidden=!message;notice.classList.toggle('is-error',error);
  };
  const request=(path,method='GET',body)=>ownerRequest(path,{method,...(body?{body:JSON.stringify(body)}:{})});

  async function load() {
    const ticket=++generation;
    panel.innerHTML=ownerLoadingView();panel.setAttribute('aria-busy','true');
    root.querySelectorAll('[data-owner-tab]').forEach(tab=>{
      const selected=tab.dataset.ownerTab===state.tab;
      tab.setAttribute('aria-selected',String(selected));tab.tabIndex=selected?0:-1;
    });
    panel.setAttribute('aria-labelledby',`owner-tab-${state.tab}`);
    let path;
    if(state.detail)path=state.detail.type==='user'?`/users/${state.detail.id}`:`/records/${state.detail.kind}/${state.detail.id}`;
    else if(state.tab==='overview')path='/overview';
    else if(state.tab==='users')path=`/users?q=${encodeURIComponent(state.query)}&page=${state.page}`;
    else if(['campaigns','content'].includes(state.tab))path=`/records?kind=${state.tab==='campaigns'?'campaigns':state.kind}&page=${state.page}`;
    else if(state.tab==='activity')path=`/audit?page=${state.page}`;
    else path='/settings';
    if(state.detail?.type==='record'&&state.detail.kind==='creative')path+=`?version_page=${state.detail.versionPage||1}`;
    try {
      const data=await request(path);
      if(!root.isConnected||ticket!==generation)return;
      currentData=data;
      if(state.detail)panel.innerHTML=state.detail.type==='user'?ownerUserView(data,currentUser):ownerRecordView(data.record);
      else if(state.tab==='overview')panel.innerHTML=ownerOverviewView(data.overview);
      else if(state.tab==='users')panel.innerHTML=ownerUsersView(data,state.query);
      else if(['campaigns','content'].includes(state.tab))panel.innerHTML=ownerRecordsView(data,state.tab==='campaigns'?'campaigns':state.kind,state.tab==='content');
      else if(state.tab==='activity')panel.innerHTML=ownerAuditView(data);
      else panel.innerHTML=ownerSettingsView(data);
    } catch(error) {
      if(!root.isConnected||ticket!==generation)return;
      currentData=null;panel.innerHTML='';
      announce(error.message||'Could not load this administration view. Refresh to retry.',true);
    } finally {
      if(root.isConnected&&ticket===generation)panel.removeAttribute('aria-busy');
    }
  }

  function confirmAction(title,message,perform) {
    if(activeDialog)return;
    const previouslyFocused=document.activeElement;
    root.insertAdjacentHTML('beforeend',ownerDialogView(title,message));
    const dialog=root.querySelector('.owner-dialog'), form=dialog.querySelector('form'), error=dialog.querySelector('[role=alert]');
    activeDialog=dialog;
    const cancel=()=>{if(form.querySelector('[type=submit]').disabled)return;dialog.close();};
    dialog.querySelectorAll('[data-owner-cancel]').forEach(button=>button.onclick=cancel);
    dialog.addEventListener('cancel',event=>{if(form.querySelector('[type=submit]').disabled)event.preventDefault();});
    dialog.addEventListener('close',()=>{
      form.reset();dialog.remove();activeDialog=null;
      if(previouslyFocused?.isConnected)previouslyFocused.focus();
    },{once:true});
    form.addEventListener('submit',async event=>{
      event.preventDefault();if(!form.reportValidity())return;
      const submit=form.querySelector('[type=submit]');if(submit.disabled)return;submit.disabled=true;error.hidden=true;
      const payload={reason:form.elements.reason.value,current_password:form.elements.current_password.value};
      try {
        await perform(payload);
        form.elements.current_password.value='';payload.current_password='';
        dialog.close();announce('Administrative change saved.');
        if(root.isConnected)await load();
      } catch(failure) {
        if(dialog.isConnected){error.textContent=failure.message||'This change could not be completed.';error.hidden=false;}
      } finally {
        payload.current_password='';form.elements.current_password.value='';
        if(submit.isConnected)submit.disabled=false;
      }
    });
    dialog.showModal();form.elements.reason.focus();
  }

  root.addEventListener('click',async event=>{
    const tab=event.target.closest('[data-owner-tab]');
    if(tab){state.tab=tab.dataset.ownerTab;state.detail=null;state.page=1;announce('');await load();return;}
    const target=event.target.closest('[data-owner-action]');
    if(!target||target.disabled)return;
    const action=target.dataset.ownerAction,id=Number(target.dataset.id);
    if(action==='refresh'){announce('');await load();return;}
    if(action==='page'){state.page=Number(target.dataset.page);await load();return;}
    if(action==='version-page'){
      const versionPage=Number(target.dataset.page);
      if(state.detail?.type!=='record'||state.detail.kind!=='creative'||!Number.isInteger(versionPage)||versionPage<1)return;
      state.detail.versionPage=versionPage;await load();panel.focus();return;
    }
    if(action==='kind'){state.kind=target.dataset.kind;state.page=1;await load();return;}
    if(action==='back'){state.detail=null;await load();return;}
    if(action==='user'){state.detail={type:'user',id};await load();panel.focus();return;}
    if(action==='record'){state.detail={type:'record',id,kind:target.dataset.kind,versionPage:1};await load();panel.focus();return;}
    if(action==='user-status'){
      const status=target.dataset.status;
      confirmAction(status==='suspended'?'Suspend this account?':'Restore this account?',`Account #${id}: ${currentData?.user?.email||''}. ${status==='suspended'?'Existing sessions will be revoked and access blocked. Saved work is retained.':'This account will be able to sign in again.'}`,
        payload=>request(`/users/${id}/status`,'POST',{...payload,status}));
    }
    if(action==='revoke')confirmAction('Sign out all sessions?',`Account #${id}: ${currentData?.user?.email||''}. This customer will need to sign in again on every device.`,payload=>request(`/users/${id}/revoke-sessions`,'POST',payload));
    if(action==='campaign-status'){
      const status=target.dataset.status;
      confirmAction('Change campaign workspace status?',`Campaign #${id} will be marked ${status}. This affects the saved workspace record only.`,payload=>request(`/campaigns/${id}/status`,'PATCH',{...payload,status}));
    }
  });

  root.addEventListener('submit',async event=>{
    if(event.target.id==='ownerSearchForm'){
      event.preventDefault();state.query=event.target.elements.query.value.trim();state.page=1;announce('');await load();
    }
    if(event.target.id==='ownerSettingsForm'){
      event.preventDefault();const form=event.target;if(!form.reportValidity())return;
      const settings={announcement:form.elements.announcement.value.trim(),maintenance:form.elements.maintenance.checked};
      confirmAction('Update platform settings?',settings.maintenance?'Customer workspace changes will be paused. Customers can continue reading and accessing their accounts.':'Customer workspace changes will be available. The announcement will be updated.',payload=>request('/settings','PUT',{...payload,...settings}));
    }
  });

  root.querySelector('[role=tablist]').addEventListener('keydown',event=>{
    if(!['ArrowRight','ArrowLeft','Home','End'].includes(event.key))return;
    const tabs=[...root.querySelectorAll('[data-owner-tab]')],index=tabs.indexOf(document.activeElement);
    if(index<0)return;event.preventDefault();
    const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
    tabs[next].focus();tabs[next].click();
  });
  await load();
}
