"""Static public KIS channel contracts; no credentials, network or owner state."""
import ast
from dataclasses import FrozenInstanceError
from pathlib import Path
import re

from data.kis_live_catalog import (
    APPROVAL_PATH, CHANNELS, COMPANION_CHANNELS, MARKETS, PAPER_APPROVAL_URL, PAPER_WS_URL,
    PRODUCTION_APPROVAL_URL, PRODUCTION_WS_URL, QUARANTINED,
    CatalogError, companion_channel, subscription_delay_seconds, validate_subscription,
)


def refused(call, code):
    try:
        call()
    except CatalogError as exc:
        assert str(exc) == code
        return
    raise AssertionError("expected catalog refusal")


def test_channel_contracts_keep_unique_ordered_fields_and_source_row_citations():
    assert len(CHANNELS) == 32
    assert set(c.market for c in CHANNELS.values()) == set(MARKETS)
    for tr_id, channel in CHANNELS.items():
        assert channel.tr_id == tr_id and channel.document_path == "/tryitout/" + tr_id
        assert type(channel.fields) is tuple and len(channel.fields) == len(set(channel.fields))
        assert len(channel.fields) == len(channel.field_rows) and channel.field_rows[0] == 24
        assert channel.field_rows == tuple(sorted(set(channel.field_rows)))
        assert re.fullmatch(r"[0-9a-f]{64}", channel.source_sha256)
        assert channel.source_file.endswith(".xlsx") and channel.source_sheet == channel.label
        for value in (channel.symbol_field, channel.time_field, channel.date_field, channel.price_field,
                      channel.size_field, channel.cumulative_volume_field, channel.state_field):
            assert not value or value in channel.fields
        for names in (channel.ask_fields, channel.bid_fields, channel.ask_size_fields, channel.bid_size_fields):
            assert type(names) is tuple and all(name in channel.fields for name in names)
        assert len(channel.ask_fields) == len(channel.bid_fields)
        assert len(channel.ask_size_fields) == len(channel.bid_size_fields)


def test_domestic_krx_integrated_and_nxt_have_distinct_wire_layouts():
    krx, total, nxt = (CHANNELS[t] for t in ("H0STASP0", "H0UNASP0", "H0NXASP0"))
    assert tuple(len(c.fields) for c in (krx, total, nxt)) == (63, 66, 62)
    assert krx.fields[-4:] == ("MID_PRC", "MIDP_TOTAL_RSQN", "MIDP_CLS_CODE", "MARKET_CLS_CODE")
    assert total.fields[-1] == "ANTC_EXCH_CLS_CODE" and nxt.fields[-1] == "NMID_CLS_CODE"
    assert krx.ask_fields == tuple("ASKP" + str(i) for i in range(1, 11))
    assert not any("ANTC" in name for name in krx.ask_fields + krx.bid_fields)
    assert CHANNELS["H0STCNT0"].fields[21] == "CCLD_DVSN"
    assert CHANNELS["H0UNCNT0"].fields[21] == "CNTG_CLS_CODE"


def test_individual_trade_size_is_not_cumulative_volume():
    expected = {"H0STCNT0": ("CNTG_VOL", "ACML_VOL"), "HDFSCNT0": ("EVOL", "TVOL"),
                "H0IFCNT0": ("LAST_CNQN", "ACML_VOL"), "HDFFF020": ("LAST_QNTT", "VOL")}
    for tr_id, values in expected.items():
        channel = CHANNELS[tr_id]
        assert (channel.size_field, channel.cumulative_volume_field) == values
    assert CHANNELS["H0UPCNT0"].kind == "indicator"
    assert CHANNELS["H0UPCNT0"].size_field == ""


def test_private_notifications_orders_unknown_and_conflicted_channels_are_refused():
    forbidden = ("H0STCNI0", "H0STCNI9", "H0GSCNI0", "H0GSCNI9", "H0IFCNI0", "H0IFCNI9",
                 "H0EUCNI0", "H0MFCNI0", "HDFFF1C0", "HDFFF2C0", "TTTC0802U", "H0STCNT1",
                 "/tryitout/H0STCNT0", "h0stcnt0")
    for tr_id in forbidden + tuple(QUARANTINED):
        refused(lambda: validate_subscription(tr_id, "005930"), "KIS_LIVE_CHANNEL_NOT_ALLOWED")
    assert not set(CHANNELS).intersection(QUARANTINED)
    assert CHANNELS["H0BJCNT0"].kind == "trade" and len(CHANNELS["H0BJCNT0"].fields) == 19


def test_fixed_symbol_syntax_refuses_injection_unicode_and_whitespace():
    assert validate_subscription("H0STCNT0", "005930").tr_id == "H0STCNT0"
    assert validate_subscription("H0STCNT0", "Q500001").market == "domestic_equity"
    for value in ("005930\n", " 005930", "００５９３０", "005930,000660", "005930^x", "005930|x",
                  "../../file", "https://example.com", "", 5930, "Q50001"):
        refused(lambda: validate_subscription("H0STCNT0", value), "KIS_LIVE_SUBSCRIPTION_KEY_INVALID")
    assert validate_subscription("H0IFCNT0", "101S12").market == "domestic_derivative"
    assert validate_subscription("H0IOCNT0", "201S11305").market == "domestic_derivative"
    assert validate_subscription("H0BJCNT0", "KR103502GA34").market == "bond"


def test_overseas_keys_distinguish_free_daytime_paid_and_delayed_scopes():
    for key in ("DNASAAPL", "RBAQAAPL", "RHKS00003"):
        assert validate_subscription("HDFSASP0", key).kind == "book"
    refused(lambda: validate_subscription("HDFSASP0", "DHKS00003"), "KIS_LIVE_SUBSCRIPTION_KEY_INVALID")
    assert validate_subscription("HDFSASP1", "DHKS00003").delay_seconds == 900
    refused(lambda: validate_subscription("HDFSASP1", "DNASAAPL"), "KIS_LIVE_SUBSCRIPTION_KEY_INVALID")
    assert subscription_delay_seconds("HDFSCNT0", "DNASAAPL") == 0
    assert subscription_delay_seconds("HDFSCNT0", "DHKS00003") == 900
    assert subscription_delay_seconds("HDFSCNT0", "RHKS00003") == 0
    assert subscription_delay_seconds("HDFSASP1", "DTSE7203") == 900


def test_only_documented_krx_stock_channels_accept_paper_environment():
    assert {t for t, c in CHANNELS.items() if c.paper} == {"H0STCNT0", "H0STASP0"}
    assert validate_subscription("H0STCNT0", "005930", paper=True).paper
    refused(lambda: validate_subscription("H0UNCNT0", "005930", paper=True), "KIS_LIVE_PAPER_UNSUPPORTED")
    refused(lambda: validate_subscription("HDFSCNT0", "DNASAAPL", paper=True), "KIS_LIVE_PAPER_UNSUPPORTED")
    refused(lambda: validate_subscription("H0STCNT0", "005930", paper=1), "KIS_LIVE_ENVIRONMENT_INVALID")


def test_documented_socket_is_cleartext_and_approval_remains_exact_https():
    assert PRODUCTION_WS_URL == "ws://ops.koreainvestment.com:21000/tryitout"
    assert PAPER_WS_URL == "ws://ops.koreainvestment.com:31000/tryitout"
    assert APPROVAL_PATH == "/oauth2/Approval"
    assert PRODUCTION_APPROVAL_URL == "https://openapi.koreainvestment.com:9443/oauth2/Approval"
    assert PAPER_APPROVAL_URL == "https://openapivts.koreainvestment.com:29443/oauth2/Approval"


def test_scaling_time_unknowns_and_auction_markers_are_not_fabricated():
    for tr_id in ("HDFFF010", "HDFFF020"):
        channel = CHANNELS[tr_id]
        assert channel.normalization == "requires_master_scale" and channel.timezone == ""
    assert CHANNELS["H0STNAV0"].time_field == CHANNELS["H0STNAV0"].date_field == ""
    for tr_id in ("H0STCNT0", "H0STASP0"):
        assert CHANNELS[tr_id].state_field == "HOUR_CLS_CODE"
        assert CHANNELS[tr_id].indicative_values == ("A", "B", "C", "D")
        assert CHANNELS[tr_id].regular_values == ("0",)
    for tr_id in ("H0UNASP0", "H0NXASP0", "H0EWASP0"):
        assert CHANNELS[tr_id].state_field == "HOUR_CLS_CODE"
        assert CHANNELS[tr_id].indicative_values == CHANNELS[tr_id].regular_values == ()
    assert CHANNELS["HDFSASP0"].date_field == "KYMD" and CHANNELS["HDFSASP0"].time_field == "KHMS"


def test_companions_pin_feed_and_validate_both_keys_without_symbol_rewriting():
    for first, second in COMPANION_CHANNELS.items():
        assert COMPANION_CHANNELS[second] == first
        assert {CHANNELS[first].kind, CHANNELS[second].kind} == {"trade", "book"}
        assert CHANNELS[first].market == CHANNELS[second].market
    assert companion_channel("H0STCNT0", "005930", paper=True).tr_id == "H0STASP0"
    assert companion_channel("H0NXCNT0", "005930").tr_id == "H0NXASP0"
    assert companion_channel("H0UNCNT0", "005930").tr_id == "H0UNASP0"
    assert companion_channel("HDFSCNT0", "DNASAAPL").tr_id == "HDFSASP0"
    assert companion_channel("HDFSASP0", "RBAQAAPL").tr_id == "HDFSCNT0"
    assert companion_channel("HDFSCNT0", "DHKS00003") is None
    assert companion_channel("HDFSCNT0", "RNASAAPL") is None
    assert companion_channel("HDFSASP1", "DHKS00003") is None
    assert companion_channel("H0BJCNT0", "KR103502GA34") is None
    refused(lambda: companion_channel("H0STCNI0", "005930"), "KIS_LIVE_CHANNEL_NOT_ALLOWED")
    refused(lambda: companion_channel("H0NXCNT0", "005930", paper=True), "KIS_LIVE_PAPER_UNSUPPORTED")


def test_catalog_mapping_and_channel_records_are_immutable():
    try:
        CHANNELS["other"] = CHANNELS["H0STCNT0"]
    except TypeError:
        pass
    else:
        raise AssertionError("catalog was mutable")
    try:
        CHANNELS["H0STCNT0"].tr_id = "other"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("channel was mutable")


def test_catalog_has_no_network_credentials_environment_or_execution_imports():
    source = Path(__file__).resolve().parents[1] / "data" / "kis_live_catalog.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
    assert imports == {"__future__", "dataclasses", "types", "re"}
    calls = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    assert not calls.intersection({"open", "eval", "exec", "getattr", "__import__"})
