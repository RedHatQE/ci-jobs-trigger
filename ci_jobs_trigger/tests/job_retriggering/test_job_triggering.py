import copy

import pytest
import xmltodict
from simple_logger.logger import get_logger

from ci_jobs_trigger.libs.openshift_ci.re_trigger.re_trigger import JobTriggering

LOGGER = get_logger(name=__name__)


@pytest.fixture()
def junit_file(request):
    with open(request.param) as fd:
        return xmltodict.parse(fd.read())


@pytest.fixture()
def hook_data_dict():
    return copy.deepcopy({
        "job_name": "periodic-test-job",
        "build_id": "1",
        "prow_job_id": "123456",
        "trigger_token": "trigger_token",
    })


@pytest.fixture()
def job_triggering(hook_data_dict):
    return JobTriggering(hook_data=hook_data_dict, logger=LOGGER)


@pytest.fixture(scope="class")
def db_filepath(tmp_path_factory):
    return tmp_path_factory.getbasetemp() / "job_re_triggering_test.db"


@pytest.mark.parametrize("param", ["job_name", "build_id", "prow_job_id", "trigger_token"])
def test_verify_job_trigger_mandatory_params(hook_data_dict, param):
    hook_data_dict.pop(param)

    with pytest.raises(ValueError):
        JobTriggering(hook_data=hook_data_dict, logger=LOGGER)


@pytest.mark.parametrize(
    "junit_file",
    ["ci_jobs_trigger/tests/job_retriggering/manifests/junit_operator_failed_pre_phase.xml"],
    indirect=True,
)
def test_failed_job_in_pre_phase(junit_file, job_triggering):
    tests_dict = job_triggering.get_testsuites_testcase_from_junit_operator(junit_xml=junit_file)
    assert job_triggering.is_build_failed_on_setup(tests_dict=tests_dict), "Job should fail on pre phase but did not"


@pytest.mark.parametrize(
    "junit_file",
    ["ci_jobs_trigger/tests/job_retriggering/manifests/junit_operator_failed_test_phase.xml"],
    indirect=True,
)
def test_failed_job_in_tests_phase(junit_file, job_triggering):
    tests_dict = job_triggering.get_testsuites_testcase_from_junit_operator(junit_xml=junit_file)
    assert not job_triggering.is_build_failed_on_setup(tests_dict=tests_dict), (
        "Job should fail on test phase but did not"
    )


class TestJobTriggering:
    JOB_NAME = "periodic-ci-CSPI-QE-MSI-openshift-ci-trigger-poc-test-fail-setup"
    PROW_JOB_ID = "123456"

    @pytest.mark.parametrize(
        "junit_file",
        ["ci_jobs_trigger/tests/job_retriggering/manifests/junit_operator_failed_pre_phase.xml"],
        indirect=True,
    )
    def test_add_job_trigger(self, mocker, db_filepath, junit_file, job_triggering):
        job_trigger_module_path = "ci_jobs_trigger.libs.openshift_ci.re_trigger.re_trigger.JobTriggering"
        mocker.patch(
            f"{job_trigger_module_path}._trigger_job",
            return_value=TestJobTriggering.PROW_JOB_ID,
        )
        mocker.patch(
            f"{job_trigger_module_path}.wait_for_job_completed",
            return_value=True,
        )
        mocker.patch(
            f"{job_trigger_module_path}.get_tests_from_junit_operator_by_build_id",
            return_value=junit_file,
        )

        assert job_triggering.execute_trigger(job_db_path=db_filepath, retrigger_timeout=1), "Job should be triggered"

    def test_already_triggered(self, db_filepath, hook_data_dict):
        hook_data_dict["prow_job_id"] = TestJobTriggering.PROW_JOB_ID
        job_triggering = JobTriggering(hook_data=hook_data_dict, logger=LOGGER)
        assert not job_triggering.execute_trigger(db_filepath), "Job should not be triggered"
