from pathlib import Path
import subprocess,json,datetime,hashlib,base64
root=Path('D:/投资学/三家公司证券投资分析');local=root/'.local';local.mkdir(exist_ok=True)
key='AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl'
fp='SHA256:'+base64.b64encode(hashlib.sha256(base64.b64decode(key)).digest()).decode().rstrip('=')
assert fp=='SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU'
(local/'known_hosts').write_text('github.com ssh-ed25519 '+key+'\n')
git='C:/Program Files/Git/cmd/git.exe';ssh='C:/Program Files/Git/usr/bin/ssh.exe'
opts=['-i',(Path.home()/'.ssh/id_ed25519_investment_github').as_posix(),'-o','IdentitiesOnly=yes','-o','UserKnownHostsFile='+str(local/'known_hosts').replace('\\','/'),'-o','StrictHostKeyChecking=yes','-o','BatchMode=yes','-o','ConnectTimeout=10']
cmds=[[git,'--version'],[ssh,'-V'],[ssh,*opts,'-T','git@github.com'],[git,'-c','core.sshCommand="'+ssh+'" '+' '.join(opts),'ls-remote','git@github.com:Loyyed/3-.git']]
records=[]
for cmd in cmds:
 try:r=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=25);item={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
 except Exception as e:item={'command':cmd,'error':str(e)}
 records.append(item)
(root/'docs/git-connection-checks.json').write_text(json.dumps({'official_url':'https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints','fingerprint':fp,'checks':records},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(records,ensure_ascii=True))
