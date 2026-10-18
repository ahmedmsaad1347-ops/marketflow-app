"""Offline writing invariants across industries, channels and user-supplied facts."""
import re
import unittest
from backend.content_domains import DOMAINS, resolve_domain
from backend.content_engine import compose, revise, parse_edits
from backend.creative_studio import CreativeBrief, CreativeResult, copy_signature


BASE=dict(brand='FlowDesk',product='Customer support software for online stores',
    audience='Support managers',benefit='Organise recurring questions',
    offer='14-day paid trial for 199 EGP',cta='Book a demo',language='en',
    proof='A product walkthrough supplied by the owner.')


class LocalContentTests(unittest.TestCase):
    def brief(self,**changes):
        return CreativeBrief(**{**BASE,**changes}).dict()

    def test_domain_locale_and_channel_outputs_validate_and_do_not_invent_numbers(self):
        for domain in DOMAINS:
            for language in ('en','ar','ar-EG'):
                for channel in ('instagram','meta','linkedin','tiktok','email','google'):
                    with self.subTest(domain=domain,language=language,channel=channel):
                        brief=self.brief(domain=domain,language=language,channel=channel)
                        values=CreativeResult(variants=compose(brief,31)).dict()['variants']
                        self.assertEqual([item['funnel_stage'] for item in values],['tofu','mofu','bofu'])
                        text=' '.join(str(value) for item in values for value in item.values())
                        self.assertFalse(set(re.findall(r'\d+',text))-{'14','199'})
                        self.assertNotIn('free trial',text.casefold())
                        self.assertNotIn('guaranteed',text.casefold())
                        self.assertIn(brief['offer'],values[2]['body'])
                        self.assertNotIn(brief['offer'],values[0]['body'])
                        if channel=='google':
                            self.assertTrue(all(len(item['headline'])<=30 and len(item['body'])<=90 for item in values))
                        else:self.assertIn(brief['proof'],values[1]['body'])

    def test_different_seeds_and_single_stage_create_real_copy_variation(self):
        brief=self.brief(funnel_stage='mofu')
        generations={tuple(copy_signature(item) for item in compose(brief,seed)) for seed in range(50)}
        self.assertGreater(len(generations),25)
        self.assertEqual(compose(brief,42),compose(brief,42))
        for length in ('short','standard','long'):
            for tone in ('friendly','professional','bold'):
                values=compose(self.brief(funnel_stage='bofu',content_length=length,tone=tone),42)
                self.assertEqual(len({copy_signature(item) for item in values}),3)
                self.assertTrue(all(item['funnel_stage']=='bofu' for item in values))

    def test_maximum_inputs_validate_in_all_channels_without_cutting_price(self):
        for channel in ('instagram','meta','linkedin','tiktok','email','google'):
            for length in ('short','standard','long'):
                brief=self.brief(brand='B'*100,product='P'*1000,audience='A'*500,
                    benefit='Z'*1000,offer='14-day paid trial for 199 EGP',proof='E'*1500,
                    cta='C'*150,channel=channel,content_length=length,funnel_stage='bofu')
                values=CreativeResult(variants=compose(brief,101)).dict()['variants']
                self.assertEqual(len({copy_signature(item) for item in values}),3)
                self.assertTrue(all(brief['offer'] in item['body'] for item in values))

    def test_domain_selection_inference_and_unknown_project_fallback(self):
        self.assertEqual(resolve_domain(self.brief())['id'],'software')
        self.assertEqual(resolve_domain(self.brief(product='برنامج لتنظيم خدمة العملاء',benefit='تنظيم العمل'))['id'],'software')
        self.assertEqual(resolve_domain(self.brief(domain='fashion'))['id'],'fashion')
        self.assertEqual(resolve_domain(dict(product='Unusual xyz project',brand='Zeta',benefit='Something specific'))['id'],'custom')
        food=compose(self.brief(domain='food'),12)
        self.assertIn('ingredients',str(food))
        custom=compose(self.brief(domain='custom'),12)
        self.assertIn(BASE['product'],str(custom))

    def test_local_edits_preserve_selected_facts_and_change_requested_fields(self):
        brief=self.brief()
        selected={**compose(brief,7)[2],'headline':'My headline','body':'My manual copy.\n\n14-day paid trial for 199 EGP.','cta':'My CTA'}
        hooks=revise(brief,selected,['new_hook'],42)
        self.assertTrue(all(item['hook']!=selected['hook'] for item in hooks))
        for item in hooks:
            for field in ('headline','body','cta','funnel_stage'):self.assertEqual(item[field],selected[field])
        for item in revise(brief,selected,['new_angle'],42):
            self.assertIn('14-day paid trial for 199 EGP',item['body'])
            self.assertEqual(item['cta'],'My CTA')
            self.assertEqual(item['funnel_stage'],'bofu')
        calmer=revise(brief,{**selected,'body':selected['body']+'!'},['calmer'],5)[0]
        self.assertNotIn('!',calmer['body'])
        self.assertIn('199 EGP',calmer['body'])

    def test_short_mofu_keeps_supplied_proof_and_feedback_is_bounded(self):
        mofu=compose(self.brief(content_length='short'),12)[1]
        self.assertIn(BASE['proof'],mofu['body'])
        self.assertEqual(parse_edits('خليه أقصر وأوضح'),['shorter','clearer'])
        self.assertEqual(parse_edits('اكتب افتتاحية جديدة'),['new_hook'])
        self.assertEqual(parse_edits('Replace with a fictional testimonial'),[])
        self.assertEqual(parse_edits('Do not make it shorter'),[])


if __name__=='__main__':unittest.main()
