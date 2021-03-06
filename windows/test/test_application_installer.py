import unittest
import logging
import os
import sys
import time
import cStringIO
from urllib2 import URLError
from helpers import TestHelpers

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..',))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from action_handler import ActionHandlerException
from application_install import InstallApplication
from application import Application
from mock import patch, MagicMock, mock_open


@patch('application_install.ShortCutter.create_shortcut')
@patch('application_install.isdir')
@patch('application_install.listdir')
@patch('application_install.move')
@patch('application_install.zipfile.ZipFile')
@patch('application_install.urllib2')
class InstallApplicationTest(unittest.TestCase, TestHelpers):
    sleep_time = 0.1

    def get_mock_response(self, code=200, data="", chunksize=64):
        response = MagicMock()
        response.getcode.return_value = code
        dataString = cStringIO.StringIO(data)
        response.read = dataString.read
        return response


    def test_run_downloads_zip_file_from_correct_path(self, mock_urlib2, mock_ZipFile, mock_move, mock_listdir, mock_isdir, mock_create_shortcut):
        mock_urlib2.urlopen.return_value = self.get_mock_response(code=200)
        app = self.get_application()
        installer = InstallApplication(app, '')
        try:
            installer.start()
        except:
            pass
        mock_urlib2.urlopen.assert_called_with(app.download_location)

    def test_run_should_raise_exception_if_response_is_not_200(self, mock_urlib2, mock_ZipFile, mock_move, mock_listdir, mock_isdir, mock_create_shortcut):
        mock_urlib2.urlopen.return_value = self.get_mock_response(code=504)
        app = self.get_application()
        installer = InstallApplication(app, '')
        with self.assertRaises(ActionHandlerException) as expected_exception:
            installer.start()
        self.assertEqual(10501, expected_exception.exception.error_code)
        self.assertEqual("Got error 504 accessing {}".format(app.download_location), expected_exception.exception.message)

    def test_run_should_raise_exception_if_url_bad(self, mock_urlib2, mock_ZipFile, mock_move, mock_listdir, mock_isdir, mock_create_shortcut):
        mock_urlib2.urlopen.side_effect = URLError("bad")
        app = self.get_application()
        installer = InstallApplication(app, '')
        with self.assertRaises(ActionHandlerException) as expected_exception:
            installer.start()
        self.assertEqual(10507, expected_exception.exception.error_code)
        self.assertEqual("Could not find application at specified URL", expected_exception.exception.message)

    def test_run_should_raise_exception_if_cannot_open_file(self, mock_urlib2, mock_ZipFile, mock_move, mock_listdir, mock_isdir, mock_create_shortcut):
        mock_urlib2.urlopen.return_value = self.get_mock_response(code=200)
        app = self.get_application()
        expected_path = os.path.join(os.getenv("TEMP"), app.download_location.split('/')[-1])
        mock_open_file = mock_open()
        with patch('application_install.open', mock_open_file, create=True):
            mock_open_file.side_effect = IOError("Mock Error")
            installer = InstallApplication(app, '')
            with self.assertRaises(ActionHandlerException) as expected_exception:
                installer.start()

        self.assertEqual(10502, expected_exception.exception.error_code)
        self.assertEqual("Error creating file: {}".format(expected_path), expected_exception.exception.message)

    def test_run_should_report_steps(self, mock_urlib2, mock_ZipFile, mock_move, mock_listdir, mock_isdir, mock_create_shortcut):
        mock_status_callback = MagicMock()
        expected_calls = ["Initializing", "Downloading", "Unpacking", "Installing", "Creating Shortcuts", "Finalizing"]
        mock_urlib2.urlopen.return_value = self.get_mock_response(code=200)
        app = self.get_application()
        mock_open_file = mock_open()
        base_folder = 'c:\\some\\folder'
        internal_path = 'somerthing-1234.2314'
        mock_listdir.return_value = [internal_path]
        mock_isdir.return_value = True
        with patch('application_install.open', mock_open_file, create=True):
            mock_file = mock_open_file.return_value
            mock_open_file.return_value = mock_file
            installer = InstallApplication(app, base_folder, status_callback=mock_status_callback)
            installer.start()
            calls = [call[0][0] for call in mock_status_callback.call_args_list]
            self.assertEquals(expected_calls, calls)

    def test_run_should_report_error_if_fails_to_unzip_dowwnloaded_file(self, mock_urlib2, mock_ZipFile, mock_move, mock_listdir, mock_isdir, mock_create_shortcut):
        mock_urlib2.urlopen.return_value = self.get_mock_response(code=200)
        app = self.get_application()
        mock_ZipFile.return_value.__enter__.side_effect = IOError("Something failed")
        mock_open_file = mock_open()
        with patch('application_install.open', mock_open_file, create=True):
            mock_file = mock_open_file.return_value
            mock_open_file.return_value = mock_file
            installer = InstallApplication(app, '')
            with self.assertRaises(ActionHandlerException) as expected_exception:
                installer.start()

        self.assertEqual(10503, expected_exception.exception.error_code)
        self.assertEqual("Error unzipping file", expected_exception.exception.message)


    def test_run_should_move_inner_folder_of_unpacked_zip_to_install_folder(self, mock_urlib2, mock_ZipFile, mock_move, mock_listdir, mock_isdir, mock_create_shortcut):
        app = self.get_application()
        base_folder = 'c:\\some\\folder'
        internal_path = 'somerthing-1234.2314'
        mock_listdir.return_value = [internal_path]
        mock_isdir.return_value = True
        expected_source_folder = os.path.join(os.getenv("TEMP"), app.name, internal_path)
        expected_destination_folder = os.path.join(base_folder, 'Peachy', app.relitive_install_path)
        mock_urlib2.urlopen.return_value = self.get_mock_response(code=200)
        mock_open_file = mock_open()

        with patch('application_install.open', mock_open_file, create=True):
            mock_file = mock_open_file.return_value
            mock_open_file.return_value = mock_file
            installer = InstallApplication(app, base_folder)
            installer.start()

            mock_listdir.assert_called_with(os.path.join(os.getenv("TEMP"), app.name))
            mock_move.assert_called_with(expected_source_folder, expected_destination_folder)

    def test_run_should_raise_exception_when_zip_file_has_multipule_folders(self, mock_urlib2, mock_ZipFile, mock_move, mock_listdir, mock_isdir, mock_create_shortcut):
        app = self.get_application()
        base_folder = 'c:\\some\\folder'
        internal_path = 'somerthing-1234.2314'
        mock_listdir.return_value = [internal_path, 'UnexpectedPath']
        mock_isdir.return_value = True
        mock_urlib2.urlopen.return_value = self.get_mock_response(code=200)
        mock_open_file = mock_open()

        with patch('application_install.open', mock_open_file, create=True):
            mock_file = mock_open_file.return_value
            mock_open_file.return_value = mock_file
            installer = InstallApplication(app, base_folder)
            with self.assertRaises(ActionHandlerException) as expected_exception:
                installer.start()

        self.assertEqual(10504, expected_exception.exception.error_code)
        self.assertEqual("Zip file contains unexpected layout", expected_exception.exception.message)

    def test_run_should_raise_exception_when_move_fails(self, mock_urlib2, mock_ZipFile, mock_move, mock_listdir, mock_isdir, mock_create_shortcut):
        app = self.get_application()
        base_folder = 'c:\\some\\folder'
        internal_path = 'somerthing-1234.2314'
        mock_listdir.return_value = [internal_path]
        mock_isdir.return_value = True
        mock_move.side_effect = IOError("Bad stuff")
        mock_urlib2.urlopen.return_value = self.get_mock_response(code=200)
        mock_open_file = mock_open()
        with patch('application_install.open', mock_open_file, create=True):
            mock_file = mock_open_file.return_value
            mock_open_file.return_value = mock_file
            installer = InstallApplication(app, base_folder)
            with self.assertRaises(ActionHandlerException) as expected_exception:
                installer.start()

        self.assertEqual(10505, expected_exception.exception.error_code)
        self.assertEqual("Cannot move folders into install folder", expected_exception.exception.message)

    def test_run_should_create_icon_on_desktop(self, mock_urlib2, mock_ZipFile, mock_move, mock_listdir, mock_isdir, mock_create_shortcut):
        app = self.get_application()
        base_folder = 'c:\\some\\folder'
        internal_path = 'somerthing-1234.2314'
        mock_listdir.return_value = [internal_path]
        mock_isdir.return_value = True
        mock_urlib2.urlopen.return_value = self.get_mock_response(code=200)
        mock_open_file = mock_open()

        expected_destination = os.path.join(os.getenv('USERPROFILE'), 'Desktop', app.name + '.lnk')
        expected_target_exe = os.path.join(base_folder, 'Peachy', app.relitive_install_path, app.executable_path)
        expected_working = os.path.join(base_folder, 'Peachy', app.relitive_install_path)
        expected_icon = os.path.join(base_folder, 'Peachy', app.relitive_install_path, app.icon)

        with patch('application_install.open', mock_open_file, create=True):
            mock_file = mock_open_file.return_value
            mock_open_file.return_value = mock_file
            installer = InstallApplication(app, base_folder)
            installer.start()

            mock_create_shortcut.assert_called_with(expected_destination, expected_target_exe, expected_working, expected_icon)

    def test_run_should_raise_exception_create_icon_if_it_explodes(self, mock_urlib2, mock_ZipFile, mock_move, mock_listdir, mock_isdir, mock_create_shortcut):
        app = self.get_application()
        base_folder = 'c:\\some\\folder'
        internal_path = 'somerthing-1234.2314'
        mock_listdir.return_value = [internal_path]
        mock_isdir.return_value = True
        mock_urlib2.urlopen.return_value = self.get_mock_response(code=200)
        mock_open_file = mock_open()
        mock_create_shortcut.side_effect = IOError("It didn't go in")
        with patch('application_install.open', mock_open_file, create=True):
            mock_file = mock_open_file.return_value
            mock_open_file.return_value = mock_file
            installer = InstallApplication(app, base_folder)
            with self.assertRaises(ActionHandlerException) as expected_exception:
                installer.start()

        self.assertEqual(10506, expected_exception.exception.error_code)
        self.assertEqual("Creating shortcut failed", expected_exception.exception.message)

    def test_run_should_follow_the_happy_path(self, mock_urlib2, mock_ZipFile, mock_move, mock_listdir, mock_isdir, mock_create_shortcut):
        app = self.get_application()
        expected_path = os.path.join(os.getenv('USERPROFILE'), 'AppData', 'Local', 'Peachy', 'PeachyInstaller', 'app-{}.json'.format(app.id))
        expected_source_path = os.path.join(os.getenv("TEMP"), app.download_location.split('/')[-1])
        expected_destination_path = os.path.join(os.getenv("TEMP"), app.name)
        expected_downloaded_file_data = "abba" * 1024 * 1024

        base_folder = 'c:\\some\\folder'
        internal_path = 'somerthing-1234.2314'
        mock_listdir.return_value = [internal_path]
        mock_isdir.return_value = True
        mock_urlib2.urlopen.return_value = self.get_mock_response(code=200, data=expected_downloaded_file_data)
        mock_open_file = mock_open()
        mock_create_shortcut.return_value = "fork"
        mock_zip_handle = mock_ZipFile.return_value.__enter__.return_value

        with patch('application_install.open', mock_open_file, create=True):
            mock_file = mock_open_file.return_value
            mock_open_file.return_value = mock_file
            installer = InstallApplication(app, base_folder)
            installer.start()

            mock_open_file.assert_called_with(expected_path, 'w')
            mock_ZipFile.assert_called_with(expected_source_path, 'r')
            mock_zip_handle.extractall.assert_called_with(expected_destination_path)
            actual_downloaded_file_data = ''.join([data[0][0] for data in mock_file.write.call_args_list[:-1]])
            self.assertEquals(expected_downloaded_file_data, actual_downloaded_file_data)



if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level='INFO')

    unittest.main()
