import json, subprocess, tempfile, unittest
from fastapi.testclient import TestClient
from app.api.main import app
from app.engine import Story, Scene, Prompt, storyboard, render

class PipelineTests(unittest.TestCase):
    def test_story_validation(self):
        result=storyboard(Prompt(prompt='Pig walks in the garden. Rabbit jump in the forest.'))
        self.assertEqual(len(result.scenes),2)
        self.assertEqual(result.scenes[1].action,'jump')
        self.assertEqual(result.scenes[1].setting,'forest')
        self.assertLessEqual(len(storyboard(Prompt(prompt='long '*350)).scenes),8)

    def test_api_validation_and_missing_job(self):
        with TestClient(app) as client:
            self.assertEqual(client.post('/api/jobs',json={'scenes':[]}).status_code,422)
            self.assertEqual(client.get('/api/jobs/not-an-id/video').status_code,404)

    def test_real_export(self):
        with tempfile.TemporaryDirectory() as directory:
            values=[]
            render(Story(scenes=[Scene(narration='Pig and Rabbit dance!',action='dance',duration=3)]), directory, values.append)
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',directory+'/video.mp4']))
            self.assertEqual(probe['streams'][0]['codec_name'],'h264')
            self.assertEqual(probe['streams'][0]['width'],640)
            self.assertAlmostEqual(float(probe['format']['duration']),3,places=1)
            self.assertEqual(values[-1],100)

if __name__=='__main__': unittest.main()
