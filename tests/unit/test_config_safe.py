# tests/unit/test_config_safe.py

import unittest
from unittest.mock import patch, MagicMock
import socket

from autoheader.config import fetch_remote_config_safe

class TestFetchRemoteConfigSafe(unittest.TestCase):
    @patch("urllib.request.urlopen")
    def test_timeout_with_retries(self, mock_urlopen):
        mock_urlopen.side_effect = socket.timeout
        result = fetch_remote_config_safe("http://example.com")
        self.assertIsNone(result)
        self.assertEqual(mock_urlopen.call_count, 3)

    @patch("urllib.request.urlopen")
    def test_large_file_aborts_download(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b"a" * 2_000_000  # 2MB
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = fetch_remote_config_safe("http://example.com")
        self.assertIsNone(result)

    @patch("urllib.request.urlopen")
    def test_success_with_valid_toml(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.side_effect = [b'[general]\ndry_run = true', b'']
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = fetch_remote_config_safe("http://example.com")
        self.assertEqual(result, {"general": {"dry_run": True}})
