"""Creative generation, factual review flags and account/version isolation."""
import importlib
import json
import os
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from auth_helpers import prepare_client, signup_verified

BRIEF = {'brand':'FlowDesk','product':'Customer support software for online stores',
    'audience':'Small shop owners','benefit':'Organise recurring customer questions','offer':'14-day paid trial',
    'cta':'Book a demo','language':'en','tone':'friendly','channel':'instagram','goal':'leads','constraints':'No unverified statistics'}


class CreativeStudioTests(unittest.TestCase):
    def setUp(self):
        self.main=importlib.import_module('backend.main')
        self.directory=tempfile.TemporaryDirectory(prefix='mf-creative-test-')
        self.addCleanup(self.directory.cleanup)
        for target,value in [('DATABASE',str(Path(self.directory.name)/'test.db'))]:
            mock=patch.object(self.main,target,value);mock.start();self.addCleanup(mock.stop)
        config=patch.object(self.main.auth,'config',replace(self.main.auth.config,mail_mode='file',outbox=str(Path(self.directory.name)/'mail')))
        config.start();self.addCleanup(config.stop)
        env=patch.dict(os.environ,{'OPENAI_API_KEY':''});env.start();self.addCleanup(env.stop)
        self.main.init_db();self.main.auth.migrate()
        self.client=prepare_client(TestClient(self.main.app));self.addCleanup(self.client.close)
        signup_verified(self.client,self.main,json={'name':'Content owner','email':'writer@example.com','password':'Every brand has a story to tell!'})

    def generate(self, **kwargs):
        response=self.client.post('/api/creative/generate',json={'brief':BRIEF,**kwargs})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()['version']

    def test_language_is_required_and_three_local_drafts_keep_paid_offer(self):
        for language in ('en','ar','ar-EG'):
            version=self.generate(brief={**BRIEF,'language':language})
            self.assertEqual(version['result']['engine'],'local')
            self.assertEqual(len(version['result']['variants']),3)
            for variant in version['result']['variants']:
                self.assertNotIn('free trial',variant['body'].lower())
                if variant['funnel_stage']=='bofu':
                    self.assertIn('14-day paid trial',variant['body'])
            self.assertTrue(version['result']['review_flags'])
        for invalid in ('','de'):
            response=self.client.post('/api/creative/generate',json={'brief':{**BRIEF,'language':invalid}})
            self.assertEqual(response.status_code,422)
        self.assertEqual(self.client.get('/api/creative/status').json()['ai_available'],False)

    def test_selection_manual_edits_rating_and_revision_preserve_original(self):
        first=self.generate()
        selection={**first['result']['variants'][1],'body':'A customer-approved manual draft. An extra sentence to remove.'}
        response=self.client.patch(f"/api/creative/versions/{first['id']}",json={'variant_index':1,'content':selection,'rating':5,'reviewed':True})
        self.assertEqual(response.status_code,200,response.text)
        second=self.generate(project_id=first['project_id'],source_version_id=first['id'],feedback='Make it shorter')
        self.assertEqual(second['parent_id'],first['id'])
        saved=self.client.get(f"/api/creative/projects/{first['project_id']}").json()['versions']
        self.assertEqual(len(saved),2)
        old=next(item for item in saved if item['id']==first['id'])
        self.assertEqual(old['result'],first['result'])
        self.assertEqual(old['selection']['content']['body'],selection['body'])
        self.assertEqual(old['rating'],5)
        self.assertTrue(old['selection']['reviewed'])

    def test_projects_versions_and_generation_require_ownership_and_csrf(self):
        first=self.generate()
        with prepare_client(TestClient(self.main.app)) as other:
            signup_verified(other,self.main,json={'name':'Other owner','email':'other@example.com','password':'A completely separate content account!'})
            self.assertEqual(other.get('/api/creative/projects').json()['projects'],[])
            self.assertEqual(other.get(f"/api/creative/projects/{first['project_id']}").status_code,404)
            self.assertEqual(other.post('/api/creative/generate',json={'brief':BRIEF,'project_id':first['project_id']}).status_code,404)
            self.assertEqual(other.patch(f"/api/creative/versions/{first['id']}",json={'variant_index':0,'content':first['result']['variants'][0]}).status_code,404)
            other.headers.pop('X-CSRF-Token')
            self.assertEqual(other.post('/api/creative/generate',json={'brief':BRIEF}).status_code,403)
        with TestClient(self.main.app) as stranger:
            self.assertEqual(stranger.get('/api/creative/status').status_code,401)
        self.assertEqual(self.client.get('/api/creative/projects').headers['cache-control'],'no-store')

    def test_real_provider_contract_uses_feedback_and_only_server_side_credentials(self):
        first=self.generate()
        content=first['result']['variants'][0]
        selected={**content,'body':'Keep this selected and edited draft as context.'}
        self.client.patch(f"/api/creative/versions/{first['id']}",json={'variant_index':0,'content':selected})
        payload={'variants':[{**item,'funnel_stage':'tofu','body':item['body']+' Unsupported 99% claim. Start a free trial.'} for item in first['result']['variants']]}
        fake=httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(payload)}}]})
        fake.request=httpx.Request('POST','https://api.openai.com/v1/chat/completions')
        with patch.dict(os.environ,{'OPENAI_API_KEY':'private-test-key','OPENAI_MODEL':'test-model'}), patch('backend.creative_studio.httpx.post',return_value=fake) as post:
            second=self.generate(brief={**BRIEF,'generation_mode':'ai'},project_id=first['project_id'],source_version_id=first['id'],feedback='A calmer tone, please')
        call=post.call_args.kwargs
        sent=json.loads(call['json']['messages'][1]['content'])
        self.assertEqual(sent['previous_selected_draft']['body'],selected['body'])
        self.assertEqual(sent['feedback'],'A calmer tone, please')
        self.assertEqual(call['headers']['Authorization'],'Bearer private-test-key')
        self.assertEqual(second['result']['engine'],'openai')
        self.assertNotIn('private-test-key',json.dumps(second))
        self.assertTrue(any('numbers' in flag for flag in second['result']['review_flags']))
        self.assertTrue(any('free-trial' in flag for flag in second['result']['review_flags']))

    def test_provider_failure_never_substitutes_fake_ai_or_changes_saved_version(self):
        first=self.generate()
        with patch.dict(os.environ,{'OPENAI_API_KEY':'private-test-key'}), patch('backend.creative_studio.httpx.post',side_effect=httpx.TimeoutException('secret provider detail')):
            response=self.client.post('/api/creative/generate',json={'brief':{**BRIEF,'generation_mode':'ai'},'project_id':first['project_id'],'source_version_id':first['id'],'feedback':'Try again'})
        self.assertEqual(response.status_code,502)
        self.assertNotIn('secret',response.text)
        saved=self.client.get(f"/api/creative/projects/{first['project_id']}").json()
        self.assertEqual(len(saved['versions']),1)
        self.assertEqual(saved['versions'][0]['result'],first['result'])

    def test_invalid_selection_and_rate_limit(self):
        first=self.generate()
        for update in ({'variant_index':3},{'rating':6}):
            response=self.client.patch(f"/api/creative/versions/{first['id']}",json={'variant_index':0,'content':first['result']['variants'][0],**update})
            self.assertEqual(response.status_code,422)
        for _ in range(59):
            self.generate()
        self.assertEqual(self.client.post('/api/creative/generate',json={'brief':BRIEF}).status_code,429)

    def test_local_shortening_uses_selected_manual_copy_and_keeps_offer(self):
        first=self.generate()
        selected={**first['result']['variants'][1], 'headline':'My edited headline',
            'body':'Keep this manually written opening.\n\nExtra description to remove.\n\n14-day paid trial for 199 EGP.',
            'cta':'My edited call to action'}
        self.client.patch(f"/api/creative/versions/{first['id']}",json={'variant_index':1,'content':selected})
        second=self.generate(project_id=first['project_id'],source_version_id=first['id'],refinement='shorter')
        self.assertEqual(len(second['result']['variants']),1)
        choice=second['result']['variants'][0]
        self.assertEqual(choice['headline'],selected['headline'])
        self.assertEqual(choice['cta'],selected['cta'])
        self.assertIn('Keep this manually written opening.',choice['body'])
        self.assertIn('14-day paid trial for 199 EGP.',choice['body'])
        self.assertNotIn('Extra description to remove.',choice['body'])
        self.assertLess(len(choice['body']),len(selected['body']))
        self.assertEqual(second['result']['refinement'],'shorter')
        # Single-choice revisions validate the actual available index.
        response=self.client.patch(f"/api/creative/versions/{second['id']}",json={'variant_index':1,'content':choice})
        self.assertEqual(response.status_code,422)
        again=self.client.post('/api/creative/generate',json={'brief':BRIEF,'project_id':first['project_id'],
            'source_version_id':second['id'],'refinement':'shorter'})
        self.assertEqual(again.status_code,409)
        self.assertEqual(len(self.client.get(f"/api/creative/projects/{first['project_id']}").json()['versions']),2)

    def test_free_text_without_ai_and_changed_brief_do_not_save_duplicates(self):
        first=self.generate()
        for feedback in ('Change something unspecified','Do not make it shorter'):
            response=self.client.post('/api/creative/generate',json={'brief':BRIEF,'project_id':first['project_id'],
                'source_version_id':first['id'],'feedback':feedback})
            self.assertEqual(response.status_code,422,response.text)
        response=self.client.post('/api/creative/generate',json={'brief':{**BRIEF,'language':'ar'},
            'project_id':first['project_id'],'source_version_id':first['id'],'refinement':'shorter'})
        self.assertEqual(response.status_code,409)
        self.assertEqual(len(self.client.get(f"/api/creative/projects/{first['project_id']}").json()['versions']),1)

    def test_local_shortening_keeps_arabic_price_duration_and_paid_terms(self):
        brief={**BRIEF,'language':'ar-EG','offer':'تجربة مدفوعة لمدة 14 يومًا بسعر 199 جنيهًا.'}
        first=self.generate(brief=brief)
        selected={**first['result']['variants'][0],'body':'افتتاحية كتبها المستخدم بنفسه.\n\nشرح إضافي قابل للاختصار.\n\n'+brief['offer']}
        self.client.patch(f"/api/creative/versions/{first['id']}",json={'variant_index':0,'content':selected})
        revised=self.generate(brief=brief,project_id=first['project_id'],source_version_id=first['id'],refinement='shorter')
        body=revised['result']['variants'][0]['body']
        self.assertIn('افتتاحية كتبها المستخدم بنفسه.',body)
        self.assertIn(brief['offer'],body)
        self.assertNotIn('شرح إضافي',body)

    def test_model_unchanged_copy_or_label_changes_do_not_create_revision(self):
        first=self.generate()
        values=[{**item,'funnel_stage':'tofu','angle':'Changed angle label only'} for item in first['result']['variants']]
        fake=httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'variants':values})}}]},
            request=httpx.Request('POST','https://api.openai.com/v1/chat/completions'))
        with patch.dict(os.environ,{'OPENAI_API_KEY':'private-test-key'}), patch('backend.creative_studio.httpx.post',return_value=fake):
            response=self.client.post('/api/creative/generate',json={'brief':{**BRIEF,'generation_mode':'ai'},'project_id':first['project_id'],
                'source_version_id':first['id'],'feedback':'Use a calmer tone'})
        self.assertEqual(response.status_code,409)
        self.assertEqual(len(self.client.get(f"/api/creative/projects/{first['project_id']}").json()['versions']),1)

    def test_model_revision_keeps_only_changed_copy(self):
        first=self.generate()
        values=[first['result']['variants'][0], {**first['result']['variants'][1],'funnel_stage':'tofu','body':'A new revised body based on feedback.'},
            {**first['result']['variants'][1],'funnel_stage':'tofu','body':'A new revised body based on feedback.'}]
        fake=httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'variants':values})}}]},
            request=httpx.Request('POST','https://api.openai.com/v1/chat/completions'))
        with patch.dict(os.environ,{'OPENAI_API_KEY':'private-test-key'}), patch('backend.creative_studio.httpx.post',return_value=fake):
            revised=self.generate(brief={**BRIEF,'generation_mode':'ai'},project_id=first['project_id'],source_version_id=first['id'],feedback='Change the main copy')
        self.assertEqual(len(revised['result']['variants']),1)
        self.assertEqual(revised['result']['refinement'],'ai')
        self.assertEqual(revised['result']['variants'][0]['body'],'A new revised body based on feedback.')

    def test_full_funnel_and_single_stage_keep_distinct_intent_and_supported_proof(self):
        proof='Product demonstration supplied by the business owner.'
        full=self.generate(brief={**BRIEF,'funnel_stage':'full','proof':proof})
        tofu,mofu,bofu=full['result']['variants']
        self.assertEqual([item['funnel_stage'] for item in (tofu,mofu,bofu)],['tofu','mofu','bofu'])
        self.assertNotIn(BRIEF['offer'],tofu['body'])
        self.assertNotEqual(tofu['cta'],BRIEF['cta'])
        self.assertIn(proof,mofu['body'])
        self.assertIn(BRIEF['offer'],bofu['body'])
        self.assertEqual(bofu['cta'],BRIEF['cta'])
        for stage in ('tofu','mofu','bofu'):
            single=self.generate(brief={**BRIEF,'funnel_stage':stage})
            self.assertEqual([item['funnel_stage'] for item in single['result']['variants']],[stage]*3)

    def test_model_must_respect_full_funnel_coverage_and_selected_stage(self):
        from backend.creative_studio import CreativeBrief, compose_local
        drafts=compose_local(CreativeBrief(**BRIEF).dict(),42)
        invalid=[{**item,'funnel_stage':'tofu'} for item in drafts]
        fake=httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'variants':invalid})}}]},
            request=httpx.Request('POST','https://api.openai.com/v1/chat/completions'))
        with patch.dict(os.environ,{'OPENAI_API_KEY':'private-test-key'}), patch('backend.creative_studio.httpx.post',return_value=fake):
            response=self.client.post('/api/creative/generate',json={'brief':{**BRIEF,'generation_mode':'ai'}})
        self.assertEqual(response.status_code,502)
        self.assertEqual(self.client.get('/api/creative/projects').json()['projects'],[])
        first=self.generate()
        self.client.patch(f"/api/creative/versions/{first['id']}",json={'variant_index':1,'content':first['result']['variants'][1]})
        with patch.dict(os.environ,{'OPENAI_API_KEY':'private-test-key'}), patch('backend.creative_studio.httpx.post',return_value=fake):
            response=self.client.post('/api/creative/generate',json={'brief':{**BRIEF,'generation_mode':'ai'},'project_id':first['project_id'],
                'source_version_id':first['id'],'feedback':'Make this MOFU copy clearer'})
        self.assertEqual(response.status_code,502)
        self.assertEqual(len(self.client.get(f"/api/creative/projects/{first['project_id']}").json()['versions']),1)

    def test_existing_pre_funnel_versions_can_still_be_shortened(self):
        first=self.generate()
        old_brief={key:value for key,value in first['brief'].items() if key not in ('funnel_stage','proof','domain','content_length','generation_mode')}
        old_result=first['result']
        for item in old_result['variants']:
            for key in ('funnel_stage','objective','rationale'):
                item.pop(key,None)
        selected={**old_result['variants'][1],'body':'My old manually saved copy. Extra detail to remove.\n\n14-day paid trial.'}
        with self.main.get_db() as db:
            db.execute('UPDATE creative_versions SET brief_json=?,result_json=?,selection_json=? WHERE id=?',
                (json.dumps(old_brief),json.dumps(old_result),json.dumps({'variant_index':1,'content':selected,'reviewed':True}),first['id']))
        revised=self.generate(brief={**BRIEF,'funnel_stage':'full','proof':''},project_id=first['project_id'],
            source_version_id=first['id'],refinement='shorter')
        self.assertEqual(revised['result']['variants'][0]['funnel_stage'],'unspecified')
        self.assertIn('My old manually saved copy.',revised['result']['variants'][0]['body'])

    def test_local_is_default_even_with_key_and_edits_saved_copy_without_network(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'must-not-be-used'}), patch('backend.creative_studio.httpx.post') as post:
            status=self.client.get('/api/creative/status').json()
            self.assertTrue(status['local_available'])
            self.assertTrue(status['ai_available'])
            self.assertEqual(len(status['domains']),25)
            first=self.generate()
            self.assertEqual(first['result']['engine'],'local')
            self.assertEqual(first['result']['domain']['id'],'software')
            selected={**first['result']['variants'][1],'headline':'My approved headline',
                'body':'My edited text.\n\n14-day paid trial for 199 EGP.','cta':'My approved CTA'}
            self.client.patch(f"/api/creative/versions/{first['id']}",json={'variant_index':1,'content':selected})
            revised=self.generate(project_id=first['project_id'],source_version_id=first['id'],feedback='اكتب افتتاحية جديدة')
            for item in revised['result']['variants']:
                self.assertNotEqual(item['hook'],selected['hook'])
                for field in ('headline','body','cta','funnel_stage'):
                    self.assertEqual(item[field],selected[field])
            post.assert_not_called()
        saved=self.client.get(f"/api/creative/projects/{first['project_id']}").json()['versions']
        self.assertEqual(saved[-1]['selection']['content'],selected)
        self.assertEqual(saved[-1]['result'],first['result'])

    def test_compound_local_feedback_changes_copy_and_repeated_clarity_is_not_saved(self):
        first=self.generate()
        chosen={**first['result']['variants'][2],'body':'My opening paragraph.\n\nA removable explanation.\n\n14-day paid trial for 199 EGP.'}
        self.client.patch(f"/api/creative/versions/{first['id']}",json={'variant_index':2,'content':chosen})
        second=self.generate(project_id=first['project_id'],source_version_id=first['id'],feedback='خليه أقصر وأوضح')
        self.assertEqual(second['result']['applied_edits'],['shorter','clearer'])
        body=second['result']['variants'][0]['body']
        self.assertNotIn('removable',body)
        self.assertIn('199 EGP',body)
        self.assertIn('• ',body)
        repeat=self.client.post('/api/creative/generate',json={'brief':BRIEF,'project_id':first['project_id'],
            'source_version_id':second['id'],'refinement':'clearer'})
        self.assertEqual(repeat.status_code,409,repeat.text)
        self.assertEqual(len(self.client.get(f"/api/creative/projects/{first['project_id']}").json()['versions']),2)

    def test_local_domains_and_explicit_ai_without_key(self):
        brief={**BRIEF,'domain':'food','content_length':'long'}
        version=self.generate(brief=brief)
        self.assertEqual(version['result']['domain']['id'],'food')
        self.assertIn('ingredients',json.dumps(version['result']))
        with patch('backend.creative_studio.httpx.post') as post:
            response=self.client.post('/api/creative/generate',json={'brief':{**BRIEF,'generation_mode':'ai'}})
            self.assertEqual(response.status_code,503)
            post.assert_not_called()
        self.assertEqual(len(self.client.get('/api/creative/projects').json()['projects']),1)
        self.assertEqual(self.client.post('/api/creative/generate',json={'brief':{**BRIEF,'domain':'unknown'}}).status_code,422)

    def test_google_does_not_silently_cut_long_offer_terms(self):
        offer='14-day paid trial for 199 EGP. '+('Complete terms apply to this offer. '*4)
        version=self.generate(brief={**BRIEF,'channel':'google','offer':offer})
        self.assertTrue(any('full offer' in flag for flag in version['result']['review_flags']))
        for item in version['result']['variants']:
            self.assertLessEqual(len(item['body']),90)

if __name__=='__main__':
    unittest.main()
