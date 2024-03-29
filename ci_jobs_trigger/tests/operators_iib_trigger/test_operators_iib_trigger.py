import tempfile

import pytest
import requests
from simple_logger.logger import get_logger

from ci_jobs_trigger.libs.operators_iib_trigger.iib_trigger import (
    fetch_update_iib_and_trigger_jobs,
    upload_download_s3_bucket_file,
    verify_s3_or_local_file,
    get_new_iib,
)

LOGGER = get_logger("test_operators_iib_trigger")


class MockRequestGet:
    @staticmethod
    def json():
        return {
            "raw_messages": [
                {
                    "msg": {
                        "index": {
                            "ocp_version": "v4.15",
                            "index_image": "iib:quay.io/iib:690654",
                        }
                    }
                }
            ]
        }


class MockS3Client:
    @staticmethod
    def download_file(Filename, Bucket, Key):  # noqa N803
        return True

    @staticmethod
    def upload_file(Filename, Bucket, Key):  # noqa N803
        return True


@pytest.fixture()
def base_config_dict():
    return {
        "trigger_token": "token",
        "jenkins_token": "token",
        "jenkins_username": "user",
        "jenkins_url": "https://jenkins",
    }


@pytest.fixture()
def get_new_iib_config_dict(tmp_path, config_dict):
    tmpfile = tmp_path / "iib-test.json"
    tmpfile.touch()
    config_dict["local_operators_latest_iib_filepath"] = tmpfile
    return config_dict


@pytest.fixture()
def config_dict(base_config_dict):
    base_config_dict["ci_jobs"] = {
        "v4.15": [
            {
                "name": "openshift-ci-job-name",
                "ci": "openshift-ci",
                "products": {
                    "product": "operator",
                },
            }
        ],
        "v4.16": [
            {
                "name": "jenkins-job-name",
                "ci": "jenkins",
                "products": {
                    "product": "operator",
                },
            }
        ],
    }

    return base_config_dict


@pytest.fixture()
def config_dict_no_ci_jobs(base_config_dict):
    base_config_dict["ci_jobs"] = None
    return base_config_dict


@pytest.fixture()
def s3_client_mock(mocker):
    client_mock = mocker.patch("clouds.aws.session_clients.s3_client", return_value=MockS3Client())
    return client_mock()


def test_fetch_update_iib_and_trigger_jobs_no_ci_jobs_config(mocker, functions_mocker, config_dict_no_ci_jobs):
    mocker.patch.object(requests, "get", return_value=MockRequestGet())
    assert not fetch_update_iib_and_trigger_jobs(
        config_dict=config_dict_no_ci_jobs,
        logger=LOGGER,
        tmp_dir=tempfile.mkdtemp(dir="/tmp"),
    )


def test_fetch_update_iib_and_trigger_jobs(mocker, functions_mocker, config_dict):
    mocker.patch.object(requests, "get", return_value=MockRequestGet())
    fetch_update_iib_and_trigger_jobs(config_dict=config_dict, logger=LOGGER, tmp_dir=tempfile.mkdtemp(dir="/tmp"))


def test_both_s3_and_local_file_configs():
    assert not verify_s3_or_local_file(
        s3_bucket_operators_latest_iib_path="s3_bucket_operators_latest_iib",
        user_local_operators_latest_iib_filepath="user_local_operators_latest_iib",
        slack_errors_webhook_url=None,
        logger=LOGGER,
    )


def test_invalid_upload_download_s3_action():
    with pytest.raises(ValueError, match=".*Invalid action.*"):
        upload_download_s3_bucket_file(
            action="invalid_action",
            filename=None,
            s3_bucket_file_full_path=None,
            region=None,
            logger=LOGGER,
            slack_errors_webhook_url=None,
        )


def test_download_file_from_s3_bucket(s3_client_mock):
    assert upload_download_s3_bucket_file(
        action="download",
        filename="test",
        s3_bucket_file_full_path="non-existing-bucket/test",
        region=None,
        logger=LOGGER,
        boto_s3_client=s3_client_mock,
        slack_errors_webhook_url=None,
    )


def test_upload_missing_file_from_s3_bucket(s3_client_mock):
    upload_download_s3_bucket_file(
        action="upload",
        filename="test",
        s3_bucket_file_full_path="non-existing-bucket/test",
        region=None,
        logger=LOGGER,
        boto_s3_client=s3_client_mock,
        slack_errors_webhook_url=None,
    )


def test_get_new_iib(mocker, tmp_path, get_new_iib_config_dict):
    mocker.patch.object(requests, "get", return_value=MockRequestGet())
    new_data = get_new_iib(config_data=get_new_iib_config_dict, logger=LOGGER)
    expected_data = {
        "v4.15": {
            "openshift-ci-job-name": {
                "operators": {"operator": {"new-iib": True, "iib": "iib:quay.io/iib:690654"}},
                "ci": "openshift-ci",
            }
        },
        "v4.16": {"jenkins-job-name": {"operators": {"operator": {"new-iib": False}}, "ci": "jenkins"}},
    }
    assert new_data == expected_data
