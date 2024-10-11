from qgis.core import QgsTask, QgsMessageLog, Qgis,QgsApplication

class MyBackgroundTask(QgsTask):
    def __init__(self, name, task_function, *args, **kwargs):
        """
        Initialize the task.
        :param name: Name of the task.
        :param task_function: The function to be run by the task.
        :param args: Arguments to pass to the task function.
        :param next_task: Another task to execute after this one finishes.
        :param kwargs: Keyword arguments to pass to the task function.
        """
        super().__init__(name)
        self.task_function = task_function  # The function to execute
        self.args = args                    # Arguments for the function
        self.kwargs = kwargs                # Keyword arguments for the function
        self.next_task = None          # The next task to execute after this task completes
        QgsMessageLog.logMessage(f"Task {self.description()} is initialized", level=Qgis.Info)

    def run(self):
        """Run the task function."""
        QgsMessageLog.logMessage(f"Task {self.description()} is running", level=Qgis.Info)
        try:
            # Execute the function with arguments
            result = self.task_function(*self.args, **self.kwargs)
            return True
        except Exception as e:
            QgsMessageLog.logMessage(f"Error in task {self.description()}: {e}", level=Qgis.Critical)
            return False

    def finished(self, result):
        """Handle the task completion and launch the next task if any."""
        if result:
            QgsMessageLog.logMessage(f"Task {self.description()} finished successfully", level=Qgis.Success)
        else:
            QgsMessageLog.logMessage(f"Task {self.description()} failed", level=Qgis.Critical)

        # Check if there's a next task to run
        if self.next_task:
            QgsMessageLog.logMessage(f"Starting next task: {self.next_task.description()}", level=Qgis.Info)
            QgsApplication.taskManager().addTask(self.next_task)

def example_task_function(task_id, delay):
    """
    Example task function that takes an ID and a delay.
    :param task_id: ID of the task (for logging purposes).
    :param delay: Time to sleep to simulate task duration.
    :return: True if successful, False otherwise.
    """
    QgsMessageLog.logMessage(f"Task {task_id} is running", level=Qgis.Info)
    import time
    time.sleep(delay)  # Simulate a long-running task
    return True



