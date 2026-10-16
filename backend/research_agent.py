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


class ArticleText(HTMLParser):
    """Extract visible article/main text while excluding page furniture."""
    ignored = {'script', 'style', 'noscript', 'svg', 'nav', 'header', 'footer',
               'aside', 'form', 'button', 'select', 'dialog', 'template'}
    void = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
            'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__()
        self.stack = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        parent = self.stack[-1] if self.stack else ('', False, False, False)
        identifiers = (attrs.get('class', '') + ' ' + attrs.get('id', '')).lower()
        skip = (parent[1] or tag in self.ignored or 'hidden' in attrs
                or attrs.get('aria-hidden') == 'true'
                or attrs.get('role') in {'navigation', 'banner', 'contentinfo', 'dialog'}
                or any(word in identifiers for word in ('cookie', 'consent', 'site-menu')))
        main = parent[2] or tag in {'article', 'main'} or attrs.get('role') == 'main'
        link = parent[3] or tag == 'a'
        if tag not in self.void:
            self.stack.append((tag, skip, main, link))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        frame = self.stack[-1] if self.stack else ('', False, False, False)
        value = ' '.join(data.split())
        if value and not frame[1]:
            self.parts.append((value, frame[2], frame[3]))


def challenge_page(text):
    prefix = ' '.join(text.lower().split())[:3000]
    markers = ('checking your browser', 'we think you might be a bot',
               'verify you are human', 'verify that you are human',
               'enable javascript and cookies to continue', 'attention required! | cloudflare',
               'sorry, you have been blocked', 'unusual traffic from your computer network')
    return any(marker in prefix for marker in markers)


def extract_page(raw):
    if challenge_page(textify(raw)):
        return {'retrieval_status': 'blocked', 'snippet': '',
                'retrieval_reason': 'The site returned a browser or bot-verification page.'}
    parser = ArticleText()
    parser.feed(raw)
    preferred = [part for part in parser.parts if part[1]]
    parts = preferred if sum(len(part[0]) for part in preferred) >= 160 else parser.parts
    text = ' '.join(part[0] for part in parts)
    non_link_length = sum(len(part[0]) for part in parts if not part[2])
    if (len(text) < 160 or len(text.split()) < 25
            or non_link_length < max(100, len(text) * 0.25)):
        return {'retrieval_status': 'insufficient_content', 'snippet': '',
                'retrieval_reason': 'No substantial article or guidance text could be extracted.'}
    return {'retrieval_status': 'retrieved', 'snippet': text[:650],
            'retrieval_reason': 'Extracted article or main-page text; relevance still needs review.'}

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
    return retrieve_source(url)['snippet']


def retrieve_source(url):
    try:
        return extract_page(fetch(url))
    except Exception:
        return {'retrieval_status': 'unavailable', 'snippet': '',
                'retrieval_reason': 'The page could not be downloaded or parsed.'}

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
    key=platform.strip().lower()
    # Reserve a place for the official page, including failed retrieval status.
    # General business results must not fill the list before platform research.
    for url in SEEDS.get(key, [])[:1]:
        seen.add(url)
        sources.append({'title':f'{platform} official advertising help','url':url,
                        'source':'Official seed','query':'official platform documentation',
                        'purpose':'Official platform guidance', 'official_provider':key,
                        **retrieve_source(url)})
    remaining = max_sources - len(sources)
    # Search all three topics with balanced slots. Only official search hits
    # are used for the platform-guidance topic.
    for index, q in enumerate(queries):
        quota = (remaining + len(queries) - index - 1) // (len(queries) - index)
        if quota <= 0:
            continue
        topic_count = 0
        if index == 2 and key in OFFICIAL:
            q += ' ' + ' OR '.join('site:' + host for host in OFFICIAL[key])
        for item in ddg(q):
            if item['url'] in seen: continue
            if index == 2 and official_provider(item['url']) != key: continue
            item = dict(item)
            seen.add(item['url'])
            item.update(query=q, official_provider=official_provider(item['url']),
                        purpose='Official platform guidance' if index == 2 else 'Business background')
            item.update(retrieve_source(item['url']))
            sources.append(item)
            remaining -= 1
            topic_count += 1
            if topic_count >= quota: break
    for s in sources:
        s['authority_score']=50 if s.get('official_provider') else 0
        if domain(s['url']).endswith(('.gov','.edu')): s['authority_score']+=25
    sources.sort(key=lambda x:(x.get('authority_score',0),bool(x.get('snippet'))),reverse=True)
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
                 and s.get('retrieval_status') in {None, 'retrieved'}
                 and not challenge_page(s['snippet'])]
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
    proposed_changes = []
    offer = (state.get('offer') or '').strip()
    has_trial = re.search(r'\btrial\b', offer, re.I) and not re.search(
        r'\b(no|without|not|unavailable|expired)\b', offer, re.I)
    if vertical == 'saas' and has_trial and 'trial' not in cta.lower():
        message = 'CTA should reflect the supplied trial offer instead of a generic CTA.'
        corrections.append(message)
        proposed_changes.append({'field': 'cta', 'value': 'Start your trial',
                                 'reason': message, 'basis': offer})
    gaps = [check['detail'] for check in checks if not check['passed']]
    needs_review = bool(corrections or gaps)
    return {
        'status': 'needs_review' if needs_review else 'reviewed',
        # Snippets and deterministic checks cannot establish high confidence in
        # every campaign claim, even when many search results are returned.
        'confidence': 'Needs review' if needs_review else 'Medium',
        'checks': checks,
        'corrections': corrections,
        'proposed_changes': proposed_changes,
        'evidence_gaps': gaps,
        'source_count': len(retrieved),
        'discovered_source_count': len(sources),
        'summary': ('Strategy has unresolved review flags; review these before launch.'
                    if needs_review else
                    'Basic rule checks passed. Retrieved sources do not verify every campaign claim.'),
    }

def apply_review(strategy,review):
    out=dict(strategy)
    review = dict(review)
    applied = []
    unresolved = list(review.get('corrections', []))
    for change in review.get('proposed_changes', []):
        if change.get('field') != 'cta' or change.get('value') != 'Start your trial':
            continue
        if not change.get('basis') or change.get('reason') not in unresolved:
            continue
        previous = out.get('cta')
        out['cta'] = change['value']
        out['creative_plan'] = {**(out.get('creative_plan') or {}), 'cta': change['value']}
        applied.append({**change, 'previous_value': previous})
        unresolved.remove(change['reason'])
    review['applied_corrections'] = applied
    review['corrections'] = unresolved
    if applied:
        remaining = bool(unresolved or review.get('evidence_gaps'))
        review['status'] = 'needs_review' if remaining else 'corrected'
        review['confidence'] = 'Needs review' if remaining else 'Medium'
        review['summary'] = ('CTA corrected to match the supplied offer. Other review flags remain.'
                             if remaining else 'CTA corrected to match the supplied offer; basic checks passed.')
    risks=list(out.get('risks') or [])
    for c in [*review.get('corrections',[]), *review.get('evidence_gaps',[])]:
        if c not in risks: risks.append(c)
    if review.get('corrections') or review.get('evidence_gaps'):
        out['launch_readiness'] = 'Review required before launch'
    out['risks']=risks; out['agent_review']=review
    return out
