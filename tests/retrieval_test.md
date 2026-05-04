# Retrieval Tests

Manual testing guide for vector database retrieval functionality.

## Test 1: Docker Port Binding Error

### Input Log
```
Error response from daemon: driver failed programming external connectivity on endpoint nginx_container (b8c4a7f9d5e8): Error starting userland proxy: listen tcp 0.0.0.0:80: bind: address already in use
```

### Expected Retrieval
- Docker troubleshooting guide (Port Binding Errors section)
- Commands for checking port usage: `lsof -i :80`, `netstat -tulpn`
- Solutions: restart Docker, change port

### Test Steps
1. Run data ingestion: `python ingestion/ingest_data.py`
2. Query vector DB with: `"docker port binding error"`
3. Verify retrieved documents are relevant

---

## Test 2: Python Module Not Found

### Input Log
```
Traceback (most recent call last):
  File "/home/user/app/main.py", line 45, in load_config
    import yaml
ModuleNotFoundError: No module named 'yaml'
```

### Expected Retrieval
- Python debugging guide (Module Import Errors section)
- Commands: `pip install yaml`, `pip list`
- Solution: install missing package

### Test Steps
1. Query: `"ModuleNotFoundError import error"`
2. Should retrieve Python debugging documentation
3. Verify pip install commands are included

---

## Test 3: Connection Refused Error

### Input Log
```
ERROR [nginx]: [error] 1234#1234: *567 connect() failed (111: Connection refused) while connecting to upstream, client: 192.168.1.100, server: app.example.com
```

### Expected Retrieval
- Linux server guide (Connection and Networking Issues)
- Docker troubleshooting (Connection issues)
- Commands: `systemctl status`, `nc -zv`, `telnet`

### Test Steps
1. Query: `"nginx connection refused upstream"`
2. Should retrieve multiple relevant guides
3. Verify different sections are captured

---

## Test 4: Out of Memory Error

### Input Log
```
ERROR [kernel]: Out of memory: Kill process 9876 (java) score 450 or sacrifice child
```

### Expected Retrieval
- Linux server guide (Out of Memory Issues)
- Commands: `free -h`, `top`, `ps aux --sort=-%mem`
- Solutions: identify processes, increase memory, optimize

### Test Steps
1. Query: `"out of memory OOM killer"`
2. Should retrieve memory debugging guides
3. Verify diagnostic and solution commands

---

## Automated Retrieval Test

Run the included test suite:

```bash
cd ai-devops-log-analyzer
source venv/Scripts/activate
pytest tests/persistence_test.py::TestVectorRetrieval -v
```

## Expected Results

All retrieval tests should return:
- ✓ Top 3 relevant documents
- ✓ Document source properly identified
- ✓ Content chunked into readable pieces
- ✓ No corrupted or truncated content
