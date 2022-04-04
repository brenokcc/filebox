import time
from .assync import task

@task('Download Files')
def download(task=None):
    for i in task.iterate(range(10)):
        print(i)
        time.sleep(1)
    task.finalize('Files successfully downloaded.', '/')