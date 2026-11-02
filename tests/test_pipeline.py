import importlib.util, json, subprocess, sys, tempfile, unittest
from pathlib import Path
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('config',root/'scripts/config.py')
config=importlib.util.module_from_spec(spec); spec.loader.exec_module(config)
rules_spec=importlib.util.spec_from_file_location('rulesets',root/'scripts/rulesets.py')
rules_module=importlib.util.module_from_spec(rules_spec); rules_spec.loader.exec_module(rules_module)
class PipelineTests(unittest.TestCase):
    def test_release_app_cannot_bypass_tag_immutability(self):
        branch, creation, immutable=rules_module.rulesets(42,'ci / result')
        self.assertEqual([r['type'] for r in creation['rules']],['creation'])
        self.assertEqual({r['type'] for r in immutable['rules']},{'update','deletion'})
        self.assertTrue(any(a.get('actor_id')==42 for a in creation['bypass_actors']))
        self.assertFalse(any(a.get('actor_id')==42 for a in immutable['bypass_actors']))
        self.assertEqual(branch['rules'][1]['parameters']['required_status_checks'][0]['context'],'ci / result')
    def setUp(self): self.data=json.loads((root/'templates/mod-pipeline.json').read_text(encoding='utf-8'))
    def test_example(self): config.validate(self.data)
    def test_duplicate_ids(self):
        self.data['targets'].append(self.data['targets'][0])
        with self.assertRaises(ValueError): config.validate(self.data)
    def test_shell_injection_rejected(self):
        self.data['checks']=['build; echo bad']
        with self.assertRaises(ValueError): config.validate(self.data)
    def test_target_java_must_be_installed(self):
        self.data['targets'][0]['java']=17
        with self.assertRaises(ValueError): config.validate(self.data)
    def test_collect_primary_and_exclude_dev(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp); (path/'mod.jar').write_bytes(b'mod'); (path/'mod-dev.jar').write_bytes(b'dev')
            subprocess.run([sys.executable,str(root/'scripts/collect-files.py'),json.dumps([str(path/'*.jar')]),str(path/'out')],check=True)
            self.assertEqual([p.name for p in (path/'out').iterdir()],['mod.jar'])
    def test_collect_rejects_multiple_primary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp); (path/'one.jar').touch(); (path/'two.jar').touch()
            result=subprocess.run([sys.executable,str(root/'scripts/collect-files.py'),json.dumps([str(path/'*.jar')]),str(path/'out')],capture_output=True)
            self.assertNotEqual(result.returncode,0)
if __name__=='__main__': unittest.main()
