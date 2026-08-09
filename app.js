'use strict';

/*
 * Restaurant picker.
 *
 * Reads three files out of this repo and does everything in the browser:
 *   config.json           the knobs
 *   data/restaurants.yaml the list
 *   data/history.csv      where we've already been
 *
 * Nothing is written back. Recording a result is a human committing one line
 * to history.csv — see RUNBOOK.md.
 */

var CAP_MONTHS = 60; // treat "never visited" and "5+ years ago" the same

var DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

// Spelled out for poll answers. "Thu" is fine in a filter you're looking at;
// it's terse in a poll somebody reads on their phone.
var DAY_NAMES = {
  Mon: 'Monday', Tue: 'Tuesday', Wed: 'Wednesday', Thu: 'Thursday',
  Fri: 'Friday', Sat: 'Saturday', Sun: 'Sunday'
};

var state = {
  config: null,
  restaurants: [],
  history: [],
  byId: {},
  month: null,
  nonce: 0,
  days: [],            // day filter; empty means any day
  specials: 'exclude', // exclude | include | only

  // The winner. Announce and Record are separate tabs weeks apart but they
  // need the same two answers, so the selectors on both are views onto this.
  choice: { month: null, id: '', notes: '' }
};

/* ------------------------------------------------------------------ utils */

function el(id) { return document.getElementById(id); }

function repoUrl(suffix) {
  return 'https://github.com/' + state.config.repo + (suffix ? '/' + suffix : '');
}

function text(s) { return document.createTextNode(s == null ? '' : String(s)); }

function fetchText(url) {
  return fetch(url, { cache: 'no-store' }).then(function (r) {
    if (!r.ok) throw new Error(url + ' returned HTTP ' + r.status);
    return r.text();
  });
}

// Your files win; the shipped examples are the fallback. A fresh fork works
// straight away showing the demo, and adding your own data is what switches
// it over. Nothing has to be deleted — see "the contract" in the README.
var usedFallback = [];

function fetchWithFallback(preferred, fallback) {
  return fetchText(preferred).catch(function () {
    usedFallback.push(preferred);
    return fetchText(fallback);
  });
}

// Those probes show up as 404s in the console, which looks alarming and isn't.
// Say so, right next to them, so nobody files it as a bug.
function explainFallbacks() {
  if (!usedFallback.length) return;
  console.info(
    'Restaurant Picker: running on the bundled example data. The ' +
    usedFallback.length + ' preceding 404s are expected — this site looks for ' +
    usedFallback.join(', ') + ' first and falls back to the examples when ' +
    'they are absent. Run scripts/setup.py to make it yours.');
}

// Which GitHub repo the "edit this file" buttons should point at. On Pages the
// URL is https://<owner>.github.io/<repo>/, so we can work it out rather than
// making every forker remember to change a config value — getting that wrong
// used to send people to somebody else's repo, and it failed silently.
function detectRepo(cfg) {
  if (cfg && cfg.repo) return cfg.repo;            // explicit override wins
  var host = location.hostname.match(/^([^.]+)\.github\.io$/);
  var path = location.pathname.split('/').filter(Boolean);
  if (host && path.length) return host[1] + '/' + path[0];
  return null;                                      // running locally
}

// Two-digit-safe month arithmetic on "YYYY-MM" strings.
function monthToIndex(m) {
  var parts = String(m).split('-');
  return parseInt(parts[0], 10) * 12 + (parseInt(parts[1], 10) - 1);
}

function indexToMonth(i) {
  var y = Math.floor(i / 12);
  var m = (i % 12) + 1;
  return y + '-' + String(m).padStart(2, '0');
}

function currentMonth() {
  var d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
}

function monthLabel(m) {
  var parts = String(m).split('-');
  var names = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
               'August', 'September', 'October', 'November', 'December'];
  return names[parseInt(parts[1], 10) - 1] + ' ' + parts[0];
}

// The state or region to tack onto a map search. Only used when a restaurant
// has no address, where the link has to fall back to searching the name and
// area — and a bare area name is ambiguous. "mapsRegion" covers one group in
// one state; "areaRegions" is for a patch that straddles a border, where a
// couple of areas sit on the other side of the line.
function regionFor(area) {
  var overrides = state.config.areaRegions || {};
  if (Object.prototype.hasOwnProperty.call(overrides, area)) {
    return String(overrides[area] || '');
  }
  return String(state.config.mapsRegion || '');
}

function mapsUrl(r) {
  var q;
  if (r.address) {
    q = r.name + ', ' + r.address;
  } else {
    var region = regionFor(r.area);
    q = r.name + ', ' + r.area + (region ? ', ' + region : '');
  }
  return 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(q);
}

// Names are just the restaurant's name — where it is comes from area and
// address, so chains with two branches are told apart by those, not by a
// parenthetical in the name.
function whereLine(r) {
  return r.address ? r.address : r.area;
}

/* --------------------------------------------------------- seeded randomness
 * Seeded from the month, so everyone who loads the page in a given month sees
 * the same three candidates. Rerolling bumps a visible nonce, which makes a
 * reroll a deliberate and disclosed act rather than a quiet one.
 */

function hashString(str) {
  var h = 1779033703 ^ str.length;
  for (var i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return (h ^ (h >>> 16)) >>> 0;
}

function mulberry32(seed) {
  var a = seed >>> 0;
  return function () {
    a = (a + 0x6D2B79F5) >>> 0;
    var t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Pick k distinct items, chance of being picked proportional to weight.
function weightedSample(items, weightOf, k, rng) {
  var pool = items.slice();
  var out = [];
  while (out.length < k && pool.length > 0) {
    var total = 0, i;
    for (i = 0; i < pool.length; i++) total += Math.max(weightOf(pool[i]), 0.0001);
    var roll = rng() * total;
    var chosen = pool.length - 1;
    for (i = 0; i < pool.length; i++) {
      roll -= Math.max(weightOf(pool[i]), 0.0001);
      if (roll <= 0) { chosen = i; break; }
    }
    out.push(pool[chosen]);
    pool.splice(chosen, 1);
  }
  return out;
}

/* -------------------------------------------------------------- CSV parsing
 * history.csv only. Handles quoted fields so a note with a comma is safe.
 */

function parseCSV(txt) {
  var rows = [];
  var row = [];
  var field = '';
  var inQuotes = false;
  txt = txt.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  for (var i = 0; i < txt.length; i++) {
    var c = txt[i];
    if (inQuotes) {
      if (c === '"') {
        if (txt[i + 1] === '"') { field += '"'; i++; } else { inQuotes = false; }
      } else { field += c; }
    } else if (c === '"') {
      inQuotes = true;
    } else if (c === ',') {
      row.push(field); field = '';
    } else if (c === '\n') {
      row.push(field); field = '';
      if (row.length > 1 || row[0] !== '') rows.push(row);
      row = [];
    } else {
      field += c;
    }
  }
  row.push(field);
  if (row.length > 1 || row[0] !== '') rows.push(row);
  return rows;
}

function csvEscape(v) {
  v = v == null ? '' : String(v);
  return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
}

/* ------------------------------------------------------------------ loading */

function loadAll() {
  return Promise.all([
    fetchWithFallback('config.json', 'config.example.json'),
    fetchWithFallback('data/restaurants.yaml', 'data/example/restaurants.yaml'),
    fetchWithFallback('data/history.csv', 'data/example/history.csv')
  ]).then(function (res) {
    explainFallbacks();
    state.config = JSON.parse(res[0]);
    state.config.repo = detectRepo(state.config);

    var doc = jsyaml.load(res[1]);
    if (!doc || !Array.isArray(doc.restaurants)) {
      throw new Error('data/restaurants.yaml must start with "restaurants:" ' +
                      'followed by a list of entries.');
    }
    state.restaurants = doc.restaurants.map(function (r) {
      return {
        id: String(r.id || '').trim(),
        name: String(r.name || '').trim(),
        area: String(r.area || '').trim(),
        address: r.address ? String(r.address).trim() : '',
        cuisine: r.cuisine ? String(r.cuisine).trim() : '',
        notes: r.notes ? String(r.notes).trim() : '',
        // null means "we don't know the hours" — treated as open every day
        openDays: r.open_days ? String(r.open_days).trim().split(/\s+/) : null,
        category: r.category === 'special' ? 'special' : 'normal',
        active: r.active !== false && r.active !== 'no'
      };
    });

    state.byId = {};
    state.restaurants.forEach(function (r) { state.byId[r.id] = r; });

    var rows = parseCSV(res[2]);
    state.history = rows.slice(1)
      .filter(function (row) { return row[0] && row[0].trim(); })
      .map(function (row) {
        return {
          month: (row[0] || '').trim(),
          id: (row[1] || '').trim(),
          notes: (row[2] || '').trim()
        };
      })
      .sort(function (a, b) { return a.month < b.month ? -1 : 1; });
  });
}

// Problems that are worth shouting about but shouldn't stop the page working.
function dataWarnings() {
  var w = [];
  var seen = {};
  state.restaurants.forEach(function (r) {
    if (!r.id) w.push('An entry is missing an id.');
    else if (seen[r.id]) w.push('Duplicate id "' + r.id + '" in restaurants.yaml.');
    seen[r.id] = true;
    if (!r.name) w.push('Entry "' + r.id + '" is missing a name.');
    if (state.config.areas.indexOf(r.area) === -1) {
      w.push('Entry "' + r.id + '" has area "' + r.area + '", which is not in ' +
             'the areas list in config.json.');
    }
  });
  state.history.forEach(function (h) {
    if (!state.byId[h.id]) {
      w.push('history.csv row ' + h.month + ' points at "' + h.id +
             '", which is not in restaurants.yaml.');
    }
    if (!/^\d{4}-\d{2}$/.test(h.month)) {
      w.push('history.csv has month "' + h.month + '"; it should look like 2026-08.');
    }
  });
  return w;
}

/* --------------------------------------------------------------- the picking */

function gapForRestaurant(id, month) {
  var last = null;
  state.history.forEach(function (h) {
    if (h.id === id && h.month < month) { if (!last || h.month > last) last = h.month; }
  });
  if (!last) return { gap: CAP_MONTHS, last: null };
  return { gap: Math.min(monthToIndex(month) - monthToIndex(last), CAP_MONTHS), last: last };
}

function gapForArea(area, month) {
  var last = null;
  state.history.forEach(function (h) {
    var r = state.byId[h.id];
    if (r && r.area === area && h.month < month) {
      if (!last || h.month > last) last = h.month;
    }
  });
  if (!last) return { gap: CAP_MONTHS, last: null };
  return { gap: Math.min(monthToIndex(month) - monthToIndex(last), CAP_MONTHS), last: last };
}

// Open on at least one of the days currently selected. We poll for the day
// and the place together, so a restaurant that works on any candidate day is
// a fair option — the poll sorts out the combination. Unknown hours count as
// open, so a half-filled open_days column never silently hides places.
function openOnSelectedDays(r) {
  if (state.days.length === 0 || !r.openDays) return true;
  return state.days.some(function (d) { return r.openDays.indexOf(d) !== -1; });
}

function matchesSpecialsFilter(r) {
  if (state.specials === 'only') return r.category === 'special';
  if (state.specials === 'include') return true;
  return r.category !== 'special';
}

function eligibleIn(area, month, restCooldown) {
  return state.restaurants.filter(function (r) {
    return r.active && r.area === area &&
           openOnSelectedDays(r) && matchesSpecialsFilter(r) &&
           gapForRestaurant(r.id, month).gap >= restCooldown;
  });
}

// How many places the day filter alone is costing us — used to explain a
// thin draw rather than blaming the cooldowns for it.
function hiddenByDayFilter() {
  if (state.days.length === 0) return 0;
  return state.restaurants.filter(function (r) {
    return r.active && matchesSpecialsFilter(r) && !openOnSelectedDays(r);
  }).length;
}

function pick(month, nonce) {
  var cfg = state.config;
  var want = cfg.candidatesPerMonth;
  var areaCd = cfg.areaCooldownMonths;
  var restCd = cfg.restaurantCooldownMonths;
  var rng = mulberry32(hashString(month + '#' + nonce));
  var notes = [];

  // Relax the cooldowns a step at a time if they leave us short on options.
  var areas = [];
  for (;;) {
    areas = cfg.areas.filter(function (a) {
      return gapForArea(a, month).gap >= areaCd &&
             eligibleIn(a, month, restCd).length > 0;
    });
    if (areas.length >= want) break;
    if (areaCd > 0) { areaCd--; continue; }
    if (restCd > 0) { restCd--; continue; }
    break;
  }
  if (areaCd < cfg.areaCooldownMonths) {
    notes.push('Not enough areas were off cooldown, so the area cooldown was ' +
               'relaxed from ' + cfg.areaCooldownMonths + ' to ' + areaCd +
               ' month(s) for this draw.');
  }
  if (restCd < cfg.restaurantCooldownMonths) {
    notes.push('Not enough restaurants were off cooldown, so the restaurant ' +
               'cooldown was relaxed from ' + cfg.restaurantCooldownMonths +
               ' to ' + restCd + ' month(s) for this draw. Time to add some ' +
               'more places to the list.');
  }

  var hidden = hiddenByDayFilter();
  if (hidden > 0 && (areas.length < want || notes.length > 0)) {
    notes.push('The day filter (' + state.days.join(', ') + ') is ruling out ' +
               hidden + ' otherwise eligible restaurant' +
               (hidden === 1 ? '' : 's') + ', which is part of why the choice ' +
               'is thin. Places with no hours recorded are assumed open.');
  }
  if (state.specials === 'only') {
    notes.push('Showing special occasion places only. These are deliberately ' +
               'outside the normal rotation, so the usual cooldowns matter less.');
  }

  var exp = cfg.areaWeightExponent || 2;
  var chosenAreas = weightedSample(areas, function (a) {
    return Math.pow(gapForArea(a, month).gap, exp);
  }, want, rng);

  var picks = [];
  var used = {};
  chosenAreas.forEach(function (a) {
    var opts = eligibleIn(a, month, restCd).filter(function (r) { return !used[r.id]; });
    var got = weightedSample(opts, function (r) {
      return gapForRestaurant(r.id, month).gap;
    }, 1, rng)[0];
    if (got) { picks.push(got); used[got.id] = true; }
  });

  // Fewer areas available than slots: top up from the areas we already drew.
  if (picks.length < want) {
    var leftovers = [];
    chosenAreas.forEach(function (a) {
      eligibleIn(a, month, restCd).forEach(function (r) {
        if (!used[r.id]) leftovers.push(r);
      });
    });
    var extra = weightedSample(leftovers, function (r) {
      return gapForRestaurant(r.id, month).gap;
    }, want - picks.length, rng);
    extra.forEach(function (r) { picks.push(r); used[r.id] = true; });
    if (extra.length > 0) {
      notes.push('There were not enough distinct areas available, so more than ' +
                 'one candidate came from the same area.');
    }
  }

  return { picks: picks, notes: notes, areaCooldownUsed: areaCd, restCooldownUsed: restCd };
}

/* ------------------------------------------------------------------ rendering */

// Discord's limits: 300 characters for the question, 55 for each answer.
var POLL_QUESTION_MAX = 300;
var POLL_ANSWER_MAX = 55;

// Kept as the fallback so a config written before this was configurable still
// produces exactly what it used to.
var DEFAULT_POLL_QUESTION = '{group} — {monthYear} meetup. Where should we eat?';
var DEFAULT_DAY_POLL_QUESTION = '{group} — {monthYear}. Which day suits?';

function pollQuestion(month) {
  return fillTemplate(state.config.pollQuestionTemplate || DEFAULT_POLL_QUESTION,
                      null, month);
}

function dayPollQuestion(month) {
  return fillTemplate(
    state.config.dayPollQuestionTemplate || DEFAULT_DAY_POLL_QUESTION,
    null, month);
}

// Whether the group settles the day by poll before settling the place. Some
// do, some just declare it. Default on; it's the more careful sequence.
function dayPollEnabled() {
  return state.config.dayPoll !== false;
}

// How many places a given day is worth, so nobody offers a day the group
// can't actually eat on. Deliberately ignores cooldowns: this is about which
// days are viable at all, not who is due a visit.
function placesOpenOn(day) {
  return state.restaurants.filter(function (r) {
    return r.active && matchesSpecialsFilter(r) &&
           (!r.openDays || r.openDays.indexOf(day) !== -1);
  }).length;
}

// Answers can't hold an address and stay under 55 characters, so they carry
// the area instead. Names that are long enough to blow the limit on their own
// get trimmed rather than silently rejected by Discord.
function pollAnswer(r) {
  var withArea = r.name + ' — ' + r.area;
  if (withArea.length <= POLL_ANSWER_MAX) return withArea;
  if (r.name.length <= POLL_ANSWER_MAX) return r.name;
  return r.name.slice(0, POLL_ANSWER_MAX - 1) + '…';
}

// The follow-up message, where links and addresses are allowed.
function pollText(result, month) {
  var lines = [];
  lines.push(pollQuestion(month));
  lines.push('');
  result.picks.forEach(function (r, i) {
    lines.push((i + 1) + '. ' + r.name + ' — ' + whereLine(r));
    lines.push('   ' + mapsUrl(r));
  });
  return lines.join('\n');
}

// Step 1: the poll that settles which day. Its answers are the days ticked in
// the Days dropdown, so the one control drives both polls — you tick several
// for this, then tick only the winner for step 2.
function renderDayPoll() {
  var on = dayPollEnabled();
  el('dayPollStep').hidden = !on;
  el('placePollHeading').textContent = on ? 'Step 2 — poll the place'
                                          : 'Make the poll';
  el('placePollIntro').hidden = !on;
  if (!on) return;

  var q = dayPollQuestion(state.month);
  el('dayPollQuestion').value = q;
  el('dayQuestionCount').textContent = q.length + '/' + POLL_QUESTION_MAX;

  var box = el('dayPollAnswers');
  box.innerHTML = '';

  var offered = state.days.length ? state.days : [];
  offered.forEach(function (d, i) {
    var value = DAY_NAMES[d];
    var id = 'dayPollAns' + i;
    var open = placesOpenOn(d);

    var label = document.createElement('label');
    label.setAttribute('for', id);
    label.appendChild(text('Answer ' + (i + 1)));
    box.appendChild(label);

    var row = document.createElement('div');
    row.className = 'copyrow';

    var input = document.createElement('input');
    input.type = 'text';
    input.id = id;
    input.readOnly = true;
    input.value = value;
    row.appendChild(input);

    var count = document.createElement('span');
    count.className = open === 0 ? 'count over' : 'count';
    count.appendChild(text(open + ' open'));
    row.appendChild(count);

    var btn = document.createElement('button');
    btn.className = 'secondary';
    btn.appendChild(text('Copy'));
    btn.onclick = function () { copyFrom(id, btn); };
    row.appendChild(btn);

    box.appendChild(row);
  });

  var hint = el('dayPollHint');
  hint.className = 'hint';
  if (!offered.length) {
    hint.textContent = 'No days ticked yet, so there are no answers to give ' +
      'Discord. Open the Days dropdown at the top and tick the ones you\'re ' +
      'willing to offer.';
  } else if (offered.some(function (d) { return placesOpenOn(d) === 0; })) {
    hint.className = 'warn';
    hint.textContent = 'One of the days you\'re offering has nothing open. If ' +
      'it wins, you\'ll have nowhere to go — untick it before you post.';
  } else {
    hint.textContent = 'Post this first. When it closes, come back and tick ' +
      'only the winning day.';
  }
}

function renderPick() {
  var month = state.month;
  var result = pick(month, state.nonce);

  renderDayPoll();

  el('pickMonthLabel').textContent = monthLabel(month);
  el('nonceLabel').textContent = state.nonce === 0
    ? 'first draw for this month'
    : 'reroll #' + state.nonce;

  var box = el('candidates');
  box.innerHTML = '';
  result.picks.forEach(function (r, i) {
    var card = document.createElement('div');
    card.className = 'card';

    var num = document.createElement('div');
    num.className = 'num';
    num.appendChild(text(i + 1));
    card.appendChild(num);

    var body = document.createElement('div');
    body.className = 'body';

    var h = document.createElement('h3');
    h.appendChild(text(r.name));
    body.appendChild(h);

    var meta = document.createElement('div');
    meta.className = 'meta';
    meta.appendChild(text(r.area + (r.cuisine ? ' · ' + r.cuisine : '')));
    body.appendChild(meta);

    if (r.address) {
      var addr = document.createElement('div');
      addr.className = 'addr';
      addr.appendChild(text(r.address));
      body.appendChild(addr);
    } else {
      var missing = document.createElement('div');
      missing.className = 'addr missing';
      missing.appendChild(text('no address on file — please add one'));
      body.appendChild(missing);
    }

    var g = gapForRestaurant(r.id, month);
    var hist = document.createElement('div');
    hist.className = 'hist';
    hist.appendChild(text(g.last ? 'last visited ' + monthLabel(g.last)
                                 : 'never been here'));
    body.appendChild(hist);

    if (r.notes) {
      var n = document.createElement('div');
      n.className = 'note';
      n.appendChild(text(r.notes));
      body.appendChild(n);
    }

    var a = document.createElement('a');
    a.className = 'maplink';
    a.href = mapsUrl(r);
    a.target = '_blank';
    a.rel = 'noopener';
    a.appendChild(text('Open in Google Maps'));
    body.appendChild(a);

    card.appendChild(body);
    box.appendChild(card);
  });

  var noteBox = el('pickNotes');
  noteBox.innerHTML = '';
  result.notes.forEach(function (n) {
    var p = document.createElement('p');
    p.className = 'warn';
    p.appendChild(text(n));
    noteBox.appendChild(p);
  });

  var q = pollQuestion(month);
  el('pollQuestion').value = q;
  el('questionCount').textContent = q.length + '/' + POLL_QUESTION_MAX;

  var answers = el('pollAnswers');
  answers.innerHTML = '';
  result.picks.forEach(function (r, i) {
    var value = pollAnswer(r);
    var id = 'pollAns' + i;

    var label = document.createElement('label');
    label.setAttribute('for', id);
    label.appendChild(text('Answer ' + (i + 1)));
    answers.appendChild(label);

    var row = document.createElement('div');
    row.className = 'copyrow';

    var input = document.createElement('input');
    input.type = 'text';
    input.id = id;
    input.readOnly = true;
    input.value = value;
    row.appendChild(input);

    var count = document.createElement('span');
    count.className = 'count';
    if (value.length > POLL_ANSWER_MAX) count.className += ' over';
    count.appendChild(text(value.length + '/' + POLL_ANSWER_MAX));
    row.appendChild(count);

    var btn = document.createElement('button');
    btn.className = 'secondary';
    btn.appendChild(text('Copy'));
    btn.onclick = function () { copyFrom(id, btn); };
    row.appendChild(btn);

    answers.appendChild(row);
  });

  el('pollText').value = pollText(result, month);
}

// Announce and Record each carry a copy of the month + winner selector.
var CHOICE_TABS = ['announce', 'record'];

function fillWinnerSelect(sel) {
  sel.innerHTML = '';
  var blank = document.createElement('option');
  blank.value = '';
  blank.appendChild(text('— choose the winner —'));
  sel.appendChild(blank);

  state.config.areas.forEach(function (area) {
    var group = document.createElement('optgroup');
    group.label = area;
    state.restaurants
      .filter(function (r) { return r.area === area; })
      .sort(function (a, b) { return a.name < b.name ? -1 : 1; })
      .forEach(function (r) {
        var o = document.createElement('option');
        o.value = r.id;
        o.appendChild(text(r.name + (r.active ? '' : ' (inactive)')));
        group.appendChild(o);
      });
    sel.appendChild(group);
  });
}

// Push state.choice out to both copies of the selector, then redraw whatever
// depends on it. Everything that changes the choice ends here, so the two
// tabs can't drift apart.
function pushChoice() {
  CHOICE_TABS.forEach(function (t) {
    el(t + 'Month').value = state.choice.month || '';
    el(t + 'Restaurant').value = state.choice.id;
  });
  el('recordNotes').value = state.choice.notes;
  renderChoiceOutputs();
}

function renderRecord() {
  CHOICE_TABS.forEach(function (t) { fillWinnerSelect(el(t + 'Restaurant')); });

  var edit = el('editLink');
  var onGitHub = Boolean(state.config.repo);
  if (onGitHub) {
    edit.href = repoUrl('edit/' + (state.config.branch || 'main') +
                        '/data/history.csv');
  }
  // Everything about committing through GitHub is meaningless when this is
  // being served from a local directory, so the whole set goes together.
  edit.hidden = !onGitHub;
  el('commitHint').hidden = !onGitHub;
  el('editLinkHint').hidden = onGitHub;

  renderRecent();
  pushChoice();
}

// The last few months, right beside the form that writes them. The full table
// is a tab away, so a skipped month is invisible from the one place someone
// is in a position to fix it — and a skipped month is the documented reason
// the picker repeats itself.
var RECENT_MONTHS = 4;

function renderRecent() {
  var body = el('recentTable').querySelector('tbody');
  body.innerHTML = '';

  if (state.history.length === 0) {
    var tr0 = document.createElement('tr');
    var td0 = document.createElement('td');
    td0.colSpan = 2;
    td0.className = 'empty';
    td0.appendChild(text('Nothing recorded yet.'));
    tr0.appendChild(td0);
    body.appendChild(tr0);
    return;
  }

  // Anchor on this month, or later if somebody has recorded ahead.
  var latest = state.history[state.history.length - 1].month;
  var anchor = Math.max(monthToIndex(currentMonth()), monthToIndex(latest));

  var byMonth = {};
  state.history.forEach(function (h) { byMonth[h.month] = h; });

  for (var i = 0; i < RECENT_MONTHS; i++) {
    var idx = anchor - i;
    var m = indexToMonth(idx);
    var h = byMonth[m];
    var tr = document.createElement('tr');

    var tdM = document.createElement('td');
    tdM.appendChild(text(monthLabel(m)));
    tr.appendChild(tdM);

    var tdW = document.createElement('td');
    if (h) {
      var r = state.byId[h.id];
      tdW.appendChild(text(r ? r.name : h.id + ' (unknown)'));
      if (!r) tr.className = 'row-warn';
    } else if (i === 0) {
      // The current month legitimately hasn't happened yet.
      tdW.className = 'empty';
      tdW.appendChild(text('not recorded yet'));
    } else {
      tdW.appendChild(text('not recorded'));
      tr.className = 'row-warn';
    }
    tr.appendChild(tdW);
    body.appendChild(tr);
  }
}

// Fill in the {placeholders} in the templates from config.json.
// A line made up only of placeholders that come out empty — an {address} we
// don't have, say — is dropped rather than left as a blank line.
//
// r is null for templates written before a winner exists, like the poll
// question; the restaurant placeholders simply aren't offered there.
function fillTemplate(tpl, r, month) {
  function subst(s) {
    s = s
      .replace(/\{month\}/g, monthLabel(month).split(' ')[0])
      .replace(/\{monthYear\}/g, monthLabel(month))
      .replace(/\{group\}/g, state.config.groupName);
    if (r) {
      s = s
        .replace(/\{name\}/g, r.name)
        .replace(/\{area\}/g, r.area)
        .replace(/\{address\}/g, r.address || '')
        .replace(/\{maps\}/g, mapsUrl(r));
    }
    return s;
  }
  return String(tpl || '')
    .split('\n')
    .filter(function (line) {
      return line.trim() === '' || subst(line).trim() !== '';
    })
    .map(subst)
    .join('\n');
}

function renderChoiceOutputs() {
  var id = state.choice.id;
  var month = String(state.choice.month || '').trim();
  var notes = state.choice.notes.trim();
  var out = el('recordLine');
  var ready = id && state.byId[id] && /^\d{4}-\d{2}$/.test(month);

  if (!ready) {
    out.value = '';
    out.placeholder = 'Pick a month and a restaurant and the line will appear here.';
    el('eventName').value = '';
    el('eventLocation').value = '';
    el('eventDesc').value = '';
    el('eventDesc').placeholder = 'Pick a month and a restaurant first.';
    return;
  }

  out.value = [csvEscape(month), csvEscape(id), csvEscape(notes)].join(',');

  var r = state.byId[id];
  el('eventName').value = fillTemplate(state.config.eventNameTemplate, r, month);
  el('eventLocation').value = r.name + ', ' + whereLine(r);
  el('eventDesc').value = fillTemplate(state.config.eventDescriptionTemplate, r, month);
}

function renderData() {
  var month = state.month;

  var areaBody = el('areaTable').querySelector('tbody');
  areaBody.innerHTML = '';
  state.config.areas.forEach(function (a) {
    var g = gapForArea(a, month);
    var all = state.restaurants.filter(function (r) { return r.area === a; });
    var normal = all.filter(function (r) { return r.active && r.category === 'normal'; });
    var special = all.filter(function (r) { return r.active && r.category === 'special'; });
    var retired = all.filter(function (r) { return !r.active; });
    var elig = eligibleIn(a, month, state.config.restaurantCooldownMonths);
    var visits = state.history.filter(function (h) {
      var r = state.byId[h.id];
      return r && r.area === a;
    }).length;

    var tr = document.createElement('tr');
    [a,
     normal.length + (retired.length ? ' (+' + retired.length + ' retired)' : ''),
     special.length || '—',
     elig.length,
     visits,
     g.last ? monthLabel(g.last) : 'never',
     g.last ? g.gap + ' mo' : '—'
    ].forEach(function (v, i) {
      var td = document.createElement('td');
      if (i > 0 && i < 5) td.className = 'num-cell';
      td.appendChild(text(v));
      tr.appendChild(td);
    });
    if (elig.length === 0) tr.className = 'row-warn';
    areaBody.appendChild(tr);
  });

  var restBody = el('restTable').querySelector('tbody');
  restBody.innerHTML = '';
  state.restaurants
    .slice()
    .sort(function (a, b) {
      if (a.area !== b.area) {
        return state.config.areas.indexOf(a.area) - state.config.areas.indexOf(b.area);
      }
      return a.name < b.name ? -1 : 1;
    })
    .forEach(function (r) {
      var g = gapForRestaurant(r.id, month);
      var cooled = g.gap >= state.config.restaurantCooldownMonths;
      var eligible = r.active && cooled && openOnSelectedDays(r) &&
                     matchesSpecialsFilter(r);
      var status;
      if (!r.active) status = 'retired';
      else if (!matchesSpecialsFilter(r)) status = 'special occasion';
      else if (!openOnSelectedDays(r)) status = 'shut on a chosen day';
      else if (!cooled) status = 'cooling down';
      else status = 'in the running';
      var tr = document.createElement('tr');

      var tdName = document.createElement('td');
      var link = document.createElement('a');
      link.href = mapsUrl(r);
      link.target = '_blank';
      link.rel = 'noopener';
      link.appendChild(text(r.name));
      tdName.appendChild(link);
      if (r.category === 'special') {
        var sp = document.createElement('span');
        sp.className = 'pill pill-special';
        sp.appendChild(text('special'));
        tdName.appendChild(sp);
      }
      if (!r.address) {
        var flag = document.createElement('span');
        flag.className = 'pill pill-warn';
        flag.appendChild(text('no address'));
        tdName.appendChild(flag);
      }
      tr.appendChild(tdName);

      [r.area,
       r.openDays ? r.openDays.join(' ') : 'not recorded',
       g.last ? monthLabel(g.last) : 'never',
       status
      ].forEach(function (v, i) {
        var td = document.createElement('td');
        if (i === 1 && !r.openDays) td.className = 'muted';
        td.appendChild(text(v));
        tr.appendChild(td);
      });

      if (!r.active) tr.className = 'row-off';
      else if (!eligible) tr.className = 'row-dim';
      restBody.appendChild(tr);
    });

  var histBody = el('histTable').querySelector('tbody');
  histBody.innerHTML = '';
  state.history.slice().reverse().forEach(function (h) {
    var r = state.byId[h.id];
    var tr = document.createElement('tr');
    [monthLabel(h.month), r ? r.name : h.id + ' (unknown)', r ? r.area : '?', h.notes]
      .forEach(function (v) {
        var td = document.createElement('td');
        td.appendChild(text(v));
        tr.appendChild(td);
      });
    if (!r) tr.className = 'row-warn';
    histBody.appendChild(tr);
  });
  if (state.history.length === 0) {
    var tr2 = document.createElement('tr');
    var td2 = document.createElement('td');
    td2.colSpan = 4;
    td2.className = 'empty';
    td2.appendChild(text('No meetups recorded yet. Until there are a few, ' +
                         'every area and restaurant is equally likely.'));
    tr2.appendChild(td2);
    histBody.appendChild(tr2);
  }

  var live = state.restaurants.filter(function (r) { return r.active; });
  el('summary').textContent =
    live.filter(function (r) { return r.category === 'normal'; }).length +
    ' in the normal rotation · ' +
    live.filter(function (r) { return r.category === 'special'; }).length +
    ' special occasion · ' +
    state.restaurants.filter(function (r) { return !r.active; }).length +
    ' retired · ' + state.history.length + ' meetups on record · ' +
    live.filter(function (r) { return !r.openDays; }).length +
    ' with no opening days recorded';
}

function renderAll() {
  renderPick();
  renderRecord();
  renderData();

  var warns = dataWarnings();
  var box = el('warnings');
  box.innerHTML = '';
  box.hidden = warns.length === 0;
  warns.forEach(function (w) {
    var p = document.createElement('p');
    p.appendChild(text(w));
    box.appendChild(p);
  });
}

/* ------------------------------------------------------------------- wiring */

// Build the day checkboxes and keep the button label in step with them.
function buildDayFilter() {
  var box = el('dayBoxes');
  box.innerHTML = '';
  DAYS.forEach(function (d) {
    var label = document.createElement('label');
    var cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.value = d;
    cb.checked = state.days.indexOf(d) !== -1;
    cb.onchange = function () {
      state.days = DAYS.filter(function (day) {
        var found = box.querySelector('input[value="' + day + '"]');
        return found && found.checked;
      });
      state.nonce = 0;
      updateDayLabel();
      renderAll();
    };
    label.appendChild(cb);
    label.appendChild(text(' ' + d));
    box.appendChild(label);
  });
  updateDayLabel();
}

function updateDayLabel() {
  el('dayToggle').textContent = state.days.length === 0
    ? 'Any day'
    : state.days.join(', ');
}

function setDayPanel(open) {
  el('dayPanel').hidden = !open;
  el('dayToggle').setAttribute('aria-expanded', open ? 'true' : 'false');
}

function showTab(name) {
  ['pick', 'announce', 'record', 'data'].forEach(function (t) {
    el('tab-' + t).hidden = (t !== name);
    el('btn-' + t).classList.toggle('active', t === name);
  });
}

function copyFrom(id, button) {
  var field = el(id);
  field.select();
  field.setSelectionRange(0, 99999);
  var done = function () {
    var old = button.textContent;
    button.textContent = 'Copied';
    setTimeout(function () { button.textContent = old; }, 1500);
  };
  if (navigator.clipboard) {
    navigator.clipboard.writeText(field.value).then(done, function () {
      document.execCommand('copy'); done();
    });
  } else {
    document.execCommand('copy'); done();
  }
}

function boot() {
  var params = new URLSearchParams(location.search);
  state.month = /^\d{4}-\d{2}$/.test(params.get('month') || '')
    ? params.get('month') : currentMonth();
  state.choice.month = state.month;

  loadAll().then(function () {
    el('loading').hidden = true;
    el('main').hidden = false;
    el('monthInput').value = state.month;

    document.title = state.config.groupName + ' — Restaurant Picker';
    el('siteTitle').textContent = state.config.groupName + ' Restaurant Picker';

    if (state.config.repo) {
      var branch = state.config.branch || 'main';
      el('editRestaurantsLink').href =
        repoUrl('edit/' + branch + '/data/restaurants.yaml');
      el('sourceLink').href = repoUrl('');
      el('runbookLink').href = repoUrl('blob/' + branch + '/RUNBOOK.md');
      ['sourceLink', 'footerSep', 'runbookLink'].forEach(function (id) {
        el(id).hidden = false;
      });
    } else {
      el('editRestaurantsLink').removeAttribute('href');
    }

    el('btn-pick').onclick = function () { showTab('pick'); };
    el('btn-announce').onclick = function () { showTab('announce'); };
    el('btn-record').onclick = function () { showTab('record'); };
    el('btn-data').onclick = function () { showTab('data'); };

    buildDayFilter();
    el('dayToggle').onclick = function (e) {
      e.stopPropagation();
      setDayPanel(el('dayPanel').hidden);
    };
    el('dayPanel').onclick = function (e) { e.stopPropagation(); };
    document.addEventListener('click', function () { setDayPanel(false); });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') setDayPanel(false);
    });
    el('dayClear').onclick = function () {
      state.days = [];
      state.nonce = 0;
      buildDayFilter();
      renderAll();
    };
    el('specialsSelect').onchange = function () {
      state.specials = this.value;
      state.nonce = 0;
      renderAll();
    };

    el('rerollBtn').onclick = function () { state.nonce++; renderPick(); };
    el('monthInput').onchange = function () {
      if (/^\d{4}-\d{2}$/.test(this.value)) {
        state.month = this.value;
        state.choice.month = this.value;
        state.nonce = 0;
        renderAll();
      }
    };

    el('copyPoll').onclick = function () { copyFrom('pollText', this); };
    el('copyQuestion').onclick = function () { copyFrom('pollQuestion', this); };
    el('copyDayQuestion').onclick = function () { copyFrom('dayPollQuestion', this); };
    el('copyLine').onclick = function () { copyFrom('recordLine', this); };
    el('copyEventName').onclick = function () { copyFrom('eventName', this); };
    el('copyEventLocation').onclick = function () { copyFrom('eventLocation', this); };
    el('copyEventDesc').onclick = function () { copyFrom('eventDesc', this); };

    CHOICE_TABS.forEach(function (t) {
      el(t + 'Month').onchange = function () {
        state.choice.month = this.value;
        pushChoice();
      };
      el(t + 'Restaurant').onchange = function () {
        state.choice.id = this.value;
        pushChoice();
      };
    });
    el('recordNotes').oninput = function () {
      state.choice.notes = this.value;
      renderChoiceOutputs();
    };

    renderAll();
    showTab('pick');
  }).catch(function (err) {
    el('loading').hidden = true;
    var box = el('fatal');
    box.hidden = false;
    var msg = String(err && err.message ? err.message : err);
    el('fatalMsg').textContent = msg;
    if (location.protocol === 'file:') {
      el('fatalHint').hidden = false;
    }
  });
}

document.addEventListener('DOMContentLoaded', boot);
