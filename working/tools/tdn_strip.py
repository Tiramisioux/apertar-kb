#!/usr/bin/env python3
"""Copy a libcamera PiSP tuning file with every rpi.denoise "tdn" block (optionally also "sdn" / "cdn") cut out.

Usage:  python3 -I tdn_strip.py [--blocks tdn,sdn,cdn] SRC DST     (stdlib only; never writes SRC)

--blocks LIST   comma-separated subset of tdn,sdn,cdn naming the members to cut (default: tdn). Without it the
                behaviour and output bytes are those of the tdn-only tool. A requested kind that SRC does not
                have is reported; the tool refuses only if nothing at all would be removed.

If every member of a denoise config is removed, the config stays as an empty object (only with --blocks other
than plain tdn; the tdn-only tool refuses a sole member).

Only the bytes of each `, "tdn": {...}` member (likewise sdn / cdn) are removed; every other byte of SRC is kept,
so `diff SRC DST` shows the removed blocks and nothing else. Prints tdn/sdn/cdn per denoise mode before and after. Writes DST
(temp file + fsync + rename) only if:
  - SRC is strict JSON (no duplicate keys, no NaN/Infinity) with "target": "pisp" and an "algorithms" list;
  - DST ends in .json, is not SRC and is not inside a defaults* directory;
  - DST parses as strict JSON and the only key paths that differ from SRC are the removed blocks
    (diff of every leaf path, types included), with 0 keys of each removed kind and the same target and version.
A flat rpi.denoise (no "normal" key; libcamera then reads it as one config) is handled too.
"""
import copy, difflib, json, os, sys, tempfile

WS = " \t\r\n"
ALL_BLOCKS = ("tdn", "sdn", "cdn")


def fail(msg):
    sys.exit("REFUSED: " + msg)


def strict_loads(text, what):
    def pairs(kv):
        d = {}
        for k, v in kv:
            if k in d:
                fail(f"{what}: duplicate key {k!r}")
            d[k] = v
        return d

    def bad(c):
        fail(f"{what}: non-JSON constant {c}")

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=bad)
    except json.JSONDecodeError as e:
        fail(f"{what}: invalid JSON: {e}")


def member_spans(text):
    """{path: (key_start, value_end)} for every object member of a JSON text that already parsed."""
    spans, n = {}, len(text)

    def ws(i):
        while i < n and text[i] in WS:
            i += 1
        return i

    def string_end(i):
        j = i + 1
        while text[j] != '"':
            j += 2 if text[j] == "\\" else 1
        return j + 1

    def value(i, path):
        i = ws(i)
        c = text[i]
        if c in "{[":
            close, k = ("}" if c == "{" else "]"), 0
            i = ws(i + 1)
            if text[i] == close:
                return i + 1
            while True:
                if c == "{":
                    ks = i
                    ke = string_end(i)
                    key = json.loads(text[ks:ke])
                    i = ws(ke) + 1  # past ':'
                    ve = value(i, path + (key,))
                    spans[path + (key,)] = (ks, ve)
                else:
                    ve = value(i, path + (k,))
                    k += 1
                i = ws(ve)
                if text[i] == ",":
                    i = ws(i + 1)
                    continue
                return i + 1  # past close
        if c == '"':
            return string_end(i)
        j = i
        while j < n and text[j] not in ",]}" + WS:
            j += 1
        return j

    value(0, ())
    return spans


def leaves(node, path=()):
    if isinstance(node, dict):
        if not node:
            yield path, "{}"
        for k, v in node.items():
            yield from leaves(v, path + (k,))
    elif isinstance(node, list):
        if not node:
            yield path, "[]"
        for i, v in enumerate(node):
            yield from leaves(v, path + (i,))
    else:
        yield path, (type(node).__name__, node)  # keeps 1 / 1.0 / true apart


def denoise_modes(doc):
    """[(path to mode config, mode name, config)] for every rpi.denoise, the way libcamera reads it."""
    out = []
    for i, alg in enumerate(doc["algorithms"]):
        if not isinstance(alg, dict) or "rpi.denoise" not in alg:
            continue
        den = alg["rpi.denoise"]
        if not isinstance(den, dict):
            fail(f"algorithms[{i}].rpi.denoise is not an object")
        base = ("algorithms", i, "rpi.denoise")
        if "normal" not in den:
            out.append((base, "(flat)", den))
            continue
        for mode, cfg in den.items():
            if not isinstance(cfg, dict):
                fail(f"rpi.denoise.{mode} is not an object")
            out.append((base + (mode,), mode, cfg))
    return out


def show(doc, label):
    modes = denoise_modes(doc)
    print(f"{label}: target={doc.get('target')!r} version={doc.get('version')!r} "
          f"algorithms={len(doc['algorithms'])} denoise modes={len(modes)}")
    for _, mode, cfg in modes:
        for blk in ("tdn", "sdn", "cdn"):
            v = cfg.get(blk)
            print(f"  {mode if blk == 'tdn' else '':8s} {blk}={json.dumps(v) if v is not None else '-'}")
    counts = {b: sum(b in c for _, _, c in modes) for b in ("tdn", "sdn", "cdn")}
    print("  blocks: " + ", ".join(f"{b} {k}" for b, k in counts.items()))
    return counts


def main():
    args, blocks_arg, i = [], "tdn", 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--blocks":
            if i + 1 >= len(sys.argv):
                sys.exit(__doc__)
            blocks_arg, i = sys.argv[i + 1], i + 2
        elif a.startswith("--blocks="):
            blocks_arg, i = a[len("--blocks="):], i + 1
        else:
            args.append(a)
            i += 1
    if len(args) != 2:
        sys.exit(__doc__)
    src, dst = args
    asked = [b.strip() for b in blocks_arg.split(",")]
    bad = [b for b in asked if b not in ALL_BLOCKS]
    if bad or not asked:
        fail(f"--blocks takes a comma-separated subset of {','.join(ALL_BLOCKS)}; got {blocks_arg!r}")
    blocks = tuple(b for b in ALL_BLOCKS if b in asked)
    kinds = "/".join(blocks)
    rsrc, rdst = os.path.realpath(src), os.path.realpath(dst)
    if rsrc == rdst:
        fail("DST is SRC")
    if any(p.startswith("defaults") for p in rdst.split(os.sep)[:-1]):
        fail(f"DST is inside a defaults directory: {rdst}")
    if not rdst.lower().endswith(".json"):
        fail("DST must end in .json (Core refuses other names)")

    with open(rsrc, "rb") as f:
        text0 = f.read().decode("utf-8")
    d0 = strict_loads(text0, "SRC")
    if not isinstance(d0, dict) or d0.get("target") != "pisp" or not isinstance(d0.get("algorithms"), list):
        fail('SRC is not a version-2 PiSP tuning ("target": "pisp" with an "algorithms" list)')
    occ = ", ".join(f'"{b}" occurrences: {text0.count(chr(34) + b + chr(34))}' for b in blocks)
    print(f'SRC {rsrc}: {len(text0.encode())} bytes, {occ} (grep -c counts lines)')
    counts0 = show(d0, "before")
    for b in blocks:
        if counts0[b] == 0:
            print(f"requested block absent in SRC: {b} (nothing to remove)")
    if sum(counts0[b] for b in blocks) == 0:
        if blocks == ("tdn",):
            fail("SRC has no tdn block: TDN is already off with this file; nothing to write")
        fail(f"SRC has none of the requested blocks ({kinds}); nothing to write")

    # Expected result at the data level.
    d1 = copy.deepcopy(d0)
    removed = []
    for path, _, cfg in denoise_modes(d1):
        for b in blocks:
            if b in cfg:
                del cfg[b]
                removed.append(path + (b,))

    # Cut each member out of the text, with the comma that joins it to its neighbour.
    spans = member_spans(text0)
    cuts = []
    rem = set(removed)
    emptied = set()
    for parent in sorted({p[:-1] for p in removed}, key=str):
        # members of this object in text order; consecutive removed ones form a run
        sib = sorted((v[0], k) for k, v in spans.items() if len(k) == len(parent) + 1 and k[:-1] == parent)
        run = []
        for _, k in sib + [(None, None)]:
            if k in rem:
                run.append(k)
                continue
            if not run:
                continue
            p, ks, ve = run[0], spans[run[0]][0], spans[run[-1]][1]
            b = ks - 1
            while text0[b] in WS:
                b -= 1
            if text0[b] == ",":
                cuts.append((b, ve))  # ', "tdn": {...}'
            else:  # first member: drop it and the comma after it
                a = ve
                while text0[a] in WS:
                    a += 1
                if text0[a] == "}" and blocks != ("tdn",):
                    cuts.append((ks, ve))  # every member of the object is removed: it stays as an empty object
                    emptied.add(parent)
                    run = []
                    continue
                if text0[a] != ",":
                    fail(f"{'.'.join(map(str, p))} is the only member of its object; not cutting")
                a += 1
                while text0[a] in WS:
                    a += 1
                cuts.append((ks, a))
            run = []
    text1 = text0
    for a, b in sorted(cuts, reverse=True):
        text1 = text1[:a] + text1[b:]

    # Verify the text result: strict JSON, equal to the expected data, only tdn paths gone.
    d2 = strict_loads(text1, "result")
    l0, l2 = dict(leaves(d0)), dict(leaves(d2))
    added = sorted(map(str, set(l2) - set(l0) - emptied))
    changed = sorted(str(p) for p in set(l0) & set(l2) if l0[p] != l2[p])
    stray = sorted(str(p) for p in set(l0) - set(l2) if not any(p[:len(r)] == r for r in removed))
    if d2 != d1 or added or changed or stray:
        fail(f"unexpected differences: added={added} changed={changed} removed-not-{kinds}={stray}")
    if any(text1.count(f'"{b}"') for b in blocks) or d2.get("target") != "pisp" or d2.get("version") != d0.get("version"):
        fail(f"result still has a {kinds} key, or lost its target/version")
    if len(text1.encode()) > 4 * 1024 * 1024:
        fail("result is over Core's 4 MiB tuning-file limit")
    print("removed:", ", ".join(".".join(map(str, r)) for r in removed))
    print(f"leaf key paths: {len(l0)} -> {len(l2)}, none changed or added outside the removed {kinds} blocks")
    dl = list(difflib.unified_diff(text0.splitlines(), text1.splitlines(), lineterm="", n=0))
    print(f"text diff: -{sum(l.startswith('-') and not l.startswith('---') for l in dl)} "
          f"+{sum(l.startswith('+') and not l.startswith('+++') for l in dl)} lines")

    if os.path.exists(rdst):
        with open(rdst, "rb") as f:
            if f.read() == text1.encode():
                print(f"DST {rdst} already holds exactly this result; not rewritten")
                show(d2, "after")
                return
        fail(f"DST exists with other content: {rdst} (remove it first)")

    fd, tmp = tempfile.mkstemp(prefix=".tdn_strip.", suffix=".json", dir=os.path.dirname(rdst))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text1)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, rdst)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    with open(rdst, "rb") as f:
        if f.read() != text1.encode():
            fail(f"{rdst} does not read back as written; do not use it")
    print(f"DST {rdst}: {len(text1.encode())} bytes written")
    show(d2, "after")


if __name__ == "__main__":
    main()
