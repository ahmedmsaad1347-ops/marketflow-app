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

    def test_language_is_required_and_three_guided_drafts_keep_paid_offer(self):
        for language in ('en','ar','ar-EG'):
            version=self.generate(brief={**BRIEF,'language':language})
            self.assertEqual(version['result']['engine'],'guided')
            self.assertEqual(len(version['result']['variants']),3)
            for variant in version['result']['variants']:
                self.assertIn('14-day paid trial',variant['body'])
                self.assertNotIn('free trial',variant['body'].lower())
            self.assertTrue(version['result']['review_flags'])
        for invalid in ('','de'):
            response=self.client.post('/api/creative/generate',json={'brief':{**BRIEF,'language':invalid}})
            self.assertEqual(response.status_code,422)
        self.assertEqual(self.client.get('/api/creative/status').json()['ai_available'],False)

    def test_selection_manual_edits_rating_and_revision_preserve_original(self):
        first=self.generate()
        selection={**first['result']['variants'][1],'body':'A customer-approved manual draft.'}
        response=self.client.patch(f"/api/creative/versions/{first['id']}",json={'variant_index':1,'content':selection,'rating':5,'reviewed':True})
        self.assertEqual(response.status_code,200,response.text)
        second=self.generate(project_id=first['project_id'],source_version_id=first['id'],feedback='Make it shorter')
        self.assertEqual(second['parent_id'],first['id'])
        saved=self.client.get(f"/api/creative/projects/{first['project_id']}").json()['versions']
        self.assertEqual(len(saved),2)
        old=next(item for item in saved if item['id']==first['id'])
        self.assertEqual(old['result'],first['result'])
        self.assertEqual(old['selection']['content']['body'],'A customer-approved manual draft.')
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
        payload={'variants':[{**item,'body':item['body']+' Unsupported 99% claim. Start a free trial.'} for item in first['result']['variants']]}
        fake=httpx.Response(200,json={'choices':[{'message':{'content':json.dumps(payload)}}]})
        fake.request=httpx.Request('POST','https://api.openai.com/v1/chat/completions')
        with patch.dict(os.environ,{'OPENAI_API_KEY':'private-test-key','OPENAI_MODEL':'test-model'}), patch('backend.creative_studio.httpx.post',return_value=fake) as post:
            second=self.generate(project_id=first['project_id'],source_version_id=first['id'],feedback='A calmer tone, please')
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
            response=self.client.post('/api/creative/generate',json={'brief':BRIEF,'project_id':first['project_id'],'source_version_id':first['id'],'feedback':'Try again'})
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
        for _ in range(11):
            self.generate()
        self.assertEqual(self.client.post('/api/creative/generate',json={'brief':BRIEF}).status_code,429)

if __name__=='__main__':
    unittest.main()
