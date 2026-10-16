import html, re, ssl, urllib.parse, urllib.request
from html.parser import HTMLParser
from datetime import datetime
from urllib.parse import urlparse

UA='Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/124 Mobile Safari/537.36'
OFFICIAL={
 'google':('support.google.com','ads.google.com'),
 'meta':('facebook.com','meta.com'),
 'tiktok':('ads.tiktok.com','tiktok.com'),
}
SEEDS={
 'google':['https://support.google.com/google-ads/'],
 'meta':['https://www.facebook.com/business/help'],
 'tiktok':['https://ads.tiktok.com/help/'],
}

class Text(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style','noscript','svg'}: self.skip+=1
    def handle_endtag(self,tag):
        if tag in {'script','style','noscript','svg'} and self.skip: self.skip-=1
    def handle_data(self,data):
        if not self.skip:
            v=' '.join(data.split())
            if v: self.parts.append(v)

def fetch(url, timeout=9, max_bytes=300000):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept-Language':'en-US,en;q=0.9'})
    with urllib.request.urlopen(req,timeout=timeout,context=ssl.create_default_context()) as r:
        raw=r.read(max_bytes); ctype=r.headers.get('Content-Type','')
    if 'text' not in ctype and 'html' not in ctype: return ''
    return raw.decode('utf-8','ignore')

def textify(raw):
    p=Text()
    try: p.feed(raw)
    except Exception: pass
    return re.sub(r'\s+',' ',html.unescape(' '.join(p.parts))).strip()

def domain(url):
    hostname = (urlparse(url).hostname or '').lower()
    return hostname.removeprefix('www.')

def official_provider(url):
    d=domain(url)
    for provider, domains in OFFICIAL.items():
        for x in domains:
            if d==x or d.endswith('.'+x): return provider
    return None

def ddg(query, limit=6):
    url='https://html.duckduckgo.com/html/?q='+urllib.parse.quote_plus(query)
    try: raw=fetch(url)
    except Exception: return []
    out=[]
    for m in re.finditer(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',raw,re.I|re.S):
        href=html.unescape(m.group(1))
        if 'duckduckgo.com' in urllib.parse.urlparse(href).netloc:
            qs=urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
            if qs.get('uddg'): href=urllib.parse.unquote(qs['uddg'][0])
        if not href.startswith('http'): continue
        title=textify(m.group(2))
        if title: out.append({'title':title[:180],'url':href,'source':'DuckDuckGo'})
        if len(out)>=limit: break
    return out

def snippet(url):
    try: return textify(fetch(url))[:650]
    except Exception: return ''

def research_business(state,strategy,max_sources=10):
    if max_sources <= 0:
        return {'researched_at': datetime.utcnow().isoformat(), 'queries': [],
                'sources': [], 'search_provider': 'DuckDuckGo HTML + direct official sources',
                'note': 'No external sources requested.'}
    product=state.get('product','').strip(); country=state.get('country','').strip()
    profile=strategy.get('business_profile') or {}; vertical=profile.get('vertical',''); target=profile.get('target_industry','')
    platform=strategy.get('recommended_platform',''); campaign=strategy.get('recommended_campaign_type','')
    queries=[f'{product} {country} competitors marketing',f'{vertical} {target} advertising {country}',f'{platform} {campaign} official ads guidance']
    seen=set(); sources=[]
    for q in queries:
        for item in ddg(q):
            if item['url'] in seen: continue
            item = dict(item)
            seen.add(item['url']); item['query']=q; item['official_provider']=official_provider(item['url']); item['snippet']=snippet(item['url']); sources.append(item)
            if len(sources)>=max_sources: break
        if len(sources)>=max_sources: break
    key=platform.strip().lower()
    if key in SEEDS:
        for url in SEEDS[key]:
            if url not in seen:
                sources.append({'title':f'{platform} official advertising help','url':url,'source':'Official seed','query':'official platform documentation','official_provider':key,'snippet':snippet(url)})
    for s in sources:
        s['retrieval_status'] = 'retrieved' if s.get('snippet', '').strip() else 'unavailable'
        s['authority_score']=50 if s.get('official_provider') else 0
        if domain(s['url']).endswith(('.gov','.edu')): s['authority_score']+=25
    sources.sort(key=lambda x:(bool(x.get('snippet')),x.get('authority_score',0)),reverse=True)
    return {'researched_at':datetime.utcnow().isoformat(),'queries':queries,'sources':sources[:max_sources],'search_provider':'DuckDuckGo HTML + direct official sources','note':'Live research is best-effort; official platform sources are prioritized when reachable.'}

def review_strategy(strategy,state,research):
    corrections=[]; checks=[]; profile=strategy.get('business_profile') or {}
    platform=strategy.get('recommended_platform',''); campaign=strategy.get('recommended_campaign_type','')
    vertical=profile.get('vertical_key') or profile.get('vertical','').lower(); buyer=profile.get('buyer_type','')
    objective=state.get('objective','').strip().lower(); demand=state.get('demand_type','').strip().lower(); has_website=bool(state.get('has_website')); has_tracking=bool(state.get('has_tracking'))
    sources = research.get('sources') or []
    # A discovered URL is not evidence that a page was read. Recompute authority
    # from the URL rather than trusting saved or search-provided metadata.
    retrieved = [s for s in sources if s.get('snippet', '').strip()
                 and s.get('retrieval_status') in {None, 'retrieved'}]
    official = any(official_provider(s.get('url', '')) == platform.strip().lower()
                   for s in retrieved)
    checks.append({'name':'Business identity','passed':bool(profile.get('vertical')),'detail':profile.get('vertical') or 'Generic'})
    checks.append({'name':'Official platform evidence','passed':official,'detail':'Official page content retrieved; campaign-specific claims still need verification.' if official else 'No official page content was retrieved for the selected platform.'})
    if platform=='Google' and campaign=='Google Search' and not has_website: corrections.append('Google Search needs a usable website or landing page before launch.')
    if objective in {'sales','leads'} and has_website and not has_tracking: corrections.append('Conversion tracking is not verified; treat launch as setup-required.')
    if vertical=='saas' and buyer in {'B2B','B2B + B2C'} and demand in {'search','mixed'}:
        card=strategy.get('channel_scorecard') or []
        g=next((x for x in card if x.get('campaign_type')=='Google Search' and x.get('eligible')),None)
        if g and platform!='Google' and g.get('score',0)>=strategy.get('fit_score',0)-5:
            corrections.append('B2B SaaS has a near-tied Google Search option; the final plan must explicitly justify choosing another channel.')
    cta=((strategy.get('creative_plan') or {}).get('cta') or strategy.get('cta') or '')
    if vertical=='saas' and 'trial' in (state.get('offer') or '').lower() and 'trial' not in cta.lower(): corrections.append('CTA should reflect the verified trial offer instead of a generic quote CTA.')
    gaps = [check['detail'] for check in checks if not check['passed']]
    needs_review = bool(corrections or gaps)
    return {
        'status': 'needs_review' if needs_review else 'reviewed',
        # Snippets and deterministic checks cannot establish high confidence in
        # every campaign claim, even when many search results are returned.
        'confidence': 'Needs review' if needs_review else 'Medium',
        'checks': checks,
        'corrections': corrections,
        'evidence_gaps': gaps,
        'source_count': len(retrieved),
        'discovered_source_count': len(sources),
        'summary': ('Strategy has unresolved review flags; review these before launch.'
                    if needs_review else
                    'Basic rule checks passed. Retrieved sources do not verify every campaign claim.'),
    }

def apply_review(strategy,review):
    out=dict(strategy); risks=list(out.get('risks') or [])
    for c in [*review.get('corrections',[]), *review.get('evidence_gaps',[])]:
        if c not in risks: risks.append(c)
    if review.get('corrections') or review.get('evidence_gaps'):
        out['launch_readiness'] = 'Review required before launch'
    out['risks']=risks; out['agent_review']=review
    return out
