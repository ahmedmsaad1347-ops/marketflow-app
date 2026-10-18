"""Local writing topics: editorial context, never assertions about a business."""
# id, English label, Arabic label, English topic, Arabic topic, English decision criterion,
# Arabic criterion, English visual direction, Arabic visual direction, detection keywords.
_ROWS = [
('software','Software & SaaS','البرمجيات وSaaS','day-to-day workflows','تنظيم الشغل اليومي','fit with your current workflow','مدى مناسبة الحل لطريقة شغلك','Show a real screen recording using only demonstrated features','اعرض تسجيل شاشة حقيقي للخصائص الموجودة فعلًا','software,saas,crm,app,برمجيات,برنامج,تطبيق,نظام,دعم العملاء'),
('ecommerce','Online stores','المتاجر الإلكترونية','choosing products online','اختيار المنتجات أونلاين','product details and order terms','تفاصيل المنتج وشروط الطلب','Show the actual product, packaging and ordering steps','اعرض المنتج الحقيقي والتغليف وخطوات الطلب','ecommerce,e-commerce,online store,متجر,متاجر,تجارة إلكترونية'),
('fashion','Fashion & accessories','الأزياء والإكسسوارات','choosing your next look','اختيار الستايل المناسب','available sizes, materials and fit','المقاسات والخامات وطريقة اللبس','Show actual available items and material details','صوّر القطع المتاحة فعلًا وتفاصيل خامتها','fashion,clothes,clothing,ملابس,أزياء,موضة,اكسسوارات'),
('beauty','Beauty & personal care','التجميل والعناية','a personal-care routine','روتين العناية الشخصية','ingredients, suitability and usage instructions','المكونات وطريقة الاستخدام ومدى الملاءمة','Show packaging and real usage instructions without outcome claims','اعرض العبوة وتعليمات الاستخدام دون ادعاء نتائج','beauty,skincare,cosmetics,تجميل,بشرة,مستحضرات,عناية'),
('food','Food & beverages','الأكل والمشروبات','choosing something to enjoy','اختيار أكلة أو مشروب','ingredients, portion and ordering details','المكونات والكمية وتفاصيل الطلب','Film the real preparation and serving process','صوّر التحضير والتقديم الحقيقي للمنتج','food,restaurant,coffee,bakery,مطعم,أكل,قهوة,مخبوزات,مشروبات'),
('education','Courses & education','التعليم والكورسات','choosing what to learn next','اختيار الخطوة التعليمية الجاية','syllabus, level and learning format','المحتوى والمستوى وطريقة التعلم','Show a genuine lesson excerpt and the stated syllabus','اعرض جزءًا حقيقيًا من الدرس والمنهج المعلن','course,courses,education,training,تعليم,كورس,دورة,تدريب'),
('health','Healthcare','الخدمات الصحية','finding the right care information','الوصول لمعلومات عن الخدمة الصحية','service scope, qualifications and booking details','نطاق الخدمة والمؤهلات وتفاصيل الحجز','Show the actual service environment with consent and no treatment guarantees','اعرض مكان الخدمة بموافقة أصحابه ودون ضمانات علاج','clinic,healthcare,dental,عيادة,صحة,طبيب,أسنان,علاج'),
('fitness','Fitness & sport','اللياقة والرياضة','building a suitable exercise routine','اختيار روتين رياضي مناسب','schedule, coaching format and suitability','المواعيد وطريقة التدريب ومدى الملاءمة','Show an actual session or equipment without promising body changes','صوّر حصة أو معدات حقيقية دون وعود بتغييرات جسدية','fitness,gym,sport,جيم,رياضة,لياقة,تمارين'),
('real_estate','Real estate','العقارات','choosing a property','اختيار عقار','location, specifications and stated payment terms','الموقع والمواصفات وشروط السداد المعلنة','Use verified property footage and clearly labelled specifications','استخدم صور العقار الفعلية ومواصفاته المؤكدة','property,real estate,apartment,عقار,عقارات,شقة,وحدة سكنية'),
('finance','Financial services','الخدمات المالية','understanding a financial service','فهم الخدمة المالية','fees, conditions and risk disclosures','الرسوم والشروط وإفصاحات المخاطر','Explain actual terms visually without return promises','اعرض الشروط الفعلية بصريًا دون وعود بعائد','finance,insurance,investment,تمويل,تأمين,استثمار,محاسبة'),
('travel','Travel & hospitality','السفر والضيافة','planning a trip or stay','التخطيط للسفر أو الإقامة','included services and booking conditions','الخدمات المشمولة وشروط الحجز','Show verified destination or accommodation footage','اعرض صور الوجهة أو الإقامة الفعلية','travel,tourism,hotel,سفر,سياحة,فندق,رحلات'),
('services','Professional services','الخدمات المهنية','choosing the right service partner','اختيار مقدم الخدمة المناسب','scope, process and deliverables','نطاق العمل والخطوات والمخرجات','Walk through the actual service process and deliverables','اشرح خطوات الخدمة ومخرجاتها الفعلية','consulting,agency,marketing,legal,استشارات,وكالة,تسويق,محاماة'),
('home','Home services','خدمات المنزل','arranging a home service','ترتيب خدمة للبيت','service area, scope and appointment terms','مناطق الخدمة ونطاق العمل وشروط الموعد','Show a real work process with the owner’s permission','اعرض خطوات شغل حقيقية بموافقة صاحب المكان','plumbing,cleaning,home services,سباكة,تنظيف,صيانة,كهربائي'),
('automotive','Automotive','السيارات','choosing a vehicle or car service','اختيار سيارة أو خدمة للسيارة','specifications, condition and service scope','المواصفات والحالة ونطاق الخدمة','Show the actual vehicle or service inspection process','صوّر السيارة الفعلية أو خطوات فحص الخدمة','car,cars,automotive,سيارة,سيارات,عربية,مركز صيانة'),
('events','Events & celebrations','الفعاليات والمناسبات','planning an event','التخطيط لمناسبة','included items, date and booking terms','البنود المشمولة والموعد وشروط الحجز','Show real setups or clearly labelled concept boards','اعرض تجهيزات حقيقية أو أفكارًا موضّحًا أنها تصورات','event,wedding,فعاليات,مناسبات,زفاف,حفلات'),
('industrial','B2B & manufacturing','الأعمال والصناعة','evaluating a business supplier','تقييم مورد أو حل للأعمال','specifications, capacity and delivery terms','المواصفات والطاقة وشروط التسليم','Show documented production steps and actual specifications','اعرض خطوات إنتاج موثقة ومواصفات فعلية','manufacturing,factory,industrial,b2b,مصنع,تصنيع,صناعة,توريد'),
('retail','Local retail','المحلات والبيع المباشر','choosing a local shop','اختيار محل قريب','available items, location and opening details','المنتجات المتاحة والموقع ومواعيد العمل','Show the real shop and available stock','صوّر المحل الحقيقي والمنتجات المتاحة','shop,retail,محل,دكان,تجزئة'),
('entertainment','Entertainment','الترفيه','choosing something to do','اختيار تجربة ترفيهية','experience details, suitability and entry terms','تفاصيل التجربة ومدى ملاءمتها وشروط الدخول','Show real experience footage with necessary permissions','اعرض لقطات فعلية للتجربة بالتصاريح المطلوبة','entertainment,game,gaming,ترفيه,ألعاب,سينما,مسرح'),
('pets','Pet products & services','منتجات وخدمات الحيوانات','choosing care for a pet','اختيار رعاية للحيوان الأليف','suitability and clear product instructions','مدى الملاءمة وتعليمات المنتج الواضحة','Show the real product or care process without health guarantees','اعرض المنتج أو الرعاية الفعلية دون ضمانات صحية','pet,pets,حيوانات,قطط,كلاب,بيطري'),
('children','Children & family','الأطفال والأسرة','choosing something for the family','اختيار ما يناسب الأسرة','age suitability, contents and usage guidance','العمر المناسب والمحتويات وإرشادات الاستخدام','Show the actual item and age guidance; use consent for people','اعرض المنتج وإرشادات العمر مع موافقة أي أشخاص ظاهرين','kids,children,baby,أطفال,طفل,رضع,حضانة'),
('handmade','Handmade & design','الهاند ميد والتصميم','choosing a distinctive piece','اختيار قطعة بتفاصيل مميزة','materials, dimensions and customisation terms','الخامات والمقاسات وشروط التخصيص','Film the real making process and material details','صوّر خطوات التصنيع الفعلية وتفاصيل الخامات','handmade,craft,design,هاند ميد,حرف,تصميم,يدوي'),
('nonprofit','Nonprofit & community','المبادرات والمجتمع','choosing a way to participate','اختيار طريقة للمشاركة','purpose, use of contributions and reporting','الهدف واستخدام المساهمات وطريقة المتابعة','Use permitted, documented activity footage without invented impact','اعرض نشاطًا موثقًا بموافقة أصحابه دون اختلاق أثر','nonprofit,charity,community,جمعية,خيرية,مبادرة,مجتمع'),
('energy','Energy & sustainability','الطاقة والاستدامة','evaluating an energy solution','تقييم حل للطاقة','specifications, installation needs and stated terms','المواصفات ومتطلبات التركيب والشروط المعلنة','Show actual equipment and documented setup steps','اعرض المعدات الفعلية وخطوات تركيب موثقة','solar,energy,sustainability,طاقة,شمسية,استدامة'),
('logistics','Delivery & logistics','الشحن والخدمات اللوجستية','choosing a delivery service','اختيار خدمة شحن','coverage, timing terms and handling rules','التغطية وشروط المواعيد وقواعد التعامل','Show real packing and handover steps','اعرض خطوات التغليف والتسليم الفعلية','logistics,shipping,delivery,شحن,توصيل,لوجستيات'),
('custom','Other / custom project','مشروع آخر أو مخصص','choosing a suitable solution','اختيار الحل المناسب','what is included and how to take the next step','ما يشمله العرض والخطوة التالية','Show the real product or service using only supplied facts','اعرض المنتج أو الخدمة الحقيقية بناءً على المعلومات المدخلة فقط',''),
]
DOMAINS={row[0]:dict(zip(('id','label_en','label_ar','topic_en','topic_ar','criterion_en','criterion_ar','visual_en','visual_ar','keywords'),row)) for row in _ROWS}


def domain_catalog():
    return [{'id':item['id'],'label_en':item['label_en'],'label_ar':item['label_ar']} for item in DOMAINS.values()]


def resolve_domain(brief):
    import re
    if brief.get('domain') in DOMAINS:return DOMAINS[brief['domain']]
    text=' '.join(str(brief.get(key,'')) for key in ('brand','product','benefit')).casefold()
    def normalize(value):
        for old,new in (('أ','ا'),('إ','ا'),('آ','ا'),('ى','ي'),('ة','ه')):value=value.replace(old,new)
        return value
    text=normalize(text)
    scores=[]
    for index,item in enumerate(DOMAINS.values()):
        hits=sum(1 for word in item['keywords'].split(',') if word and re.search(r'(?<!\w)'+re.escape(normalize(word))+r'(?!\w)',text))
        scores.append((hits,-index,item))
    best=max(scores,key=lambda value:value[:2])
    return best[2] if best[0] else DOMAINS['custom']
