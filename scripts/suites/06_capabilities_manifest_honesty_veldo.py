"""capabilities manifest honesty (WARP-0906, W6 of PLAN-0009): the manifest names only what a

ONE SUITE OF THE UNIT SUITE, AND A FRAGMENT RATHER THAN A MODULE. It is compiled and executed
into scripts/suites/shared.py's namespace by scripts/selftest.py, in manifest order, so every
suite sees exactly the state the monolith gave it and this decomposition cannot change what any
assertion proves. That is the whole reason for the design: the monolith carries cross-region
dependencies through MUTATED objects and through the filesystem, not only through names, and no
mechanical analysis finds those. Sharing one namespace in the original order means no membership
rule has to be closed and correctness is a property of the construction.

Run it: `python3 scripts/selftest.py --upto 06_capabilities_manifest_honesty_veldo` runs everything up to and including this
file, which is the inner loop for a change here. `python3 scripts/selftest.py` runs everything
and is the only thing that means green.

Regions 71-89 of the pre-split monolith.
"""


# --- capabilities manifest honesty (WARP-0906, W6 of PLAN-0009): the manifest names only what an
# adopter actually gets, plus honestly-marked repo-only entries. Two teeth, end to end:
#   1. every capability entry's home must EXIST in the repo (a home pointing at a missing file is a bug);
#   2. every entry NOT marked `scope: repo-only` must have its home resolve in the SHIPPED engine - what
#      installing a pack lays: the ENGINE_GLOBS tree under engine plus the plugin wrapper
#      (skills/agents) - so an adopter who installs a pack actually has it; a `scope: repo-only` entry
#      (dogfood or build machinery whose home does not ship) is exempt from the shipped requirement but
#      still must exist in the repo. A procedure whose home is documentation (docs/...) is honestly
#      available to any adopter and is exempt from the shipped-code requirement; a mechanical/reference
#      entry may NOT hide behind a docs home. Ship-truth is computed from pack.py engine_files (the ONE
#      source of what ships), never a second hardcoded glob list here.
# TEETH proven below: un-marking a repo-only dogfood entry turns it RED, and pointing a shipped entry's
# home at a missing file turns it RED.
import re
_chpkspec = importlib.util.spec_from_file_location("veldo_pack_honesty", ROOT / ".veldo/pack.py")
_CHPK = importlib.util.module_from_spec(_chpkspec); _chpkspec.loader.exec_module(_CHPK)
_CH_ENGINE = set(_CHPK.engine_files(str(ROOT / "engine")))  # relative engine paths a pack lays

def _ch_is_doc(part):
    return part == "docs" or part.startswith("docs/")

def _ch_part_ships(part):
    # an adopter who installs a pack gets: the engine (ENGINE_GLOBS under engine) and the
    # plugin wrapper (skills/agents), plus any home already written as a shipped packs/claude/ path.
    if part in _CH_ENGINE:
        return True
    if part.startswith(("skills", "agents")) and (ROOT / "packs" / "claude" / part).exists():
        return True
    if part.startswith("packs/claude/") and (ROOT / part).exists():
        return True
    # A BASE PATH SHIPS, and this needs saying since the split. Before it, every engine file sat
    # under plugin/, so one prefix test covered both the pack and the base. Now they are separate
    # trees and an `engine/...` home is the MOST shipped thing there is: it is the base every pack
    # extends. Without this the CI workflow template read as not shipping to an adopter.
    if part.startswith("engine/") and (ROOT / part).exists():
        return True
    return False

def _ch_part_in_repo(part):
    # exists somewhere in the veldo repo: the repo-root working copy (dogfood), docs/, a packs/claude/ path,
    # or a shipped location (skills/agents under packs/claude/, engine files under engine).
    return (ROOT / part).exists() or _ch_part_ships(part)

_CH_ENTRY = re.compile(r"(?m)^\s{2}([a-z0-9_]+):\s*\{(.*)\}\s*$")
_CH_HOME = re.compile(r"home:\s*([^,}]+)")
_CH_STATUS = re.compile(r"status:\s*([a-z\-]+)")

def _caps_honesty_findings(caps_text):
    findings = []
    for m in _CH_ENTRY.finditer(caps_text):
        name, body = m.group(1), m.group(2)
        hm = _CH_HOME.search(body)
        if not hm:
            continue  # a status-only entry (absent / control-plane) declares no home to check
        status = (_CH_STATUS.search(body).group(1) if _CH_STATUS.search(body) else "?")
        parts = [p.strip() for p in hm.group(1).split(" + ")]
        for part in parts:
            if not _ch_part_in_repo(part):
                findings.append("%s: home %r does not exist in the repo" % (name, part))
        if "scope: repo-only" in body:
            continue  # dogfood / build machinery: honestly marked, exempt from the shipped requirement
        for part in parts:
            if _ch_is_doc(part):
                if status != "procedure":
                    findings.append("%s (%s): home %r is documentation, not shipped code" % (name, status, part))
                continue  # a procedure documented in docs is available to any adopter
            if not _ch_part_ships(part):
                findings.append("%s (%s): home %r does not ship to an adopter and is not marked scope: repo-only"
                                % (name, status, part))
    return findings

_ch_caps = (ROOT / ".veldo/capabilities.yaml").read_text()
expect("capabilities manifest is honest end to end (every unmarked home ships, every home exists)",
       _caps_honesty_findings(_ch_caps) == [])
expect("both capabilities.yaml copies are byte-identical (the repo-only marker lands in both)",
       (ROOT / ".veldo/capabilities.yaml").read_bytes()
       == (ROOT / "engine/.veldo/capabilities.yaml").read_bytes())
expect("capabilities manifest marks the known dogfood entries repo-only (at least the tracker+pack family)",
       _ch_caps.count("scope: repo-only") >= 15)

# TEETH 1: un-marking a repo-only dogfood entry (budget_governance, home .veldo/budget.py, which does
# NOT land in the shipped engine) makes the honesty check name it as an over-claim.
_ch_unmarked = _ch_caps.replace("home: .veldo/budget.py, scope: repo-only,", "home: .veldo/budget.py,", 1)
expect("TEETH: un-marking a dogfood entry turns the honesty check RED",
       _ch_unmarked != _ch_caps
       and any("budget_governance" in f and "does not ship" in f for f in _caps_honesty_findings(_ch_unmarked)))

# TEETH 2: pointing a SHIPPED entry's home at a missing file turns it RED (metrics_dashboard ships and
# is not repo-only; its home .veldo/dashboard.py appears once).
_ch_missing = _ch_caps.replace(".veldo/dashboard.py", ".veldo/does_not_exist_0906.py", 1)
expect("TEETH: pointing a shipped entry's home at a missing file turns the honesty check RED",
       _ch_missing != _ch_caps
       and any("metrics_dashboard" in f for f in _caps_honesty_findings(_ch_missing)))

# --- Claude pack + pack drift (WARP-0802, W2 of PLAN-0008): the pack engine wired to the real
# plugin engine, a pack manifest declaring the Claude pack (option B), and a drift-check ENFORCED
# here (the gate's unit check) so no pack silently forks the canonical engine. Mechanism teeth over
# a temp assembled pack; the real manifest asserted drift-free.
_pkspec = importlib.util.spec_from_file_location("veldo_pack", ROOT / ".veldo/pack.py")
PK = importlib.util.module_from_spec(_pkspec); _pkspec.loader.exec_module(PK)

# AC1: finalized ENGINE_GLOBS covers the real engine (guard + runners) and excludes build artifacts
_pk_engine = PK.engine_files(str(ROOT / "engine"))
expect("pack engine files include the guard script", "scripts/veldo-guard.sh" in _pk_engine)
expect("pack engine files include the runners tree", any(f.startswith("scripts/runners/") for f in _pk_engine))
expect("pack engine files include the gate and a .veldo module", "scripts/verify.sh" in _pk_engine and ".veldo/validate.py" in _pk_engine)
expect("pack engine files exclude build artifacts (__pycache__/.pyc)",
       not any("__pycache__" in f or f.endswith(".pyc") for f in _pk_engine))

# AC2: the manifest loads and validates; a malformed manifest is rejected by name
_pk_cfg = PK.load_packs(repo_root=str(ROOT))
expect("pack manifest loads and declares the Claude pack",
       _pk_cfg.get("schema") == "veldo.packs/v1" and any(p["id"] == "claude" for p in _pk_cfg["packs"]))
def _pk_bad(cfg):
    with tempfile.TemporaryDirectory() as _d:
        (Path(_d) / ".veldo").mkdir()
        (Path(_d) / ".veldo" / "packs.json").write_text(json.dumps(cfg))
        try:
            PK.load_packs(repo_root=_d)
            return False
        except PK.PackManifestError:
            return True
expect("pack manifest rejects a bad schema by name", _pk_bad({"schema": "nope", "packs": []}))
expect("pack manifest rejects an empty packs list by name", _pk_bad({"schema": "veldo.packs/v1", "packs": []}))
expect("pack manifest rejects a pack missing a required field by name",
       _pk_bad({"schema": "veldo.packs/v1", "packs": [{"id": "x", "tool": "t"}]}))
expect("pack manifest rejects duplicate pack ids by name",
       _pk_bad({"schema": "veldo.packs/v1", "packs": [{"id": "x", "tool": "t", "engine_src": "e", "pack_dir": "d"},
                                                     {"id": "x", "tool": "t", "engine_src": "e", "pack_dir": "d"}]}))

# AC3 gate enforcement. THE ENGINE IS NO LONGER COPIED INTO PACKS, so "the copy matches the
# source" is not a property this repository has any more, and asserting it would be a witness for
# a retired design. What replaces it is the property that actually matters: COMPOSING a declared
# pack (canonical engine + that pack's extension files) yields the complete engine.
# THE ASSERTION THAT USED TO SIT HERE COULD NOT FAIL. It carried a label about COMPOSING and
# evaluated `len(packs) >= 1 and len(engine_files) > 0`: it never opened a pack directory, so it was
# true with all seven packs empty, which is measurably what six of them are. That is the vacuity rule
# C1 exists to refuse, and it was guarding the claim the README makes to every adopter.
#
# MY FIRST REPLACEMENT WAS VACUOUS TOO, which is worth leaving written down. It asserted that the
# base composed with a pack covers the engine set - and the BASE IS the engine set, so the union
# contains it whatever the pack holds. Only the teeth beside it exposed that. Under the base-and-
# extends model Dmitry confirmed on 2026-08-09, a pack SHOULD NOT carry engine files, so "missing
# from the pack" is correct and not a finding.
#
# THE PROPERTY THAT CAN ACTUALLY FAIL is the one that matters under that model: if a pack ships its
# own copy of an engine file, that copy must be byte-identical to the base. Absent is fine, the base
# provides it. DIFFERENT is a silent fork, which is exactly what the drift check existed to prevent.
_pk_cfg_all = PK.load_packs(repo_root=str(ROOT))
_pk_eng = set(PK.engine_files(str(ROOT / _pk_cfg_all["canonical_engine"])))
_PK_BASE = str(ROOT / _pk_cfg_all["canonical_engine"])


def _pk_forks(pack_dir):
    """Engine files a pack ships that DIFFER from the base. Absent files are not forks."""
    d = ROOT / pack_dir
    if not d.is_dir():
        return []
    return [f for f, why in PK.engine_drift(_PK_BASE, str(d)) if why == "differs"]


expect("no declared pack silently forks the base: an engine file a pack also ships is byte-identical "
       "to the base copy, checked per pack. Absent is not a fork - under base-and-extends the base "
       "provides it - but DIFFERENT is, and that is the failure the drift check exists to catch",
       len(_pk_cfg_all["packs"]) >= 1 and len(_pk_eng) > 0
       and all(_pk_forks(p["pack_dir"]) == [] for p in _pk_cfg_all["packs"]))
with tempfile.TemporaryDirectory() as _pkfd:
    # TEETH, because the assertion above passes on six packs that ship nothing and would pass on a
    # pack that ships nothing whatever the base looked like. A pack that ships a MUTATED engine file
    # must be named.
    PK.assemble_pack(_PK_BASE, None, None, _pkfd)
    _pkf_victim = Path(_pkfd) / ".veldo" / "validate.py"
    _pkf_victim.write_text(_pkf_victim.read_text() + "\n# forked\n")
    expect("that fork check CAN FAIL: a pack shipping a MUTATED engine file is named as differing",
           ".veldo/validate.py" in [f for f, why in PK.engine_drift(_PK_BASE, _pkfd) if why == "differs"])

# AC5 mechanism teeth: assemble a pack from the canonical engine, then prove drift is detected
with tempfile.TemporaryDirectory() as _pkd:
    _pk_src = str(ROOT / "engine")
    PK.assemble_pack(_pk_src, None, None, _pkd)
    expect("an assembled pack is byte-identical to the source (drift empty)", PK.engine_drift(_pk_src, _pkd) == [])
    # mutate one engine file -> differs
    _pk_mut = Path(_pkd) / "scripts" / "verify.sh"
    _pk_mut.write_text(_pk_mut.read_text() + "\n# drift\n")
    _pk_drift = dict(PK.engine_drift(_pk_src, _pkd))
    expect("pack drift detects a mutated engine file as differing", _pk_drift.get("scripts/verify.sh") == "differs")
    # remove one engine file -> missing
    (Path(_pkd) / ".veldo" / "validate.py").unlink()
    _pk_drift2 = dict(PK.engine_drift(_pk_src, _pkd))
    expect("pack drift detects a removed engine file as missing", _pk_drift2.get(".veldo/validate.py") == "missing")

# --- Cursor pack (WARP-0803, W3 of PLAN-0008): the first committed self-contained pack. The full
# canonical engine is copied into packs/cursor (held byte-identical by the drift-check, now
# cross-pack load-bearing) plus a Cursor driver wrapper. Uses PK from the WARP-0802 block.
_cur = ROOT / "packs/cursor"
_cur_ids = [p["id"] for p in PK.load_packs(repo_root=str(ROOT))["packs"]]
expect("the cursor pack is declared in the manifest", "cursor" in _cur_ids and len(_cur_ids) >= 2)
# the pack is an EXTENSION, not a copy: it carries its tool-specific files and NOT the engine
expect("the cursor pack ships its extension only, with no copied engine",
       (_cur / ".cursor/rules/veldo.mdc").is_file() and not (_cur / ".veldo/validate.py").exists())
# the Cursor driver wrapper is present
expect("the cursor pack has the canonical AGENTS.md", (_cur / "AGENTS.md").is_file())
expect("the cursor pack has an always-on .cursor rule pointing at VELDO", (_cur / ".cursor/rules/veldo.mdc").is_file())
expect("the cursor pack has the guard (git pre-push + .cursor hook)",
       (_cur / "hooks/pre-push").is_file() and (_cur / ".cursor/hooks/hooks.json").is_file())
# enforcement: both hooks must feed the guard the JSON payload it parses (tool_input.command on
# stdin), NOT an env CMD the guard ignores - the fix for the fail-open gap the W3 review caught.
_cur_pp = (_cur / "hooks/pre-push").read_text()
_cur_hk = (_cur / ".cursor/hooks/veldo-guard-hook.sh").read_text()
expect("the cursor push gate feeds veldo-guard.sh the JSON stdin payload (not an ignored env CMD)",
       "tool_input" in _cur_pp and "veldo-guard.sh" in _cur_pp and "tool_input" in _cur_hk)
expect("the cursor pack carries the reused skills and agents",
       (_cur / "skills/spec/SKILL.md").is_file() and (_cur / ".cursor/agents/veldo-reviewer.md").is_file())
# cross-pack teeth: a drifted engine copy in a real pack tree is caught (proven on a temp clone)
import shutil as _cur_sh
with tempfile.TemporaryDirectory() as _curd:
    _clone = Path(_curd) / "packs" / "cursor"
    _cur_sh.copytree(_cur, _clone)
    # compose the way an install does before asserting drift: engine first, extension on top
    for _rel in PK.engine_files(str(ROOT / "engine")):
        _s = ROOT / "engine" / _rel; _d = _clone / _rel
        _d.parent.mkdir(parents=True, exist_ok=True); _cur_sh.copy2(_s, _d)
    expect("a composed cursor pack is drift-free", PK.engine_drift(str(ROOT / "engine"), str(_clone)) == [])
    _vf = _clone / "scripts" / "verify.sh"
    _vf.write_text(_vf.read_text() + "\n# pack drift\n")
    _cur_dd = dict(PK.engine_drift(str(ROOT / "engine"), str(_clone)))
    expect("cross-pack drift-check catches a mutated engine file in a committed pack copy",
           _cur_dd.get("scripts/verify.sh") == "differs")

# --- Codex CLI pack (WARP-0804, W4 of PLAN-0008): the first CLI-cluster committed self-contained
# pack. Engine copy + Codex driver (.codex/config.toml + hooks). Uses PK from the WARP-0802 block.
_cdx = ROOT / "packs/codex"
expect("the codex pack is declared in the manifest",
       "codex" in [p["id"] for p in PK.load_packs(repo_root=str(ROOT))["packs"]])
expect("the codex pack ships its extension only, with no copied engine",
       (_cdx / "AGENTS.md").is_file() and not (_cdx / ".veldo/validate.py").exists())
expect("the codex pack has its Codex driver (config.toml + hooks) and reused skills/agents",
       (_cdx / ".codex/config.toml").is_file() and (_cdx / ".codex/hooks.json").is_file()
       and (_cdx / "skills/spec/SKILL.md").is_file() and (_cdx / ".codex/agents/veldo-reviewer.md").is_file())
# enforcement: both hooks feed veldo-guard.sh the JSON payload it parses (the WARP-0803 fix), not env CMD
_cdx_pp = (_cdx / "hooks/pre-push").read_text()
_cdx_hk = (_cdx / ".codex/veldo-guard-hook.sh").read_text()
expect("the codex push gate feeds veldo-guard.sh the JSON stdin payload (not an ignored env CMD)",
       "tool_input" in _cdx_pp and "veldo-guard.sh" in _cdx_pp and "tool_input" in _cdx_hk)

# --- GitHub Copilot pack (WARP-0805, W5 of PLAN-0008): the hook-less-enforcement case. No editor
# hook; the guaranteed gate is the git pre-push hook + the CI required check. Uses PK from W2 block.
_cop = ROOT / "packs/copilot"
expect("the copilot pack is declared in the manifest",
       "copilot" in [p["id"] for p in PK.load_packs(repo_root=str(ROOT))["packs"]])
# the CI workflow moved with the engine: it is identical in every pack, so it has one home now
expect("the copilot pack ships its extension only, with no copied engine",
       (_cop / "AGENTS.md").is_file() and not (_cop / ".veldo/validate.py").exists()
       and (_cop / ".github/copilot-instructions.md").is_file())
expect("the copilot pack has its always-injected instructions + a prompt + reused skills/agents",
       (_cop / ".github/copilot-instructions.md").is_file()
       and (_cop / ".github/prompts/veldo-loop.prompt.md").is_file()
       and (_cop / "skills/spec/SKILL.md").is_file() and (_cop / ".github/agents/veldo-reviewer.md").is_file())
# hook-less enforcement: the git pre-push hook feeds the guard the JSON payload (not env CMD), and
# the instructions document both the git hook and the required CI check.
_cop_pp = (_cop / "hooks/pre-push").read_text()
_cop_ci = (_cop / ".github/copilot-instructions.md").read_text()
expect("the copilot git pre-push hook feeds veldo-guard.sh the JSON stdin payload",
       "tool_input" in _cop_pp and "veldo-guard.sh" in _cop_pp)
expect("the copilot instructions document the hook-less gate (git pre-push + required CI check)",
       "core.hooksPath" in _cop_ci and "veldo-gate.yml" in _cop_ci and "required status check" in _cop_ci)

# --- Antigravity CLI (agy) pack (WARP-0806, W6 of PLAN-0008): retargeted from the wound-down Gemini
# CLI to agy, whose plugin model mirrors Claude's. Uses PK from the WARP-0802 block.
_agy = ROOT / "packs/antigravity"
expect("the antigravity pack is declared in the manifest",
       "antigravity" in [p["id"] for p in PK.load_packs(repo_root=str(ROOT))["packs"]])
expect("the antigravity pack ships its extension only, with no copied engine",
       (_agy / "AGENTS.md").is_file() and not (_agy / ".veldo/validate.py").exists())
expect("the antigravity pack has its agy plugin wrapper (plugin.json + hooks.json + rules) and reused skills/agents",
       (_agy / "plugin.json").is_file() and (_agy / "hooks.json").is_file() and (_agy / "rules/veldo.md").is_file()
       and (_agy / "skills/spec/SKILL.md").is_file() and (_agy / "agents/veldo-reviewer.md").is_file())
# enforcement: both hooks feed veldo-guard.sh the JSON payload it parses (the WARP-0803 fix)
_agy_pp = (_agy / "hooks/pre-push").read_text()
_agy_hk = (_agy / "veldo-guard-hook.sh").read_text()
expect("the antigravity push gate feeds veldo-guard.sh the JSON stdin payload (not an ignored env CMD)",
       "tool_input" in _agy_pp and "veldo-guard.sh" in _agy_pp and "tool_input" in _agy_hk)

# --- OpenCode pack (WARP-0807, W7 of PLAN-0008): CLI-cluster committed self-contained pack. Uses PK.
_oc = ROOT / "packs/opencode"
expect("the opencode pack is declared in the manifest",
       "opencode" in [p["id"] for p in PK.load_packs(repo_root=str(ROOT))["packs"]])
expect("the opencode pack ships its extension only, with no copied engine",
       (_oc / "AGENTS.md").is_file() and not (_oc / ".veldo/validate.py").exists())
expect("the opencode pack has its OpenCode driver (opencode.json + command) and reused skills/agents",
       (_oc / "opencode.json").is_file() and (_oc / ".opencode/command/veldo.md").is_file()
       and (_oc / "skills/spec/SKILL.md").is_file() and (_oc / ".opencode/agent/veldo-reviewer.md").is_file())
_oc_pp = (_oc / "hooks/pre-push").read_text()
_oc_hk = (_oc / ".opencode/veldo-guard-hook.sh").read_text()
expect("the opencode push gate feeds veldo-guard.sh the JSON stdin payload (not an ignored env CMD)",
       "tool_input" in _oc_pp and "veldo-guard.sh" in _oc_pp and "tool_input" in _oc_hk)

# enforcement mode fix (WARP-0807 review): a committed git pre-push hook + guard scripts MUST be
# executable, else git silently skips the hook and an unproven push fails OPEN. The assembler now
# copies mode and engine_drift is mode-aware, so a non-executable engine-script copy is caught.
import os as _pkos
import shutil as _pkshutil
for _pkid in ("cursor", "codex", "copilot", "antigravity", "opencode"):
    expect("pack %s git pre-push hook is executable (git runs it, not fail-open)" % _pkid,
           _pkos.access(ROOT / "packs" / _pkid / "hooks/pre-push", _pkos.X_OK))
# veldo-guard.sh is engine, not extension: it has ONE home now and is checked once, at the source.
expect("the canonical veldo-guard.sh is executable (every composed pack inherits it)",
       _pkos.access(ROOT / "engine/scripts/veldo-guard.sh", _pkos.X_OK))
with tempfile.TemporaryDirectory() as _pkmd:
    _pkclone = Path(_pkmd) / "opencode"; _pkshutil.copytree(ROOT / "engine", _pkclone)
    _pkshutil.copytree(ROOT / "packs/opencode", _pkclone, dirs_exist_ok=True)
    expect("a composed pack has no mode drift", PK.engine_drift(str(ROOT / "engine"), str(_pkclone)) == [])
    _pkos.chmod(_pkclone / "scripts/veldo-guard.sh", 0o644)
    expect("engine_drift catches a stripped exec bit as mode drift (not silently ignored)",
           ("scripts/veldo-guard.sh", "mode") in PK.engine_drift(str(ROOT / "engine"), str(_pkclone)))

# --- Aider pack (WARP-0808, W8 of PLAN-0008): the thin-primitives case, the seventh and final pack.
# Aider defaults to --no-verify, so the pack sets git-commit-verify true + the executable git pre-push
# hook + CI. Uses PK from the WARP-0802 block; _pkos from the mode-fix block.
_ai = ROOT / "packs/aider"
expect("the aider pack is declared in the manifest",
       "aider" in [p["id"] for p in PK.load_packs(repo_root=str(ROOT))["packs"]])
expect("the aider pack ships its extension only, with no copied engine",
       (_ai / "AGENTS.md").is_file() and not (_ai / ".veldo/validate.py").exists())
expect("the aider pack has its Aider driver (CONVENTIONS.md + .aider.conf.yml) and reused skills/agents",
       (_ai / "CONVENTIONS.md").is_file() and (_ai / ".aider.conf.yml").is_file()
       and (_ai / "skills/spec/SKILL.md").is_file() and (_ai / "agents/veldo-reviewer.md").is_file())
# thin-tool enforcement: git-commit-verify enabled (Aider defaults to no-verify) + the pre-push hook
# is EXECUTABLE (git skips a non-executable hook) and feeds the guard the JSON payload
_ai_conf = (_ai / ".aider.conf.yml").read_text()
_ai_pp = (_ai / "hooks/pre-push").read_text()
expect("the aider config enables git-commit-verify (does not bypass hooks)", "git-commit-verify: true" in _ai_conf)
expect("the aider git pre-push hook feeds veldo-guard.sh the JSON stdin payload", "tool_input" in _ai_pp and "veldo-guard.sh" in _ai_pp)
expect("the aider git pre-push hook is executable (git runs it, not fail-open)", _pkos.access(_ai / "hooks/pre-push", _pkos.X_OK))

# --- cross-pack conformance (WARP-0809, W9 of PLAN-0008): the join point. A table-driven harness
# (.veldo/pack_conformance.py, build machinery) drives EACH declared pack through a constructed VELDO
# loop against its OWN assembled engine and proves, by construction, that the push gate blocks the
# unproven and allows the proven, that policy_check (as CI runs it) agrees, that the committed hook
# and guard are executable in the git INDEX (closing the WARP-0808 review note), and that no pack's
# engine has drifted. Portability and no-fail-open become gate-enforced properties, not inspection.
_ccspec = importlib.util.spec_from_file_location("veldo_pack_conformance", ROOT / ".veldo/pack_conformance.py")
CC = importlib.util.module_from_spec(_ccspec); _ccspec.loader.exec_module(CC)

# AC1/AC2/AC4: every declared pack conforms (drift-free + guard block/allow + policy + exec-bit)
_cc_findings = CC.pack_conformance(repo_root=str(ROOT))
if _cc_findings:
    for _f in _cc_findings:
        print("  CONFORMANCE: " + _f)
expect("cross-pack conformance passes for every declared pack (guard + policy + exec-bit + drift)",
       _cc_findings == [])

# AC3: the WARP-0808 note closed at the git INDEX - every pack's committed hook + guard is 100755
_cc_modes = CC.committed_hook_modes(str(ROOT))
expect("every pack's committed git pre-push hook + guard is executable in the git index (100755)",
       # 6 pack pre-push hooks (extension, one each) + the canonical guard (engine, one home)
       len(_cc_modes) >= 7 and all(_m == "100755" for _m in _cc_modes.values()))

# AC3/AC5 teeth: the exec bit is load-bearing END TO END under a real git push (git skips a
# non-executable committed hook, so an unproven push fails OPEN; an executable one blocks it)
_cc_eb = CC.real_push_exec_bit(str(ROOT), "aider")
expect("a non-executable committed hook fails OPEN under a real git push (exec bit is load-bearing)",
       _cc_eb["nonexec_landed"] is True)
expect("an executable committed hook BLOCKS an unproven real git push (nothing lands)",
       _cc_eb["exec_blocked"] is True)

# AC5 teeth: the conformance driver is directional and non-tautological - the SAME driver blocks an
# unproven push and allows a proven one; a state-blind gate could not satisfy both. Proven on a
# hook-shipping pack (copilot: git pre-push) and the guard-direct pack (claude: option B, no
# committed hook of its own), so both drive paths are exercised.
expect("conformance driver blocks an unproven push via the committed hook (copilot)",
       CC.gate_exit_for_state(str(ROOT), "copilot", proven=False) != 0)
expect("conformance driver allows a proven push via the committed hook (copilot)",
       CC.gate_exit_for_state(str(ROOT), "copilot", proven=True) == 0)
expect("conformance driver blocks an unproven push via the guard directly (claude, option B)",
       CC.gate_exit_for_state(str(ROOT), "claude", proven=False) != 0)
expect("conformance driver allows a proven push via the guard directly (claude, option B)",
       CC.gate_exit_for_state(str(ROOT), "claude", proven=True) == 0)

# --- real fleet dispatcher (WARP-0901, W1 of PLAN-0009): the Dispatcher that fills the
# work.py seam, driven over a THROWAWAY git repo with a FAKE executor build hook (the
# existing _FakeLoop), a FAKE fresh-context reviewer, and a FAKE lander - no live agent. The
# build path drives the executor and STOPS at review (spec flipped ready -> review, no review
# run); the review path lands a passing verdict (spec -> shipped) and returns a failing one to
# ready (never shipped). Non-tautological teeth: a mutant that ships without a passing verdict,
# and a mutant whose build path reviews its own build, each turn an assertion red; and the real
# LiveLoop/LiveReviewer path fails loud rather than fabricate a build or a verdict.
_dspspec = importlib.util.spec_from_file_location("veldo_dispatch", ROOT / ".veldo/dispatch.py")
DSP = importlib.util.module_from_spec(_dspspec); _dspspec.loader.exec_module(DSP)


class _DspReviewer(DSP.Reviewer):
    """A fresh-context reviewer wired to a scripted verdict; counts its calls so
    'the build worker made no review' is an observation, not an article of faith."""
    def __init__(self, verdict="pass", findings=None):
        self.verdict = verdict; self.findings = findings; self.calls = 0
    def review(self, spec, unit):
        self.calls += 1
        rv = {"verdict": self.verdict, "human_minutes": 4}
        if self.findings is not None:
            rv["findings"] = self.findings
        return rv


class _DspLander:
    """A fake serialized lander: records what it landed and returns a scripted ok."""
    def __init__(self, ok=True):
        self.ok = ok; self.lands = []
    def land(self, unit):
        self.lands.append(unit["spec"])
        return {"ok": self.ok, "stage": "landed" if self.ok else "gate"}


class _MutShipNoVerdict(DSP.Dispatcher):
    """MUTANT: the verdict gate always passes, so a change ships on ANY verdict.
    This is exactly the independence-breaking bug the review path must not have."""
    def _verdict_passes(self, rv):
        return True


class _MutBuildReviews(DSP.Dispatcher):
    """MUTANT: the build worker reviews (and ships) its OWN build instead of
    stopping at review - the forbidden shortcut that collapses independence."""
    def _dispatch_build(self, unit):
        r = super()._dispatch_build(unit)
        if r.get("ok"):
            r["self_review"] = self._dispatch_review({"spec": unit["spec"], "kind": "review"})
            r["reviewed"] = True
        return r


with tempfile.TemporaryDirectory() as _dwrepo, tempfile.TemporaryDirectory() as _dwclaims:
    subprocess.run(["git", "init", "-q", "-b", "main", _dwrepo], check=True)
    subprocess.run(["git", "-C", _dwrepo, "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", _dwrepo, "config", "user.name", "t"], check=True)
    os.makedirs(os.path.join(_dwrepo, "specs"))

    def _dw(sid, status, extra=""):
        with open(os.path.join(_dwrepo, "specs", sid + ".md"), "w") as _f:
            _f.write("---\nschema: veldo.spec/v1\nid: %s\ntitle: t\nstatus: %s\nowner: dmitry\n"
                     "%s---\nbody\n" % (sid, status, extra))

    for _sid in ("VELDO-DB1", "VELDO-DB2", "VELDO-DBG"):
        _dw(_sid, "ready", "lane: standalone\n")
    for _sid in ("VELDO-DR1", "VELDO-DR2", "VELDO-DR3", "VELDO-DR5"):
        _dw(_sid, "review", "lane: standalone\n")
    _dw("VELDO-DB3", "ready", "lane: standalone\n")     # real build path (fails loud)
    _dw("VELDO-DR4", "review", "lane: standalone\n")    # real review path (fails loud)
    _dw("VELDO-DM1", "review", "lane: standalone\n")    # mutant: ship without a pass
    _dw("VELDO-DM2", "ready", "lane: standalone\n")     # mutant: build reviews own work

    # (1) BUILD path: drive the executor and STOP at review, reviewing nothing.
    _fb = _FakeLoop()  # gate green, build ok, proof ok - a clean build/gate/proof
    _frev = _DspReviewer(); _fl = _DspLander()
    _disp = DSP.Dispatcher(repo_root=_dwrepo, hooks=_fb, reviewer=_frev, lander=_fl)
    _rb = _disp.dispatch({"spec": "VELDO-DB1", "kind": "build"})
    expect("dispatch build path returns ok and fills the work.py seam (duck-typed dispatch)",
           _rb["ok"] is True and callable(getattr(_disp, "dispatch", None)))
    expect("dispatch build path flips the spec ready -> review (a claimable review unit)",
           FR.current_status("VELDO-DB1", _dwrepo) == "review")
    expect("dispatch build path reviews nothing (independence: review is a separate unit)",
           _frev.calls == 0 and _fl.lands == [] and _rb.get("reviewed") is False)

    # (2) REVIEW path with a passing verdict: land and ship.
    _frev2 = _DspReviewer(verdict="pass"); _fl2 = _DspLander(ok=True)
    _disp2 = DSP.Dispatcher(repo_root=_dwrepo, hooks=_FakeLoop(), reviewer=_frev2, lander=_fl2)
    _rr = _disp2.dispatch({"spec": "VELDO-DR1", "kind": "review"})
    expect("dispatch review path with a passing verdict lands and ships",
           _rr["ok"] is True and _rr["shipped"] is True and _frev2.calls == 1
           and _fl2.lands == ["VELDO-DR1"] and FR.current_status("VELDO-DR1", _dwrepo) == "shipped")

    # pass_with_notes with zero blocking findings ships; with a blocking finding it does not.
    _disp_pn = DSP.Dispatcher(repo_root=_dwrepo, hooks=_FakeLoop(),
                              reviewer=_DspReviewer(verdict="pass_with_notes",
                                                    findings={"blocking": [], "non_blocking": ["n"]}),
                              lander=_DspLander(ok=True))
    _rpn = _disp_pn.dispatch({"spec": "VELDO-DR5", "kind": "review"})
    expect("dispatch review path ships pass_with_notes when zero blocking findings",
           _rpn["ok"] is True and FR.current_status("VELDO-DR5", _dwrepo) == "shipped")
    _fl_pnb = _DspLander(ok=True)
    _disp_pnb = DSP.Dispatcher(repo_root=_dwrepo, hooks=_FakeLoop(),
                               reviewer=_DspReviewer(verdict="pass_with_notes",
                                                     findings={"blocking": ["must fix"], "non_blocking": []}),
                               lander=_fl_pnb)
    _rpnb = _disp_pnb.dispatch({"spec": "VELDO-DR3", "kind": "review"})
    expect("dispatch review path does NOT ship pass_with_notes with a blocking finding (fails closed)",
           _rpnb["ok"] is False and _fl_pnb.lands == []
           and FR.current_status("VELDO-DR3", _dwrepo) != "shipped")

    # (3) a failing build returns ok False and leaves the spec NOT in review (retry stays ready).
    _disp_bf = DSP.Dispatcher(repo_root=_dwrepo, hooks=_FakeLoop(build_ok=False),
                              reviewer=_DspReviewer(), lander=_DspLander())
    _rbf = _disp_bf.dispatch({"spec": "VELDO-DB2", "kind": "build"})
    expect("dispatch failing build returns ok False and does NOT flip the spec to review",
           _rbf["ok"] is False and FR.current_status("VELDO-DB2", _dwrepo) == "ready")
    # a red gate is the same: halt, ok False, no flip to review (evidence never reached review).
    _disp_rg = DSP.Dispatcher(repo_root=_dwrepo, hooks=_FakeLoop(gate_green=False),
                              reviewer=_DspReviewer(), lander=_DspLander())
    _rrg = _disp_rg.dispatch({"spec": "VELDO-DBG", "kind": "build"})
    expect("dispatch red gate returns ok False and does NOT flip the spec to review",
           _rrg["ok"] is False and _rrg.get("halted_at") == "gate"
           and FR.current_status("VELDO-DBG", _dwrepo) == "ready")

    # (4) a failing verdict returns ok False, does not land, and leaves the spec NOT shipped.
    _fl_fv = _DspLander(ok=True)  # a lander that WOULD ship - it must never be called on a fail
    _disp_fv = DSP.Dispatcher(repo_root=_dwrepo, hooks=_FakeLoop(),
                              reviewer=_DspReviewer(verdict="fail"), lander=_fl_fv)
    _rfv = _disp_fv.dispatch({"spec": "VELDO-DR2", "kind": "review"})
    expect("dispatch failing verdict returns ok False, lands nothing, and does NOT ship",
           _rfv["ok"] is False and _rfv["shipped"] is False and _fl_fv.lands == []
           and FR.current_status("VELDO-DR2", _dwrepo) == "ready")

    # (5) the REAL reference path fails loud rather than fabricate a build or a verdict.
    # dispatch.py loads its own executor copy, so the loud error is DSP.EX.ExecutorError.
    _real = DSP.Dispatcher(repo_root=_dwrepo)  # hooks=None -> LiveLoop, reviewer=None -> LiveReviewer
    try:
        _real.dispatch({"spec": "VELDO-DB3", "kind": "build"}); _loud = False
    except DSP.EX.ExecutorError:
        _loud = True
    expect("dispatch real build path fails loud (LiveLoop refuses to fabricate a build)", _loud)
    expect("dispatch real build path left the spec untouched (ready, not review)",
           FR.current_status("VELDO-DB3", _dwrepo) == "ready")
    try:
        _real.dispatch({"spec": "VELDO-DR4", "kind": "review"}); _loud = False
    except DSP.EX.ExecutorError:
        _loud = True
    expect("dispatch real review path fails loud (LiveReviewer refuses to fabricate a verdict)", _loud)
    expect("dispatch real review path left the spec untouched (review, not shipped)",
           FR.current_status("VELDO-DR4", _dwrepo) == "review")

    # NON-TAUTOLOGY TEETH. The two mutants take the SAME inputs as the real dispatcher above
    # but violate the invariant, turning the corresponding assertion red - proving those
    # assertions are not vacuous.
    # Mutant 1: ships on a FAIL verdict. Real (VELDO-DR2) left it un-shipped on a fail; this
    # ships on the same fail, so the 'does NOT ship on a failing verdict' assertion has teeth.
    _mut1 = _MutShipNoVerdict(repo_root=_dwrepo, hooks=_FakeLoop(),
                              reviewer=_DspReviewer(verdict="fail"), lander=_DspLander(ok=True))
    _m1 = _mut1.dispatch({"spec": "VELDO-DM1", "kind": "review"})
    expect("MUTANT that ships without a passing verdict turns the no-ship-on-fail assertion RED (teeth)",
           _m1["shipped"] is True and FR.current_status("VELDO-DM1", _dwrepo) == "shipped")
    # Mutant 2: the build path reviews (and ships) its own build. Real (VELDO-DB1) reviewed
    # nothing and left the spec at review; this reviews its own build and ships, so the 'build
    # reviews nothing' assertion has teeth.
    _mrev2 = _DspReviewer(verdict="pass")
    _mut2 = _MutBuildReviews(repo_root=_dwrepo, hooks=_FakeLoop(),
                             reviewer=_mrev2, lander=_DspLander(ok=True))
    _m2 = _mut2.dispatch({"spec": "VELDO-DM2", "kind": "build"})
    expect("MUTANT whose build path reviews its own build turns the 'reviews nothing' assertion RED (teeth)",
           _mrev2.calls > 0 and FR.current_status("VELDO-DM2", _dwrepo) == "shipped")

# (6) INTEGRATION: the real Dispatcher plugs into the WorkLoop seam. One step claims a ready
# build unit, dispatches it through the build path, leaves the spec at review, and releases the
# claim - the same claim/dispatch/release contract the work loop tests with a fake dispatcher.
with tempfile.TemporaryDirectory() as _direpo, tempfile.TemporaryDirectory() as _diclaims:
    os.makedirs(os.path.join(_direpo, "specs"))
    with open(os.path.join(_direpo, "specs", "VELDO-DI1.md"), "w") as _f:
        _f.write("---\nschema: veldo.spec/v1\nid: VELDO-DI1\ntitle: t\nstatus: ready\n"
                 "owner: dmitry\nlane: standalone\n---\nbody\n")
    _idisp = DSP.Dispatcher(repo_root=_direpo, hooks=_FakeLoop(),
                            reviewer=_DspReviewer(), lander=_DspLander())
    _iloop = WK.WorkLoop("w-dispatch", [], _idisp, repo_root=_direpo, claims_root=_diclaims)
    _iout = _iloop.step()
    expect("work loop + real dispatcher: a claimed build unit is dispatched to the build path",
           _iout is not None and _iout["unit"]["kind"] == "build" and _iout["result"]["ok"] is True)
    expect("work loop + real dispatcher: the built spec is left at review with the claim released",
           FR.current_status("VELDO-DI1", _direpo) == "review"
           and not WK.CL.is_claimed("VELDO-DI1", root=_diclaims))

# --- clean-context dispatch receipt projection (WARP-0909): the BOUNDED receipt a thin
# orchestrator retains per spec so its memory stays flat across a many-spec loop (the
# 2026-07-19 OOM cure). The pure projection copies ONLY allowlisted summary scalars and
# DROPS everything else; the teeth are a size bound plus a mutant that smuggles a bulky
# transcript / the full nested executor result through and is REJECTED. Driven directly over
# fakes, no live agent.
_RCPT_MAX_BYTES = 2048  # a receipt is a handful of small scalars: kilobytes, never megabytes

# A realistic BULKY dispatch outcome: a passing build that ALSO carries the full nested
# executor result (steps + receipt, exactly what _dispatch_build returns today) plus a fat
# review transcript. The projection must keep the summary and drop the bulk.
_rc_big_result = {"state": "built",
                  "steps": [{"name": "build", "ok": True, "log": "x" * 6000}],
                  "receipt": {"criteria_proven": ["AC1"], "detail": "y" * 6000}}
_rc_outcome = {"ok": True, "kind": "build", "spec": "WARP-0909", "status": "review",
               "reviewed": False, "verdict": None, "commit": "c0ffee",
               "proof_digest": "sha256:abc", "result": _rc_big_result, "transcript": "z" * 20000}
_rcpt = WK.dispatch_receipt(_rc_outcome)
expect("WARP-0909 receipt keeps only allowlisted keys (no result/transcript leak)",
       set(_rcpt).issubset(set(WK.RECEIPT_FIELDS))
       and "result" not in _rcpt and "transcript" not in _rcpt)
expect("WARP-0909 receipt carries the summary fields present (spec/kind/ok/status/commit/proof_digest)",
       _rcpt.get("spec") == "WARP-0909" and _rcpt.get("kind") == "build"
       and _rcpt.get("ok") is True and _rcpt.get("status") == "review"
       and _rcpt.get("commit") == "c0ffee" and _rcpt.get("proof_digest") == "sha256:abc")
expect("WARP-0909 receipt is bounded (serialized well under the small byte cap)",
       len(json.dumps(_rcpt)) < _RCPT_MAX_BYTES)
# a review outcome projects verdict/halted_at/reason where present, and drops a bulky land.
_rcpt_rv = WK.dispatch_receipt({"ok": False, "kind": "review", "spec": "WARP-0909",
                                "verdict": "fail", "status": "ready",
                                "land": {"stage": "gate", "log": "q" * 9000}})
expect("WARP-0909 review receipt drops the bulky nested land and keeps the verdict",
       _rcpt_rv.get("verdict") == "fail" and "land" not in _rcpt_rv
       and len(json.dumps(_rcpt_rv)) < _RCPT_MAX_BYTES)

# TEETH: a mutant projection that passes the whole outcome through (a raw copy, or a denylist
# that forgets 'transcript') reintroduces the unbounded retention this contract forbids: it
# carries the bulky fields and blows the size cap the real projection respects. Same input as
# the real projection above, so those assertions are NOT vacuous.
def _rc_mut_receipt(outcome):
    return dict(outcome or {})  # passthrough: the exact regression the projection prevents
_rc_mut = _rc_mut_receipt(_rc_outcome)
expect("WARP-0909 TEETH: a passthrough mutant receipt leaks the bulky result/transcript (allowlist breached)",
       ("result" in _rc_mut or "transcript" in _rc_mut)
       and not set(_rc_mut).issubset(set(WK.RECEIPT_FIELDS)))
expect("WARP-0909 TEETH: a passthrough mutant receipt blows the size bound the real projection respects",
       len(json.dumps(_rc_mut)) >= _RCPT_MAX_BYTES)

# --- in-session worker spawner + account model (WARP-0902, W2 of PLAN-0009): the account
# registry (name -> CLAUDE_CONFIG_DIR profile, persisted under the git common dir like the claim
# ledger) and the REAL fill of the fleet WorkerSpawner seam - assemble each worker's env (its
# account's CLAUDE_CONFIG_DIR, id, scope, caps), spread one account per worker, start over an
# INJECTED in-session primitive (a fake here; the reference FAILS LOUD, never detaches), reconcile
# up/down, retire. Driven over a THROWAWAY accounts root with NO real login and NO process
# spawned. Non-tautology teeth: a spawner that drops the account's CLAUDE_CONFIG_DIR, and a
# reference primitive that fabricates instead of failing loud, each turn an assertion red.
_acspec = importlib.util.spec_from_file_location("veldo_accounts", ROOT / ".veldo/accounts.py")
AC = importlib.util.module_from_spec(_acspec); _acspec.loader.exec_module(AC)
with tempfile.TemporaryDirectory() as _acroot:
    # account_add creates + registers a profile (its CLAUDE_CONFIG_DIR) but performs NO login;
    # resolve returns that dir, list enumerates. No .credentials.json is written by the code.
    _r1 = AC.account_add("alpha", root=_acroot)
    _r2 = AC.account_add("bravo", root=_acroot)
    expect("account add registers a profile dir and performs no login",
           os.path.isdir(_r1["config_dir"]) and AC.resolve("alpha", root=_acroot) == _r1["config_dir"]
           and not os.path.exists(os.path.join(_r1["config_dir"], ".credentials.json")))
    expect("account list enumerates the registered accounts",
           AC.list_accounts(root=_acroot) == ["alpha", "bravo"])
    # a duplicate add and an unknown resolve each fail BY NAME (a named error), never silently.
    try:
        AC.account_add("alpha", root=_acroot); _dup = False
    except AC.DuplicateAccountError:
        _dup = True
    expect("duplicate account add fails by name (DuplicateAccountError)", _dup)
    try:
        AC.resolve("ghost", root=_acroot); _unk = False
    except AC.UnknownAccountError:
        _unk = True
    expect("unknown account resolve fails by name (UnknownAccountError)", _unk)
    # cross-invocation persistence: a FRESH module load over the same root sees the registry,
    # so a registered account is reused with no relogin (the whole point of the persistent map).
    _ac2spec = importlib.util.spec_from_file_location("veldo_accounts_2", ROOT / ".veldo/accounts.py")
    AC2 = importlib.util.module_from_spec(_ac2spec); _ac2spec.loader.exec_module(AC2)
    expect("account registry persists across invocations (fresh load sees both accounts)",
           AC2.list_accounts(root=_acroot) == ["alpha", "bravo"]
           and AC2.resolve("bravo", root=_acroot) == _r2["config_dir"])

    # the spawner assembles the right env (the account's CLAUDE_CONFIG_DIR threaded to the worker)
    # over a FAKE in-session start primitive that records env and returns a handle - no process is
    # spawned. Reconcile up spawns, reconcile down retires, and retiring frees the account slot.
    _started = []
    def _fake_start(wid, env):
        _started.append((wid, dict(env))); return ("in-session", wid)
    _stopped = []
    def _fake_stop(handle):
        _stopped.append(handle)
    _sp, _cap = FL.make_in_session_spawner(
        _fake_start, accounts=["alpha", "bravo"], accounts_root=_acroot,
        capabilities=["linux"], stop=_fake_stop)
    _fll2 = FL.FleetLauncher(_sp, _cap, scope="plan:PLAN-Y")
    _sn, _rt = _fll2.reconcile(2)
    expect("spawner reconciles up to the account-pool capacity",
           _cap == 2 and _sn == 2 and _fll2.active_count() == 2)
    # every started worker carries its account's CLAUDE_CONFIG_DIR (the account threading), its
    # scope, and its capabilities.
    _cfgs = {e[1].get("CLAUDE_CONFIG_DIR") for e in _started}
    _wanted = {AC.resolve("alpha", root=_acroot), AC.resolve("bravo", root=_acroot)}
    expect("spawner threads each account's CLAUDE_CONFIG_DIR to its worker",
           _cfgs == _wanted and all(e[1].get("VELDO_SCOPE") == "plan:PLAN-Y"
                                    and e[1].get("VELDO_CAPABILITIES") == "linux" for e in _started))
    # one account per worker: the two live workers hold two DISTINCT accounts.
    _accts = sorted(e[1].get("VELDO_ACCOUNT") for e in _started)
    expect("spreader gives one account per worker (two workers, two distinct accounts)",
           _accts == ["alpha", "bravo"])
    # reconcile down retires, calling the stop primitive and freeing the account slots.
    _sn2, _rt2 = _fll2.reconcile(0)
    expect("spawner reconciles down, retires, and frees the account slots",
           _rt2 == 2 and _fll2.active_count() == 0 and len(_stopped) == 2)
    # the pool never doubles an account: a THIRD assign from a 2-account spreader fails loud.
    _spr = FL.AccountSpreader(["alpha", "bravo"])
    _a1 = _spr.assign(); _a2 = _spr.assign()
    try:
        _spr.assign(); _over = False
    except FL.NoAccountAvailableError:
        _over = True
    expect("spreader never doubles an account (a 3rd assign on 2 accounts fails loud)",
           _a1 != _a2 and _over)
    # a released account slot really comes back (re-assignable), so a drained fleet can respawn.
    _spr.release(_a1)
    expect("a released account slot is re-assignable", _spr.assign() == _a1)

    # account selection threads through a full launcher run: a spread fleet scales up to the
    # account count, drains, and retires every worker (freeing every account), each worker
    # carrying its own account's CLAUDE_CONFIG_DIR.
    _rst = []
    def _rstart(wid, env):
        _rst.append(dict(env)); return ("in-session", wid)
    _rsp, _rcap = FL.make_in_session_spawner(_rstart, accounts=["alpha", "bravo"],
                                             accounts_root=_acroot)
    _rfll = FL.FleetLauncher(_rsp, _rcap, scope="plan:PLAN-Z"); _rflw = _FLWaiter()
    _rfll.run(_FLController([{"desired": 2, "work_remains": True},
                             {"desired": 2, "work_remains": True}]), _rflw)
    expect("account fleet run scales to the account count, drains, and retires every worker",
           _rcap == 2 and len({e.get("CLAUDE_CONFIG_DIR") for e in _rst}) == 2
           and _rfll.active_count() == 0)

    # the reference in-session start primitive FAILS LOUD (no wired mechanism): it never
    # fabricates a handle and never detaches a process.
    try:
        FL.in_session_start("w-real", {AC.CONFIG_DIR_ENV: _r1["config_dir"]}); _loud = False
    except FL.SpawnPrimitiveError:
        _loud = True
    expect("reference spawn primitive fails loud (no fabricated handle, no detached process)", _loud)

    # NON-TAUTOLOGY TEETH.
    # (1) a spawner that DROPS the selected account's CLAUDE_CONFIG_DIR turns the account-
    # threading assertion red: the started env carries no config dir, so the worker would run as
    # the wrong account / prompt for a login. Same fake start; only the env assembly is mutated.
    class _MutNoConfigDir(FL.InSessionSpawner):
        def _assemble_env(self, worker_id, scope, account):
            env = super()._assemble_env(worker_id, scope, account)
            env.pop(AC.CONFIG_DIR_ENV, None)   # forget to thread the account
            return env
    _mstarted = []
    def _mstart(wid, env):
        _mstarted.append(dict(env)); return ("in-session", wid)
    _msp = _MutNoConfigDir(_mstart, FL.AccountSpreader(["alpha"]), accounts_root=_acroot)
    FL.FleetLauncher(_msp, 1).reconcile(1)
    expect("MUTANT spawner that drops CLAUDE_CONFIG_DIR turns the account-threading assertion RED (teeth)",
           _mstarted and _mstarted[0].get(AC.CONFIG_DIR_ENV) is None)
    # (2) a reference primitive that FABRICATES a handle instead of failing loud turns the
    # fail-loud assertion red: it returns a handle and raises nothing.
    def _fabricating_start(wid, env):
        return ("fabricated", wid)   # a rogue: pretends to have started something
    try:
        _fh = _fabricating_start("w", {AC.CONFIG_DIR_ENV: "x"}); _fab_loud = False
    except FL.SpawnPrimitiveError:
        _fab_loud = True
    expect("MUTANT fabricating primitive does NOT fail loud, so the fail-loud assertion has teeth",
           _fab_loud is False and _fh == ("fabricated", "w"))

# --- real in-session worker spawner (WARP-1010): fill the WorkerSpawner START seam with a REAL
# worktree-isolated IN-SESSION start, NEVER a detached process. The launch is AGENT-MEDIATED: a git
# worktree isolates the worker's tree (an in-line git call, not a spawned worker) and an INJECTED
# in-session dispatch starts the worker; a fake provisioner + fake dispatch drive the gate (the live
# start is a REFERENCE, not gate-run). The no-detach boundary has TEETH: fleet.py's spawn path uses
# NO detached/background process primitive for the worker, and a mutation that introduces one fails
# the check. Non-tautology teeth throughout: an unwired dispatch and a dispatch that starts no worker
# each fail loud (never a fabricated handle, never a leaked worktree).
class _FakeWorktree:
    """A fake WorktreeProvisioner: records add/remove and returns a fake path, spawning nothing and
    touching no git, so the CONTROL LOGIC is exercised with no real worktree created in the gate."""
    def __init__(self):
        self.added = []; self.removed = []
    def add(self, worker_id):
        p = "/wt/" + str(worker_id); self.added.append(p); return p
    def remove(self, path):
        if path:
            self.removed.append(path)
with tempfile.TemporaryDirectory() as _wtroot:
    AC.account_add("alpha", root=_wtroot); AC.account_add("bravo", root=_wtroot)
    _disp = []
    def _dispatch(worker_id, env, worktree):
        _disp.append({"wid": worker_id, "env": dict(env), "wt": worktree})
        return ("in-session-worker", worker_id)   # a fake in-session worker handle, nothing detached
    _dstopped = []
    def _dispatch_stop(worker):
        _dstopped.append(worker)
    _wtp = _FakeWorktree()
    _wsp, _wcap = FL.make_worktree_in_session_spawner(
        _dispatch, accounts=["alpha", "bravo"], accounts_root=_wtroot, capabilities=["linux"],
        dispatch_stop=_dispatch_stop, provisioner=_wtp)
    _wfll = FL.FleetLauncher(_wsp, _wcap, scope="plan:PLAN-WT")
    _wsn, _ = _wfll.reconcile(2)
    # AC1: each worker gets a provisioned worktree and is dispatched in-session, carrying its env.
    expect("WARP-1010 AC1: worktree-isolated start provisions a worktree per worker and dispatches in-session",
           _wcap == 2 and _wsn == 2 and len(_wtp.added) == 2 and len(_disp) == 2
           and all(d["wt"] in _wtp.added for d in _disp))
    expect("WARP-1010 AC1: the dispatch carries the worker's account CLAUDE_CONFIG_DIR, scope, and worktree",
           {d["env"].get(AC.CONFIG_DIR_ENV) for d in _disp}
           == {AC.resolve("alpha", root=_wtroot), AC.resolve("bravo", root=_wtroot)}
           and all(d["env"].get("VELDO_SCOPE") == "plan:PLAN-WT" for d in _disp)
           and all(d["wt"] for d in _disp))
    # AC1: the returned handle is retireable - retire stops the worker AND removes its worktree.
    _wsn2, _wrt2 = _wfll.reconcile(0)
    expect("WARP-1010 AC1: retire stops the in-session worker and removes its worktree (retireable handle)",
           _wrt2 == 2 and _wfll.active_count() == 0
           and len(_dstopped) == 2 and sorted(_wtp.removed) == sorted(_wtp.added))
    # AC1: a full launcher run scales to the account pool, drains, and retires every worker, each
    # having been dispatched into its own worktree under its own account (one account per worker).
    _wtp2 = _FakeWorktree(); _disp2 = []
    def _dispatch2(worker_id, env, worktree):
        _disp2.append(env.get("VELDO_ACCOUNT")); return ("w", worker_id)
    _wsp2, _wcap2 = FL.make_worktree_in_session_spawner(
        _dispatch2, accounts=["alpha", "bravo"], accounts_root=_wtroot, provisioner=_wtp2)
    _wfll2 = FL.FleetLauncher(_wsp2, _wcap2, scope="plan:PLAN-WT2")
    _wfll2.run(_FLController([{"desired": 2, "work_remains": True},
                              {"desired": 2, "work_remains": True}]), _FLWaiter())
    expect("WARP-1010 AC1: a worktree fleet run scales to the account count, one account per worker, and drains",
           _wcap2 == 2 and sorted(_disp2) == ["alpha", "bravo"]
           and _wfll2.active_count() == 0 and sorted(_wtp2.removed) == sorted(_wtp2.added)
           and len(_wtp2.added) == 2)
    # AC4: FAIL LOUD where no in-session mechanism is wired - dispatch None delegates to the fail-loud
    # reference and provisions no worktree (no fabricated handle, no detach).
    _wtp_none = _FakeWorktree()
    _loud_start = FL.WorktreeInSessionStart(None, provisioner=_wtp_none)
    try:
        _loud_start("w-x", {AC.CONFIG_DIR_ENV: "x"}); _wt_loud = False
    except FL.SpawnPrimitiveError:
        _wt_loud = True
    expect("WARP-1010 AC4: with no in-session dispatch wired the start FAILS LOUD (no worktree, no fabricated handle)",
           _wt_loud is True and _wtp_none.added == [])
    # AC4: a dispatch that returns no worker also fails loud, and its worktree is removed (never a
    # leaked worktree, never a faked running worker).
    _wtp_n = _FakeWorktree()
    _nstart = FL.WorktreeInSessionStart(lambda wid, env, wt: None, provisioner=_wtp_n)
    try:
        _nstart("w-n", {AC.CONFIG_DIR_ENV: "x"}); _n_loud = False
    except FL.SpawnPrimitiveError:
        _n_loud = True
    expect("WARP-1010 AC4: a dispatch that starts no worker fails loud and leaks no worktree",
           _n_loud is True and _wtp_n.added == _wtp_n.removed and len(_wtp_n.added) == 1)
    # AC4: a dispatch that RAISES tears the worktree down and re-raises (no leak).
    _wtp_r = _FakeWorktree()
    def _raise_dispatch(wid, env, wt):
        raise RuntimeError("boom")
    _rstart = FL.WorktreeInSessionStart(_raise_dispatch, provisioner=_wtp_r)
    try:
        _rstart("w-r", {AC.CONFIG_DIR_ENV: "x"}); _r_raised = False
    except RuntimeError:
        _r_raised = True
    expect("WARP-1010 AC4: a dispatch that raises removes the worktree and re-raises (no leaked worktree)",
           _r_raised is True and _wtp_r.added == _wtp_r.removed and len(_wtp_r.added) == 1)

# AC2/AC3: the no-detached-process boundary has TEETH (the supervisor spawn-on-install posture, VELDO-
# 0907). fleet.py's worker spawn path uses NO detached/background process primitive for the worker:
# its only external program is an in-line `git worktree` (git, not a worker), and the worker launch
# is an INJECTED in-session dispatch seam. A mutation that introduces a detached spawn (a Popen, a
# background claude -p, a fork/setsid/nohup) flips this check RED, so a future change cannot slip a
# rogue process past the gate.
_fl_src = (ROOT / ".veldo/fleet.py").read_text()
_DETACH_TOKENS = ("Popen", "os.fork", "os.forkpty", "os.exec", "os.spawn", "os.posix_spawn",
                  "os.system", "setsid", "nohup", "start_new_session", "creationflags",
                  "multiprocessing", "pty.spawn", "claude -p")
def _no_detached_worker_spawn(src):
    return not any(tok in src for tok in _DETACH_TOKENS)
expect("WARP-1010 AC2/AC3: fleet.py spawns no detached/background worker (no Popen/fork/exec/spawn/setsid/nohup/claude -p)",
       _no_detached_worker_spawn(_fl_src))
# the only subprocess use is the in-line git worktree helper (git only), imported LAZILY (never at
# module top), and the worker launch is a dispatch seam - not a process this module spawns.
_fl_head = _fl_src.split("\ndef ", 1)[0].split("\nclass ", 1)[0]
expect("WARP-1010 AC2: fleet.py does not import subprocess at module top (the git worktree helper imports it lazily)",
       "import subprocess" not in _fl_head and "import subprocess" in _fl_src)
expect("WARP-1010 AC2: fleet.py's only external program is an in-line `git worktree` (git, never a worker)",
       'subprocess.run(["git", "worktree"]' in _fl_src and "Popen" not in _fl_src
       and "self._dispatch(worker_id, env, worktree)" in _fl_src)
# MUTATION teeth: inject a detached worker spawn and prove the no-detach check goes RED (not vacuous).
_fl_mut_popen = _fl_src + '\n_p = subprocess.Popen(["claude", "-p", prompt], start_new_session=True)\n'
_fl_mut_bg = _fl_src + '\nos.system("claude -p work &")\n'
expect("WARP-1010 AC3 TEETH: a detached subprocess.Popen(claude -p) mutation fails the no-detach check",
       _no_detached_worker_spawn(_fl_mut_popen) is False)
expect("WARP-1010 AC3 TEETH: a background `claude -p` (os.system) mutation fails the no-detach check",
       _no_detached_worker_spawn(_fl_mut_bg) is False)

# --- per-account governor + in-session resume-waiter (WARP-0903, W3 of PLAN-0009): pace each
# account against its OWN session/weekly windows and OWN measured burn by REUSING the single-pool
# control law per account (desired_workers / resume_at, unchanged), sum the per-account desired
# capped at the pool max so a spent account yields 0 while others keep pacing, attribute burn by
# the account tag the worker carries, and fill the launcher's wait seam with a REAL in-session
# waiter driven here by a FAKE clock (deterministic now_epoch, no real sleeping). Non-tautology
# teeth: a governor that zeroes the WHOLE pool when one account is spent, and a launcher that
# resumes WITHOUT re-checking desired, each turn an assertion red.
# a spend event tagged with the account it was produced under (VELDO_ACCOUNT from W2)
def _agev(secs_ago, tokens, account):
    at = (_GNOW - _gov_dt.timedelta(seconds=secs_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"at": at, "tokens": tokens, "type": "x", "account": account}
_AG_SESSION = GOV.Window("session", 100, 1000)             # 100s / 1000 tokens (small for the gate)
_AG_WEEKLY = GOV.Window("weekly", 7 * 24 * 3600, 10 ** 9)  # effectively non-binding here
_AG_WINS = [_AG_SESSION, _AG_WEEKLY]
# burn attribution (AC2): events.py tags a spend event with its account, and the governor filters
# by it so one account's spend never counts against another's window.
_ag_tagged = EV.make_event("gate.passed", correlation_id="WARP-0903", tokens=500, account="alpha")
expect("events.make_event tags a spend event with its account (VELDO_ACCOUNT attribution)",
       _ag_tagged.get("account") == "alpha" and _ag_tagged.get("tokens") == 500)
expect("events.make_event leaves the account absent when untagged (old events stay valid)",
       "account" not in EV.make_event("gate.passed", correlation_id="WARP-0903", tokens=500))
_mixed = [_agev(10, 1000, "alpha"), _agev(60, 5000, "bravo")]
expect("burn is attributed per account (alpha's window sees only alpha's spend, not bravo's)",
       GOV.windowed_spend(GOV.events_for_account(_mixed, "alpha"), _GNOW_E, 100) == 1000
       and GOV.windowed_spend(_mixed, _GNOW_E, 100) == 6000)
expect("events_for_account partitions the stream by the account tag",
       [e["tokens"] for e in GOV.events_for_account(_mixed, "bravo")] == [5000])
# AC1 per-account pacing: one account spent, others with budget -> the pool is NOT stalled, and
# the fleet desired is the per-account SUM capped at the pool max.
_pace_stream = [_agev(10, 1000, "spent")]   # 'spent' has burned its whole 1000-token session window
_p_spent = GOV.AccountPacer("spent", _AG_WINS, per_worker_rate=2.0, max_workers=2)
_p_b = GOV.AccountPacer("bud_b", _AG_WINS, per_worker_rate=0.0, max_workers=2)   # no burn -> bootstrap
_p_c = GOV.AccountPacer("bud_c", _AG_WINS, per_worker_rate=0.0, max_workers=2)   # no burn -> bootstrap
_ag = GOV.AccountGovernor([_p_spent, _p_b, _p_c], pool_max=3)
expect("a spent account contributes 0 desired workers",
       _ag.account_desired("spent", _pace_stream, _GNOW_E) == 0)
expect("an account with no burn yet bootstraps to its cap (single-pool bootstrap, per account)",
       _ag.account_desired("bud_b", _pace_stream, _GNOW_E) == 2
       and _ag.account_per_worker_rate("bud_b", _pace_stream, _GNOW_E, 100, 4) == 0.0)
expect("fleet desired is the per-account SUM capped at the pool max (0+2+2=4 -> 3), pool not stalled",
       _ag.desired(_pace_stream, _GNOW_E) == 3)
# reuse (not reimplementation): per-account desired IS desired_workers over the account's own stream
expect("per-account desired REUSES the single-pool control law (identical to desired_workers)",
       _ag.account_desired("spent", _pace_stream, _GNOW_E)
       == GOV.desired_workers(_p_spent.windows, GOV.events_for_account(_pace_stream, "spent"),
                              _GNOW_E, _p_spent.per_worker_rate, _p_spent.max_workers))
# a per-account limit cooldown zeroes only THAT account, and its resume respects the cooldown.
_p_lc = GOV.AccountPacer("cooling", _AG_WINS, per_worker_rate=2.0, max_workers=2,
                         limit_cooldown_until=_GNOW_E + 300)
_ag_lc = GOV.AccountGovernor([_p_lc, _p_b], pool_max=4)
expect("an account in a limit cooldown yields 0 while another keeps pacing (pool not stalled)",
       _ag_lc.account_desired("cooling", [], _GNOW_E) == 0 and _ag_lc.desired([], _GNOW_E) == 2)
expect("a cooling account's resume respects its own cooldown end",
       _ag_lc.account_resume_at("cooling", [], _GNOW_E) == _GNOW_E + 300)
# TEETH (AC5): a governor that zeroes the WHOLE pool when ANY account is spent stalls the pool,
# turning the 'pool not stalled' assertion red. The real governor keeps a positive desired.
def _mut_whole_pool_desired(gov, events, now_epoch):
    per = [gov.account_desired(n, events, now_epoch) for n in gov.pacers]
    return 0 if any(d == 0 for d in per) else min(sum(per), gov.pool_max)   # WRONG: any spent -> stall
expect("MUTANT whole-pool-zeroing governor stalls the pool when one account is spent (teeth)",
       _mut_whole_pool_desired(_ag, _pace_stream, _GNOW_E) == 0
       and _ag.desired(_pace_stream, _GNOW_E) > 0)
# AC3 per-account resume timing: each backed-off account resumes when ITS OWN window rolls,
# independent of the others. alpha spent 10s ago and bravo 60s ago (each over its own 100s/1000
# window) resume at their own reset (now+90 and now+40).
_res_stream = [_agev(10, 1000, "alpha"), _agev(60, 1000, "bravo")]
_pr_a = GOV.AccountPacer("alpha", _AG_WINS, per_worker_rate=2.0, max_workers=1)
_pr_b = GOV.AccountPacer("bravo", _AG_WINS, per_worker_rate=2.0, max_workers=1)
_ag_res = GOV.AccountGovernor([_pr_a, _pr_b], pool_max=2)
_r_alpha = _ag_res.account_resume_at("alpha", _res_stream, _GNOW_E)
_r_bravo = _ag_res.account_resume_at("bravo", _res_stream, _GNOW_E)
expect("alpha resumes when ITS OWN 100s window rolls (now + 90), from its own burn",
       abs((_r_alpha - _GNOW_E) - 90) < 1.0)
expect("bravo resumes when ITS OWN window rolls (now + 40), independent of alpha",
       abs((_r_bravo - _GNOW_E) - 40) < 1.0 and _r_bravo < _r_alpha)
# TEETH: computing bravo's resume over the UNFILTERED (mixed) stream folds alpha's spend in and
# mis-times it to now+90, so per-account filtering is load-bearing, not cosmetic.
_r_bravo_mixed = GOV.resume_at(_AG_WINS, _res_stream, _GNOW_E)
expect("MUTANT unattributed resume (mixed stream) mis-times bravo to now+90 (attribution teeth)",
       abs((_r_bravo_mixed - _GNOW_E) - 90) < 1.0 and _r_bravo_mixed != _r_bravo)
expect("pool resume_at after a full backoff is the earliest account's own reset (now+40)",
       abs((_ag_res.resume_at(_res_stream, _GNOW_E) - _GNOW_E) - 40) < 1.0)
# AC4 the REAL in-session waiter waits with a fake clock (no real sleeping), in BOUNDED steps,
# spawning nothing (its only primitive is an injected in-session sleep).
class _AGClock:
    def __init__(self, t=1000.0):
        self.t = float(t); self.slept = []
    def time(self):
        return self.t
    def sleep(self, d):        # a FAKE in-session sleep: records and advances the fake clock only
        self.slept.append(d); self.t += d
_wc = _AGClock(1000.0)
_wtr = FL.InSessionWaiter(interval=5.0, step=5.0, clock=_wc.time, sleep=_wc.sleep)
_wsteps = _wtr.wait_until(1037.0)
expect("in-session waiter blocks until the epoch in bounded in-session steps (no real sleep)",
       _wc.t == 1037.0 and _wsteps == 8 and all(s <= 5.0 for s in _wc.slept)
       and abs(sum(_wc.slept) - 37.0) < 1e-9)
_wc_past = _AGClock(2000.0)
_wtr_past = FL.InSessionWaiter(clock=_wc_past.time, sleep=_wc_past.sleep)
expect("in-session waiter returns immediately for a past-or-now epoch (no sleep, no spawn)",
       _wtr_past.wait_until(1500.0) == 0 and _wc_past.slept == [])
_wc_tick = _AGClock(0.0)
_wtr_tick = FL.InSessionWaiter(interval=7.0, step=5.0, clock=_wc_tick.time, sleep=_wc_tick.sleep)
expect("in-session waiter tick advances exactly one control interval in-session",
       _wtr_tick.tick() == 7.0 and _wc_tick.slept == [7.0] and _wc_tick.t == 7.0)
# AC4 the launcher RE-CHECKS desired after the wait: a backed-off pool whose FIRST resume is still
# spent must wait AGAIN (re-check) instead of spawning into the still-spent window. Driven by the
# REAL InSessionWaiter over a fake clock; a spy spawner records the fake-clock time at each spawn.
class _AGSpySpawner(FL.WorkerSpawner):
    def __init__(self, clock):
        self._clock = clock; self.spawn_times = []; self.retired = 0
    def spawn(self, wid, scope):
        self.spawn_times.append(self._clock()); return ("h", wid)
    def retire(self, handle):
        self.retired += 1
def _recheck_steps():
    return [{"desired": 0, "work_remains": True, "resume_at": 1100},   # back off, wait to 1100
            {"desired": 0, "work_remains": True, "resume_at": 1200},   # re-check at 1100: STILL 0, wait to 1200
            {"desired": 2, "work_remains": True},                      # re-check at 1200: runnable -> spawn 2
            {"desired": 0, "work_remains": False}]                     # drain
_rc_clock = _AGClock(1000.0)
_rc_waiter = FL.InSessionWaiter(interval=5.0, step=5.0, clock=_rc_clock.time, sleep=_rc_clock.sleep)
_rc_spawner = _AGSpySpawner(_rc_clock.time)
_rc_launcher = FL.FleetLauncher(_rc_spawner, 4)
_rc_launcher.run(_FLController(_recheck_steps()), _rc_waiter)
expect("launcher re-checks desired after the wait: it waits past the still-spent first resume and "
       "spawns only after the window rolled (at 1200, not 1100)",
       _rc_spawner.spawn_times == [1200.0, 1200.0] and _rc_clock.t >= 1200.0
       and _rc_launcher.active_count() == 0)
# TEETH: a launcher that resumes WITHOUT re-checking desired spawns at the FIRST resume (1100),
# straight into the still-spent window, turning the re-check assertion red.
class _MutNoRecheckLauncher(FL.FleetLauncher):
    def run(self, controller, waiter, max_ticks=100000):
        for _t in range(1, max_ticks + 1):
            target = max(0, min(controller.desired(), self.max_workers))
            self.reconcile(target)
            if target == 0:
                if not controller.work_remains():
                    break
                self.reconcile(0)
                waiter.wait_until(controller.resume_at())
                self.reconcile(self.max_workers)   # WRONG: spawn without re-checking desired()
                break
            waiter.tick()
        return 0
_mut_clock = _AGClock(1000.0)
_mut_waiter = FL.InSessionWaiter(interval=5.0, step=5.0, clock=_mut_clock.time, sleep=_mut_clock.sleep)
_mut_spawner = _AGSpySpawner(_mut_clock.time)
_MutNoRecheckLauncher(_mut_spawner, 4).run(_FLController(_recheck_steps()), _mut_waiter)
expect("MUTANT no-re-check launcher spawns at the FIRST resume (1100) into a still-spent window (teeth)",
       _mut_spawner.spawn_times and _mut_spawner.spawn_times[0] == 1100.0)

# --- veldo CLI front door (WARP-0904, W4 of PLAN-0009): the single `veldo` executable that
# dispatches subcommands to the EXISTING modules with no new control logic. Driven over
# THROWAWAY roots with NO live agent, NO detached process, and NO real fleet run - the read/
# registry subcommands route to their modules (proven both in-process AND by running the real
# bin/veldo executable over a throwaway root), work/fleet assemble the real W1-W3 machinery but
# fail loud without an agent or a real spawn, and an unknown subcommand / bad args / unknown
# account each fail loud (nonzero). Non-tautology teeth: a dispatcher that swallowed an unknown
# subcommand (exit 0), a work wiring that fabricated a build, and a fleet wiring that spawned
# instead of failing loud, each turn an assertion red.
import contextlib as _c904
import io as _io904
from importlib.machinery import SourceFileLoader as _SFL904
_veldo_bin = ROOT / "bin" / "veldo"
_cli_loader = _SFL904("veldo_cli_904", str(_veldo_bin))
_clispec = importlib.util.spec_from_loader("veldo_cli_904", _cli_loader)
CLI = importlib.util.module_from_spec(_clispec); _cli_loader.exec_module(CLI)


def _route904(argv):
    """Run the CLI dispatcher and capture (code, stdout, stderr) - no process, no agent."""
    _o, _e = _io904.StringIO(), _io904.StringIO()
    with _c904.redirect_stdout(_o), _c904.redirect_stderr(_e):
        _code = CLI.route(list(argv))
    return _code, _o.getvalue(), _e.getvalue()


# the executable itself: present, and executable with mode 0755 (DoD).
expect("bin/veldo exists and is executable (exec bit set, umask-independent)",
       _veldo_bin.exists() and (os.stat(str(_veldo_bin)).st_mode & 0o111) != 0)

# AC2: run the REAL bin/veldo executable over a throwaway root and prove it routes to the module.
with tempfile.TemporaryDirectory() as _cliacct:
    _cli_env = dict(os.environ); _cli_env["VELDO_RUNS_ROOT"] = _cliacct
    _add = subprocess.run([str(_veldo_bin), "account", "add", "alpha"],
                          capture_output=True, text=True, env=_cli_env)
    _lst = subprocess.run([str(_veldo_bin), "account", "list"],
                          capture_output=True, text=True, env=_cli_env)
    expect("bin/veldo account add|list runs the executable and routes to accounts.py",
           _add.returncode == 0 and _lst.returncode == 0 and "alpha" in _lst.stdout)
    _st = subprocess.run([str(_veldo_bin), "status", "--json"],
                         capture_output=True, text=True, env=_cli_env)
    _st_ok = False
    try:
        _st_ok = json.loads(_st.stdout).get("schema") == "veldo.runstatus/v1"
    except ValueError:
        _st_ok = False
    expect("bin/veldo status --json runs the executable and routes to runstatus.py",
           _st.returncode == 0 and _st_ok)

# AC2 (in-process): a representative call of each read/registry subcommand reaches its module.
with tempfile.TemporaryDirectory() as _cliruns:
    _env0 = os.environ.get("VELDO_RUNS_ROOT"); os.environ["VELDO_RUNS_ROOT"] = _cliruns
    try:
        _rc_ans = _route904(["answer", "no-such-run", "hi"])
        expect("veldo answer routes to runcmd.py (runcmd's own 'no such run' refusal, nonzero)",
               _rc_ans[0] == 2 and "no such run" in _rc_ans[2])
        _rc_ab = _route904(["abort", "no-such-run"])
        expect("veldo abort routes to runcmd.py (same runcmd refusal path)",
               _rc_ab[0] == 2 and "no such run" in _rc_ab[2])
        _rc_acl = _route904(["account", "list"])
        expect("veldo account list routes to accounts.py (in-process)",
               _rc_acl[0] == 0 and "no accounts registered" in _rc_acl[1])
        _rc_stj = _route904(["status", "--json"])
        _js_ok = False
        try:
            _js_ok = json.loads(_rc_stj[1]).get("schema") == "veldo.runstatus/v1"
        except ValueError:
            _js_ok = False
        expect("veldo status --json routes to runstatus.py (its read model)", _rc_stj[0] == 0 and _js_ok)
        _rc_w = _route904(["watch"])
        expect("veldo watch routes to runstatus.py (renders the compact view)",
               _rc_w[0] == 0 and "VELDO status" in _rc_w[1])

        # AC1/AC5: an unknown subcommand and bad arguments fail loud (nonzero), never a silent no-op.
        _rc_unk = _route904(["frobnicate"])
        expect("unknown subcommand fails loud (nonzero) with an honest message",
               _rc_unk[0] != 0 and "unknown subcommand" in _rc_unk[2] and "frobnicate" in _rc_unk[2])
        expect("no subcommand fails loud (nonzero)", _route904([])[0] != 0)
        expect("bad args fail loud: fleet without N (nonzero)", _route904(["fleet"])[0] != 0)
        expect("bad args fail loud: fleet with a non-integer N (nonzero)",
               _route904(["fleet", "notanint"])[0] != 0)
        # TEETH: a dispatcher that SWALLOWED an unknown subcommand (returned 0) would turn the
        # fail-loud assertion red. The real route() returns nonzero; the mutant returns 0.
        def _mut_swallow_unknown(argv):
            return 0   # WRONG: treat an unknown subcommand as a silent no-op success
        expect("MUTANT swallow-unknown dispatcher returns 0 for a bad subcommand (teeth)",
               _mut_swallow_unknown(["frobnicate"]) == 0 and _route904(["frobnicate"])[0] != 0)
    finally:
        if _env0 is None:
            os.environ.pop("VELDO_RUNS_ROOT", None)
        else:
            os.environ["VELDO_RUNS_ROOT"] = _env0

# AC3: an unknown --account fails BY NAME, and the except ACTUALLY catches it. CARRY-FORWARD (W2):
# fleet.py double-loads accounts.py, so its AccountError family is DISTINCT class objects; a
# handler that caught only a freshly-imported accounts.UnknownAccountError would NOT match.
with tempfile.TemporaryDirectory() as _cliacc2:
    # (a) the double-load gotcha is REAL: the fleet raises through fleet.py's OWN accounts copy.
    _ghost_err = None
    try:
        FL.veldo_account_fleet(
            _FLController([{"desired": 0, "work_remains": False}]), _FLWaiter(),
            (lambda wid, env: ("h", wid)), account="ghost",
            accounts_root=_cliacc2, max_workers=1)
    except Exception as _e904:
        _ghost_err = _e904
    expect("fleet unknown account raises fleet.py's OWN AccountError class (double-load is real)",
           isinstance(_ghost_err, FL.ACCT.UnknownAccountError)
           and not isinstance(_ghost_err, AC.UnknownAccountError))
    # (b) the CLI's base-tuple handler ACTUALLY catches it: route returns nonzero and names the
    # account (never a propagated raise, which is what a wrong single-class except would do).
    _env0b = os.environ.get("VELDO_RUNS_ROOT"); os.environ["VELDO_RUNS_ROOT"] = _cliacc2
    try:
        _gc = _route904(["fleet", "2", "--account", "ghost"])
    finally:
        if _env0b is None:
            os.environ.pop("VELDO_RUNS_ROOT", None)
        else:
            os.environ["VELDO_RUNS_ROOT"] = _env0b
    expect("unknown --account fails BY NAME (nonzero, names the account) and the except CATCHES it",
           _gc[0] == 2 and "ghost" in _gc[2])
    # the base tuple the handler catches includes the CLI's OWN fleet copy's AccountError (the copy
    # cmd_fleet raises through), which is a DISTINCT object from a freshly-imported accounts module -
    # this is the load-bearing fix for the W2 double-load gotcha.
    _cli_bases = CLI._account_error_bases()
    expect("CLI account-error base tuple includes fleet.py's double-loaded AccountError (the fix)",
           CLI._fleet().ACCT.AccountError in _cli_bases
           and CLI._fleet().ACCT.AccountError is not AC.AccountError)

# AC3/AC5: veldo work assembles the real single-worker loop but FAILS LOUD with no agent wired,
# and NEVER fabricates a build. Driven over a THROWAWAY repo + claims root. Teeth: a mutant
# dispatcher with a fake ok build hook fabricates the build (spec advances, exit 0).
with tempfile.TemporaryDirectory() as _cwrepo, tempfile.TemporaryDirectory() as _cwclaims:
    os.makedirs(os.path.join(_cwrepo, "specs"))
    with open(os.path.join(_cwrepo, "specs", "VELDO-CW1.md"), "w") as _f:
        _f.write("---\nschema: veldo.spec/v1\nid: VELDO-CW1\ntitle: t\nstatus: ready\n"
                 "owner: dmitry\nlane: standalone\n---\nbody\n")
    _cw_code = CLI.cmd_work(repo_root=_cwrepo, claims_root=_cwclaims)
    expect("veldo work fails loud (nonzero) with no agent wired and does NOT fabricate a build",
           _cw_code != 0 and FR.current_status("VELDO-CW1", _cwrepo) == "ready")
    # TEETH: a dispatcher that FABRICATES the build/review advances the spec past ready and exits 0.
    with open(os.path.join(_cwrepo, "specs", "VELDO-CW2.md"), "w") as _f:
        _f.write("---\nschema: veldo.spec/v1\nid: VELDO-CW2\ntitle: t\nstatus: ready\n"
                 "owner: dmitry\nlane: standalone\n---\nbody\n")
    _mut_disp = DSP.Dispatcher(repo_root=_cwrepo, hooks=_FakeLoop(),
                               reviewer=_DspReviewer(), lander=_DspLander())
    _cw_mut = CLI.cmd_work(repo_root=_cwrepo, claims_root=_cwclaims, dispatcher=_mut_disp)
    expect("MUTANT work wiring that fabricates a build advances the spec and exits 0 (teeth)",
           _cw_mut == 0 and FR.current_status("VELDO-CW2", _cwrepo) != "ready")

# AC3/AC5: veldo fleet assembles the elastic launcher (W2 spawner + W3 governor seam + waiter) but
# the spawn primitive stays the fail-loud in-session reference, so it FAILS LOUD at the first
# spawn and spawns/detaches NOTHING. Teeth: a fabricating start primitive lets the fleet spawn.
with tempfile.TemporaryDirectory() as _cliflt:
    AC.account_add("alpha", root=_cliflt)   # one registered account (capacity 1)
    # the CLI loads its OWN fleet copy, so the loud error is CLI._fleet().SpawnPrimitiveError
    # (the same double-load reality the account-error handling accounts for).
    _CLIFL = CLI._fleet()
    _spawn_loud = None
    try:
        CLI.cmd_fleet(1, account="alpha", accounts_root=_cliflt,
                      controller=_FLController([{"desired": 1, "work_remains": True}]),
                      waiter=_FLWaiter(), start=None)   # start=None -> fail-loud in_session_start
        _spawn_loud = False
    except _CLIFL.SpawnPrimitiveError:
        _spawn_loud = True
    expect("veldo fleet fails loud at the spawn primitive with no in-session start wired (spawns nothing)",
           _spawn_loud is True)
    # TEETH: a fabricating start returns a handle instead of failing loud, so the fleet 'spawns'
    # (records a start) and drains without raising - turning the fail-loud/no-spawn assertion red.
    _fab_starts = []
    def _fab_start904(wid, env):
        _fab_starts.append(wid); return ("fabricated", wid)   # rogue: pretends to have started
    _fab_ticks = CLI.cmd_fleet(
        1, account="alpha", accounts_root=_cliflt,
        controller=_FLController([{"desired": 1, "work_remains": True},
                                  {"desired": 0, "work_remains": False}]),
        waiter=_FLWaiter(), start=_fab_start904)
    expect("MUTANT fabricating start makes the fleet spawn (records a start) instead of failing loud (teeth)",
           len(_fab_starts) == 1 and isinstance(_fab_ticks, int))

# AC3: the W3 AccountGovernor is genuinely wired (not faked). _build_governor_controller assembles
# an AccountGovernor over the registered accounts, and the controller's desired() REUSES that
# governor's arithmetic; work_remains() IS the frontier. Without a token budget it fails loud
# rather than fabricate one (RULE #2 spend gate / RULE #6).
with tempfile.TemporaryDirectory() as _cligov, tempfile.TemporaryDirectory() as _cligovrepo:
    AC.account_add("alpha", root=_cligov); AC.account_add("bravo", root=_cligov)
    os.makedirs(os.path.join(_cligovrepo, "specs"))
    _gwins = [GOV.Window("session", 100, 1000), GOV.Window("weekly", 7 * 24 * 3600, 10 ** 9)]
    _gevents = os.path.join(_cligov, "events.jsonl"); open(_gevents, "w").close()  # no burn -> bootstrap
    _gctl = CLI._build_governor_controller(
        accounts_root=_cligov, windows=_gwins, repo_root=_cligovrepo,
        claims_root=_cligov, events_path=_gevents, now=(lambda: _GNOW_E))
    expect("governor-backed controller desired() REUSES the W3 AccountGovernor (identical count)",
           _gctl.desired() == _gctl._gov.desired([], _GNOW_E) and _gctl.desired() == 2)
    expect("governor-backed controller work_remains() reflects the frontier (empty -> no work)",
           _gctl.work_remains() is False)
    _budget_loud = False
    try:
        CLI._build_governor_controller(accounts_root=_cligov, windows=None)
    except ValueError:
        _budget_loud = True
    expect("fleet controller with no token budget fails loud (no fabricated budget)", _budget_loud)

# --- fleet supervisor (WARP-0907, W7 of PLAN-0009): the in-session resume is the WIRED DEFAULT of
# veldo fleet, and an OPT-IN external supervisor (a user systemd timer, OFF by default) closes the
# killed-session gap. The sensitive boundary (feedback_no_rogue_processes) is proven adversarially:
# nothing detached runs by default, the gate installs/launches NOTHING, install is opt-in and
# idempotent, uninstall is clean, and the session-launch is a fail-loud reference seam. Every
# supervisor mechanic runs over a TEMP unit dir and a FAKE systemctl - the real user systemd is
# never touched and no session is ever launched.
_supspec = importlib.util.spec_from_file_location("veldo_supervisor", ROOT / ".veldo/supervisor.py")
SUP = importlib.util.module_from_spec(_supspec); _supspec.loader.exec_module(SUP)

# AC1: the in-session waiter is the WIRED DEFAULT of veldo fleet. Drive cmd_fleet with NO waiter and
# prove the default it builds is fleet.InSessionWaiter (a living session waits + re-checks), spawning
# NOTHING (a backed-off pool that then drains detaches nothing: start is never called).
class _SpyDefaultWaiter:
    made = []
    def __init__(self, *a, **k):
        self.waits = []; _SpyDefaultWaiter.made.append(self)
    def wait_until(self, epoch):
        self.waits.append(epoch)
    def tick(self):
        pass
with tempfile.TemporaryDirectory() as _supflt:
    AC.account_add("alpha", root=_supflt)
    _sup_start_calls = []
    def _sup_no_start(wid, env):
        _sup_start_calls.append(wid); return ("h", wid)
    _real_isw = CLI._fleet().InSessionWaiter
    _SpyDefaultWaiter.made = []
    try:
        CLI._fleet().InSessionWaiter = _SpyDefaultWaiter   # observe the DEFAULT cmd_fleet builds
        CLI.cmd_fleet(
            1, account="alpha", accounts_root=_supflt,
            controller=_FLController([{"desired": 0, "work_remains": True, "resume_at": 4242},
                                      {"desired": 0, "work_remains": False}]),
            waiter=None, start=_sup_no_start)   # waiter=None -> the in-session default must be wired
    finally:
        CLI._fleet().InSessionWaiter = _real_isw
    expect("AC1: veldo fleet defaults to the in-session waiter (built when none is injected)",
           len(_SpyDefaultWaiter.made) == 1)
    expect("AC1: the in-session default waits until the governor resume time then re-checks, spawning nothing",
           _SpyDefaultWaiter.made[0].waits == [4242] and _sup_start_calls == [])

# A FAKE systemctl runner: records every invocation and touches NO real user systemd.
class _FakeSystemctl:
    def __init__(self, enabled="disabled", active="inactive"):
        self.calls = []; self._enabled = enabled; self._active = active
    def run(self, args):
        args = list(args); self.calls.append(args)
        if args[:1] == ["is-enabled"]:
            return 0, self._enabled + "\n", ""
        if args[:1] == ["is-active"]:
            return 0, self._active + "\n", ""
        return 0, "", ""

# AC2/AC3/AC4: OFF BY DEFAULT, right architecture, visible and removable - all over a temp unit dir
# and a fake systemctl. The gate never touches the real user systemd and never launches a session.
with tempfile.TemporaryDirectory() as _supx:
    _sup_unitdir = os.path.join(_supx, "systemd", "user")
    _sup_timer = os.path.join(_sup_unitdir, "veldo-fleet.timer")
    _sup_service = os.path.join(_sup_unitdir, "veldo-fleet.service")
    # AC2: off by default - importing supervisor and NOT calling install() leaves no artifact.
    expect("AC2: supervisor is OFF by default - no unit exists until install() is explicitly called",
           not os.path.exists(_sup_timer) and not os.path.exists(_sup_service))
    _fsc = _FakeSystemctl()
    _sup_rep = SUP.install(resume_at=_GNOW_E + 3600, runner=_fsc, xdg_dir=_sup_unitdir)
    _timer_txt = open(_sup_timer).read(); _service_txt = open(_sup_service).read()
    expect("AC3: install generates a standard systemd --user timer + oneshot service unit",
           os.path.exists(_sup_timer) and os.path.exists(_sup_service)
           and "[Timer]" in _timer_txt and "OnCalendar=" in _timer_txt
           and "WantedBy=timers.target" in _timer_txt
           and "Type=oneshot" in _service_txt and "ExecStart=" in _service_txt)
    expect("AC3: install computes the OnCalendar from the resume epoch (governor.resume_at)",
           SUP.next_reset_calendar(_GNOW_E + 3600) in _timer_txt)
    expect("AC3: install enables the timer through the injected runner (systemctl --user enable --now + daemon-reload)",
           any(c[:1] == ["enable"] and "veldo-fleet.timer" in c for c in _fsc.calls)
           and ["daemon-reload"] in _fsc.calls)
    # AC4: install launches NO session - the runner only ever ran systemctl subcommands.
    expect("AC4: install launches NO session (the runner only ran systemctl subcommands, never a spawn)",
           all(c and c[0] in ("daemon-reload", "enable", "disable", "is-enabled", "is-active")
               for c in _fsc.calls))
    # AC3 idempotency + confinement: a second install rewrites byte-identical units and leaves exactly
    # the two files inside the injected unit dir (nothing leaks to the real systemd).
    _t1 = open(_sup_timer).read(); _s1 = open(_sup_service).read()
    SUP.install(resume_at=_GNOW_E + 3600, runner=_FakeSystemctl(), xdg_dir=_sup_unitdir)
    expect("AC3: install is idempotent and confined (re-run writes identical bytes; exactly two units in the temp dir)",
           open(_sup_timer).read() == _t1 and open(_sup_service).read() == _s1
           and sorted(os.listdir(_sup_unitdir)) == ["veldo-fleet.service", "veldo-fleet.timer"])
    # AC3 status: reports the timer state through the runner, writing nothing.
    _sup_stat = SUP.status(runner=_FakeSystemctl(enabled="enabled", active="active"), xdg_dir=_sup_unitdir)
    expect("AC3: status reports the timer state via the runner (installed, enabled, active)",
           _sup_stat["installed"] is True and _sup_stat["is_enabled"] == "enabled"
           and _sup_stat["is_active"] == "active")
    # AC3 uninstall: disables through the runner and removes both units cleanly; idempotent.
    _fscu = _FakeSystemctl()
    _sup_repu = SUP.uninstall(runner=_fscu, xdg_dir=_sup_unitdir)
    expect("AC3: uninstall disables via the runner and removes both unit files cleanly",
           any(c[:1] == ["disable"] for c in _fscu.calls)
           and not os.path.exists(_sup_timer) and not os.path.exists(_sup_service)
           and sorted(_sup_repu["removed"]) == sorted([_sup_timer, _sup_service]))
    _sup_repu2 = SUP.uninstall(runner=_FakeSystemctl(), xdg_dir=_sup_unitdir)
    expect("AC3: uninstall is idempotent (a second removal is a clean no-op)", _sup_repu2["removed"] == [])

# AC4: the session-launch primitive FAILS LOUD unwired (spawns nothing), and delegates when wired.
_sup_launch_loud = False
try:
    SUP.launch_session()
except SUP.SupervisorLaunchError:
    _sup_launch_loud = True
expect("AC4: launch_session FAILS LOUD with no real launcher wired (spawns nothing by default)",
       _sup_launch_loud is True)
_sup_wired = {}
def _sup_fake_launcher(**kw):
    _sup_wired.update(kw); return "launched"
expect("AC4: launch_session delegates to an injected real launcher when wired (reference seam)",
       SUP.launch_session(launcher=_sup_fake_launcher, n=3) == "launched" and _sup_wired == {"n": 3})

# TEETH: a mutant that FABRICATES a schedule (install with no resume_at and no on_calendar) breaches
# RULE #6 and is refused; and the real install NEVER launches a session as a side effect (a mutant
# that spawned on install would trip the launch spy).
_sup_no_sched = False
with tempfile.TemporaryDirectory() as _supm:
    try:
        SUP.install(runner=_FakeSystemctl(), xdg_dir=os.path.join(_supm, "u"))
    except SUP.SupervisorError:
        _sup_no_sched = True
expect("TEETH: install refuses to fabricate a schedule (no resume_at, no on_calendar -> fail loud)",
       _sup_no_sched is True)
_sup_launch_spy = []
_sup_real_launch = SUP.launch_session
with tempfile.TemporaryDirectory() as _supl:
    try:
        SUP.launch_session = lambda *a, **k: _sup_launch_spy.append(1)
        SUP.install(resume_at=_GNOW_E + 60, runner=_FakeSystemctl(), xdg_dir=os.path.join(_supl, "u"))
    finally:
        SUP.launch_session = _sup_real_launch
expect("TEETH: install never launches a session (no spawn by default or as a side effect)",
       _sup_launch_spy == [])

# AC5: bin/veldo routes `supervisor` to supervisor.py and it FAILS LOUD without touching real systemd
# (a missing subcommand and a missing schedule both fail before any systemctl call), and the module
# ships in the engine so the WARP-0906 honesty check resolves its home (NOT repo-only).
_rc_sup = _route904(["supervisor"])
expect("AC5: veldo supervisor with no action fails loud (routes to supervisor.py, nonzero, no systemd)",
       _rc_sup[0] != 0)
_rc_sup_install = _route904(["supervisor", "install"])
expect("AC5: veldo supervisor install with no schedule fails loud by name, touching no systemd",
       _rc_sup_install[0] == 2
       and ("on-calendar" in _rc_sup_install[2] or "resume-at" in _rc_sup_install[2]))
expect("AC5: supervisor.py ships in the engine (its home resolves for the honesty check, not repo-only)",
       ".veldo/supervisor.py" in _CH_ENGINE)

# AC2 (WARP-1005): bin/veldo routes `mirror` to the opt-in, off-by-default live mirror runner. It runs
# ONE reconcile pass on demand and creates no timer/daemon/auto-start; with no tracker config wired it
# is a clean no-op (nothing to do), which proves the route reaches the runner. The runner is repo-only
# build machinery, so it is NOT in the shipped engine set an adopter's pack lays (a pack that did not
# lay it fails loud in bin/veldo rather than importing a missing module).
_rc_mir = _route904(["mirror", "--dry-run"])
expect("AC2: veldo mirror routes to the tracker mirror runner (one reconcile pass, no network, rc 0)",
       _rc_mir[0] == 0 and "veldo mirror" in (_rc_mir[1] + _rc_mir[2]))
expect("AC2: the tracker mirror runner is repo-only (not in the shipped engine set) yet present in the repo",
       ".veldo/tracker_mirror_runner.py" not in _CH_ENGINE and (ROOT / ".veldo/tracker_mirror_runner.py").exists())

# --- architecture contract (WARP-1101, W1 of PLAN-0011): the intended shape of a
# system becomes a versioned, human-approved artifact (.veldo/architecture.yaml,
# schema veldo.arch/v1) and a validator structurally checks it, the same way a plan
# is checked. Negative-first with real teeth: a malformed contract, an unknown
# rule kind, a dangling area reference, an approved contract with no recorded
# approval, or an analyzer whose referenced file is absent each REFUSE. Adoption
# safe: an absent contract stands down; a required-but-absent contract fails
# closed. MUTATION teeth over the REAL shipped contract prove the check is not
# vacuous. arch.py takes the parser and the reporter from validate.py, so there is
# no second YAML parser and no import cycle.
_archspec = importlib.util.spec_from_file_location("veldo_arch", ROOT / ".veldo/arch.py")
ARCH = importlib.util.module_from_spec(_archspec); _archspec.loader.exec_module(ARCH)

GOOD_ARCH = """schema: veldo.arch/v1
id: fixture
title: A fixture contract
version: 1
status: approved
approved_by: tester
approved_at: 2026-07-22
areas:
  - id: core
    title: Core area
    includes: ["src/core/x.py"]
  - id: edge
    title: Edge area
    includes: ["src/edge/y.py"]
dependencies:
  enforcement: mechanizable
  allow:
    - {from: edge, to: core}
patterns:
  - id: p1
    text: A pattern in force.
    enforcement: review
invariants:
  - id: i1
    text: An invariant that holds.
    enforcement: mechanizable
budgets:
  - id: b1
    kind: file_lines
    applies_to: "*"
    max: 500
    enforcement: mechanizable
analyzers:
  - {language: python, kind: reference}
"""

def _arch_errs(text, root=ROOT):
    """Parse the contract subset and validate structurally; a parse failure is
    itself a fail-closed rejection (non-zero), never a silent zero."""
    try:
        d = V.parse_yamlish(text)
    except ValueError:
        return 1
    return ARCH.validate_contract(d, root, "selftest.arch", V.fail)

# AC1/AC2 positive control: a well-formed contract validates clean.
expect("WARP-1101 AC1: a well-formed veldo.arch/v1 contract validates", _arch_errs(GOOD_ARCH) == 0)
# AC2 unknown rule kind rejected AT CONTRACT TIME (the plan property).
expect("WARP-1101 AC2: an unknown budget rule kind is rejected at contract time",
       _arch_errs(GOOD_ARCH.replace("kind: file_lines", "kind: loc_count")) > 0)
# AC2 closed vocabularies: schema, enforcement label, version.
expect("WARP-1101 AC2: a wrong schema id refuses",
       _arch_errs(GOOD_ARCH.replace("veldo.arch/v1", "veldo.arch/v9")) > 0)
expect("WARP-1101 AC2: an out-of-vocabulary enforcement label refuses",
       _arch_errs(GOOD_ARCH.replace("enforcement: review", "enforcement: perhaps")) > 0)
expect("WARP-1101 AC2: a non-integer version refuses (a contract is versioned)",
       _arch_errs(GOOD_ARCH.replace("version: 1", "version: soon")) > 0)
# AC2 referential integrity: a dependency edge to an undeclared area is a rule
# about something that does not exist (referenced but absent), and a duplicate
# area id refuses.
expect("WARP-1101 AC2: a dependency edge to an undeclared area refuses (referenced but absent)",
       _arch_errs(GOOD_ARCH.replace("to: core", "to: ghost")) > 0)
expect("WARP-1101 AC2: a duplicate area id refuses",
       _arch_errs(GOOD_ARCH.replace("id: edge", "id: core")) > 0)
# AC3 governance: the contract leaves draft ONLY by a recorded human approval.
expect("WARP-1101 AC3: an approved contract with no recorded approver refuses",
       _arch_errs(GOOD_ARCH.replace("approved_by: tester\n", "")) > 0)
expect("WARP-1101 AC3: a draft contract needs no approver (draft is the un-approved state)",
       _arch_errs(GOOD_ARCH.replace("status: approved\napproved_by: tester\napproved_at: 2026-07-22\n",
                                    "status: draft\n")) == 0)
# AC4 pluggable analyzer slot (D6): a reference analyzer whose config file is
# absent fails closed (referenced but absent).
expect("WARP-1101 AC4: an analyzer ref pointing at an absent file fails closed",
       _arch_errs(GOOD_ARCH.replace("  - {language: python, kind: reference}\n",
                                    "  - {language: python, kind: reference, ref: nope/missing_0011.cfg}\n")) > 0)

# AC4 adoption-safe and fail-closed at the FILE boundary (check_contract).
with tempfile.TemporaryDirectory() as _ad:
    _adp = Path(_ad)
    _absent = _adp / "architecture.yaml"
    expect("WARP-1101 AC4: an absent contract stands down (adoption safe, a repo without one is unaffected)",
           ARCH.check_contract(_absent, _adp, False, V.parse_yamlish, V.fail) == 0)
    expect("WARP-1101 AC4: a required-but-absent contract fails closed by name",
           ARCH.check_contract(_absent, _adp, True, V.parse_yamlish, V.fail) > 0)
    (_adp / "good.yaml").write_text(GOOD_ARCH)
    expect("WARP-1101 AC1: a present, well-formed contract validates through check_contract",
           ARCH.check_contract(_adp / "good.yaml", _adp, False, V.parse_yamlish, V.fail) == 0)
    (_adp / "tab.yaml").write_text("schema: veldo.arch/v1\n\tid: tabbed\n")
    expect("WARP-1101 AC2: a malformed contract (outside the parser subset) fails closed",
           ARCH.check_contract(_adp / "tab.yaml", _adp, False, V.parse_yamlish, V.fail) > 0)

# AC5 this repository carries its OWN approved contract as the first instance, and
# it validates through the integrated validate.py entry point (run in the gate).
expect("WARP-1101 AC5: this repository's own .veldo/architecture.yaml validates via check_arch",
       V.check_arch() == 0)
expect("WARP-1101 AC5: the seed contract is present and approved on the record",
       (ROOT / ".veldo/architecture.yaml").is_file()
       and "status: approved" in (ROOT / ".veldo/architecture.yaml").read_text())

# MUTATION teeth over the REAL shipped contract: the check goes RED if the actual
# artifact is malformed or a declared rule is violated (non-vacuous, the anti-
# vacuity rule C1). A real dependency edge repointed to an undeclared area, and the
# recorded approval stripped while approved, each turn it red.
_arch_real = (ROOT / ".veldo/architecture.yaml").read_text()
_arch_mut_dep = _arch_real.replace("{from: fleet, to: loop}", "{from: fleet, to: ghost_area}", 1)
expect("WARP-1101 TEETH: repointing a real dependency edge to an undeclared area turns the check RED",
       _arch_mut_dep != _arch_real and _arch_errs(_arch_mut_dep) > 0)
_arch_mut_gov = _arch_real.replace("approved_by: dmitry\n", "", 1)
expect("WARP-1101 TEETH: stripping the recorded approval while approved turns the check RED",
       _arch_mut_gov != _arch_real and _arch_errs(_arch_mut_gov) > 0)

# --- foundational decision record (WARP-1105, W5 of PLAN-0011): a foundational
# choice becomes a first-class, versioned, human-decided unit of work
# (.veldo/decisions/*.yaml, schema veldo.decision/v1) and a validator structurally
# checks it, the same way a plan and the architecture contract are checked.
# Negative-first with real teeth: a malformed record, a wrong schema, an
# out-of-vocabulary status/reversal-cost/risk, an option lacking its dead-end
# condition, an assumption lacking its signal or breach, a decided record with no
# recorded human decider, an irreversible choice not at the critical tier (D5), a
# duplicate id, and a chosen option that does not resolve each REFUSE. Adoption
# safe: an absent .veldo/decisions/ directory stands down; a required-but-absent
# record fails closed. MUTATION teeth over the REAL shipped example prove the
# check is not vacuous. decision.py takes the parser and the reporter from
# validate.py, so there is no second YAML parser and no import cycle.
_decspec = importlib.util.spec_from_file_location("veldo_decision", ROOT / ".veldo/decision.py")
DEC = importlib.util.module_from_spec(_decspec); _decspec.loader.exec_module(DEC)

GOOD_DECISION = """schema: veldo.decision/v1
id: DEC-FIX
title: A fixture decision
version: 1
status: draft
owner: fixture-owner
problem_class: A choice judged against the problem class, not today's scale.
reversal_cost: costly
risk: high
options:
  - id: opt_a
    summary: The first candidate option.
    dead_end: Stops working once the fan-out grows past a single node.
  - id: opt_b
    summary: The second candidate option.
    dead_end: Couples to one engine and dead-ends when a second producer appears.
assumptions:
  - id: a1
    statement: The fan-out grows over the life of the system.
    signal: node count recorded in the inventory
    breach: node count exceeds the level where per-node polling is a measurable cost
"""

_DECIDED_BLOCK = ("status: decided\ndecision:\n  chosen: opt_b\n"
                  "  decided_by: a-recorded-human\n  decided_at: 2026-07-22\n")


def _dec_errs(text, root=ROOT):
    """Parse the record subset and validate structurally; a parse failure is itself
    a fail-closed rejection (non-zero), never a silent zero."""
    try:
        d = V.parse_yamlish(text)
    except ValueError:
        return 1
    return DEC.validate_record(d, root, "selftest.decision", V.fail)

# AC1/AC2 positive control: a well-formed record validates clean.
expect("WARP-1105 AC1: a well-formed veldo.decision/v1 record validates", _dec_errs(GOOD_DECISION) == 0)
# AC2 closed vocabularies: schema, status, reversal_cost, risk, version.
expect("WARP-1105 AC2: a wrong schema id refuses",
       _dec_errs(GOOD_DECISION.replace("veldo.decision/v1", "veldo.decision/v9")) > 0)
expect("WARP-1105 AC2: an out-of-vocabulary status refuses",
       _dec_errs(GOOD_DECISION.replace("status: draft", "status: perhaps")) > 0)
expect("WARP-1105 AC2: an out-of-vocabulary reversal_cost class refuses",
       _dec_errs(GOOD_DECISION.replace("reversal_cost: costly", "reversal_cost: maybe")) > 0)
expect("WARP-1105 AC2: an out-of-vocabulary risk tier refuses",
       _dec_errs(GOOD_DECISION.replace("risk: high", "risk: spicy")) > 0)
expect("WARP-1105 AC2: a non-integer version refuses (a record is versioned)",
       _dec_errs(GOOD_DECISION.replace("version: 1", "version: soon")) > 0)
# AC2 the option space: an option lacking its dead-end condition is rejected at
# record time (the anti-vacuity move for the option space).
expect("WARP-1105 AC2: an option lacking its dead_end condition refuses",
       _dec_errs(GOOD_DECISION.replace("    dead_end: Stops working once the fan-out grows past a single node.\n", "", 1)) > 0)
# AC2 referential and uniqueness integrity.
expect("WARP-1105 AC2: a duplicate option id refuses",
       _dec_errs(GOOD_DECISION.replace("id: opt_b", "id: opt_a")) > 0)
expect("WARP-1105 AC2: a duplicate assumption id refuses within a record",
       _dec_errs(GOOD_DECISION.replace(
           "assumptions:\n  - id: a1\n    statement: The fan-out grows over the life of the system.\n    signal: node count recorded in the inventory\n    breach: node count exceeds the level where per-node polling is a measurable cost\n",
           "assumptions:\n  - id: a1\n    statement: One.\n    signal: s1\n    breach: b1\n  - id: a1\n    statement: Two.\n    signal: s2\n    breach: b2\n")) > 0)
# AC4 assumptions are living tripwires: signal and breach are each required.
expect("WARP-1105 AC4: an assumption missing its signal refuses",
       _dec_errs(GOOD_DECISION.replace("    signal: node count recorded in the inventory\n", "", 1)) > 0)
expect("WARP-1105 AC4: an assumption missing its breach condition refuses",
       _dec_errs(GOOD_DECISION.replace("    breach: node count exceeds the level where per-node polling is a measurable cost\n", "", 1)) > 0)
expect("WARP-1105 AC1: a record with no assumptions refuses (a memo is not a tripwire)",
       _dec_errs(GOOD_DECISION.replace(
           "assumptions:\n  - id: a1\n    statement: The fan-out grows over the life of the system.\n    signal: node count recorded in the inventory\n    breach: node count exceeds the level where per-node polling is a measurable cost\n",
           "")) > 0)
# AC3 governance: only a HUMAN decides, on the record; no machine-decided state.
expect("WARP-1105 AC3: a record marked decided with no decision block refuses",
       _dec_errs(GOOD_DECISION.replace("status: draft\n", "status: decided\n")) > 0)
expect("WARP-1105 AC3: a decided record with a decision block but no recorded decider refuses",
       _dec_errs(GOOD_DECISION.replace("status: draft\n",
           "status: decided\ndecision:\n  chosen: opt_b\n  decided_at: 2026-07-22\n")) > 0)
expect("WARP-1105 AC3: a decided record whose chosen option does not resolve refuses (referenced but absent)",
       _dec_errs(GOOD_DECISION.replace("status: draft\n", _DECIDED_BLOCK.replace("chosen: opt_b", "chosen: ghost_opt"))) > 0)
expect("WARP-1105 AC3: a fully decided record with a recorded human decider validates",
       _dec_errs(GOOD_DECISION.replace("status: draft\n", _DECIDED_BLOCK)) == 0)
expect("WARP-1105 AC3: a draft needs no decider (draft is the un-decided state)",
       _dec_errs(GOOD_DECISION) == 0)
expect("WARP-1105 AC3: a draft may not smuggle a decision block with a decider (no machine-decided state)",
       _dec_errs(GOOD_DECISION + "decision:\n  chosen: opt_b\n  decided_by: sneaky\n") > 0)
# AC3 D5: an irreversible choice must map to the critical tier.
expect("WARP-1105 AC3: an irreversible decision NOT at the critical tier refuses (D5)",
       _dec_errs(GOOD_DECISION.replace("reversal_cost: costly", "reversal_cost: irreversible")) > 0)
expect("WARP-1105 AC3: an irreversible decision AT the critical tier validates (D5)",
       _dec_errs(GOOD_DECISION.replace("reversal_cost: costly", "reversal_cost: irreversible").replace("risk: high", "risk: critical")) == 0)

# AC4 adoption-safe and fail-closed at the DIRECTORY and FILE boundary.
with tempfile.TemporaryDirectory() as _dd:
    _ddp = Path(_dd)
    _absent_dir = _ddp / "decisions"
    expect("WARP-1105 AC4: an absent decisions directory stands down (adoption safe, a repo without records is unaffected)",
           DEC.check_decisions_dir(_absent_dir, _ddp, V.parse_yamlish, V.fail) == 0)
    expect("WARP-1105 AC4: a required-but-absent single record fails closed by name",
           DEC.check_record(_ddp / "nope.yaml", _ddp, True, V.parse_yamlish, V.fail) > 0)
    _absent_dir.mkdir()
    (_absent_dir / "good.yaml").write_text(GOOD_DECISION)
    expect("WARP-1105 AC1: a present, well-formed record validates through the directory scan",
           DEC.check_decisions_dir(_absent_dir, _ddp, V.parse_yamlish, V.fail) == 0)
    # AC2 malformed (outside the parser subset) fails closed.
    (_absent_dir / "tab.yaml").write_text("schema: veldo.decision/v1\n\tid: tabbed\n")
    expect("WARP-1105 AC2: a malformed record (outside the parser subset) fails closed",
           DEC.check_decisions_dir(_absent_dir, _ddp, V.parse_yamlish, V.fail) > 0)
    (_absent_dir / "tab.yaml").unlink()
    # AC4 a decision id declared by more than one record is refused (ambiguous reference).
    (_absent_dir / "dup.yaml").write_text(GOOD_DECISION)  # same id DEC-FIX as good.yaml
    expect("WARP-1105 AC4: a duplicate decision id across records is refused",
           DEC.check_decisions_dir(_absent_dir, _ddp, V.parse_yamlish, V.fail) > 0)

# AC1 this repository ships the illustrative example, and it validates through the
# integrated validate.py entry point (run in the gate via the examples block).
_dec_example = ROOT / ".veldo/examples/decision-example.yaml"
expect("WARP-1105 AC1: the shipped decision example validates via check_decision",
       V.check_decision(_dec_example) == 0)
expect("WARP-1105 AC1: the shipped example is present and in the un-decided (draft) state with no attributed decider",
       _dec_example.is_file()
       and "status: draft" in _dec_example.read_text()
       and "decided_by:" not in _dec_example.read_text())

# MUTATION teeth over the REAL shipped example: the check goes RED if the actual
# artifact loses an option's dead-end condition or is marked decided without a
# recorded human decider (non-vacuous, the anti-vacuity rule C1).
_dec_real = _dec_example.read_text()
_dec_mut_deadend = _dec_real.replace("    dead_end:", "    was_dead_end:", 1)
expect("WARP-1105 TEETH: stripping an option's dead_end condition from the real example turns the check RED",
       _dec_mut_deadend != _dec_real and _dec_errs(_dec_mut_deadend) > 0)
# target the field line (status: draft\n), not the prose in the header comment.
_dec_mut_decided = _dec_real.replace("status: draft\n", "status: decided\n", 1)
expect("WARP-1105 TEETH: flipping the real example to decided without a recorded human decider turns the check RED",
       _dec_mut_decided != _dec_real and _dec_errs(_dec_mut_decided) > 0)

# --- placement and footprint at elaboration (WARP-1103, W3 of PLAN-0011): a spec
# declares WHERE its change lands (one or more architecture-contract areas) and its
# FOOTPRINT (the path globs it touches), and validate_placement (in .veldo/arch.py,
# invoked from validate.py check_spec) validates the declaration AGAINST the
# contract's areas at spec-validation time. Negative-first with real teeth: a
# placement area the contract does not declare, a footprint that is empty or a
# non-string, a footprint without a placement, and a duplicate placement area each
# REFUSE. OPTIONAL and adoption safe on two axes: no contract in the repository, or
# a spec that declares neither field, each stand down. MUTATION teeth over this
# repository's REAL WARP-1103 spec prove the check is not vacuous. This is the
# DECLARATION and its structural validation only: enforcing the footprint against
# the diff is WARP-1102 (W2), and shape-fit review is WARP-1104 (W4).
# ARCH and GOOD_ARCH are defined by the WARP-1101 block above; reuse them (one
# fixture contract, one parser, no second loader).
_P13_CONTRACT = V.parse_yamlish(GOOD_ARCH)  # areas: core, edge

def _place_errs(fm_text, contract=_P13_CONTRACT):
    """Parse a spec's front-matter subset and validate its placement/footprint; a
    parse failure is itself a fail-closed rejection (non-zero), never a silent zero."""
    try:
        fm = V.parse_yamlish(fm_text)
    except ValueError:
        return 1
    return ARCH.validate_placement(fm, contract, "selftest.placement", V.fail)

# AC1 positive control: a well-formed placement + footprint resolving to a declared
# area validates clean; a spec that declares NEITHER stands down (optional).
expect("WARP-1103 AC1: a placement resolving to a declared area with a footprint validates",
       _place_errs("placement: [core]\nfootprint:\n  - src/core/x.py\n") == 0)
expect("WARP-1103 AC1: a spec that declares neither placement nor footprint stands down (optional)",
       _place_errs("id: X\ntitle: Y\n") == 0)
# AC2 fail-closed structural rules, negative-first.
expect("WARP-1103 AC2: a placement area the contract does not declare refuses (referenced but absent)",
       _place_errs("placement: [ghost]\nfootprint: [src/x.py]\n") > 0)
expect("WARP-1103 AC2: a placement that is not a non-empty list refuses",
       _place_errs("placement: core\nfootprint: [src/x.py]\n") > 0)
expect("WARP-1103 AC2: a footprint missing when a placement is declared refuses",
       _place_errs("placement: [core]\n") > 0)
expect("WARP-1103 AC2: an empty footprint list refuses",
       _place_errs("placement: [core]\nfootprint: []\n") > 0)
expect("WARP-1103 AC2: a footprint entry that is not a non-empty string refuses",
       _place_errs("placement: [core]\nfootprint: [5]\n") > 0)
expect("WARP-1103 AC2: a footprint declared without a placement refuses (placeless)",
       _place_errs("footprint: [src/x.py]\n") > 0)
expect("WARP-1103 AC2: a duplicate placement area refuses",
       _place_errs("placement: [core, core]\nfootprint: [src/x.py]\n") > 0)
expect("WARP-1103 AC2: a placement to multiple declared areas validates",
       _place_errs("placement: [core, edge]\nfootprint: [src/x.py]\n") == 0)

# AC3 adoption safe and fail closed at the FILE boundary (check_placement over a
# temporary tree): no contract stands down; a present contract validates fail closed.
with tempfile.TemporaryDirectory() as _p13d:
    _p13p = Path(_p13d)
    (_p13p / ".veldo").mkdir()
    _p13spec = _p13p / "S.md"
    _p13spec.write_text("---\nschema: veldo.spec/v1\nplacement: [ghost]\nfootprint: [src/x.py]\n---\nbody\n")
    expect("WARP-1103 AC3: no contract in the repo stands down (adoption safe, byte-identically unaffected)",
           V.check_placement(_p13spec, repo_root=_p13p) == 0)
    (_p13p / ".veldo" / "architecture.yaml").write_text(GOOD_ARCH)  # areas core, edge
    expect("WARP-1103 AC3: a present contract fails closed on a placement to an undeclared area",
           V.check_placement(_p13spec, repo_root=_p13p) > 0)
    _p13spec.write_text("---\nschema: veldo.spec/v1\nplacement: [core]\nfootprint: [src/core/x.py]\n---\nbody\n")
    expect("WARP-1103 AC3: a present contract validates a placement that resolves",
           V.check_placement(_p13spec, repo_root=_p13p) == 0)
    _p13spec.write_text("---\nschema: veldo.spec/v1\ntitle: no placement here\n---\nbody\n")
    expect("WARP-1103 AC3: a present contract stands down for a spec that declares neither field",
           V.check_placement(_p13spec, repo_root=_p13p) == 0)

# AC1/AC4 this repository's REAL WARP-1103 spec declares its own placement (area
# contracts) and validates through the integrated entry points (run in the gate).
_p13_file = ROOT / "specs/WARP-1103-placement-and-footprint.md"
expect("WARP-1103 AC1: the real WARP-1103 spec validates via check_placement",
       V.check_placement(_p13_file) == 0)
expect("WARP-1103 AC1: the real WARP-1103 spec validates via check_spec (integrated)",
       V.check_spec(_p13_file) == 0)
expect("WARP-1103 AC1: the real spec declares placement contracts (the first dogfood instance)",
       "placement: [contracts]" in _p13_file.read_text())

# AC4 MUTATION teeth over the REAL WARP-1103 spec: the check goes RED if the actual
# placement is repointed to an undeclared area, or the placement is removed while the
# footprint remains (non-vacuous, the anti-vacuity rule C1). Validated against THIS
# repository's real contract (areas include contracts, not ghost_area). Each mutation
# is applied to a copy of the real front-matter text and reverts byte-identical.
_P13_REAL_CONTRACT = ARCH.load_contract(ROOT / ".veldo/architecture.yaml", V.parse_yamlish)
_p13_fm = re.match(r"^---\n(.*?)\n---", _p13_file.read_text(), re.S).group(1)
_p13_mut_area = _p13_fm.replace("placement: [contracts]", "placement: [ghost_area]", 1)
expect("WARP-1103 TEETH: repointing the real spec's placement to an undeclared area turns the check RED",
       _p13_mut_area != _p13_fm and _place_errs(_p13_mut_area, _P13_REAL_CONTRACT) > 0)
_p13_mut_noplace = _p13_fm.replace("placement: [contracts]\n", "", 1)
expect("WARP-1103 TEETH: removing the real spec's placement while keeping its footprint turns the check RED",
       _p13_mut_noplace != _p13_fm and _place_errs(_p13_mut_noplace, _P13_REAL_CONTRACT) > 0)
# and the unmutated real front matter validates against the real contract (positive control).
expect("WARP-1103 TEETH: the unmutated real spec validates against the real contract (non-vacuous)",
       _place_errs(_p13_fm, _P13_REAL_CONTRACT) == 0)

# AC5 the extended engine surface is byte-identical across the canonical copies (the
# gate's pack-drift and template-sync checks cover all packs; assert the root vs
# engine pair here as fast extra teeth).
expect("WARP-1103 AC5: .veldo/arch.py is byte-identical root vs engine",
       (ROOT / ".veldo/arch.py").read_bytes() == (ROOT / "engine/.veldo/arch.py").read_bytes())
expect("WARP-1103 AC5: .veldo/validate.py is byte-identical root vs engine",
       (ROOT / ".veldo/validate.py").read_bytes() == (ROOT / "engine/.veldo/validate.py").read_bytes())
expect("WARP-1103 AC5: the spec_placement_footprint capability is declared mechanical",
       bool(re.search(r"(?m)^\s{2}spec_placement_footprint:\s*\{status:\s*mechanical\b",
                      (ROOT / ".veldo/capabilities.yaml").read_text())))
expect("WARP-1103 AC5: .veldo/plan.py is byte-identical root vs engine",
       (ROOT / ".veldo/plan.py").read_bytes() == (ROOT / "engine/.veldo/plan.py").read_bytes())
expect("WARP-1103 AC5: .veldo/frontier.py is byte-identical root vs engine",
       (ROOT / ".veldo/frontier.py").read_bytes() == (ROOT / "engine/.veldo/frontier.py").read_bytes())

# --- WARP-1211 AC1/AC4: the production support organ reaches the canonical engine, and the
# capability records that name it name modules that exist -----------------------------------
# THE ROSTER IS WRITTEN DOWN HERE ON PURPOSE, unlike the drift checks above which derive their
# subject. PLAN-0012's organ is what an adopter gets from /veldo:init and what the packs assemble
# from, so "every module the plan built" is a CLAIM about a finished plan rather than a moving
# property, and pinning it is what stops a later engine change dropping one from the copy that
# ships while the repository's own copy keeps working and nobody notices.
_W1211_ORGAN = ["evidence.py", "incident.py", "incident_reconcile.py", "responder.py",
                "action.py", "action_executor.py", "executor.py", "two_key.py",
                "authorization.py"]
_w1211_absent = [m for m in _W1211_ORGAN
                 if not (ROOT / "engine/.veldo" / m).is_file()
                 or not (ROOT / ".veldo" / m).is_file()]
_w1211_differs = [m for m in _W1211_ORGAN
                  if m not in _w1211_absent
                  and (ROOT / ".veldo" / m).read_bytes()
                  != (ROOT / "engine/.veldo" / m).read_bytes()]
expect("WARP-1211 AC1: every PLAN-0012 support module exists in BOTH engine homes and is byte-identical, so what /veldo:init lays down is what this repository runs",
       _w1211_absent == [] and _w1211_differs == [] and len(_W1211_ORGAN) == 9)

# AC4: the capability entries for that organ still name modules that are really there. The
# manifest is prose until something checks the home it declares, and an entry pointing at a
# deleted module is exactly the dishonesty this suite exists to catch.
_w1211_caps = (ROOT / ".veldo/capabilities.yaml").read_text()
_w1211_homes = re.findall(r"home:\s*(\.veldo/[A-Za-z0-9_]+\.py)", _w1211_caps)
_w1211_dead = sorted({h for h in _w1211_homes if not (ROOT / h).is_file()})
expect("WARP-1211 AC4: every module a capability record names as its home actually exists (documentation is not a capability, and a record pointing at nothing is worse than none)",
       bool(_w1211_homes) and _w1211_dead == [])


# --- WARP-1704 (W4 of PLAN-0017): the publication pipeline -----------------------------------
# GATE-ENFORCED, not demonstrated once. A publication step that is only ever run by hand is a
# judgement repeated by hand, and the leak it misses is permanent the moment it is pushed.
_pubspec = importlib.util.spec_from_file_location("veldo_publish", ROOT / "scripts/publish.py")
PUB = importlib.util.module_from_spec(_pubspec); _pubspec.loader.exec_module(PUB)

# AC1: DEFAULT DENY. The manifest says what ships; anything else is absent without being named.
_pub_fake = ["engine/.veldo/validate.py", "packs/cursor/AGENTS.md", "README.md",
             "specs/WARP-0001-x.md", "plans/PLAN-0001-x.md", "proof/WARP-0001/verdict.json",
             ".veldo/private_names.txt", "docs/method.md", "docs/design/05-internal.md",
             "a-directory-nobody-thought-about/secret.md"]
_pub_sel = PUB.selected(_pub_fake)
expect("WARP-1704 AC1: the manifest is DEFAULT DENY - the engine, the packs, the generic docs and "
       "the readme ship, and the specs, plans, proof corpus, per-repo config, internal design notes "
       "AND a directory nobody thought about are all absent without any rule naming them",
       _pub_sel == ["README.md", "docs/method.md", "engine/.veldo/validate.py",
                    "packs/cursor/AGENTS.md"])
expect("WARP-1704 AC1 control: the include rules are load-bearing, so this is not passing because "
       "the selector returns nothing - the engine and packs globs each admit their file",
       PUB.selected(["engine/x.py"]) == ["engine/x.py"]
       and PUB.selected(["packs/cursor/y.md"]) == ["packs/cursor/y.md"])

# AC3 + AC4 + AC5: the scan reads the PRODUCED tree, catches a seeded artifact, and REFUSES.
with tempfile.TemporaryDirectory() as _pubd:
    _pub_out = Path(_pubd) / "tree"
    (_pub_out / "docs").mkdir(parents=True)
    (_pub_out / "docs" / "clean.md").write_text("A generic document naming nobody.\n")
    _pub_names = PUB.load_private_names()
    expect("WARP-1704 AC3: the private-name list has ONE definition, shared with the gate's "
           "genericity sweep, and it is not empty (a scan with nothing to look for reports green)",
           len(_pub_names) > 10)
    # THE SEED IS DERIVED FROM THE LIST, NEVER PINNED TO ONE ENTRY. Pinning a name made this
    # negative control a hostage of the list's contents: the successor repository carries a
    # different list, so the pinned name vanished and the only check proving the scanner has ever
    # caught anything went red for a reason that had nothing to do with the scanner. It also put a
    # supplier's name inside a test file that ships. Title case on purpose, so the seed also proves
    # the match is case-insensitive.
    _seed_name = sorted(_pub_names)[0]
    _seed_word = _seed_name.title()
    expect("WARP-1704 AC4 control: a clean produced tree scans clean, so the finding below is the "
           "seed and not the scanner",
           PUB.scan(_pub_out, _pub_names) == [])
    (_pub_out / "docs" / "seeded-internal.md").write_text(
        "Rollout coordinated with the %s migration window.\n" % _seed_word)
    _pub_found = PUB.scan(_pub_out, _pub_names)
    expect("WARP-1704 AC4: a seeded internal artifact in the PRODUCED tree is CAUGHT and NAMED "
           "with its file and line - the negative test is the evidence, because a scan that has "
           "never caught anything is not one",
           [(f, n) for f, n, _l in _pub_found] == [("docs/seeded-internal.md", _seed_name)]
           and _pub_found[0][2] == 1)
    expect("WARP-1704 AC5: the scan REFUSES rather than cleans - the offending line is still in the "
           "file after the finding, because repairing it would train us to ignore it",
           _seed_word in (_pub_out / "docs" / "seeded-internal.md").read_text())
    expect("WARP-1704 AC3: the repository's OWN distribution coordinates are not a leak (the owner "
           "account in a clone url must not read as a customer name)",
           PUB.scan(_pub_out, ["bcengi"]) == [])

# AC2: it refuses a destination that would eat the repository it is copying from. The build wipes
# its destination before writing, so this refusal is the difference between a publication and a
# deletion of the source.
def _pub_raises(dest):
    try:
        PUB.build(dest, quiet=True)
        return False
    except SystemExit:
        return True


expect("WARP-1704 AC2: a destination inside or containing this repository is REFUSED by name, "
       "because the build CLEARS its destination first and this repository is not a scratch target",
       all(_pub_raises(_d) for _d in (str(ROOT), str(ROOT / "sub"), str(ROOT.parent))))
