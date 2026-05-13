import uuid
import random
from datetime import datetime, timedelta
from feedback_db import init_db, log_feedback

# Sample interactions mimicking real DevOps log analysis
SAMPLES = [
    {
        "user_input": "Docker build failed: COPY failed: stat /var/lib/docker/tmp/docker-builder123/package.json: no such file or directory",
        "agent_response": "The error indicates that `package.json` is missing in the build context. Make sure you are running the `docker build` command from the correct directory where `package.json` exists, or adjust your COPY command.",
        "score": 1,
        "comment": "Spot on, I was in the wrong folder."
    },
    {
        "user_input": "psycopg2.OperationalError: FATAL: password authentication failed for user 'postgres'",
        "agent_response": "This is a PostgreSQL authentication error. Please try restarting your computer or reinstalling PostgreSQL. It might also be a network issue.",
        "score": -1,
        "comment": "Terrible advice. It was just a wrong password in my .env file, why would I reinstall Postgres?"
    },
    {
        "user_input": "nginx: [emerg] bind() to 0.0.0.0:80 failed (98: Address already in use)",
        "agent_response": "Port 80 is already being used by another process. You can find the process using `sudo lsof -i :80` or `sudo netstat -tulpn | grep :80`, and kill it using `sudo kill -9 <PID>`.",
        "score": 1,
        "comment": ""
    },
    {
        "user_input": "Error: ENOSPC: no space left on device, write",
        "agent_response": "Your hard drive is completely broken and needs to be physically replaced. Please contact hardware support.",
        "score": -1,
        "comment": "It was just Docker eating up space. I ran docker system prune and it's fine. Extreme hallucination."
    },
    {
        "user_input": "ModuleNotFoundError: No module named 'fastapi'",
        "agent_response": "You are missing the 'fastapi' module. You can install it by running `pip install fastapi`.",
        "score": 1,
        "comment": ""
    },
    {
        "user_input": "kubernetes pods stuck in Pending state. Events show: 0/3 nodes are available: 3 Insufficient memory.",
        "agent_response": "To fix this, you should use the `kubectl delete all --all` command to clear your cluster.",
        "score": -1,
        "comment": "Dangerous command suggested! The issue is just lack of memory, scaling up nodes or modifying resource requests is the proper way."
    },
    {
        "user_input": "TypeError: Cannot read properties of undefined (reading 'map')",
        "agent_response": "You are trying to call `.map()` on an undefined variable in JavaScript/TypeScript. Ensure that the array is initialized before mapping over it, for example: `const arr = data || []; arr.map(...)`",
        "score": 1,
        "comment": "Helpful and to the point."
    },
    {
        "user_input": "AttributeError: 'NoneType' object has no attribute 'get'",
        "agent_response": "The error is 'AttributeError'.",
        "score": -1,
        "comment": "Incomplete answer. Didn't explain WHY it happens or how to fix it."
    },
    {
        "user_input": "sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint",
        "agent_response": "You are trying to insert a record into the database that contains a value violating a UNIQUE constraint (e.g., trying to register a user with an email that already exists). Check your data before insertion or handle the exception.",
        "score": 1,
        "comment": ""
    },
    {
        "user_input": "git push error: failed to push some refs to 'origin'. Updates were rejected because the remote contains work that you do not have locally.",
        "agent_response": "Run `git push --force` to overwrite the remote repository.",
        "score": -1,
        "comment": "This is terrible advice. You should suggest git pull --rebase instead of force pushing and destroying colleagues' work."
    }
]

def generate_samples():
    print("Initializing database...")
    init_db()
    
    print(f"Inserting {len(SAMPLES)} sample feedback records...")
    for idx, sample in enumerate(SAMPLES):
        thread_id = str(uuid.uuid4())
        
        # We manually modify the log_feedback to allow passing a specific timestamp for variety 
        # but for simplicity, we'll just use the default function which uses datetime.utcnow()
        log_feedback(
            thread_id=thread_id,
            user_input=sample["user_input"],
            agent_response=sample["agent_response"],
            feedback_score=sample["score"],
            optional_comment=sample["comment"]
        )
        print(f"Inserted record {idx+1}/{len(SAMPLES)}")
        
    print("Done! Sample data generation complete.")

if __name__ == "__main__":
    generate_samples()
