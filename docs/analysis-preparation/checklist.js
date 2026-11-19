const form = document.querySelector('#valuation-checklist');
const company = document.querySelector('#check-company');
const status = document.querySelector('#check-status');
const drafts = new Map();
function snapshot() {
  return [...form.querySelectorAll('tr[data-check]')].map(row => ({
    id: Number(row.dataset.check),
    selection: row.querySelector('select').value || null,
    reason: row.querySelector('input').value.trim() || null
  }));
}
function restore(items = []) {
  for (const row of form.querySelectorAll('tr[data-check]')) {
    const entry = items.find(x => x.id === Number(row.dataset.check));
    row.querySelector('select').value = entry?.selection || '';
    row.querySelector('input').value = entry?.reason || '';
  }
}
let active = company.value;
company.addEventListener('change', () => {
  drafts.set(active, snapshot());
  active = company.value;
  restore(drafts.get(active));
  status.textContent = '';
});
document.querySelector('#save-checks').addEventListener('click', () => {
  const checks = snapshot();
  if (checks.some(x => x.selection === 'not-applicable' && !x.reason)) {
    status.textContent = '请给每项不适用填写理由。';
    return;
  }
  const object = {schema_version:1, company:active, status:'准备草稿，待真实复核', checks, reviewer:null};
  const url = URL.createObjectURL(new Blob([JSON.stringify(object,null,2)],{type:'application/json'}));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'valuation-preparation.json';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
  status.textContent = '已下载本地准备草稿。';
});
document.querySelector('#load-checks').addEventListener('change', async event => {
  try {
    const value = JSON.parse(await event.target.files[0].text());
    if (value.schema_version !== 1 || ![...company.options].some(x=>x.value===value.company) ||
        !Array.isArray(value.checks) || value.checks.length!==22 ||
        new Set(value.checks.map(item=>item.id)).size!==22 ||
        value.checks.some(item=>!Number.isInteger(item.id)||item.id<1||item.id>22||
          ![null,'applicable','not-applicable'].includes(item.selection)||
          ![null,'string'].includes(item.reason===null?null:typeof item.reason))) throw Error();
    drafts.set(active,snapshot());
    company.value = active = value.company;
    restore(value.checks);
    status.textContent = '已打开本地准备草稿。';
  } catch {
    status.textContent = '文件不符合准备台草稿格式。';
  } finally { event.target.value = ''; }
});
