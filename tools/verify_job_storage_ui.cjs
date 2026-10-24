// Actual extracted Jobs storage-state functions in a Node VM; no browser claim.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/jobs.js', 'utf8');
function extract(name) {
    const start = source.indexOf('function ' + name + '(');
    assert.ok(start >= 0, 'Missing actual function ' + name);
    const end = source.indexOf('\n}', start);
    assert.ok(end >= 0);
    return source.slice(start, end + 2);
}
const context = {
    jobsData: [{id: 4, messages: [{text: 'Retained client snapshot'}]}], jobLoadError: '',
    syncJobUnreadCache() {}, updateJobsBadge() {}, renderJobsList() {}, _unhideResolvedBreadcrumbs() {}, applyJobChannelState() {},
    document: {createElement() { return {attributes: {}, setAttribute(k, v) {this.attributes[k] = v;}}; }},
};
vm.createContext(context);
vm.runInContext(extract('renderJobStorageError') + '\n' + extract('applyJobsSnapshot'), context);
context.applyJobsSnapshot({error: '<script>unavailable</script>'});
assert.equal(context.jobsData[0].id, 4, 'An unavailable snapshot must not become an empty job history');
const list = {children: [], appendChild(value) {this.children.push(value);}};
assert.equal(context.renderJobStorageError(list), true);
assert.equal(list.children.length, 1);
assert.equal(list.children[0].attributes.role, 'alert');
assert.equal(list.children[0].textContent, '<script>unavailable</script>');
assert.equal(list.children[0].innerHTML, undefined, 'Error text must remain literal');
context.applyJobsSnapshot({data: [{id: 9}]});
assert.equal(context.jobsData[0].id, 9);
assert.equal(context.jobLoadError, '');
assert.equal(context.renderJobStorageError(list), false);
console.log(JSON.stringify({cases: 2, failures: 0, evidence: 'actual_extracted_functions_vm_only'}));
