import urllib.request, json
data = json.loads(urllib.request.urlopen('https://api.github.com/repos/kshahen905/industrial-_agent/actions/runs/25344861883/jobs').read().decode())
job = data['jobs'][0]
failed_steps = [s['name'] for s in job['steps'] if s['conclusion'] == 'failure']
print(f'Failed steps: {failed_steps}')
if len(job['steps']) > 0:
    log_url = job['url'] + '/logs'
    print(f'View logs manually at: {job["html_url"]}')
