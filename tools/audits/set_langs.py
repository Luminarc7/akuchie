import gzip, json, sys, collections
c_set = collections.defaultdict(collections.Counter)
for line in gzip.open(sys.argv[1]):
    if not line.strip(): continue
    c = json.loads(line)
    c_set[c['set']][c['lang']] += 1
json.dump({s: dict(v) for s, v in c_set.items()}, open(sys.argv[2], 'w'), indent=0)
