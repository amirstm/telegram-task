import unittest
from telegram_task.line import LineManager, TaskException, JobOrder
from telegram_task.samples import (
    SleepyWorker,
    MathematicalOperation,
    CalculatorJobDescription,
    CalculatorWorker
)


class TestLine(unittest.IsolatedAsyncioTestCase):
    """Test line operations without any president"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def test_abandoned_sleepy_worker(self):
        """Abandoned simple worker test"""
        worker = SleepyWorker()
        report = await worker.perform_task(job_description=None)
        self.assertTrue(report.information)
        self.assertTrue(report.warnings)

    async def test_abandoned_calculator_worker(self):
        """Abandoned calculator worker test"""
        worker = CalculatorWorker()
        report1 = await worker.perform_task(
            job_description=CalculatorJobDescription(
                input1=1.6,
                input2=2.6,
                operation=MathematicalOperation.SUM,
                integer_part=True
            )
        )
        self.assertTrue("4" in report1.information[0])
        self.assertFalse(report1.warnings)

    async def test_abandoned_calculator_worker_task_exception(self):
        """Abandoned calculator worker test"""
        worker = CalculatorWorker()
        try:
            report1 = await worker.perform_task(
                job_description=CalculatorJobDescription(
                    input1=1.6,
                    input2=2.6,
                    operation=MathematicalOperation.POW,
                    integer_part=True
                )
            )
        except Exception as te:
            self.assertTrue(isinstance(te, TaskException))

    async def test_line_manager_calculator_success(self):
        """Test success of a calculator worker through a LineManager"""
        lm = LineManager(worker=CalculatorWorker())
        was_success = await lm.perform_task(
            job_order=JobOrder(
                job_description=CalculatorJobDescription(
                    input1=1.6,
                    input2=2.6,
                    operation=MathematicalOperation.SUM,
                    integer_part=True
                )))
        self.assertTrue(was_success)

    async def test_line_manager_calculator_failure(self):
        """Test failure of a calculator worker through a LineManager"""
        lm = LineManager(worker=CalculatorWorker())
        was_success = await lm.perform_task(
            job_order=JobOrder(
                job_description=CalculatorJobDescription(
                    input1=1.6,
                    input2=2.6,
                    operation=MathematicalOperation.POW,
                    integer_part=True
                )))
        self.assertFalse(was_success)


if __name__ == '__main__':
    unittest.main()
