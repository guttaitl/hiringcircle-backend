from api.workers.resume_parsing_worker import process_resume_parsing
import time

print("Starting resume parsing worker...")

while True:
    process_resume_parsing()
    time.sleep(1)