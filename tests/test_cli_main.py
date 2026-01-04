"""Tests for CLI main function."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from cvextract import cli


class TestMainFunction:
    """Tests for the main CLI entry point."""
    
    @patch('cvextract.cli.execute_pipeline')
    @patch('cvextract.cli.prepare_execution_environment')
    @patch('cvextract.cli.gather_user_requirements')
    def test_main_success(self, mock_gather, mock_prepare, mock_execute):
        """main() should return 0 on successful execution."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.log_file = None
        mock_gather.return_value = mock_config
        
        mock_prepared_config = MagicMock()
        mock_prepare.return_value = mock_prepared_config
        
        mock_execute.return_value = 0
        
        # Call main
        result = cli.main(["--extract", "source=cv.docx", "--target", "/output"])
        
        # Verify
        assert result == 0
        mock_gather.assert_called_once()
        mock_prepare.assert_called_once_with(mock_config)
        mock_execute.assert_called_once_with(mock_prepared_config)
    
    @patch('cvextract.cli.execute_pipeline')
    @patch('cvextract.cli.prepare_execution_environment')
    @patch('cvextract.cli.gather_user_requirements')
    def test_main_with_log_file(self, mock_gather, mock_prepare, mock_execute):
        """main() should create log file directory if needed."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.log_file = "/tmp/test.log"
        mock_gather.return_value = mock_config
        
        mock_prepared_config = MagicMock()
        mock_prepare.return_value = mock_prepared_config
        
        mock_execute.return_value = 0
        
        with patch('cvextract.cli.Path') as mock_path_class:
            mock_path = MagicMock()
            mock_path_class.return_value = mock_path
            mock_path.expanduser.return_value = mock_path
            mock_path.resolve.return_value = mock_path
            mock_path.parent = MagicMock()
            
            result = cli.main(["--extract", "source=cv.docx", "--target", "/output"])
        
        assert result == 0
        mock_execute.assert_called_once()
    
    @patch('cvextract.cli.execute_pipeline')
    @patch('cvextract.cli.prepare_execution_environment')
    @patch('cvextract.cli.gather_user_requirements')
    def test_main_exception_without_debug(self, mock_gather, mock_prepare, mock_execute):
        """main() should return 1 on exception and not log traceback without debug."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.log_file = None
        mock_gather.return_value = mock_config
        
        # Make prepare raise an exception
        mock_prepare.side_effect = ValueError("Test error")
        
        # Call main
        result = cli.main(["--extract", "source=cv.docx", "--target", "/output"])
        
        # Verify
        assert result == 1
    
    @patch('cvextract.cli.LOG')
    @patch('cvextract.cli.execute_pipeline')
    @patch('cvextract.cli.prepare_execution_environment')
    @patch('cvextract.cli.gather_user_requirements')
    def test_main_gather_fails(self, mock_gather, mock_prepare, mock_execute, mock_log):
        """main() should propagate exception from gather_user_requirements."""
        # Setup mocks to fail at gather phase
        mock_gather.side_effect = ValueError("Invalid arguments")
        
        # Call main - should raise because gather is not in try-except
        with pytest.raises(ValueError, match="Invalid arguments"):
            cli.main(["--invalid"])
        
        # Verify
        mock_prepare.assert_not_called()
        mock_execute.assert_not_called()
    
    @patch('cvextract.cli.execute_pipeline')
    @patch('cvextract.cli.prepare_execution_environment')
    @patch('cvextract.cli.gather_user_requirements')
    def test_main_execute_returns_nonzero(self, mock_gather, mock_prepare, mock_execute):
        """main() should return execute_pipeline's return code."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.log_file = None
        mock_gather.return_value = mock_config
        
        mock_prepared_config = MagicMock()
        mock_prepare.return_value = mock_prepared_config
        
        # Make execute return an error code
        mock_execute.return_value = 5
        
        # Call main
        result = cli.main(["--extract", "source=cv.docx", "--target", "/output"])
        
        # Verify
        assert result == 5
    
    @patch('cvextract.cli.execute_pipeline')
    @patch('cvextract.cli.prepare_execution_environment')
    @patch('cvextract.cli.gather_user_requirements')
    def test_main_with_no_args(self, mock_gather, mock_prepare, mock_execute):
        """main() should handle no arguments."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.log_file = None
        mock_gather.return_value = mock_config
        
        mock_prepared_config = MagicMock()
        mock_prepare.return_value = mock_prepared_config
        
        mock_execute.return_value = 0
        
        # Call main with no arguments
        result = cli.main([])
        
        # Verify gather was called with empty list
        mock_gather.assert_called_once_with([])
        assert result == 0
    
    @patch('cvextract.cli.execute_pipeline')
    @patch('cvextract.cli.prepare_execution_environment')
    @patch('cvextract.cli.gather_user_requirements')
    def test_main_with_argv_none(self, mock_gather, mock_prepare, mock_execute):
        """main() should handle argv=None."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.log_file = None
        mock_gather.return_value = mock_config
        
        mock_prepared_config = MagicMock()
        mock_prepare.return_value = mock_prepared_config
        
        mock_execute.return_value = 0
        
        # Call main with argv=None
        result = cli.main(None)
        
        # Verify gather was called with None
        mock_gather.assert_called_once_with(None)
        assert result == 0
    
    @patch('cvextract.cli.LOG')
    @patch('cvextract.cli.execute_pipeline')
    @patch('cvextract.cli.prepare_execution_environment')
    @patch('cvextract.cli.gather_user_requirements')
    def test_main_exception_with_complex_error(self, mock_gather, mock_prepare, mock_execute, mock_log):
        """main() should handle complex exceptions with debug logging."""
        # Setup mocks
        mock_config = MagicMock()
        mock_config.log_file = None
        mock_gather.return_value = mock_config
        
        # Make prepare raise a complex exception
        def raise_error():
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise RuntimeError("Outer error") from e
        
        mock_prepare.side_effect = raise_error
        
        # Call main
        result = cli.main(["--extract", "source=cv.docx", "--target", "/output"])
        
        # Verify
        assert result == 1
        # Should have called LOG.error twice
        assert mock_log.error.call_count == 2
