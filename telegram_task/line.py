"""This module contains the outline for workers and jobs/tasks"""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, time
from abc import ABC, abstractmethod
from dataclasses import dataclass
import telegram_task.president


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
        job_description: JobDescription = None,
        job_code: uuid.UUID = None
    ):
        if job_description:
            self.job_description = job_description
        else:
            self.job_description = JobDescription()
        if job_code:
            self.job_code = job_code
        else:
            self.job_code = uuid.uuid4()


@dataclass
class CronJobOrder(JobOrder):
    """
    CronJobOrder is like a JubOrder, 
    but it holds necessary data to run the task on a daily schedul
    """
    daily_run_time: time = None
    off_days: list[int] = None

    def __init__(
            self,
            daily_run_time: time,
            job_description: JobDescription = None,
            job_code: uuid.UUID = uuid.uuid4(),
            off_days: list[int] = None
    ):
        self.daily_run_time = daily_run_time
        if off_days:
            self.off_days = off_days
        else:
            self.off_days = []
        super().__init__(job_description=job_description, job_code=job_code)


@dataclass
class JobReport:
    """Holds the results of running a job/task"""
    information: list[str] = None
    warnings: list[str] = None

    def __init__(
            self,
            information: list[str] = None,
            warnings: list[str] = None
    ):
        if information is None:
            self.information = []
        else:
            self.information = information
        if warnings is None:
            self.warnings = []
        else:
            self.warnings = warnings


class Worker(ABC):
    """Abstract class to be implemented for each kind of tasks the user may have"""
    @abstractmethod
    async def perform_task(self, job_description: JobDescription) -> JobReport:
        """Performs a specific task using the provided job description"""

    @classmethod
    @abstractmethod
    def default_job_description(cls) -> JobDescription:
        """Checks if the provided job description is of a suitable type"""


class TaskException(Exception):
    """Exception raised by a particular shift."""


class LineManager:
    """Has a single worker of a specific type and manages its tasks"""
    _LOGGER = logging.getLogger(__name__)

    def __init__(
        self,
        worker: Worker,
        cron_job_orders: list[CronJobOrder] = None
    ):
        self.worker: Worker = worker
        self.display_name: str = worker.__class__.__name__
        self.cron_job_orders: list[CronJobOrder] = cron_job_orders \
            if cron_job_orders \
            else []

    def __str__(self) -> str:
        return self.display_name

    async def perform_task(
            self,
            job_order: JobOrder,
            president: telegram_task.president.President = None
    ) -> bool:
        """Handles the execution of a specific task using the provided job order"""
        self.__handle_job_start(
            job_order.job_code, president
        )
        try:
            report = await self.worker.perform_task(job_description=job_order.job_description)
            self.__handle_job_report(
                job_order.job_code, report, president
            )
            return True
        except TaskException as exception:
            self.__handle_task_exception(
                job_order.job_code, exception, president
            )
        except Exception as exception:
            self.__handle_unfamiliar_exception(
                job_order.job_code, exception, president
            )
        return False

    def __telegram_report(self, president: telegram_task.president.President, text: str) -> None:
        if president:
            president.telegram_report(text=text)

    def __handle_job_start(
        self,
        job_code: uuid.UUID,
        president: telegram_task.president.President = None
    ) -> None:
        """Handle the initiation of a job/task"""
        self._LOGGER.info(
            "Starting to manage the job [%s]", {job_code}
        )
        self.__telegram_report(
            president=president,
            text=f"""
⛏ <b>{self}</b> starting job <b>{job_code}</b> at <b>{datetime.now():%Y/%m/%d %H:%M:%S}</b>.
"""
        )

    def __handle_job_report(
            self,
            job_code: uuid.UUID,
            report: JobReport,
            president: telegram_task.president.President = None
    ) -> None:
        """Handle report from a completed job/task"""
        self.__handle_job_warnings(
            job_code=job_code, warnings=report.warnings, president=president
        )
        information = "\n" + \
            "\n".join(report.information) if report.information else ""
        self._LOGGER.info(
            "Job [%s] is complete:%s", job_code, information
        )
        self.__telegram_report(
            president=president,
            text=f"""
✅ <b>{self}</b> on job <b>{job_code}</b> is done.{information}
"""
        )

    def __handle_job_warnings(
            self,
            job_code: uuid.UUID,
            warnings: list[str],
            president: telegram_task.president.President = None
    ) -> None:
        """Handle a completed job/task's warnings, if any"""
        if warnings:
            warnings_agg = "\n".join(warnings)
            self._LOGGER.error(
                "Job [%s] raised some warnings:\n%s", job_code, warnings_agg
            )
            self.__telegram_report(
                president=president,
                text=f"""
⚠️ <b>{self}</b> on job <b>{job_code}</b> raised some warnings. Check the logs for more details.
"""
            )

    def __handle_task_exception(
            self,
            job_code: uuid.UUID,
            exception: TaskException,
            president: telegram_task.president.President = None
    ) -> None:
        """Handle familiar task exception"""
        self._LOGGER.error("Job [%s] hit exception: %s",
                           job_code, exception.__traceback__)
        self.__telegram_report(
            president=president,
            text=f"""
❌ <b>{self}</b> on job <b>{job_code}</b> hit TaskException. Check the logs for more details.
"""
        )

    def __handle_unfamiliar_exception(
            self,
            job_code: uuid.UUID,
            exception: Exception,
            president: telegram_task.president.President = None
    ) -> None:
        """Handle unfamiliar exception raised while performing a task"""
        self._LOGGER.fatal("Job [%s] hit exception: %s",
                           job_code, exception.__traceback__)
        self.__telegram_report(
            president=president,
            text=f"""
☠️ <b>{self}</b> on job <b>{job_code}</b> hit an unfamiliar exception. Check the logs for more details.
"""
        )
