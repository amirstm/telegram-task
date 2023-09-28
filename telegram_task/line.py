"""This module contains the outline for workers and jobs/tasks"""
import logging
import uuid
from datetime import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from telegram_task.president import President


@dataclass
class JobDescription:
    """
    JobDescription holds input for new tasks and should be inheritted 
    in case a particular task has a more sophisticated job description.
    """


@dataclass
class JobOrder:
    """JobOrder is created for the worker to run a specific job/task once"""
    job_description: JobDescription = None
    job_code: uuid.UUID = None

    def __init__(
        self,
        job_description: JobDescription = JobDescription(),
        job_code: uuid.UUID = uuid.uuid4()
    ):
        self.job_description = job_description
        self.job_code = job_code


@dataclass
class JobReport:
    """Holds the results of running a job/task"""
    information: list[str] = None
    warnings: list[str] = None

    def __init__(self):
        self.information = []
        self.warnings = []


class Worker(ABC):
    """Abstract class to be implemented for each kind of tasks the user may have"""
    @abstractmethod
    async def perform_task(self, job_description: JobDescription) -> JobReport:
        """Performs a specific task using the provided job description"""


class TaskException(Exception):
    """Exception raised by a particular shift."""


class LineManager:
    """Has a single worker of a specific type and manages its tasks"""
    _LOGGER = logging.getLogger(__name__)

    def __init__(self, worker: Worker, president: President):
        self.worker: Worker = worker
        self.president: President = president
        self.display_name: str = str(type(worker))

    def __str__(self) -> str:
        return self.display_name

    async def perform_task(self, job_order: JobOrder) -> None:
        """Handles the execution of a specific task using the provided job order"""
        self._LOGGER.info(
            "Starting to manage the job [%s]", {job_order.job_code}
        )
        self.__handle_job_start(job_order.job_code)
        try:
            report = await self.worker.perform_task(job_description=job_order.job_description)
            self.__handle_job_report(job_order.job_code, report)
        except TaskException as exception:
            self.__handle_task_exception(job_order.job_code, exception)
        except Exception as exception:
            self.__handle_unfamiliar_exception(job_order.job_code, exception)

    def __handle_job_start(self, job_code: uuid.UUID):
        """Handle report from a completed job/task"""
        self.president.telegram_bot.send_message(
            chat_id=self.president.telegram_admin_id,
            text=f"""
⛏ <b>{self}</b> starting job <b>{job_code}</b> at <b>{datetime.now():%Y-%m-%d %H:%M:%S}</b>.
""",
            parse_mode='html'
        )

    def __handle_job_report(self, job_code: uuid.UUID, report: JobReport):
        """Handle report from a completed job/task"""
        self.__handle_job_warnings(
            job_code=job_code, warnings=report.warnings
        )
        information = ", final report:\n" + \
            "\n".join(report.information) if report.information else ""
        self._LOGGER.info(
            "Job [%s] is complete:%s", job_code, information
        )
        self.president.telegram_bot.send_message(
            chat_id=self.president.telegram_admin_id,
            text=f"""
✅ <b>{self}</b> on job <b>{job_code}</b> is done.\n{information}
""",
            parse_mode='html'
        )

    def __handle_job_warnings(self, job_code: uuid.UUID, warnings: list[str]):
        """Handle a completed job/task's warnings, if any"""
        if warnings:
            warnings_agg = "\n".join(warnings)
            self._LOGGER.error(
                "Job [%s] raised some warnings:\n%s", job_code, warnings_agg
            )
            self.president.telegram_bot.send_message(
                chat_id=self.president.telegram_admin_id,
                text=f"""
⚠️ <b>{self}</b> on job <b>{job_code}</b> raised some warnings. Check the logs for more details.
""",
                parse_mode='html'
            )

    def __handle_task_exception(self, job_code: uuid.UUID, exception: TaskException):
        """Handle familiar task exception"""
        self._LOGGER.error("Job [%s] hit exception: %s",
                           job_code, exception.__traceback__)
        self.president.telegram_bot.send_message(
            chat_id=self.president.telegram_admin_id,
            text=f"""
❌ <b>{self}</b> on job <b>{job_code}</b> hit TaskException. Check the logs for more details.
{exception.__traceback__}
""",
            parse_mode='html'
        )

    def __handle_unfamiliar_exception(self, job_code: uuid.UUID, exception: Exception):
        """Handle unfamiliar exception raised while performing a task"""
        self._LOGGER.fatal("Job [%s] hit exception: %s",
                           job_code, exception.__traceback__)
        self.president.telegram_bot.send_message(
            chat_id=self.president.telegram_admin_id,
            text=f"""
☠️ <b>{self}</b> on job <b>{job_code}</b> hit an unfamiliar exception. Check the logs for more details.
""",
            parse_mode='html'
        )
