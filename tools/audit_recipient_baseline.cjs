// Characterize the real composer function with a fake DOM and WebSocket.
// No browser/server/provider is started. Expected baseline behavior is a defect.
const fs = require('fs');
const source = fs.readFileSync(require('path').join(__dirname, '../static/chat.js'), 'utf8');
const start = source.indexOf('function sendMessage() {');
const end = source.indexOf('// --- Image paste/drop ---', start);
if (start < 0 || end < start) throw new Error('Composer boundaries changed; inspect before updating audit');
const input = {value: '@claude review this', style: {}, focus() {}};
const document = {getElementById() { return input; }};
const activeMentions = new Set(['claude', 'codex', 'glm']);
const pendingAttachments = [];
const username = 'test', activeChannel = 'general', replyingTo = null;
const WebSocket = {OPEN: 1};
let captured;
const ws = {readyState: 1, send(payload) { captured = JSON.parse(payload); }};
const restartVoiceAfterEdit = () => {}, clearAttachments = () => {};
const cancelReply = () => {}, updateSendButton = () => {};
eval(source.slice(start, end) + '\nsendMessage();');
if (captured.text !== '@codex @glm @claude review this') throw new Error('Baseline behavior changed');
console.log(JSON.stringify({id: 'E10', input: '@claude review this',
  selected: ['claude', 'codex', 'glm'], actual: captured.text}));
