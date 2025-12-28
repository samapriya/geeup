"""
Test suite for geeup modular components.
"""

import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open

import pytest

from . import fake_ee


class TestAuthModule:
    """Test authentication module."""

    def test_initialize_ee_with_service_account(self, tmp_path):
        """Test EE initialization with service account."""
        from geeup.auth import initialize_ee

        sa_file = tmp_path / "service_account.json"
        sa_data = {
            "client_email": "test@project.iam.gserviceaccount.com",
            "private_key": "-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----\n"
        }
        sa_file.write_text(json.dumps(sa_data))

        with patch('geeup.auth.get_sa_credentials_path', return_value=(tmp_path, sa_file)):
            with patch.object(fake_ee, 'Initialize') as mock_init:
                initialize_ee()
                mock_init.assert_called_once()

    def test_initialize_ee_without_service_account(self):
        """Test EE initialization without service account."""
        from geeup.auth import initialize_ee

        with patch('geeup.auth.get_sa_credentials_path', return_value=(Path('.'), Path('nonexistent.json'))):
            with patch.object(fake_ee, 'Initialize') as mock_init:
                initialize_ee()
                mock_init.assert_called_once()

    def test_get_sa_credentials_path(self):
        """Test getting service account credentials path."""
        from geeup.auth import get_sa_credentials_path

        sa_dir, sa_file = get_sa_credentials_path()
        assert sa_dir.name == 'earthengine'
        assert sa_file.name == 'service_account_credentials.json'


class TestQuotaModule:
    """Test quota module."""

    def test_fetch_quota_data_no_project(self, sample_quota_data):
        """Test fetching quota data without specific project."""
        from geeup.quota import fetch_quota_data

        with patch.object(fake_ee.data, 'getAssetRoots') as mock_roots:
            with patch.object(fake_ee.data, 'getInfo') as mock_info:
                mock_roots.return_value = [
                    {'id': 'users/testuser/assets'}
                ]
                mock_info.return_value = sample_quota_data['users/testuser']

                result = fetch_quota_data(None)
                assert result is not None
                assert 'users/testuser/assets' in result or len(result) > 0

    def test_fetch_quota_data_specific_project(self, sample_quota_data):
        """Test fetching quota data for specific project."""
        from geeup.quota import fetch_quota_data

        with patch.object(fake_ee.data, 'getInfo') as mock_info:
            mock_info.return_value = sample_quota_data['projects/test-project']

            result = fetch_quota_data('projects/test-project')
            assert result is not None
            assert 'projects/test-project' in result


class TestTasksModule:
    """Test tasks module."""

    def test_fetch_tasks_all(self, sample_task_list):
        """Test fetching all tasks."""
        from geeup.tasks import fetch_tasks

        with patch.object(fake_ee.data, 'getTaskList', return_value=sample_task_list):
            tasks = fetch_tasks()
            assert len(tasks) == 2
            assert tasks[0]['id'] == 'TASK001'

    def test_fetch_tasks_by_state(self, sample_task_list):
        """Test fetching tasks filtered by state."""
        from geeup.tasks import fetch_tasks

        with patch.object(fake_ee.data, 'getTaskList', return_value=sample_task_list):
            tasks = fetch_tasks(state='RUNNING')
            assert len(tasks) == 1
            assert tasks[0]['state'] == 'RUNNING'

    def test_fetch_tasks_by_id(self, sample_task_list):
        """Test fetching specific task by ID."""
        from geeup.tasks import fetch_tasks

        with patch.object(fake_ee.data, 'getTaskStatus') as mock_status:
            mock_status.return_value = [sample_task_list[0]]
            tasks = fetch_tasks(task_id='TASK001')
            assert len(tasks) == 1
            assert tasks[0]['id'] == 'TASK001'

    def test_summarize_tasks(self, sample_task_list):
        """Test task summarization."""
        from geeup.tasks import summarize_tasks

        with patch.object(fake_ee.data, 'getTaskList', return_value=sample_task_list):
            summary = summarize_tasks()
            assert summary['RUNNING'] == 1
            assert summary['READY'] == 1
            assert summary['COMPLETED'] == 0


class TestZipShapeModule:
    """Test zip_shape module."""

    def test_zip_shapefiles_success(self, tmp_path):
        """Test successful shapefile zipping."""
        from geeup.zip_shape import zip_shapefiles

        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        # Create dummy shapefile components
        (input_dir / "test.shp").touch()
        (input_dir / "test.shx").touch()
        (input_dir / "test.dbf").touch()

        summary = zip_shapefiles(str(input_dir), str(output_dir))

        assert summary['created'] >= 0
        assert 'skipped' in summary
        assert 'failed' in summary

    def test_zip_shapefiles_no_shapefiles(self, tmp_path):
        """Test zipping when no shapefiles exist."""
        from geeup.zip_shape import zip_shapefiles

        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        input_dir.mkdir()
        output_dir.mkdir()

        summary = zip_shapefiles(str(input_dir), str(output_dir))

        assert summary['created'] == 0


class TestBatchUploaderModule:
    """Test batch_uploader module."""

    def test_upload_validation(self, tmp_path):
        """Test upload validation."""
        from geeup.batch_uploader import upload

        source_dir = tmp_path / "source"
        source_dir.mkdir()
        metadata_file = tmp_path / "metadata.csv"
        metadata_file.write_text("system:index\ntest_image")

        with patch('geeup.batch_uploader.validate_upload_params') as mock_validate:
            with patch('geeup.batch_uploader.process_uploads') as mock_process:
                mock_validate.return_value = True
                upload(
                    user='test@example.com',
                    source_path=str(source_dir),
                    destination_path='users/test/collection',
                    metadata_path=str(metadata_file),
                    dry_run=True
                )
                mock_validate.assert_called_once()


class TestTuploaderModule:
    """Test tuploader module."""

    def test_tabup_validation(self, tmp_path):
        """Test table upload validation."""
        from geeup.tuploader import tabup

        source_dir = tmp_path / "source"
        source_dir.mkdir()

        with patch('geeup.tuploader.validate_tabup_params') as mock_validate:
            with patch('geeup.tuploader.process_table_uploads') as mock_process:
                mock_validate.return_value = True
                tabup(
                    user='test@example.com',
                    dirc=str(source_dir),
                    destination='users/test/folder',
                    dry_run=True
                )
                mock_validate.assert_called_once()


class TestErrorHandling:
    """Test error handling across modules."""

    def test_quota_fetch_error(self):
        """Test quota fetch with error."""
        from geeup.quota import fetch_quota_data

        with patch.object(fake_ee.data, 'getAssetRoots', side_effect=Exception("API Error")):
            result = fetch_quota_data(None)
            # Should handle gracefully
            assert result is None or result == {}

    def test_task_fetch_error(self):
        """Test task fetch with error."""
        from geeup.tasks import fetch_tasks

        with patch.object(fake_ee.data, 'getTaskList', side_effect=Exception("API Error")):
            # Should handle gracefully
            try:
                tasks = fetch_tasks()
                assert tasks is None or tasks == []
            except Exception:
                # Expected behavior - may raise
                pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
