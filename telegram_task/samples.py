"""
Some sample implementation of the abstract classes 
are provided in this module
"""
import asyncio
import random
from dataclasses import dataclass
from enum import Enum
from telegram_task.line import JobReport, Worker, JobDescription, TaskException


class SleepyWorker(Worker):
    """Sample worker that sleeps some random seconds"""
    async def perform_task(self, job_description: JobDescription) -> JobReport:
        nap_length = random.randint(1, 3)
        await asyncio.sleep(nap_length)
        return JobReport(
            information=[f"Nap Length ➡️ {nap_length}"],
            warnings=["Worker is too sleepy!"]
        )

    @classmethod
    def default_job_description(cls) -> JobDescription:
        return JobDescription()


class MathematicalOperation(Enum):
    """
    Enum for 4 basic mathematical operations,
    used in the CalculatorJobDescription class
    """
    SUM = "summation"
    SUB = "subtraction"
    MUL = "multiplication"
    DIV = "division"
    POW = "exponentiation"

    def __str__(self) -> str:
        return self.name


@dataclass
class CalculatorJobDescription(JobDescription):
    """Sample job description for a simple calculator"""
    input1: float
    input2: float
    operation: MathematicalOperation
    integer_part: bool = False


class CalculatorWorker(Worker):
    """Sample worker that does simple mathematical operations"""
    async def perform_task(self, job_description: CalculatorJobDescription) -> JobReport:
        if job_description.operation == MathematicalOperation.SUM:
            result = job_description.input1 + job_description.input2
        elif job_description.operation == MathematicalOperation.SUB:
            result = job_description.input1 - job_description.input2
        elif job_description.operation == MathematicalOperation.MUL:
            result = job_description.input1 * job_description.input2
        elif job_description.operation == MathematicalOperation.DIV:
            # division to zero is not handled delibrately, so that you can catch a fatal error
            result = job_description.input1 / job_description.input2
        elif job_description.operation == MathematicalOperation.POW:
            # exponentiation raises a known task exception
            raise TaskException("I don't know exponentiation!")
        if job_description.integer_part:
            result = int(result)
        return JobReport(
            information=[f"Result ➡️ {result}"]
        )

    @classmethod
    def default_job_description(cls) -> CalculatorJobDescription:
        return CalculatorJobDescription(
            input1=0,
            input2=0,
            operation=MathematicalOperation.SUM
        )
