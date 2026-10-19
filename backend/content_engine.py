"""Offline, fact-grounded marketing copy composition. No network or model calls."""
import random
import re
from backend.content_domains import resolve_domain

EDIT_LABELS={
    'shorter':('Shorter','أقصر'), 'longer':('More detail','تفاصيل أكثر'),
    'clearer':('Clearer','أوضح'), 'calmer':('Calmer','أهدى'), 'bolder':('Bolder','أقوى'),
    'benefit':('Benefit first','ابدأ بالفائدة'), 'new_hook':('New hook','افتتاحية جديدة'),
    'new_angle':('New angle','زاوية جديدة'), 'new_cta':('New CTA','دعوة مختلفة'),
    'formal':('More formal','أكثر رسمية'), 'friendly':('More friendly','أقرب للعميل'),
}


def _norm(value):return ' '.join(str(value).casefold().split()).strip(' .!؟?')

def parse_edits(feedback,action=None):
    text=feedback.casefold().strip()
    if re.search(r"\b(?:do not|don't|dont|not)\b|مش عايز|لا تختصر",text):return []
    phrases={
        'shorter':('shorter','shorten','أقصر','اقصر','اختصر'),
        'longer':('longer','more detail','أطول','اطول','تفاصيل أكثر','تفاصيل اكتر'),
        'clearer':('clearer','clarify','أوضح','اوضح','وضّح','وضح'),
        'calmer':('calmer','calm tone','أهدى','اهدى','أهدأ','اهدا'),
        'bolder':('bolder','stronger','أقوى','اقوي','اقوى'),
        'benefit':('benefit','الفائدة','الفايده','الفايدة'),
        'new_hook':('new hook','new opening hook','different hook','هوك جديد','افتتاحية جديدة','غير الهوك'),
        'new_angle':('new angle','different angle','زاوية جديدة','زاويه جديده','فكرة جديدة','فكره جديده'),
        'new_cta':('new cta','different cta','دعوة مختلفة','دعوه مختلفه','غير الcta'),
        'formal':('formal','professional','رسمية','رسميه','رسمي','احترافي'),
        'friendly':('friendly','أقرب للعميل','اقرب للعميل','ودود'),
    }
    result=[action] if action else []
    for key,words in phrases.items():
        if any(word in text for word in words) and key not in result:result.append(key)
    return result


def _join(*parts):
    values=[]
    for part in parts:
        part=str(part).strip()
        if part and _norm(part) not in {_norm(value) for value in values}:values.append(part)
    return '\n\n'.join(values)


def _context(brief):
    domain=resolve_domain(brief)
    ar=brief['language']!='en'
    return domain,ar,brief['language']=='ar-EG',domain['topic_ar' if ar else 'topic_en'],domain['criterion_ar' if ar else 'criterion_en']


def hooks(brief,stage):
    domain,ar,egy,topic,criterion=_context(brief)
    brand,benefit=brief['brand'],brief['benefit']
    if ar:
        if stage=='tofu':return [f'{topic}... تبدأ منين؟' if egy else f'من أين تبدأ في {topic}؟',
            f'إيه اللي يفرق معاك في {topic}؟' if egy else f'ما الذي يهمك عند {topic}؟',
            f'قبل ما تختار، فكّر في {criterion}.' if egy else f'قبل الاختيار، فكّر في {criterion}.',
            f'{brief["audience"]}، السؤال ده ليكم.' if egy else f'سؤال يهم {brief["audience"]}.',
            f'خلينا نبص على فكرة {benefit}.' if egy else f'لننظر إلى فكرة {benefit}.']
        if stage=='mofu':return [f'هل {brand} مناسب لاحتياجك؟',f'إيه اللي بيقدمه {brand} فعلًا؟' if egy else f'ماذا يقدّم {brand} فعلًا؟',
            f'{criterion}: تفاصيل تستحق السؤال.',f'بص على التفاصيل قبل القرار.' if egy else 'انظر إلى التفاصيل قبل القرار.',
            f'{benefit}... الفكرة في التفاصيل.']
        return [brief['offer'] or f'خطوتك التالية مع {brand}.',f'جاهز تعرف تفاصيل {brand}؟' if egy else f'هل أنت مستعد لمعرفة تفاصيل {brand}؟',
            f'{benefit} — اعرف تفاصيل الخطوة الجاية.' if egy else f'{benefit} — تعرّف على الخطوة التالية.',
            f'قبل ما تقرر، شوف العرض بوضوح.' if egy else 'قبل القرار، اطّلع على تفاصيل العرض.',f'{brand}: التفاصيل قبل الاختيار.']
    if stage=='tofu':return [f'Where do you start with {topic}?',f'What matters to you about {topic}?',
        f'Before you choose, consider {criterion}.',f'A question for {brief["audience"]}.',f'A fresh look at {benefit}.']
    if stage=='mofu':return [f'Does {brand} fit what you need?',f'What does {brand} actually offer?',
        f'{criterion.capitalize()}: details worth asking about.','Look at the details before deciding.',f'{benefit}: look beyond the headline.']
    return [brief['offer'] or f'Your next step with {brand}.',f'Ready to explore {brand}?',
        f'{benefit}. Take a closer look.', 'Know the offer before you decide.',f'{brand}: the details before the next step.']


def ctas(brief,stage):
    ar=brief['language']!='en';egy=brief['language']=='ar-EG'
    if stage=='tofu':return ['اكتشف الفكرة','اعرف أكتر' if egy else 'تعرّف على المزيد','شوف التفاصيل' if egy else 'اطّلع على التفاصيل'] if ar else ['Explore the idea','Learn more','Take a closer look']
    if stage=='mofu':return ['اعرف تفاصيل الحل','اسأل عن التفاصيل','شوف هل مناسب ليك' if egy else 'اكتشف مدى ملاءمته لك'] if ar else ['Explore how it fits','Ask about the details','See what is included']
    return [brief['cta'],'اطلب تفاصيل العرض','تواصل لمعرفة الخطوة التالية'] if ar else [brief['cta'],'Ask about the offer','Contact us about the next step']


def _body(brief,stage,index):
    domain,ar,egy,topic,criterion=_context(brief)
    brand,product,benefit,offer,proof=[brief.get(key,'').strip() for key in ('brand','product','benefit','offer','proof')]
    if ar:
        if stage=='tofu':
            frames=[_join(f'اختيارك في {topic} بيبدأ من فهم احتياجك.' if egy else f'الاختيار في {topic} يبدأ من فهم احتياجك.',
                benefit,f'{brand}: {product}'),
                _join(f'لو {benefit} من الحاجات اللي بتدور عليها، خد فكرة عن {brand}.' if egy else f'إذا كان {benefit} ضمن ما تبحث عنه، تعرّف على {brand}.',product),
                _join(f'قبل المقارنة، فكّر في {criterion}.',f'{brand} يقدّم {product}',benefit)]
        elif stage=='mofu':
            frames=[_join(f'{brand}: {product}',f'الفائدة اللي بنقدّمها: {benefit}' if egy else f'الفائدة التي نقدّمها: {benefit}',proof or f'اسأل عن {criterion} قبل الاختيار.'),
                _join(f'تعرّف على {brand} من خلال التفاصيل.',product,benefit,proof or f'هل تفاصيل {criterion} مناسبة لاحتياجك؟'),
                _join(f'مقارنة الخيارات تبدأ من {criterion}.',f'ما نقدّمه في {brand}: {product}',benefit,proof)]
        else:
            frames=[_join(f'{brand}: {product}',benefit,offer),
                _join(f'مهتم بـ{benefit}؟',f'ده اللي بيقدمه {brand}: {product}' if egy else f'هذا ما يقدّمه {brand}: {product}',offer),
                _join(offer,f'مع {brand}: {benefit}',product)]
    else:
        if stage=='tofu':frames=[_join(f'Choosing {topic} starts with understanding what matters to you.',benefit,f'Meet {brand}: {product}'),
            _join(f'If {benefit} is what you are looking for, take a closer look at {brand}.',product),
            _join(f'Before comparing options, consider {criterion}.',f'{brand} offers {product}',benefit)]
        elif stage=='mofu':frames=[_join(f'{brand}: {product}',f'The stated benefit: {benefit}',proof or f'Ask about {criterion} before choosing.'),
            _join(f'Get to know {brand} through the details.',product,benefit,proof or f'Does the approach to {criterion} fit your needs?'),
            _join(f'Compare options through {criterion}.',f'What {brand} offers: {product}',benefit,proof)]
        else:frames=[_join(f'{brand}: {product}',benefit,offer),_join(f'Interested in {benefit}?',f'Explore {brand}: {product}',offer),_join(offer,f'With {brand}: {benefit}',product)]
    body=frames[index%len(frames)]
    length=brief.get('content_length','standard')
    if length=='short':body=_join(benefit,proof if stage=='mofu' else offer if stage=='bofu' else '')
    elif length=='long':body=_join(body,(f'قبل الاختيار، اسأل عن {criterion}.' if ar else f'Before choosing, ask about {criterion}.'))
    return body


def compose(brief,seed,stage_override=None):
    rng=random.Random(seed);domain,ar,egy,topic,criterion=_context(brief)
    stages=[stage_override]*3 if stage_override else ['tofu','mofu','bofu'] if brief.get('funnel_stage','full')=='full' else [brief['funnel_stage']]*3
    hook_start,headline_start,body_start,cta_start=[rng.randrange(1000) for _ in range(4)]
    values=[]
    for index,stage in enumerate(stages):
        offset=hook_start+index
        hook=hooks(brief,stage)[offset%len(hooks(brief,stage))]
        headline=([brief['benefit'] if len(brief['benefit'])<=250 else brief['brand'],
            f'تعرّف على {brief["brand"]}' if ar else f'Meet {brief["brand"]}',
            f'{brief["brand"]} | التفاصيل' if ar else f'{brief["brand"]} | The details'])[(headline_start+index)%3]
        if brief['tone']=='bold':hook=brief['benefit'].rstrip('.!')+'!'
        elif brief['tone']=='professional':hook=(f'تعرّف على {brief["brand"]}: {topic}.' if ar else f'Explore {brief["brand"]}: {topic}.')
        if len(hook)>500:hook=(f'تعرّف على {brief["brand"]}.' if ar else f'Explore {brief["brand"]}.')
        body=_body(brief,stage,body_start+index)
        cta=ctas(brief,stage)[(cta_start+index)%3] if stage!='bofu' else brief['cta']
        channel=brief['channel']
        if channel=='google':
            fallback_headlines=['اكتشف التفاصيل','اعرف ما يناسبك','الخطوة التالية'] if ar else ['Explore the details','Find your fit','Your next step']
            headline=next(value for value in [headline,brief['brand'],fallback_headlines[index]] if len(value)<=30)
            facts=[brief['benefit'],brief['product'],brief['cta']]
            fallback_bodies=['اعرف تفاصيل المنتج وشروطه قبل الاختيار.','اسأل عن التفاصيل ومدى ملاءمتها لاحتياجك.','اطّلع على ما يشمله العرض والخطوة التالية.'] if ar else ['Explore the product details and terms before choosing.','Ask about the details and how they fit your needs.','See what is included and how to take the next step.']
            base=next((fact for fact in facts if len(fact)<=90),fallback_bodies[index])
            body=_join(base,brief['offer'] if stage=='bofu' and len(base)+len(brief['offer'])+2<=90 else '')
            if stage=='bofu' and brief['offer'] and len(brief['offer'])<=90 and brief['offer'] not in body:body=brief['offer']
        elif channel=='tiktok':
            body=_join(('افتتاحية منطوقة: ' if ar else 'Spoken opening: ')+hook,
                       ('الفكرة الأساسية: ' if ar else 'Main message: ')+body,('النهاية: ' if ar else 'Close: ')+cta)
        elif channel=='email':body=_join('مرحبًا،' if ar else 'Hello,',body,cta)
        objective={'tofu':('التعريف بالمشكلة وجذب الانتباه','Introduce the problem and earn attention'),
            'mofu':('شرح الملاءمة ومساعدة العميل على المقارنة','Explain fit and support consideration'),
            'bofu':('عرض الشروط والدعوة لخطوة واضحة','Present the terms and invite a clear next step')}[stage][0 if ar else 1]
        rationale=(f'الرسالة مرتبطة بمرحلة {stage.upper()}، مع التركيز على {criterion} دون إضافة نتائج غير مدخلة.' if ar else f'This {stage.upper()} message focuses on {criterion} without adding unsupported outcomes.')
        angles=[('سؤال يفتح الفكرة','A question to start with'),('الفائدة في المقدمة','Benefit first'),('التفاصيل قبل القرار','Details before deciding')]
        visual=domain['visual_ar' if ar else 'visual_en']
        visual+=('؛ ضع الافتتاحية كنص واضح، ثم لقطة للتفاصيل، ثم الدعوة للخطوة التالية.' if ar else '; show the hook clearly, then the relevant details, then the next-step invitation.')
        values.append(dict(angle=angles[offset%3][0 if ar else 1],headline=headline,hook=hook,body=body,cta=cta,
            visual_idea=visual,funnel_stage=stage,objective=objective,rationale=rationale))
    return values


def revise(brief,previous,edits,seed):
    rng=random.Random(seed);domain,ar,egy,topic,criterion=_context(brief)
    stage=previous.get('funnel_stage','unspecified')
    if stage=='unspecified':stage=brief['funnel_stage'] if brief['funnel_stage']!='full' else 'mofu'
    fresh=compose(brief,seed,stage)
    new_hooks=[value for value in hooks(brief,stage) if len(value)<=500 and _norm(value)!=_norm(previous['hook'])]
    rng.shuffle(new_hooks)
    results=[]
    for index in range(3):
        item=dict(previous)
        for edit in edits:
            if edit=='new_angle':
                item={**fresh[index],'cta':previous['cta']}
                # Keep any manually entered numeric/offer conditions as complete units.
                for part in re.split(r'\n\s*\n',previous['body']):
                    if re.search(r'\d|\b(?:paid|free|not|no|only)\b|مدفوع|مجان|غير|بدون',part,re.I) and _norm(part) not in _norm(item['body']):item['body']=_join(item['body'],part)
            elif edit=='new_hook':
                candidates=new_hooks
                item['hook']=candidates[index%len(candidates)] if candidates else item['hook']
            elif edit=='new_cta':
                candidates=[value for value in ctas(brief,stage) if _norm(value)!=_norm(previous['cta'])]
                if candidates:item['cta']=candidates[index%len(candidates)]
            elif edit=='clearer':
                prefix='الفكرة بوضوح:\n' if ar else 'The key points:\n'
                if not item['body'].startswith(prefix):
                    parts=[part.strip() for part in re.split(r'\n\s*\n',item['body']) if part.strip()]
                    item['body']=prefix+'\n'.join('• '+part for part in parts)
            elif edit=='longer':
                candidates=[brief.get('proof','') if stage=='mofu' else '',brief['product'],brief['benefit'],
                    (f'اسأل عن {criterion} حتى تختار بناءً على تفاصيل واضحة.' if ar else f'Ask about {criterion} so you can decide with clear details.')]
                extra=[part for part in candidates if part and _norm(part) not in _norm(item['body'])]
                if extra:item['body']=_join(item['body'],extra[index%len(extra)])
            elif edit=='benefit':
                if _norm(brief['benefit']) not in _norm(item['body'].split('\n\n')[0]):item['body']=_join(brief['benefit'],item['body'])
                item['hook']=brief['benefit'].rstrip('.!')+(' — اعرف التفاصيل.' if ar else ' — explore the details.')
            elif edit in ('calmer','formal','friendly','bolder'):
                if edit=='bolder':item['hook']=brief['benefit'].rstrip('.!')+'!'
                elif edit=='formal':item['hook']=(f'تعرّف على تفاصيل {brief["brand"]}.' if ar else f'Explore the details of {brief["brand"]}.')
                elif edit=='friendly':item['hook']=(f'خلينا نشوف هل {brief["brand"]} يناسبك؟' if egy else f'لنكتشف مدى ملاءمة {brief["brand"]} لك.' if ar else f'Let us see whether {brief["brand"]} fits what you need.')
                else:
                    item['hook']=(f'خد وقتك في معرفة {brief["brand"]}.' if egy else f'تعرّف بهدوء على {brief["brand"]}.' if ar else f'Take a closer look at {brief["brand"]}, at your own pace.')
                    for field in ('headline','body'):item[field]=item[field].replace('!','.')
        item['angle']=(' / '.join(EDIT_LABELS[edit][0 if not ar else 1] for edit in edits))[:150]
        results.append(item)
    return results
