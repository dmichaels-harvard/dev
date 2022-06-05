import mock
import unittest
#from src.auto.main import get_test_creds_script_file
#from src.auto.main import foo
import src.auto.main as main

class MyTest(unittest.TestCase):

    def foom(self):
        return "xyz"
    def test(self):
        with mock.patch("src.auto.main.get_test_creds_script_file") as mock_get_test_creds_script_file, \
             mock.patch("src.auto.main.os.path.abspath") as mock_os_path_abspath:
            mock_get_test_creds_script_file.return_value = "abc"
            print(mock_get_test_creds_script_file.return_value)
            x = main.foo()
            assert x == "abc"
            mock_os_path_abspath.return_value = "xyz"
            y = main.goo("GOO")
            #assert y == "/Users/dmichaels/repos/cgap/4dn-cloud-infra/src/auto/GOO"
            assert y == "xyz"
            #assert x == "foo/test_creds.sh"
        #main([ "--env", "mytest" ])
        #assert True == True
