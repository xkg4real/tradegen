"""Reviewed pure renewal ports across the E2 boundary; supplemental AST checks.

This is a bounded review of 45 callable bodies and 16 initialization surfaces,
not a whole-program analyzer or proof against hostile Python. Existing E2
control/compliance/isolation/snapshot dependencies and standard-library behavior
remain the prior trusted base. Owner source hashes and behavioral tests still
bind/check the complete deployment. Do not regenerate pins to accept a failure
without reviewing the changed callable, import, default or decorator.

Only the two renewal validation entry points are exposed to controller/session.
The account source class is outside the reachable callable list; no caller can
gain an E1 read through these exact imports. Mixed-module initialization surfaces
include the newly reached E1 transport, key module, route and package initializers.
"""
import ast
import hashlib
import json

# These reviewed values describe imports, declarations, class fields, defaults,
# decorators and top-level statements. Function bodies are checked separately.
INITIALIZERS = {
    "execution/__init__.py": "dbbe3001d9d0d1bf6393b4d823b997e9ae163f45f8eb26860474cd6ec902f380",
    "execution/keys.py": "4e5c674aad9265edb21eb1ac71c4795bb1ae7d89aa7fb880e86131bae44c644a",
    "execution/transport.py": "0aeec926859748a0321aa03da988ee69a8425f12a9dfe608d78990a1f0229104",
    "execution/upbit_inquiry.py": "cdeb85aa8c1fbe5f63c5328716406cb298909fe82543207949106b6ecd5b7b10",
    "execution_accounts/__init__.py": "dbbe3001d9d0d1bf6393b4d823b997e9ae163f45f8eb26860474cd6ec902f380",
    "execution_accounts/collector.py": "7c2dd003297d051d3248b0c3ad30d105bf8e59037a4e2b2b347217d877b44d9d",
    "execution_accounts/instrument_terms.py": "7a87af0de172ba598c158ebf646be226c045bfed540a26671402af2198662dda",
    "execution_accounts/model.py": "a3afc9c2d728bd6ebf63aac20f9e46d515781c6a4cc4747dd8bfe7d33640552a",
    "execution_accounts/provider.py": "8f3996d9ba330ec9ba6211471d8a41c760e0ab4c6374498177c4c5aec635aefe",
    "execution_control/model.py": "ab169e357bd160bd66c83a9293da29403f122c92e648bea69848432b9caaeba9",
    "execution_control/risk.py": "852ae2f20707670b8f0429ec34da5cd338f1aeb5a812c83867f190dfc63b42b0",
    "execution_launch/__init__.py": "dbbe3001d9d0d1bf6393b4d823b997e9ae163f45f8eb26860474cd6ec902f380",
    "execution_launch/instrument_refresh.py": "fc52e2ea59221ac5d3a6d0c3a170a8f5aa3e16fc830380d04dc11b30f7c732d1",
    "execution_launch/profile.py": "74a7733068b1b392df3389054c4e300881f274383adf42da7831455e6aaa0c32",
    "execution_network/__init__.py": "dbbe3001d9d0d1bf6393b4d823b997e9ae163f45f8eb26860474cd6ec902f380",
    "execution_network/route.py": "861df080f66a4f292723815de3010e485c7f078fbed345d42a25631a7dc331a4"
}

# Exact callable targets in the reviewed transitive validation graph. This also
# covers JSON object/constant hooks, dataclass __post_init__, receipt.decode and
# the profile/model/risk validators. Attribute calls are not broadly permitted.
CALLS = {
    "execution_launch/instrument_refresh.py": {
        "_require": ["RenewalError"],
        "_time": ["_require","type","value.utcoffset"],
        "validate_renewal": ["_validate_renewal"],
        "_validate_renewal": ["_HEADS.get","_ISSUED.get","_require","_time","id","profile_contract_digest","profile_digest","rules_digest","type","validate_issued_observation"],
        "rules_binding_matches": ["_BOUND.get","_time","rules_digest","validate_renewal"],
        "validate_observed_order": ["Fraction","_BOUND.get","_require","observation_for_rules","rules_digest","validate_order","validate_renewal"],
    },
    "execution_accounts/instrument_terms.py": {
        "_require": ["TermsError"],
        "_time": ["TermsError","_require","type","value.astimezone","value.utcoffset"],
        "_sha": ["_SHA.fullmatch","_require","type"],
        "_number": ["Decimal","TermsError","_require","len","result.as_tuple","result.is_finite","type"],
        "_digest": ["hashlib.sha256","hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')).hexdigest","json.dumps","json.dumps(body, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode"],
        "authority_digest": ["_SCOPE.fullmatch","_SYMBOL.fullmatch","_digest","_number","_require","_sha","_time","decimal_text","end.isoformat","getattr","start.isoformat","type"],
        "_receipt": ["TermsError","_require","_time","abs","len","receipt.decode","timedelta","type"],
        "parse_term_receipts": ["InstrumentRules","TermsObservation","_digest","_number","_receipt","_require","_time","_time(r.received_at).isoformat","_time(r.server_time).isoformat","all","ask.get","authority_digest","before.isoformat","bid.get","chance.get","checked.isoformat","instrument.get","instruments[0].get","len","market.get","min","rules_digest","symbol.split","timedelta","tuple","type"],
        "validate_issued_observation": ["_ISSUED.get","_require","id","parse_term_receipts","rules_digest","type"],
        "observation_for_rules": ["_OBSERVED_RULES.get","_require","rules_digest","validate_issued_observation"],
    },
    "execution_launch/profile.py": {
        "profile_digest": ["hashlib.sha256","hashlib.sha256(raw.encode('ascii')).hexdigest","json.dumps","profile_body","raw.encode"],
        "profile_contract_digest": ["hashlib.sha256","hashlib.sha256(raw.encode('ascii')).hexdigest","json.dumps","profile_body","raw.encode"],
        "profile_body": ["_validate_profile","decimal_text","fields","getattr","type","v.astimezone","v.astimezone(timezone.utc).isoformat"],
        "_validate_profile": ["ProfileError","_amount","_text","getattr","rules_digest","type","validate_recovery_condition"],
        "_amount": ["ProfileError","abs","len","type","value.as_tuple","value.is_finite"],
        "_text": ["ProfileError","pattern.fullmatch","type"],
        "LaunchProfile.__post_init__": ["_validate_profile"],
        "ProfileError.__init__": ["super","super().__init__"],
    },
    "execution_control/model.py": {
        "decimal_text": ["_decimal","format","text.rstrip","text.rstrip('0').rstrip"],
        "rules_digest": ["ValueError","_digest","_rule_fields","decimal_text","fields","getattr","type","value.astimezone","value.astimezone(timezone.utc).isoformat"],
        "validate_order": ["Fraction","ValueError","_order_fields","_rule_fields","type"],
        "_rule_fields": ["ValueError","_aware","_decimal","_identity","_text","getattr"],
        "_order_fields": ["Fraction","ValueError","_decimal","_identity","_text","getattr","type"],
        "_decimal": ["ValueError","abs","len","type","value.as_tuple","value.is_finite"],
        "_identity": ["ValueError","re.fullmatch","type"],
        "_text": ["ValueError","pattern.fullmatch","type"],
        "_aware": ["ValueError","type","value.astimezone","value.utcoffset"],
        "_digest": ["hashlib.sha256","hashlib.sha256(raw.encode('ascii')).hexdigest","json.dumps","raw.encode"],
        "InstrumentRules.__post_init__": ["_rule_fields"],
        "Order.__post_init__": ["_order_fields"],
    },
    "execution_control/risk.py": {
        "validate_recovery_condition": ["ValueError","type"],
    },
    "execution_accounts/collector.py": {
        "SourceReceipt.decode": ["EvidenceError","digest","hashlib.sha256","hashlib.sha256(self.raw_body).hexdigest","identifier","instant","isinstance","json.loads","len","require","self.raw_body.decode","type"],
        "identifier": ["_ID.fullmatch","require","type"],
        "instant": ["require","type","value.astimezone","value.utcoffset"],
        "digest": ["_SHA.fullmatch","require","type"],
        "require": ["EvidenceError"],
        "_object": ["require"],
        "_constant": ["EvidenceError"],
    },
    "execution_accounts/provider.py": {
        "EvidenceError.__init__": ["super","super().__init__"],
    },
}

_EFFECT_REFERENCES = frozenset({
    "current_terms", "E1UpbitTermsSource", "inquiry_clock", "managed_route", "route_options",
    "request", "_send", "requests", "socket", "urlopen", "getenv", "environ",
    "read_bytes", "read_text", "write_bytes", "write_text", "open", "load_context",
    "append_system_entry", "arm", "sign_entry",
    "eval", "exec", "__import__", "__globals__", "__closure__", "__dict__", "__class__", "f_globals",
})
_REGISTRIES = frozenset({"_ISSUED", "_HEADS", "_BOUND", "_USED", "_OBSERVED_RULES", "_AUTHORITIES"})
_CALLBACK_KEYWORDS = frozenset({"default", "cls", "object_hook", "object_pairs_hook", "parse_constant",
                               "parse_float", "parse_int"})
_JSON_HOOKS = {"object_pairs_hook": "_object", "parse_constant": "_constant", "parse_float": "Decimal"}


class _Surface(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        node.body = [ast.Pass()]
        return self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Module(self, node):
        node.body = [n for n in node.body if not isinstance(n, ast.Expr)
                     or not isinstance(n.value, ast.Constant) or not isinstance(n.value.value, str)]
        return self.generic_visit(node)

    visit_ClassDef = visit_Module


def _surface(source):
    tree = _Surface().visit(ast.parse(source))
    def canonical(node):
        if isinstance(node, ast.AST):
            # Python adds empty optional AST fields across supported versions.
            # They have no executable meaning; never discard nonempty fields.
            return [type(node).__name__, [[name, canonical(value)] for name, value in ast.iter_fields(node)
                                         if value is not None and value != []]]
        if isinstance(node, list):
            return [canonical(value) for value in node]
        return [type(node).__name__, repr(node)]
    encoded = json.dumps(canonical(tree), separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _definitions(tree):
    found = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            found[node.name] = node
        elif isinstance(node, ast.ClassDef):
            found.update({node.name + "." + child.name: child for child in node.body
                          if isinstance(child, ast.FunctionDef)})
    return found


def source_map(root):
    return {relative: (root / relative).read_text(encoding="utf-8") for relative in INITIALIZERS}


def problems(sources):
    hits = []
    if set(sources) != set(INITIALIZERS):
        return ["renewal dependency surface changed"]
    for relative, expected in INITIALIZERS.items():
        source = sources[relative]
        if _surface(source) != expected:
            hits.append(relative + ": initialization surface changed")
        definitions = _definitions(ast.parse(source))
        for name, permitted in CALLS.get(relative, {}).items():
            function = definitions.get(name)
            if function is None:
                hits.append(relative + ":" + name + ": reviewed callable missing")
                continue
            nodes = tuple(ast.walk(function))
            actual = {ast.unparse(n.func) for n in nodes if isinstance(n, ast.Call)}
            if actual != set(permitted):
                hits.append(relative + ":" + name + ": callable surface changed")
            if any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in nodes):
                hits.append(relative + ":" + name + ": helper import")
            parents = {id(child): parent for parent in nodes for child in ast.iter_child_nodes(parent)}
            # JSON hooks are invoked by the decoder, so their names do not
            # appear as ast.Call targets in this function's body.
            trusted_names = {target for target in permitted if target.isidentifier()} | set(_JSON_HOOKS.values()) | {
                "hashlib", "json", "re", "timezone", "datetime", "Decimal", "Fraction"}
            for node in nodes:
                if isinstance(node, (ast.Global, ast.Nonlocal)):
                    hits.append(relative + ":" + name + ": registry/global mutation")
                if ((isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del))
                     and node.id in trusted_names)
                    or (isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                        and node is not function and node.name in trusted_names)
                    or (isinstance(node, ast.ExceptHandler) and node.name in trusted_names)):
                    hits.append(relative + ":" + name + ": trusted callable rebinding")
                if isinstance(node, ast.Name) and node.id in _REGISTRIES:
                    parent = parents.get(id(node))
                    grandparent = parents.get(id(parent))
                    read_get = (isinstance(node.ctx, ast.Load) and isinstance(parent, ast.Attribute)
                                and parent.attr == "get" and isinstance(grandparent, ast.Call)
                                and grandparent.func is parent)
                    membership = (node.id == "_AUTHORITIES" and isinstance(node.ctx, ast.Load)
                                  and isinstance(parent, ast.Compare) and len(parent.ops) == 1
                                  and isinstance(parent.ops[0], ast.In) and parent.comparators == [node])
                    if not (read_get or membership):
                        hits.append(relative + ":" + name + ": registry mutation or escape")
                if isinstance(node, ast.Attribute) and isinstance(node.ctx, (ast.Store, ast.Del)):
                    if (relative, name) not in {("execution_launch/profile.py", "ProfileError.__init__"),
                                               ("execution_accounts/provider.py", "EvidenceError.__init__")}:
                        hits.append(relative + ":" + name + ": observed object mutation")
                if isinstance(node, ast.Call):
                    for keyword in node.keywords:
                        if keyword.arg is None:
                            hits.append(relative + ":" + name + ": dynamic keyword arguments")
                        elif keyword.arg in _CALLBACK_KEYWORDS:
                            if not (relative == "execution_accounts/collector.py" and name == "SourceReceipt.decode"
                                    and ast.unparse(node.func) == "json.loads"
                                    and ast.unparse(keyword.value) == _JSON_HOOKS.get(keyword.arg)):
                                hits.append(relative + ":" + name + ": unreviewed callback argument")
            if any((isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                    and n.id in _EFFECT_REFERENCES)
                   or (isinstance(n, ast.Attribute) and n.attr in _EFFECT_REFERENCES | {"now", "utcnow", "today"})
                   for n in nodes):
                hits.append(relative + ":" + name + ": effect reference")
    return hits


def _inject(source, qualified_name, statement):
    tree = ast.parse(source)
    function = _definitions(tree)[qualified_name]
    function.body.extend(ast.parse(statement).body)
    return ast.unparse(tree)


def check_negative_controls(root):
    original = source_map(root)
    assert not problems(original)
    cases = [
        ("execution_accounts/instrument_terms.py", "validate_issued_observation",
         "current_terms('KRW-BTC')"),
        ("execution_accounts/instrument_terms.py", "validate_issued_observation",
         "E1UpbitTermsSource(authority=authority, clock=clock).read()"),
        ("execution_accounts/instrument_terms.py", "_receipt", "os.environ.get('KEY')"),
        ("execution_accounts/instrument_terms.py", "_receipt", "open(path, 'rb')"),
        ("execution_accounts/collector.py", "SourceReceipt.decode", "Path(path).read_bytes()"),
        ("execution_accounts/collector.py", "SourceReceipt.decode", "datetime.now()"),
        ("execution_accounts/collector.py", "SourceReceipt.decode", "json.loads(body, object_pairs_hook=network)"),
        ("execution_launch/instrument_refresh.py", "validate_observed_order",
         "def hidden():\n    return current_terms('KRW-BTC')\nhidden()"),
        ("execution_launch/instrument_refresh.py", "validate_observed_order",
         "validate_order = current_terms\nvalidate_order('KRW-BTC')"),
        ("execution_launch/instrument_refresh.py", "validate_observed_order",
         "fetch = transport.request\nfetch('upbit', 'GET', path)"),
        ("execution_launch/instrument_refresh.py", "rules_binding_matches", "unreviewed.get()"),
        ("execution_launch/profile.py", "profile_digest", "path.read_text()"),
        ("execution_launch/profile.py", "LaunchProfile.__post_init__", "open(path)"),
        ("execution_control/model.py", "InstrumentRules.__post_init__", "client.request()"),
        ("execution_control/risk.py", "validate_recovery_condition", "datetime.now()"),
        ("execution_accounts/instrument_terms.py", "validate_issued_observation",
         "_ISSUED[id(observation)] = observation"),
        ("execution_launch/instrument_refresh.py", "validate_observed_order", "_BOUND[key] = renewal"),
        ("execution_accounts/instrument_terms.py", "observation_for_rules", "del _OBSERVED_RULES[key]"),
        ("execution_launch/instrument_refresh.py", "validate_observed_order", "_HEADS.clear()"),
        ("execution_accounts/instrument_terms.py", "observation_for_rules", "_AUTHORITIES.add(source)"),
        ("execution_accounts/instrument_terms.py", "observation_for_rules",
         "registry = _OBSERVED_RULES\nregistry[key] = observation"),
        ("execution_launch/instrument_refresh.py", "validate_observed_order",
         "renewal.original_rule_digests = roots"),
        ("execution_launch/instrument_refresh.py", "validate_observed_order",
         "validate_renewal = _renew_profile"),
        ("execution_launch/instrument_refresh.py", "validate_renewal",
         "_validate_renewal = _renew_profile"),
        ("execution_accounts/instrument_terms.py", "validate_issued_observation",
         "observation.__dict__['rules'] = rules"),
    ]
    for relative, name, statement in cases:
        changed = dict(original)
        changed[relative] = _inject(original[relative], name, statement)
        assert problems(changed), (relative, name, statement)

    # A fixed hook spelling is insufficient if that local name can be rebound
    # to an existing, otherwise unreachable helper with an effectful body.
    for hook in ("_object", "_constant"):
        relative = "execution_accounts/collector.py"
        tree = ast.parse(original[relative])
        definitions = _definitions(tree)
        definitions["SourceReceipt.decode"].body[:0] = ast.parse(hook + " = number").body
        definitions["number"].body[:0] = ast.parse(
            "from execution.upbit_inquiry import current_terms\ncurrent_terms('KRW-BTC')").body
        changed = dict(original)
        changed[relative] = ast.unparse(tree)
        assert relative + ":SourceReceipt.decode: trusted callable rebinding" in problems(changed), hook

    for relative, statement in (
        ("execution_accounts/instrument_terms.py", "BOOT = current_terms('KRW-BTC')"),
        ("execution_launch/instrument_refresh.py", "validate_order = current_terms"),
        ("execution/transport.py", "LEAK = open(path).read()"),
        ("execution/keys.py", "VALUE = os.environ['KEY']"),
        ("execution_network/route.py", "BOOT = route_options(url)"),
        ("execution/__init__.py", "VALUE = open(path).read()"),
        ("execution_accounts/__init__.py", "import unreviewed_network"),
    ):
        changed = dict(original)
        changed[relative] += "\n" + statement + "\n"
        assert problems(changed), (relative, statement)
