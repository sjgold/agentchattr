// Actual schedule snapshot/error functions in a VM, not rendered browser evidence.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/chat.js', 'utf8');
function extract(name) {
    const start = source.indexOf('function ' + name + '(');
    assert.ok(start >= 0, 'Missing actual function ' + name);
    return source.slice(start, source.indexOf('\n}', start) + 2);
}
const elements = [];
const summary = {classList: {toggle() {}}};
const list = {classList: {add() {}}};
const bar = {classList: {remove() {}},
    querySelector(selector) {return selector === '.schedules-bar-summary' ? summary : elements[0] || null;},
    appendChild(item) {elements.push(item);}};
const context = {
    schedulesList: [{id: 'retained', prompt: 'Cached data'}], scheduleLoadError: '',
    renderSchedulesBar() {},
    document: {
        getElementById() {return list;},
        createElement() {return {style: {}, attributes: {},
            setAttribute(k, v) {this.attributes[k] = v;},
            remove() {elements.splice(elements.indexOf(this), 1);}};},
    },
};
vm.createContext(context);
vm.runInContext(extract('applyScheduleSnapshot') + '\n' + extract('renderScheduleStorageError'), context);
context.applyScheduleSnapshot({error: '<script>Storage unavailable</script>'});
assert.equal(context.schedulesList[0].id, 'retained');
assert.equal(context.renderScheduleStorageError(bar), true);
assert.equal(elements.length, 1);
assert.equal(elements[0].attributes.role, 'alert');
assert.equal(elements[0].textContent, '<script>Storage unavailable</script>');
assert.equal(elements[0].innerHTML, undefined);
context.renderScheduleStorageError(bar);
assert.equal(elements.length, 1, 'Repeated error renders reuse one alert');
context.applyScheduleSnapshot({data: [{id: 'healthy'}]});
assert.equal(context.renderScheduleStorageError(bar), false);
assert.equal(elements.length, 0);
assert.equal(context.schedulesList[0].id, 'healthy');
assert.equal(context.scheduleLoadError, '');
console.log(JSON.stringify({cases: 2, failures: 0, evidence: 'actual_extracted_functions_vm_only'}));
