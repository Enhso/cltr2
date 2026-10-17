# Reproduces the numbers in essay/examples.md, Part 2 (Claude Code rogue reports, Jul-Oct 2025).
# Run: python3 -I spike_2025.py
# Inputs: deep_codes.jsonl, queue.jsonl, deep_cache/ (research dir); weekly_den.csv (GitHub search total_count per
# Monday-Sunday week, repo:anthropics/claude-code is:issue); live_meta_2025.json (live state/labels, reporter ids hashed).
import csv, json, re, collections, datetime
R = '/home/hatim/applications/cltr2/rtc/research/'
H = R + 'essay/spike_2025/'
L = {3, 4, 5}
MONTHS = ['2025-07', '2025-08', '2025-09', '2025-10']
DEN = {'2025-07': 2033, '2025-08': 1942, '2025-09': 1580, '2025-10': 2113}  # denominators.csv, claude-code

deep = {}
for line in open(R + 'deep_codes.jsonl'):
    if line.strip():
        d = json.loads(line)
        deep[d['key']] = d
q = {}
for line in open(R + 'queue.jsonl'):
    r = json.loads(line)
    q[r['key']] = r
live = {d['key']: d for d in json.load(open(H + 'live_meta_2025.json'))}


def keys(month, rogue=None):
    ks = [k for k, r in q.items() if r['repo'] == 'anthropics/claude-code' and r['month'] == month]
    assert all(k in deep for k in ks), 'month not fully deep-coded'
    if rogue is not None:
        ks = [k for k in ks if bool(set(deep[k]['codes']) & L) == rogue]
    return sorted(ks, key=lambda k: q[k]['created_at'])


def text(k):
    c = json.load(open(R + 'deep_cache/' + k.replace('/', '_').replace('#', '_') + '.json'))
    return (c.get('title') or '') + '\n' + (c.get('body') or '')


print('T1 monthly (Claude Code; every keyword match deep-coded)')
print('month | matches | match/1k | rogue | share | rogue/1k | c3 | c4 | c5 | high | med | low | med+high/1k')
for m in MONTHS:
    ks, rg = keys(m), keys(m, True)
    c = collections.Counter(x for k in rg for x in set(deep[k]['codes']) & L)
    cf = collections.Counter(deep[k]['confidence'] for k in rg)
    print(m, len(ks), round(1000 * len(ks) / DEN[m], 1), len(rg), round(len(rg) / len(ks), 3), round(1000 * len(rg) / DEN[m], 1),
          c[3], c[4], c[5], cf['high'], cf['medium'], cf['low'], round(1000 * (cf['high'] + cf['medium']) / DEN[m], 1), sep=' | ')

print('\nT2 weekly (week starting Monday)')
den = {r['week_start']: int(r['total_issues']) for r in csv.DictReader(open(H + 'weekly_den.csv'))}
W = collections.defaultdict(collections.Counter)
for k, r in q.items():
    if r['repo'] != 'anthropics/claude-code' or k not in deep or not ('2025-05-26' <= r['created_at'][:10] <= '2025-11-30'):
        continue
    d0 = datetime.date.fromisoformat(r['created_at'][:10])
    w = (d0 - datetime.timedelta(days=d0.weekday())).isoformat()
    W[w]['matches'] += 1
    if set(deep[k]['codes']) & L:
        W[w]['rogue'] += 1
print('week | issues | matches | rogue | rogue/1k | rogue share of matches')
for w in sorted(den):
    if w >= '2025-06-30' and w <= '2025-11-17':
        c = W[w]
        print(w, den[w], c['matches'], c['rogue'], round(1000 * c['rogue'] / den[w], 1), round(c['rogue'] / c['matches'], 2), sep=' | ')

print('\nT3 reporters and duplicates (reporter ids are hashed)')
print('month | rogue | distinct reporters | dup label/state | extra filing same month | union | independent | independent/1k')
for m in MONTHS:
    rg = keys(m, True)
    first = {}
    for k in rg:
        u = live[k]['reporter_id']
        if u not in first or q[k]['created_at'] < q[first[u]]['created_at']:
            first[u] = k
    dup = {k for k in rg if 'duplicate' in live[k]['labels'] or live[k]['state_reason'] == 'duplicate'}
    extra = {k for k in rg if first[live[k]['reporter_id']] != k}
    ind = len(rg) - len(dup | extra)
    print(m, len(rg), len(first), len(dup), len(extra), len(dup | extra), ind, round(1000 * ind / DEN[m], 1), sep=' | ')

print('\nT4 title/rationale tags (not exclusive)')
TAGS = collections.OrderedDict([
    ('CLAUDE.md or project rules', r"CLAUDE\.?(local\.)?md|project (rule|guideline)|explicit(ly)? (rule|instruction|prohibit)|user-defined rule|documented rule"),
    ('deny/ask rule, permission, plan mode, hook', r"deny|permission|plan mode|ExitPlanMode|approval|ask rule|\bhook|restriction|allowlist"),
    ('false claim / fabrication / fake or mock output', r"\blie[sd]?\b|\blying\b|fabricat|false(ly)?\b|\bfake|\bmock|simulat|hallucinat|misreport|misrepresent|mislead|deceiv|deception|synthetic|claimed|falsif"),
    ('delete / rm / reset / data loss', r"\bdelet|\brm\b|rm -rf|wipe|destroy|git reset|reset --hard|data loss|overwr|restore|lost\b"),
    ('sub-agent / Task tool', r"sub-?agent|Task tool|\bTask\b"),
])
print('tag | ' + ' | '.join(MONTHS))
for t, rx in TAGS.items():
    rx = re.compile(rx, re.I)
    print(t, *[sum(1 for k in keys(m, True) if rx.search(q[k]['title'] + ' || ' + deep[k]['rationale'])) for m in MONTHS], sep=' | ')

print('\nT5 text mentions in title/body (rogue only)')
VER = re.compile(r"(?<![\d.])(1\.0\.\d{1,3}|2\.0\.\d{1,2})(?![\d.])")
MOD = re.compile(r"\b(opus|sonnet|haiku)\b", re.I)
O41 = re.compile(r"opus[\s\-_]*4[\.\-_]?1|claude-opus-4-1", re.I)
FIELD = re.compile(r"### Claude Model\s*\n+\s*([^\n]+)", re.I)
print('month | version string | model name | model name outside template field | Opus 4.1 | structured-template headings | [MODEL] title')
for m in MONTHS:
    rg = keys(m, True)
    v = mo = mo2 = o4 = tp = tm = 0
    for k in rg:
        t = text(k)
        v += bool(VER.search(t))
        mo += bool(MOD.search(t))
        mo2 += bool(MOD.search(FIELD.sub('', t)))
        o4 += bool(O41.search(t))
        tp += bool(re.search(r"### Preflight Checklist|### Type of Behavior Issue|### Claude Model", t))
        tm += q[k]['title'].startswith('[MODEL]')
    print(m, v, mo, mo2, o4, tp, tm, sep=' | ')
