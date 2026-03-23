from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
from redis import Redis
from rq import Queue

redis_conn = Redis()
queue = Queue("resume_jobs", connection=redis_conn)


class ResumeHandler(FileSystemEventHandler):

    def on_created(self, event):

        if event.is_directory:
            return

        filepath = event.src_path

        if filepath.endswith((".pdf", ".docx", ".txt")):
            print("New resume:", filepath)

            queue.enqueue("workers.parse_resume_job", filepath)


if __name__ == "__main__":

    folder = "uploads/resumes"

    observer = Observer()
    observer.schedule(ResumeHandler(), folder, recursive=False)

    observer.start()

    print("Watching resume folder...")

    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()