from freepybx.tests import *

class TestProvisioningController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='provisioning', action='index'))
        # Test response...
