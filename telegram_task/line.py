"""This module contains the outline for workers and jobs/tasks"""
import logging
import uuid
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
        job_description: JobDescription = JobDescription(),
        job_code: uuid.UUID = uuid.uuid4()
    ):
        self.job_description = job_description
        self.job_code = job_code


@dataclass
class JobReport:
    """Holds the results of running a job/task"""
    general_information: list[str] = None
    detailed_information: list[str] = None

    def __init__(self):
        self.general_information = []
        self.detailed_information = []


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

    def __init__(self, worker: Worker):
        self.worker: Worker = worker
        self.display_name: str = str(type(worker))

    async def perform_task(self, job_order: JobOrder) -> None:
        self._LOGGER.info(f"Starting to manage the job [{job_order.job_code}]")
        try:
            await self.worker.perform_task(job_description=job_order.job_description)
        except:
            pass
