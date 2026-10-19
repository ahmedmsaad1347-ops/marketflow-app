import { getCreativeStatus, getCreativeProjects, getCreativeProject, generateCreative, saveCreativeSelection } from '../services/api.js';
import { creativeResultsView, creativeEscape } from '../views/creativeView.js';

const DRAFT_KEY = 'marketflow_creative_brief';
export function seedCreativeBrief(brief) {
  try { sessionStorage.setItem(DRAFT_KEY,JSON.stringify({brief})); } catch { /* In-tab editing still works. */ }
}

export async function attachCreativeStudio() {
  const section=document.querySelector('.creative-studio-page');
  if (!section) return;
  const form=section.querySelector('#creativeBriefForm');
  let projectId=null, version=null, versions=[], drafts=new Map(), busy=false, aiAvailable=false;
  const notice=(message,error=false)=>{
    const node=section.querySelector('#creativeNotice');
    node.hidden=false;node.className=error?'is-error':'';node.textContent=message;
  };
  const brief=()=>Object.fromEntries([...form.elements].filter(node=>node.name).map(node=>[node.name,node.value]));
  const remember=()=>{try {sessionStorage.setItem(DRAFT_KEY,JSON.stringify({brief:brief(),projectId,versionId:version?.id}));}catch {}};
  const fillBrief=value=>{Object.entries({funnel_stage:'full',proof:'',domain:'auto',content_length:'standard',generation_mode:'local',...value}).forEach(([key,value])=>{if(form.elements[key]) form.elements[key].value=value;});if(!aiAvailable)form.elements.generation_mode.value='local';};
  const usingAI=()=>form.elements.generation_mode.value==='ai'&&aiAvailable;
  const showEngine=()=>{section.querySelector('#creativeEngineStatus').textContent=usingAI()?'AI writing mode configured':'Local content engine · no API key needed';};
  const withBusy=async action=>{
    if(busy)return;
    busy=true;
    const controls=[...section.querySelectorAll('button,input,select,textarea')];
    const states=controls.map(node=>node.disabled);
    controls.forEach(node=>{node.disabled=true;});section.setAttribute('aria-busy','true');
    try {await action();}catch(error){if(section.isConnected)notice(error.message||'Could not complete this step. Please retry.',true);}
    finally{busy=false;if(section.isConnected){section.removeAttribute('aria-busy');controls.forEach((node,index)=>{if(node.isConnected)node.disabled=states[index];});}}
  };
  const refreshLibrary=async()=>{
    const response=await getCreativeProjects();
    if(!section.isConnected)return;
    const node=section.querySelector('#creativeProjectList');
    node.innerHTML=response.projects.length?response.projects.map(item=>`<button data-creative-project="${item.id}"><span>${creativeEscape(item.title)}</span><small>${new Date(item.updated_at).toLocaleDateString()}</small></button>`).join(''):'<p class="creative-muted">Your saved content projects will appear here.</p>';
    node.querySelectorAll('[data-creative-project]').forEach(button=>{button.onclick=()=>withBusy(()=>loadProject(Number(button.dataset.creativeProject)));});
  };
  const editorData=()=>{
    const editor=section.querySelector('#creativeSelectionForm');
    if(!editor || !editor.reportValidity())return null;
    const fields=new FormData(editor);
    return {variant_index:Number(editor.dataset.selectedIndex),content:Object.fromEntries(['angle','headline','hook','body','cta','visual_idea','funnel_stage','objective','rationale'].map(key=>[key,fields.get(key)])),
      reviewed:fields.get('reviewed')==='on',rating:fields.get('rating')?Number(fields.get('rating')):null};
  };
  const saveChoice=async(payload)=>{
    if(!payload)throw new Error('Complete your draft fields before saving.');
    const response=await saveCreativeSelection(version.id,payload);
    version=response.version;
    versions=versions.map(item=>item.id===version.id?version:item);
    return version;
  };
  const renderVersion=(current,selected=null)=>{
    version=current;showEngine();
    const root=section.querySelector('#creativeResults');
    root.innerHTML=creativeResultsView(current,selected,usingAI());
    const editor=root.querySelector('#creativeSelectionForm');
    const selectedIndex=Number(editor.dataset.selectedIndex);
    if(drafts.has(selectedIndex)) {
      const cached=drafts.get(selectedIndex);
      Object.entries(cached.content).forEach(([key,value])=>{editor.elements[key].value=value;});
      editor.elements.rating.value=cached.rating||'';
      editor.elements.reviewed.checked=cached.reviewed;
    }
    const picker=root.querySelector('#creativeVersions');
    versions.forEach(item=>{const option=document.createElement('option');option.value=item.id;option.textContent=`Version #${item.id} · ${new Date(item.created_at).toLocaleString()}${item.selection?' · choice saved':''}`;option.selected=item.id===current.id;picker.append(option);});
    picker.onchange=()=>{drafts=new Map();const next=versions.find(item=>item.id===Number(picker.value));fillBrief(next.brief);renderVersion(next);remember();};
    root.querySelectorAll('[data-creative-variant]').forEach(button=>{button.onclick=()=>{
      const data=editorData();if(data)drafts.set(selectedIndex,data);
      renderVersion(version,Number(button.dataset.creativeVariant));
    };});
    const countCharacters=()=>{
      root.querySelectorAll('[data-char-count]').forEach(node=>{
        const key=node.dataset.charCount, length=editor.elements[key].value.length;
        const limit=form.elements.channel.value==='google'?{headline:30,body:90}[key]:null;
        node.textContent=`${length}${limit?' / '+limit:''} characters${limit&&length>limit?' · shorten for Google Search':''}`;
        node.classList.toggle('is-warning',Boolean(limit&&length>limit));
      });
    };
    editor.oninput=()=>{countCharacters();root.querySelector('#creativeSaveState').textContent='Unsaved changes — save your choice to keep them.';};countCharacters();
    editor.onsubmit=event=>{event.preventDefault();const payload=editorData();if(!payload)return;withBusy(async()=>{
      await saveChoice(payload);if(!section.isConnected)return;
      root.querySelector('#creativeSaveState').textContent=payload.reviewed?'Saved with your review. Nothing has been published.':'Draft choice saved. Review the facts and offer before using it.';
      remember();await refreshLibrary();
    });};
    root.querySelector('#creativeCopy').onclick=async()=>{
      const payload=editorData();if(!payload)return;
      const text=['headline','hook','body','cta'].map(key=>payload.content[key]).join('\n\n');
      try {await navigator.clipboard.writeText(text);root.querySelector('#creativeSaveState').textContent='Content copied. Save your choice to keep any edits.';}
      catch {editor.elements.body.focus();editor.elements.body.select();notice('Clipboard access is unavailable. Select and copy the draft text manually.');}
    };
    let editAction=null;
    root.querySelectorAll('[data-creative-feedback]').forEach(button=>{button.onclick=()=>{const box=root.querySelector('#creativeFeedback');box.value=button.dataset.creativeFeedback;editAction=button.dataset.localEdit;box.focus();};});
    root.querySelector('#creativeFeedback').oninput=()=>{editAction=null;};
    root.querySelector('#creativeRefine').onclick=()=>{
      if(!form.reportValidity())return;
      const feedback=root.querySelector('#creativeFeedback').value.trim();
      if(!feedback){notice('Tell your agent what to change before creating a revision.',true);root.querySelector('#creativeFeedback').focus();return;}
      const payload=editorData();if(!payload)return;
      const nextBrief=brief();
      withBusy(async()=>{
        await saveChoice(payload);
        root.querySelector('#creativeSaveState').textContent='Your current choice is saved. Preparing the requested edit…';
        await generate(nextBrief,feedback,version.id,usingAI()?null:editAction);
      });
    };
  };
  const loadProject=async(id,versionId=null)=>{
    const response=await getCreativeProject(id);
    if(!section.isConnected)return;
    projectId=id;versions=response.versions;drafts=new Map();
    const selected=versions.find(item=>item.id===versionId)||versions[0];
    fillBrief(selected?.brief||response.project.brief);
    if(selected)renderVersion(selected);
    remember();notice('Saved project loaded. Your versions are kept separately.');
  };
  const generate=async(nextBrief,feedback='',sourceId=null,refinement=null)=>{
    notice(sourceId?'Updating your selected copy…':nextBrief.funnel_stage==='full'?'Creating TOFU, MOFU and BOFU content…':'Creating three angles for your selected funnel stage…');
    const response=await generateCreative({brief:nextBrief,project_id:projectId,source_version_id:sourceId,feedback,refinement});
    if(!section.isConnected)return;
    projectId=response.version.project_id;versions=[response.version,...versions];drafts=new Map();
    renderVersion(response.version);remember();await refreshLibrary();
    const total=response.version.result.variants.length;
    notice(sourceId?(response.version.result.engine==='openai'?`${total} changed AI direction${total===1?'':'s'} saved. Your previous choice is kept.`:`${total} changed local direction${total===1?'':'s'} saved. Edits: ${(response.version.result.applied_edits||[]).join(', ')}. Your original is kept.`):(response.version.result.engine==='openai'?'Three AI directions saved. Choose one and make it yours.':'Three local content directions saved. No AI or API key was used.'));
    section.querySelector('#creativeResults').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
  };
  form.oninput=remember;form.onchange=event=>{
    remember();
    if(event.target.name==='generation_mode'){
      const current=editorData();if(current)drafts.set(current.variant_index,current);
      showEngine();if(version)renderVersion(version,current?.variant_index??null);
    }
  };
  form.onsubmit=event=>{event.preventDefault();const next=brief();withBusy(()=>generate(next));};
  section.querySelector('#creativeNew').onclick=()=>{projectId=null;version=null;versions=[];drafts=new Map();form.reset();showEngine();remember();section.querySelector('#creativeResults').innerHTML='<div class="creative-studio-empty"><h2>A new story starts here.</h2><p>Complete your brief and choose a content language.</p></div>';notice('New project. Your previous projects remain in the library.');};
  try {
    let saved;try{saved=JSON.parse(sessionStorage.getItem(DRAFT_KEY)||'null');}catch{}
    const [status]=await Promise.all([getCreativeStatus(),refreshLibrary()]);
    if(!section.isConnected)return;
    aiAvailable=Boolean(status.ai_available);
    const domainSelect=form.elements.domain;
    (status.domains||[]).forEach(item=>{const option=document.createElement('option');option.value=item.id;option.textContent=item.label_en+' · '+item.label_ar;domainSelect.append(option);});
    form.querySelector('option[value="ai"]').disabled=!aiAvailable;
    showEngine();
    if(saved?.projectId){await loadProject(saved.projectId,saved.versionId);if(saved.brief)fillBrief(saved.brief);}
    else if(saved?.brief)fillBrief(saved.brief);
    showEngine();
  }catch(error){if(section.isConnected)notice('Could not load your creative library. Refresh this page to retry.',true);}
}
