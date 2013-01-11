from freepybx.tests import *

class TestServicesController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='services', action='index'))
        # Test response...
