(function () {
  var AGENT_ID = 'golfsuite-wiki-assistant';
  var BASE_URL = window.location.origin;
  var MAX_RETRIES = 2;
  var RETRY_DELAY = 2500;
  var STORAGE_SESSIONS = 'ws_sessions';
  var STORAGE_CURRENT = 'ws_current';
  var STORAGE_PREFIX = 'ws_conv_';
  var loading = false;
  var panelsOpen = false;

  function safeSet(key, val) { try { localStorage.setItem(key, val); return true; } catch (e) { return false; } }
  function safeRemove(key) { try { localStorage.removeItem(key); } catch (e) {} }

  var Store = {
    getAll: function () { try { return JSON.parse(localStorage.getItem(STORAGE_SESSIONS)) || []; } catch (e) { return []; } },
    saveAll: function (l) { safeSet(STORAGE_SESSIONS, JSON.stringify(l)); },
    getCurId: function () { return localStorage.getItem(STORAGE_CURRENT) || ''; },
    setCurId: function (id) { if (id) safeSet(STORAGE_CURRENT, id); else safeRemove(STORAGE_CURRENT); },
    addSession: function (id, preview) {
      var list = this.getAll();
      list = list.filter(function (s) { return s.id !== id; });
      list.unshift({ id: id, name: '', preview: preview.substring(0, 100), ts: Date.now() });
      if (list.length > 50) list = list.slice(0, 50);
      this.saveAll(list);
    },
    renameSession: function (id, name) { var list = this.getAll(); for (var i = 0; i < list.length; i++) { if (list[i].id === id) { list[i].name = name; break; } } this.saveAll(list); },
    removeSession: function (id) {
      this.saveAll(this.getAll().filter(function (s) { return s.id !== id; }));
      safeRemove(STORAGE_PREFIX + id);
      if (this.getCurId() === id) this.setCurId('');
    },
    getConv: function (id) { try { return JSON.parse(localStorage.getItem(STORAGE_PREFIX + id)) || []; } catch (e) { return []; } },
    saveConv: function (id, m) { safeSet(STORAGE_PREFIX + id, JSON.stringify(m)); },
    addMsgToConv: function (id, role, text, ts) { var msgs = this.getConv(id); msgs.push({ role: role, text: text, ts: ts || Date.now() }); this.saveConv(id, msgs); }
  };

  function init() {
    var link = document.createElement('link');
    link.rel = 'stylesheet'; link.href = BASE_URL + '/static/widget.css';
    document.head.appendChild(link);

    var font = document.createElement('link');
    font.rel = 'stylesheet'; font.href = 'https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap';
    document.head.appendChild(font);

    if (document.getElementById('ws-body')) {
      initFullPage();
    } else {
      initWidget();
    }
  }

  function initFullPage() {
    bindEvents('full');
    loadSessionFromStorage();
  }

  function initWidget() {
    if (document.getElementById('ws-chat-widget')) return;
    var w = document.createElement('div');
    w.id = 'ws-chat-widget';
    w.innerHTML =
      '<button id="ws-btn" aria-label="Apri assistente"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></button>' +
      '<div id="ws-chat">' +
      '<div id="ws-hdr"><div id="ws-hdr-i"><span id="ws-hdr-t">Wiki Assistant</span><span id="ws-hdr-s">Nexxchange</span></div>' +
      '<button id="ws-hdr-btn" aria-label="Sessioni"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg></button>' +
      '<button id="ws-close-btn" aria-label="Chiudi" style="background:rgba(255,255,255,.12);border:none;color:#fff;width:30px;height:30px;border-radius:50%;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:16px">&times;</button></div>' +
      '<div id="ws-panel"><button id="ws-new-btn">+ Nuova chat</button><div id="ws-sess-list"></div></div>' +
      '<div id="ws-body"><div class="m bot">Ciao! Sono Wiki Assistant di GolfSuite. Come posso aiutarti oggi?</div></div>' +
      '<div id="ws-typing"><span class="d"></span><span class="d"></span><span class="d"></span><span class="t">Sto scrivendo...</span></div>' +
      '<div id="ws-err"></div>' +
      '<div id="ws-inp"><input id="ws-inp-field" type="text" placeholder="Scrivi una domanda..." autocomplete="off"><button id="ws-send-btn" aria-label="Invia"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg></button></div>' +
      '</div>';
    document.body.appendChild(w);
    bindEvents('widget');
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && document.getElementById('ws-chat').classList.contains('open')) closeChat(); });
    document.addEventListener('click', function (e) { var chat = document.getElementById('ws-chat'), btn = document.getElementById('ws-btn'); if (chat.classList.contains('open') && !chat.contains(e.target) && e.target !== btn && !btn.contains(e.target)) closeChat(); });
  }

  function bindEvents(mode) {
    document.getElementById('ws-inp-field').addEventListener('keydown', function (e) { if (e.key === 'Enter') send(); });
    document.getElementById('ws-send-btn').addEventListener('click', send);
    document.getElementById('ws-new-btn').addEventListener('click', function (e) { e.stopPropagation(); newChat(); });
    document.getElementById('ws-hdr-btn').addEventListener('click', function (e) { e.stopPropagation(); togglePanel(); });
    if (mode === 'widget') {
      document.getElementById('ws-btn').addEventListener('click', toggle);
      document.getElementById('ws-close-btn').addEventListener('click', toggle);
    }
  }

  function loadSessionFromStorage() {
    var sid = Store.getCurId();
    if (sid) {
      var msgs = Store.getConv(sid);
      if (msgs.length > 0) {
        var body = document.getElementById('ws-body');
        body.innerHTML = '';
        for (var i = 0; i < msgs.length; i++) {
          body.appendChild(renderMsg(msgs[i].role, msgs[i].text, msgs[i].ts));
        }
        if (body.lastChild) body.lastChild.scrollIntoView({ block: 'end' });
      }
    }
  }

  function closeChat() {
    document.getElementById('ws-chat').classList.remove('open');
    document.getElementById('ws-panel').classList.remove('open');
    panelsOpen = false;
  }

  function toggle() {
    var chat = document.getElementById('ws-chat');
    chat.classList.toggle('open');
    if (chat.classList.contains('open')) { renderSessions(); setTimeout(function () { document.getElementById('ws-inp-field').focus(); }, 300); }
    else { document.getElementById('ws-panel').classList.remove('open'); panelsOpen = false; }
  }

  function togglePanel() {
    panelsOpen = !panelsOpen;
    document.getElementById('ws-panel').classList.toggle('open', panelsOpen);
    if (panelsOpen) renderSessions();
  }

  function renderSessions() {
    var list = Store.getAll(), el = document.getElementById('ws-sess-list'), cur = Store.getCurId();
    if (!list.length) { el.innerHTML = '<div style="padding:16px;text-align:center;color:#999;font-size:12px">Nessuna conversazione</div>'; return; }
    var html = '';
    for (var i = 0; i < list.length; i++) {
      var s = list[i], active = s.id === cur ? ' active' : '', label = s.name || s.preview;
      var d = new Date(s.ts), ds = d.toLocaleDateString('it-IT', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      html += '<div class="sess-item' + active + '" data-id="' + s.id + '"><div class="sess-item-i"><div class="sess-item-p" data-switch="1">' + escHtml(label) + '</div><div class="sess-item-t">' + ds + '</div></div><button class="sess-rename" data-rename="' + s.id + '" aria-label="Rinomina">✎</button><button class="sess-del" data-del="' + s.id + '" aria-label="Elimina">&times;</button></div>';
    }
    el.innerHTML = html;
    el.querySelectorAll('[data-switch]').forEach(function (item) { item.addEventListener('click', function () { switchSession(this.closest('[data-id]').getAttribute('data-id')); }); });
    el.querySelectorAll('[data-del]').forEach(function (btn) { btn.addEventListener('click', function (e) { e.stopPropagation(); deleteSession(this.getAttribute('data-del')); }); });
    el.querySelectorAll('[data-rename]').forEach(function (btn) { btn.addEventListener('click', function (e) { e.stopPropagation(); renameSession(this.getAttribute('data-rename')); }); });
  }

  var renamingId = null;
  function renameSession(id) {
    var item = document.querySelector('.sess-item[data-id="' + id + '"]');
    if (!item) return;
    var label = item.querySelector('.sess-item-p'), cur = label.textContent;
    var inp = document.createElement('input');
    inp.className = 'rename-inp'; inp.type = 'text'; inp.value = cur;
    inp.setAttribute('data-orig', cur);
    label.innerHTML = ''; label.appendChild(inp);
    inp.focus(); inp.select();
    renamingId = id;
    inp.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); doSaveRename(id, inp.value); }
      if (e.key === 'Escape') { e.preventDefault(); doCancelRename(id); }
    });
    inp.addEventListener('blur', function () { doSaveRename(id, inp.value); });
  }
  function doSaveRename(id, val) {
    if (renamingId !== id) return;
    val = val.trim();
    if (!val) { doCancelRename(id); return; }
    Store.renameSession(id, val);
    renamingId = null;
    renderSessions();
  }
  function doCancelRename(id) {
    if (renamingId !== id) return;
    renamingId = null;
    renderSessions();
  }

  function newChat() {
    Store.setCurId('');
    document.getElementById('ws-body').innerHTML = '<div class="m bot">Ciao! Sono Wiki Assistant di GolfSuite. Come posso aiutarti oggi?</div>';
    document.getElementById('ws-panel').classList.remove('open'); panelsOpen = false;
    renderSessions();
    document.getElementById('ws-inp-field').focus();
  }

  function switchSession(id) {
    Store.setCurId(id);
    var msgs = Store.getConv(id), body = document.getElementById('ws-body');
    body.innerHTML = '';
    if (msgs.length === 0) body.innerHTML = '<div class="m bot">Ciao! Sono Wiki Assistant di GolfSuite. Come posso aiutarti oggi?</div>';
    else {
      for (var i = 0; i < msgs.length; i++) {
        body.appendChild(renderMsg(msgs[i].role, msgs[i].text, msgs[i].ts));
      }
      if (body.lastChild) body.lastChild.scrollIntoView({ block: 'end' });
    }
    document.getElementById('ws-panel').classList.remove('open'); panelsOpen = false;
    renderSessions();
    document.getElementById('ws-inp-field').focus();
  }

  function deleteSession(id) { var cur = Store.getCurId(); Store.removeSession(id); if (cur === id) newChat(); else renderSessions(); }

  function formatTime(ts) {
    if (!ts) return '';
    var diff = (Date.now() - ts) / 1000;
    if (diff < 5) return 'ora';
    if (diff < 60) return Math.round(diff) + 's';
    if (diff < 3600) return Math.round(diff / 60) + 'min';
    if (diff < 86400) return Math.round(diff / 3600) + 'h';
    return new Date(ts).toLocaleDateString('it-IT', { day: 'numeric', month: 'short' });
  }

  function renderMsg(role, text, ts) {
    var div = document.createElement('div');
    div.className = 'm ' + role;
    div.innerHTML = (role === 'bot' ? renderMarkdown(text) : escHtml(text)) + '<div class="m-t">' + formatTime(ts) + '</div>';
    if (role === 'bot') addCopyButtons(div);
    return div;
  }

  function addCopyButtons(el) {
    var blocks = el.querySelectorAll('pre');
    blocks.forEach(function (pre) {
      var btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.textContent = 'Copia';
      pre.style.position = 'relative';
      pre.appendChild(btn);
      btn.addEventListener('click', function () {
        var code = pre.querySelector('code');
        if (!code) return;
        navigator.clipboard.writeText(code.textContent).then(function () {
          btn.textContent = 'Copiato!';
          btn.classList.add('copied');
          setTimeout(function () { btn.textContent = 'Copia'; btn.classList.remove('copied'); }, 2000);
        });
      });
    });
  }

  function addMsg(text, role, ts) {
    var body = document.getElementById('ws-body'), div = renderMsg(role, text, ts);
    body.appendChild(div);
    div.scrollIntoView({ behavior: 'smooth', block: 'end' });
    return div;
  }

  function send() {
    var input = document.getElementById('ws-inp-field'), text = input.value.trim();
    if (!text || loading) return;
    input.value = '';
    addMsg(text, 'user', Date.now());
    showTyping(true);
    showError('');
    var sid = Store.getCurId(), retries = 0, botTs = Date.now();
    var streamMsg = null, streamText = '';

    function attempt() {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', BASE_URL + '/agents/' + AGENT_ID + '/runs', true);
      xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');

      xhr.onreadystatechange = function () {
        if (xhr.readyState >= 3 && streamMsg === null) {
          showTyping(false);
          streamMsg = addMsg('', 'bot', botTs);
        }
        if (xhr.readyState >= 3) {
          var data = parseSSE(xhr.responseText);
          if (data.content && data.content !== streamText) {
            streamText = data.content;
            streamMsg.innerHTML = renderMarkdown(streamText) + '<div class="m-t">' + formatTime(botTs) + '</div>';
            streamMsg.scrollIntoView({ behavior: 'smooth', block: 'end' });
          }
          if (data.session_id) {
            if (streamMsg) addCopyButtons(streamMsg);
            Store.setCurId(data.session_id);
            Store.addSession(data.session_id, text);
            Store.addMsgToConv(data.session_id, 'user', text, Date.now());
            Store.addMsgToConv(data.session_id, 'bot', streamText || data.content, botTs);
            renderSessions();
          }
        }
        if (xhr.readyState === 4) {
          showTyping(false);
          if (xhr.status !== 200) {
            if (retries < MAX_RETRIES) { retries++; setTimeout(attempt, RETRY_DELAY); }
            else showError('Errore di connessione. Riprova.');
          } else if (!streamText) {
            addMsg('Scusa, non ho trovato informazioni. Prova a riformulare.', 'bot', Date.now());
          }
        }
      };
      xhr.onerror = function () { if (retries < MAX_RETRIES) { retries++; setTimeout(attempt, RETRY_DELAY); } else { showTyping(false); showError('Errore di connessione. Riprova.'); } };
      var params = 'message=' + encodeURIComponent(text);
      if (sid) params += '&session_id=' + encodeURIComponent(sid);
      xhr.send(params);
    }
    attempt();
  }

  function parseSSE(raw) {
    var result = { content: '', session_id: '' };
    var lines = raw.split('\n');
    for (var i = 0; i < lines.length; i++) {
      if (lines[i].startsWith('data: ')) {
        try { var d = JSON.parse(lines[i].slice(6)); if (d.event && d.event.toLowerCase().indexOf('runcompleted') >= 0 || d.event && d.event.toLowerCase().indexOf('complete') >= 0) { if (d.content) result.content = d.content.trim(); if (d.session_id) result.session_id = d.session_id; } } catch (_) {}
      }
    }
    return result;
  }

  function showTyping(show) { loading = show; document.getElementById('ws-typing').style.display = show ? 'flex' : 'none'; document.getElementById('ws-send-btn').disabled = show; }
  function showError(msg) { var el = document.getElementById('ws-err'); el.textContent = msg; el.style.display = msg ? 'block' : 'none'; }
  function escHtml(t) { return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

  function renderMarkdown(text) {
    var html = escHtml(text)
      .replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" loading="lazy">')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em>$1</em>');
    if (html.includes('\n\n')) { var parts = html.split('\n\n'); html = parts.map(function (p) { return '<p>' + p.replace(/\n/g, '<br>') + '</p>'; }).join(''); }
    else { html = '<p>' + html.replace(/\n/g, '<br>') + '</p>'; }
    return html;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
