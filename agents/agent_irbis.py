"""Universal agent that fetches ALL counterparty data via ir-bis API.
Uses token: e4c43ba9-d5d9-4462-8ab8-d9eafee7c08c

Replaces agent_egrul, agent_transparent, agent_fssp, agent_arbitr,
agent_bankrupt, agent_rusprofile, agent_licenses, agent_ndp,
agent_inspections, agent_crosscheck, agent_tochka, agent_kontur,
agent_listorg, agent_b2bhouse.

Fetches ALL JSON endpoints from ir-bis swagger spec.
"""
import asyncio
from utils.logger import logger
from utils.irbis_client import IrbisClient


def _safe(val, default=None):
    return val if val is not None else default


def _fmt(val):
    if val is None or val == "":
        return ""
    return str(val)


def _extract_face(fl_list: list, default_key: str = "face") -> dict:
    if not fl_list:
        return {}
    entry = fl_list[0]
    face = entry.get(default_key, entry)
    return face


def _person_name(face: dict) -> str:
    parts = [face.get("last_name", ""), face.get("first_name", ""), face.get("second_name", "")]
    return " ".join(p for p in parts if p).strip()


async def fetch(inn: str) -> dict:
    """Main entry point. Fetches ALL data for a given INN from ir-bis API.

    Returns dict with keys for every agent_* module plus _irbis_* raw data.
    """
    client = IrbisClient()
    try:
        is_ip = len(inn) == 12
        uuid = await client.create_check(inn)

        if is_ip:
            await client.wait_ready(uuid, "people-orgs.json", "data", timeout=90, version="5")
        else:
            await client.wait_ready(uuid, timeout=90)

        endpoints = _get_endpoints(is_ip)
        tasks = {}
        for key, (path, event, version, params) in endpoints.items():
            tasks[key] = client.get(uuid, path, event, version, params)

        raw_results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        results = {}
        pending = []
        for key, value in zip(tasks.keys(), raw_results):
            if isinstance(value, Exception):
                logger.warning(f"irbis {key} error: {value}")
                results[key] = {"error": str(value)}
            elif isinstance(value, dict) and value.get("status") == -1:
                pending.append(key)
            else:
                results[key] = value

        # Second pass: quick retry for transient -1 responses
        if pending:
            await asyncio.sleep(5)
            retasks = {}
            for key in pending:
                path, event, version, params = endpoints[key]
                retasks[key] = client.get(uuid, path, event, version, params)
            retry_results = await asyncio.gather(*retasks.values(), return_exceptions=True)
            for key, value in zip(retasks.keys(), retry_results):
                if isinstance(value, Exception):
                    results[key] = {"error": str(value)}
                elif isinstance(value, dict) and value.get("status") == -1:
                    logger.info(f"irbis {key} not ready after retry, preview data used")
                    results[key] = value
                else:
                    results[key] = value

        return _transform(results, inn, is_ip)
    finally:
        await client.close()


# ═══════════════════════════════════════════════════════════════
# ALL endpoints from swagger spec
# ═══════════════════════════════════════════════════════════════

def _org_endpoints():
    P = {"page": 0, "rows": 20}
    return {
        # ── EGRUL ──
        "egrul_result_v4": ("org-egrul.json", "result", "4", None),
        "egrul_result": ("org-egrul.json", "result", None, None),
        "egrul_result_v2": ("org-egrul.json", "result", "2", None),
        "egrul_fns": ("org-egrul.json", "fns", None, None),
        "egrul_tax_modes": ("org-egrul.json", "tax-modes", None, None),
        "egrul_taxmode_history": ("org-egrul.json", "taxmode-history", None, None),
        "egrul_licenses": ("org-egrul.json", "licenses", None, P),
        "egrul_licenses_preview": ("org-egrul.json", "licenses-preview", None, None),
        "egrul_founded": ("org-egrul.json", "founded", None, P),
        "egrul_history": ("org-egrul.json", "history", None, None),
        "egrul_neighbours": ("org-egrul.json", "neighbours", None, P),
        "egrul_graph_node": ("org-egrul.json", "graph-node", None, None),
        # ── Balance ──
        "balance_preview": ("org-balance.json", "preview", None, None),
        "balance_preview_v2": ("org-balance.json", "preview", "2", None),
        "balance_analysis": ("org-balance.json", "analysis", None, None),
        "balance_analysis_years": ("org-balance.json", "analysisYears", None, None),
        "balance_result": ("org-balance.json", "result", None, None),
        # ── Arbitr ──
        "arbitr_preview": ("org-arbitr.json", "preview", None, None),
        "arbitr_preview_v2": ("org-arbitr.json", "preview_v2", None, None),
        "arbitr_preview_v3": ("org-arbitr.json", "preview", "3", None),
        "arbitr_data_v3": ("org-arbitr.json", "data", "3", {"page": 0, "rows": 20, "match_filter": "INN"}),
        "arbitr_role_preview": ("org-arbitr.json", "role-preview", None, None),
        "arbitr_region_preview": ("org-arbitr.json", "region-preview", None, None),
        "arbitr_bankrot_existance": ("org-arbitr.json", "bankrot-existance", None, None),
        "arbitr_data_v2": ("org-arbitr.json", "data", "2", {"page": 0, "rows": 20, "match_filter": "INN"}),
        # ── FSSP ──
        "fssp_preview": ("org-fssp.json", "preview", None, None),
        "fssp_preview_fns": ("org-fssp.json", "preview_fns", None, None),
        "fssp_preview_fns_v2": ("org-fssp.json", "preview_fns", "2", None),
        "fssp_preview_count": ("org-fssp.json", "preview_count", None, None),
        "fssp_preview_chart": ("org-fssp.json", "preview_chart", None, None),
        "fssp_data": ("org-fssp.json", "data", None, P),
        # ── Arrest ──
        "arrest_preview": ("org-arrest.json", "preview", None, None),
        "arrest_saldo": ("org-arrest.json", "saldo", None, None),
        "arrest_data": ("org-arrest.json", "data", None, None),
        # ── Bankrot ──
        "bankrot_preview": ("org-bankrot.json", "preview", None, None),
        "bankrot_preview_v2": ("org-bankrot.json", "preview", "2", None),
        "bankrot_data": ("org-bankrot.json", "data", None, None),
        # ── Bankruptcy intention ──
        "bankruptcy_intention_preview": ("org-bankruptcy-intention.json", "preview", None, None),
        "bankruptcy_intention_data": ("org-bankruptcy-intention.json", "data", None, P),
        # ── Dishonest supplier ──
        "dishonest_supplier_preview": ("org-dishonest-supplier.json", "preview", None, None),
        "dishonest_supplier_preview_v2": ("org-dishonest-supplier.json", "preview", "2", None),
        "dishonest_supplier_data": ("org-dishonest-supplier.json", "data", None, P),
        # ── Goscon ──
        "goscon_preview": ("org-goscon.json", "preview", None, None),
        "goscon_preview_v2": ("org-goscon.json", "preview", "2", None),
        "goscon_data": ("org-goscon.json", "data", None, P),
        # ── KNM ──
        "knm_preview": ("org-knm.json", "preview", None, None),
        "knm_data": ("org-knm.json", "data", None, P),
        # ── Proverki ──
        "proverki_preview": ("org-proverki.json", "preview", None, None),
        "proverki_data": ("org-proverki.json", "data", None, P),
        # ── Sanctions ──
        "sanctions_preview": ("org-sanctions.json", "preview", None, None),
        "sanctions_data": ("org-sanctions.json", "data", None, None),
        "sanctions_data_v2": ("org-sanctions.json", "data", "2", P),
        # ── Pledge ──
        "pledge_preview": ("org-pledge-local.json", "preview", None, None),
        "pledge_preview_v2": ("org-pledge-local.json", "preview", "2", None),
        "pledge_data": ("org-pledge-local.json", "data", None, P),
        # ── Trademarks ──
        "trademarks_preview": ("org-trademarks.json", "preview", None, None),
        "trademarks_data": ("org-trademarks.json", "data", None, P),
        # ── Leasing ──
        "leasing_preview": ("org-leasing-sources.json", "preview", None, None),
        "leasing_preview_v2": ("org-leasing-sources.json", "preview", "2", None),
        "leasing_preview_v3": ("org-leasing-sources.json", "preview", "3", None),
        "leasing_data": ("org-leasing-sources.json", "data", None, P),
        "leasing_history": ("org-leasing-sources.json", "history", None, P),
        # ── Foreign agent ──
        "foreign_agent_preview": ("org-foreign-agent.json", "preview", None, None),
        "foreign_agent_data_v3": ("org-foreign-agent.json", "data", "3", P),
        # ── Terrorist ──
        "terrorist_preview": ("org-terrorist.json", "preview", None, None),
        "terrorist_data": ("org-terrorist.json", "data", None, P),
        # ── Remuneration (corruption) ──
        "remuneration_preview": ("org-remuneration.json", "preview", None, None),
        "remuneration_data": ("org-remuneration.json", "data", None, P),
        # ── Subsidiary ──
        "subsidiary_preview": ("org-subsidiary.json", "preview", None, None),
        "subsidiary_data": ("org-subsidiary.json", "data", None, None),
        # ── ROM ──
        "rom_preview": ("org-rom.json", "preview", None, None),
        "rom_data": ("org-rom.json", "data", None, P),
        # ── CBR ──
        "cbr_wl": ("org-cbr-wl.json", "data", None, None),
        # ── FSGS ──
        "fsgs_preview": ("org-fsgs.json", "preview", None, None),
        "fsgs_data": ("org-fsgs.json", "data", None, P),
        # ── RD ──
        "rd_preview": ("org-rd.json", "preview", None, None),
        "rd_data": ("org-rd.json", "data", None, P),
        # ── Nalog opendata (MSP) ──
        "msp_preview_v2": ("org-nalog-opendata.json", "preview", "2", None),
        "msp_data": ("org-nalog-opendata.json", "data", None, P),
        "msp_data_v2": ("org-nalog-opendata.json", "data", "2", P),
        "msp_chart": ("org-nalog-opendata.json", "rsmppp-chart", None, None),
        # ── Contacts ──
        "contact": ("org-contact.json", "data", None, None),
        # ── Disclosure ──
        "disclosure": ("org-disclosure.json", "data", None, None),
        # ── PB ──
        "pb_preview": ("org-pb.json", "preview", None, None),
        "pb_docs": ("org-pb.json", "docs", None, P),
        "pb_urls": ("org-pb.json", "urls", None, None),
        # ── OKATO ──
        "okato": ("org-okato-address.json", "address", None, None),
        # ── Judge ──
        "judge_preview": ("org-judge.json", "role-preview", None, None),
        "judge_preview_v2": ("org-judge.json", "role-preview", "2", None),
        "judge_data": ("org-judge.json", "role-data", "2", P),
        "judge_category_preview": ("org-judge.json", "category-preview", None, None),
        "judge_region_preview": ("org-judge.json", "region-preview", None, None),
        "judge_resolution": ("org-judge.json", "resolution", None, P),
        "judge_result": ("org-judge.json", "result", None, None),
    }


def _people_endpoints():
    P = {"page": 0, "rows": 20}
    return {
        # ── EGRIP ──
        "egrip": ("people-egrip.json", "data", None, None),
        "egrip_tax_modes": ("people-egrip.json", "tax-modes", None, None),
        "egrip_tax_modes_history": ("people-egrip.json", "tax-modes-history", None, None),
        # ── People orgs ──
        "people_orgs": ("people-orgs.json", "data", "5", {"page": 0, "rows": 50}),
        "people_orgs_data": ("people-orgs.json", "data", None, P),
        "people_orgs_preview_v2": ("people-orgs.json", "preview", "2", None),
        "people_orgs_preview_v3": ("people-orgs.json", "preview", "3", None),
        "people_orgs_egrip": ("people-orgs.json", "egrip", None, None),
        "people_orgs_ip": ("people-orgs.json", "ip", None, None),
        "people_orgs_name_changes": ("people-orgs.json", "name_changes", None, None),
        "people_orgs_graph_node": ("people-orgs.json", "graph-node", None, None),
        # ── Arbitr ──
        "arbitr_data_v2": ("people-arbitr.json", "data", "2", P),
        "arbitr_data_v3": ("people-arbitr.json", "data", "3", {"page": 0, "rows": 3, "match_filter": "INN"}),
        "arbitr_preview_v3": ("people-arbitr.json", "preview", "3", None),
        "arbitr_region_preview": ("people-arbitr.json", "region-preview", None, None),
        "arbitr_role_preview": ("people-arbitr.json", "role-preview", None, None),
        # ── Arrest ──
        "arrest_preview": ("people-arrest.json", "preview", None, None),
        "arrest_data": ("people-arrest.json", "data", None, None),
        "arrest_saldo": ("people-arrest.json", "saldo", None, None),
        # ── Bankrot ──
        "bankrot_preview": ("people-bankrot.json", "preview", None, None),
        "bankrot_data": ("people-bankrot.json", "data", None, None),
        # ── Bankruptcy intention ──
        "bankruptcy_intention_preview": ("people-bankruptcy-intention.json", "preview", None, None),
        "bankruptcy_intention_data": ("people-bankruptcy-intention.json", "data", None, P),
        # ── Dishonest supplier ──
        "dishonest_supplier_preview": ("people-dishonest-supplier.json", "preview", None, None),
        "dishonest_supplier_preview_v2": ("people-dishonest-supplier.json", "preview", "2", None),
        "dishonest_supplier_data": ("people-dishonest-supplier.json", "data", None, P),
        # ── Goscon ──
        "goscon_preview": ("people-goscon.json", "preview", None, None),
        "goscon_preview_v2": ("people-goscon.json", "preview", "2", None),
        "goscon_data": ("people-goscon.json", "data", None, P),
        # ── Sanctions ──
        "sanctions_preview": ("people-sanctions.json", "preview", None, None),
        "sanctions_data": ("people-sanctions.json", "data", None, None),
        "sanctions_data_v2": ("people-sanctions.json", "data", "2", P),
        # ── Pledge ──
        "pledge_preview": ("people-pledge-local.json", "preview", None, None),
        "pledge_preview_v2": ("people-pledge-local.json", "preview", "2", None),
        "pledge_data": ("people-pledge-local.json", "data", None, P),
        # ── Trademarks ──
        "trademarks_preview": ("people-trademarks.json", "preview", None, None),
        "trademarks_data": ("people-trademarks.json", "data", None, P),
        # ── Leasing ──
        "leasing_preview": ("people-leasing-sources.json", "preview", None, None),
        "leasing_preview_v2": ("people-leasing-sources.json", "preview", "2", None),
        "leasing_preview_v3": ("people-leasing-sources.json", "preview", "3", None),
        "leasing_data": ("people-leasing-sources.json", "data", None, P),
        "leasing_history": ("people-leasing-sources.json", "history", None, P),
        # ── Foreign agent ──
        "foreign_agent_preview": ("people-foreign-agent.json", "preview", None, None),
        "foreign_agent_preview_v2": ("people-foreign-agent.json", "preview", "2", None),
        "foreign_agent_data_v3": ("people-foreign-agent.json", "data", "3", P),
        # ── Terrorist ──
        "terrorist_preview": ("people-terrorist.json", "preview", None, None),
        "terrorist_preview_v2": ("people-terrorist.json", "preview", "2", None),
        "terrorist_data": ("people-terrorist.json", "data", None, P),
        # ── Subsidiary ──
        "subsidiary_preview": ("people-subsidiary.json", "preview", None, None),
        "subsidiary_data": ("people-subsidiary.json", "data", None, None),
        # ── ROM ──
        "rom_preview": ("people-rom.json", "preview", None, None),
        "rom_data": ("people-rom.json", "data", None, P),
        # ── Corrupt ──
        "corrupt_preview": ("people-corrupt.json", "preview", None, None),
        "corrupt_preview_v2": ("people-corrupt.json", "preview", "2", None),
        "corrupt_data": ("people-corrupt.json", "data", None, P),
        "corrupt_history": ("people-corrupt.json", "history", None, P),
        # ── FSGS ──
        "fsgs_preview": ("people-fsgs.json", "preview", None, None),
        "fsgs_data": ("people-fsgs.json", "data", None, P),
        # ── Nalog ──
        "nalog_data": ("people-nalog.json", "data", None, None),
        "nalog_ens": ("people-nalog-ens.json", "preview", None, None),
        # ── Nalog opendata (MSP) ──
        "msp_preview_v2": ("people-nalog-opendata.json", "preview", "2", None),
        "msp_data": ("people-nalog-opendata.json", "data", None, P),
        "msp_data_v2": ("people-nalog-opendata.json", "data", "2", P),
        "msp_chart": ("people-nalog-opendata.json", "rsmppp-chart", None, None),
        # ── Passport ──
        "passport": ("people-passport.json", "*", "4", None),
        # ── INN ──
        "inn_data": ("people-inn.json", "data", None, None),
        "invalid_inn_data": ("people-invalid-inn.json", "data", None, None),
        # ── MVD ──
        "mvd_data": ("people-mvd.json", "data", None, None),
        "mvd_bannedfans_preview": ("people-mvd-bannedfans.json", "preview", None, None),
        "mvd_bannedfans_data": ("people-mvd-bannedfans.json", "data", None, P),
        # ── FSIN ──
        "fsin_data": ("people-fsin.json", "data", None, None),
        # ── Self-employed ──
        "self_employed": ("people-self-employed.json", "preview", None, None),
        # ── Scoring ──
        "scoring": ("people-scoring.json", "scoring", None, {"retry": "true"}),
        # ── Popularity ──
        "popularity": ("people-popularity.json", "data", None, None),
        # ── Inheritance ──
        "inheritance_preview": ("people-inheritance.json", "preview", None, None),
        "inheritance_data": ("people-inheritance.json", "data", None, P),
        # ── Judge ──
        "judge_preview": ("people-judge.json", "role-preview", None, None),
        "judge_preview_v2": ("people-judge.json", "role-preview", "2", None),
        "judge_data": ("people-judge.json", "role-data", "2", P),
        "judge_category_preview": ("people-judge.json", "category-preview", None, None),
        "judge_region_preview": ("people-judge.json", "region-preview", None, None),
        "judge_resolution": ("people-judge.json", "resolution", None, P),
        "judge_result": ("people-judge.json", "result", None, None),
        # ── Disqualified ──
        "disqualified_preview": ("people-disqualified.json", "preview", None, None),
        "disqualified_data": ("people-disqualified.json", "data", None, P),
        # ── KNM ──
        "knm_preview": ("people-knm.json", "preview", None, None),
        "knm_data": ("people-knm.json", "data", None, P),
        # ── Proverki ──
        "proverki_preview": ("people-proverki.json", "preview", None, None),
        "proverki_data": ("people-proverki.json", "data", None, P),
        # ── FSSP ──
        "fssp_all_regions_preview": ("people-fssp-all-regions.json", "preview", None, None),
        "fssp_all_regions_preview_v3": ("people-fssp-all-regions.json", "preview", "3", None),
        "fssp_all_regions_previewV2": ("people-fssp-all-regions.json", "previewV2", None, None),
        "fssp_all_regions_data": ("people-fssp-all-regions.json", "data", None, P),
        "fssp_ip_preview": ("people-fssp-ip.json", "preview", None, None),
        "fssp_ip_preview_chart": ("people-fssp-ip.json", "preview_chart", None, None),
        "fssp_ip_data": ("people-fssp-ip.json", "data", None, P),
        "fssp_search_data": ("people-fssp-search.json", "data", None, None),
        "fssp_suspect_data": ("people-fssp-suspect.json", "data", None, None),
        "fssp_aliment_preview": ("people-fssp-aliment.json", "preview", None, None),
        "fssp_aliment_data": ("people-fssp-aliment.json", "data", None, P),
        "fssp_preview": ("people-fssp.json", "preview", None, None),
        "fssp_preview_v3": ("people-fssp.json", "preview", "3", None),
        "fssp_previewV2": ("people-fssp.json", "previewV2", None, None),
        "fssp_data": ("people-fssp.json", "data", None, P),
        # ── OKATO ──
        "okato": ("people-okato-address.json", "address", None, None),
        # ── Driver license ──
        "driver_license": ("driver-license.json", "data", None, None),
        "driver_tractor_license": ("driver-tractor-license.json", "data", None, None),
        # ── Foreigner registration ──
        "foreigner_rkl": ("foreigner-rkl.json", "data", None, None),
    }


def _get_endpoints(is_ip: bool) -> dict:
    if is_ip:
        return _people_endpoints()
    return _org_endpoints()


# ═══════════════════════════════════════════════════════════════
# Transform functions
# ═══════════════════════════════════════════════════════════════

def _transform(results: dict, inn: str, is_ip: bool) -> dict:
    if is_ip:
        return _transform_ip(results, inn)
    return _transform_ul(results, inn)


def _transform_fssp(results: dict, count: int, total_debt: float) -> dict:
    raw = results.get("fssp_data", {}) or {}
    proceedings = _extract_result(raw)

    transformed = []
    for p in proceedings:
        transformed.append({
            "number": p.get("number", ""),
            "amount": p.get("amount", p.get("sum", 0)),
            "status": p.get("status", ""),
            "date": p.get("date", ""),
        })
    return {
        "total_proceedings": count,
        "total_debt": total_debt,
        "has_proceedings": count > 0,
        "proceedings": transformed,
    }


def _extract_result(raw) -> list:
    """Extract result list from nested {response: {result: ...}} or flat {result: ...} or {itemList: [...]}."""
    if isinstance(raw, dict):
        if "response" in raw and isinstance(raw["response"], dict):
            res = raw["response"].get("result", []) or raw["response"].get("itemList", [])
        elif "status" in raw:
            return []
        else:
            res = raw.get("result", []) or raw.get("itemList", [])
        if isinstance(res, list):
            return res
        if isinstance(res, dict):
            return [res]
        return []
    if isinstance(raw, list):
        return raw
    return []


def _transform_arbitr(results: dict, total_cases: int) -> dict:
    raw = results.get("arbitr_data_v3", {}) or results.get("arbitr_data_v2", {}) or results.get("arbitr_data", {}) or {}
    if isinstance(raw, dict) and "error" in raw:
        raw = results.get("arbitr_data_v2", {}) or results.get("arbitr_data_v3", {}) or results.get("arbitr_data", {}) or {}
    if isinstance(raw, dict) and "error" in raw:
        raw = results.get("arbitr_data", results.get("arbitr_preview", [])) or {}
    cases_raw = _extract_result(raw)

    role_map = {"P": "Истец", "R": "Ответчик", "SIDE": "Третье лицо", "OTHER": "Иное"}
    cases = []
    plaintiff_count = 0
    defendant_count = 0
    for c in cases_raw:
        role_code = c.get("role", "")
        role_ru = role_map.get(role_code, role_code)
        if role_code == "P":
            plaintiff_count += 1
        elif role_code == "R":
            defendant_count += 1
        cases.append({
            "number": c.get("case_number", ""),
            "date": c.get("case_date", ""),
            "role": role_ru,
            "amount": "",
            "subject": c.get("court_name_val", ""),
            "opponents": [o.get("name", "") for o in c.get("opponent_names", [])],
        })

    return {
        "total_cases": total_cases,
        "as_plaintiff": plaintiff_count,
        "as_defendant": defendant_count,
        "tax_disputes": 0,
        "total_claims_amount": 0,
        "cases": cases,
    }


def _transform_ul(results: dict, inn: str) -> dict:
    egrul = results.get("egrul_result_v4", {}) or {}
    if isinstance(egrul, dict) and "error" in egrul:
        egrul = {}

    manager_list = egrul.get("manager_fl", []) or []
    director_face = {}
    if manager_list:
        director_face = manager_list[0].get("fl", {}) or {}
    founders_fl = egrul.get("founders", {}).get("fl", []) or []
    addr = egrul.get("address", {})
    base_okved = egrul.get("base_okved", {}) or {}
    additional_okved = egrul.get("additional_okved", []) or []
    born = egrul.get("born", {}) or {}

    tax_modes = results.get("egrul_tax_modes", {}) or {}
    if isinstance(tax_modes, dict):
        tax_mode_str = tax_modes.get("tax_modes", "")
    else:
        tax_mode_str = ""

    balance = results.get("balance_preview_v2") or results.get("balance_preview", [])
    if isinstance(balance, dict):
        balance_list = balance.get("itemList", [])
    elif isinstance(balance, list):
        balance_list = balance
    else:
        balance_list = []

    fssp_preview = results.get("fssp_preview", []) or []
    if isinstance(fssp_preview, list):
        fssp_count = sum(item.get("count", 0) for item in fssp_preview)
        fssp_sum = sum(item.get("sum", 0) for item in fssp_preview)
    else:
        fssp_count = 0
        fssp_sum = 0

    arbitr_preview = results.get("arbitr_preview", []) or []
    if isinstance(arbitr_preview, list):
        total_cases = sum(item.get("count", 0) for item in arbitr_preview)
    else:
        total_cases = 0

    arrest_saldo_raw = results.get("arrest_saldo", {}) or {}
    if isinstance(arrest_saldo_raw, dict):
        tax_debt_arrest = arrest_saldo_raw.get("saldo") or arrest_saldo_raw.get("sum") or 0
    else:
        tax_debt_arrest = 0
    if isinstance(tax_debt_arrest, dict):
        tax_debt_arrest = 0

    revenue_by_year = {}
    profit_by_year = {}
    balance_by_year = {}
    for item in balance_list:
        year = str(item.get("year", ""))
        if year:
            try:
                revenue_by_year[year] = float(item.get("sales", 0) or 0)
            except (ValueError, TypeError):
                pass
            try:
                profit_by_year[year] = float(item.get("net_profit", 0) or 0)
            except (ValueError, TypeError):
                pass
            try:
                balance_by_year[year] = float(item.get("balance", 0) or 0)
            except (ValueError, TypeError):
                pass

    ds = results.get("dishonest_supplier_preview", []) or []
    if isinstance(ds, list):
        in_registry = len(ds) > 0
    else:
        in_registry = False

    lic = results.get("egrul_licenses", {}) or {}
    lic_count = lic.get("count", 0) if isinstance(lic, dict) else 0

    knm = results.get("knm_preview", {}) or {}
    if isinstance(knm, dict):
        knm_type = knm.get("type", {}) or {}
        knm_all = knm_type.get("all", 0)
    else:
        knm_all = 0

    goscon = results.get("goscon_preview", []) or []

    company_name = egrul.get("short_name", "") or egrul.get("full_name", "") or f"ИНН_{inn}"

    agent_data = {
        "agent_egrul": {
            "inn": inn,
            "ogrn": egrul.get("ogrn", ""),
            "kpp": egrul.get("kpp", ""),
            "short_name": egrul.get("short_name", ""),
            "full_name": egrul.get("full_name", ""),
            "status": egrul.get("status", ""),
            "reg_date": born.get("ogrn_date", ""),
            "tax_regime": tax_mode_str,
            "okved_main": f"{base_okved.get('code', '')} — {base_okved.get('name', '')}",
            "okved_main_code": base_okved.get("code", ""),
            "okved_additional": [
                {"code": o.get("code", ""), "name": o.get("name", "")}
                for o in additional_okved
            ],
            "address": addr.get("full_address", ""),
            "employees": "",
            "authorized_capital": egrul.get("capital", ""),
            "ifns": egrul.get("reg_org_name", "") or egrul.get("reg_org_number", ""),
            "director": {
                "fio": _person_name(director_face),
                "inn": director_face.get("inn", ""),
            },
            "founders": [
                {
                    "fio": _person_name(f.get("face", {})),
                    "inn": f.get("face", {}).get("inn", ""),
                    "share": f.get("share_capital", ""),
                }
                for f in founders_fl
            ],
            "is_ip": False,
            "tax_debt": tax_debt_arrest,
            "tax_paid": 0,
            "tax_burden_percent": 0,
            "revenue_2025": revenue_by_year.get("2025", 0),
            "revenue_2024": revenue_by_year.get("2024", 0),
            "revenue_2023": revenue_by_year.get("2023", 0),
            "revenue_2022": revenue_by_year.get("2022", 0),
        },
        "agent_transparent": {
            "tax_debt": tax_debt_arrest,
            "taxes_paid": 0,
            "employees_count": 0,
            "tax_burden_percent": 0,
            "income": revenue_by_year.get(list(revenue_by_year.keys())[-1], 0) if revenue_by_year else 0,
            "expenses": 0,
        },
        "agent_fssp": _transform_fssp(results, fssp_count, fssp_sum),
        "agent_arbitr": _transform_arbitr(results, total_cases),
        "agent_rusprofile": {
            "revenue": revenue_by_year,
            "net_profit": profit_by_year,
            "net_assets": balance_by_year,
        },
        "agent_media": {
            "overall_sentiment": "нейтральная",
            "media_articles": [],
            "note": "Поиск по СМИ через ir-bis не поддерживается",
        },
        "agent_ndp": {
            "in_registry": in_registry,
            "entries": results.get("dishonest_supplier_data", []),
        },
        "agent_inspections": {
            "total_inspections": knm_all,
            "tax_inspections": 0,
            "violations": 0,
            "inspections": results.get("knm_data", []),
        },
        "agent_bankrupt": {
            "total_records": results.get("bankrot_preview", {}).get("inn", 0) if isinstance(results.get("bankrot_preview"), dict) else 0,
            "has_bankruptcy": bool(results.get("bankrot_data", []) and isinstance(results.get("bankrot_data"), list) and len(results.get("bankrot_data")) > 0),
            "records": results.get("bankrot_data", []) if isinstance(results.get("bankrot_data"), list) else [],
        },
        "agent_licenses": {
            "count": lic_count,
            "licenses": lic.get("result", []) if isinstance(lic, dict) else [],
            "license_required": False,
            "has_license": lic_count > 0,
            "risk_no_license": False,
        },
        "agent_crosscheck": {
            "connections": _build_connections(results.get("egrul_graph_node", {}), company_name),
        },
        # ── All raw data ──
        "_irbis_raw": results,
        "_irbis_balance": balance_list,
        "_irbis_tax_modes": tax_mode_str,
        "_irbis_goscon": results.get("goscon_data", results.get("goscon_preview", [])),
        "_irbis_sanctions": results.get("sanctions_data_v2", results.get("sanctions_data", {})),
        "_irbis_pledge": results.get("pledge_data", []),
        "_irbis_trademarks": results.get("trademarks_data", []),
        "_irbis_leasing": results.get("leasing_data", []),
        "_irbis_foreign_agent": results.get("foreign_agent_data_v3", results.get("foreign_agent_preview", {})),
        "_irbis_terrorist": results.get("terrorist_data", []),
        "_irbis_remuneration": results.get("remuneration_data", []),
        "_irbis_subsidiary": results.get("subsidiary_data", []),
        "_irbis_rom": results.get("rom_data", []),
        "_irbis_cbr_wl": results.get("cbr_wl", {}),
        "_irbis_fsgs": results.get("fsgs_data", {}),
        "_irbis_rd": results.get("rd_data", []),
        "_irbis_msp": results.get("msp_data_v2", results.get("msp_data", {})),
        "_irbis_contacts": results.get("contact", {}),
        "_irbis_disclosure": results.get("disclosure", {}),
        "_irbis_pb_urls": results.get("pb_urls", {}),
        "_irbis_history": results.get("egrul_history", {}),
        "_irbis_graph": results.get("egrul_graph_node", {}),
        "_irbis_neighbours": results.get("egrul_neighbours", {}),
        "_irbis_founded": results.get("egrul_founded", {}),
        "_irbis_judge": results.get("judge_data", []),
        "_irbis_judge_preview": results.get("judge_preview", {}),
        "_irbis_judge_resolution": results.get("judge_resolution", []),
        "_irbis_judge_result": results.get("judge_result", {}),
        "_irbis_arrest": results.get("arrest_data", []) if isinstance(results.get("arrest_data"), list) else [],
        "_irbis_proverki": results.get("proverki_data", []),
        "_irbis_bankruptcy_intention": results.get("bankruptcy_intention_data", []),
        "_irbis_okato": results.get("okato", {}),
        "_irbis_arrest_saldo": tax_debt_arrest,
        "_irbis_fssp_preview_fns": results.get("fssp_preview_fns_v2", results.get("fssp_preview_fns", {})),
        # ── People-specific keys (empty defaults for org checks) ──
        "_irbis_disqualified": [],
        "_irbis_fsin": {},
        "_irbis_inheritance": [],
        "_irbis_mvd": {},
        "_irbis_mvd_bannedfans": [],
        "_irbis_passport": {},
        "_irbis_popularity": {},
        "_irbis_scoring": {},
        "_irbis_self_employed": {},
        "_irbis_driver_license": {},
        "_irbis_driver_tractor_license": {},
        "_irbis_foreigner_rkl": {},
        "_irbis_nalog": {},
        "_irbis_nalog_ens": {},
        "_irbis_corrupt": {},
    }

    return agent_data


def _transform_ip(results: dict, inn: str) -> dict:
    egrip = results.get("egrip", {}) or {}
    people_orgs = results.get("people_orgs", {}) or {}
    orgs_list = []
    if isinstance(people_orgs, dict):
        orgs_list = people_orgs.get("result", [])
    elif isinstance(people_orgs, list):
        orgs_list = people_orgs

    person_name = inn
    person_inn = inn
    okved_code = ""
    okved_name = ""

    for org_entry in orgs_list:
        ind = org_entry.get("individual_data", {})
        if ind.get("inn") == inn:
            person_name = ind.get("name", person_name)
        org_d = org_entry.get("org_data", {})
        if org_d.get("inn") == inn:
            okved = org_d.get("okved", {}) or {}
            okved_code = okved.get("code", "")
            okved_name = okved.get("name", "")

    fssp = results.get("fssp_all_regions_preview", []) or []
    if isinstance(fssp, list):
        fssp_count = sum(item.get("count", 0) for item in fssp)
        fssp_sum = sum(item.get("sum", 0) for item in fssp)
    else:
        fssp_count = 0
        fssp_sum = 0

    agent_data = {
        "agent_egrul": {
            "inn": inn,
            "short_name": person_name,
            "full_name": person_name,
            "is_ip": True,
            "ogrn": "",
            "status": "Действующий",
            "okved_main": f"{okved_code} — {okved_name}" if okved_code else "",
            "director": {"fio": person_name, "inn": person_inn},
            "founders": [],
            "address": "",
        },
        "agent_transparent": {"tax_debt": 0, "taxes_paid": 0, "employees_count": 0,
                               "tax_burden_percent": 0, "income": 0, "expenses": 0},
        "agent_fssp": {"total_proceedings": fssp_count, "total_debt": fssp_sum,
                        "has_proceedings": fssp_count > 0, "proceedings": []},
        "agent_arbitr": {"total_cases": 0, "as_plaintiff": 0, "as_defendant": 0,
                          "tax_disputes": 0, "total_claims_amount": 0, "cases": []},
        "agent_rusprofile": {"revenue": {}, "net_profit": {}, "net_assets": {}},
        "agent_media": {"overall_sentiment": "нейтральная", "media_articles": []},
        "agent_ndp": {"in_registry": False, "entries": []},
        "agent_inspections": {"total_inspections": 0, "tax_inspections": 0,
                               "violations": 0, "inspections": []},
        "agent_bankrupt": {"total_records": 0, "has_bankruptcy": False, "records": []},
        "agent_licenses": {"count": 0, "licenses": [], "license_required": False,
                            "has_license": False, "risk_no_license": False},
        "agent_crosscheck": {"connections": []},
        "_irbis_raw": results,
        # ── People-specific _irbis_ keys ──
        "_irbis_sanctions": results.get("sanctions_data_v2", results.get("sanctions_data", {})),
        "_irbis_pledge": results.get("pledge_data", []),
        "_irbis_trademarks": results.get("trademarks_data", []),
        "_irbis_leasing": results.get("leasing_data", []),
        "_irbis_foreign_agent": results.get("foreign_agent_data_v3", results.get("foreign_agent_preview", {})),
        "_irbis_terrorist": results.get("terrorist_data", []),
        "_irbis_subsidiary": results.get("subsidiary_data", []),
        "_irbis_rom": results.get("rom_data", []),
        "_irbis_corrupt": results.get("corrupt_data", results.get("corrupt_preview", {})),
        "_irbis_fsgs": results.get("fsgs_data", {}),
        "_irbis_nalog": results.get("nalog_data", {}),
        "_irbis_nalog_ens": results.get("nalog_ens", {}),
        "_irbis_msp": results.get("msp_data_v2", results.get("msp_data", {})),
        "_irbis_passport": results.get("passport", {}),
        "_irbis_inn_data": results.get("inn_data", {}),
        "_irbis_invalid_inn": results.get("invalid_inn_data", {}),
        "_irbis_mvd": results.get("mvd_data", {}),
        "_irbis_mvd_bannedfans": results.get("mvd_bannedfans_data", []),
        "_irbis_fsin": results.get("fsin_data", {}),
        "_irbis_self_employed": results.get("self_employed", {}),
        "_irbis_scoring": results.get("scoring", {}),
        "_irbis_popularity": results.get("popularity", {}),
        "_irbis_inheritance": results.get("inheritance_data", []),
        "_irbis_judge": results.get("judge_data", []),
        "_irbis_judge_resolution": results.get("judge_resolution", []),
        "_irbis_judge_result": results.get("judge_result", {}),
        "_irbis_driver_license": results.get("driver_license", {}),
        "_irbis_driver_tractor_license": results.get("driver_tractor_license", {}),
        "_irbis_foreigner_rkl": results.get("foreigner_rkl", {}),
        "_irbis_disqualified": results.get("disqualified_data", []),
        "_irbis_proverki": results.get("proverki_data", []),
        "_irbis_goscon": results.get("goscon_data", results.get("goscon_preview", [])),
        "_irbis_arrest": results.get("arrest_data", []),
        "_irbis_arrest_saldo": results.get("arrest_saldo", {}),
        "_irbis_bankruptcy_intention": results.get("bankruptcy_intention_data", []),
        "_irbis_fssp_ip": results.get("fssp_ip_data", []),
        "_irbis_fssp_search": results.get("fssp_search_data", {}),
        "_irbis_fssp_suspect": results.get("fssp_suspect_data", {}),
        "_irbis_fssp_aliment": results.get("fssp_aliment_data", []),
        "_irbis_egrip_tax_modes": results.get("egrip_tax_modes", {}),
        # ── Org-specific keys (empty defaults for people checks) ──
        "_irbis_cbr_wl": {},
        "_irbis_contacts": {},
        "_irbis_disclosure": {},
        "_irbis_fssp_preview_fns": {},
        "_irbis_history": {},
        "_irbis_okato": {},
        "_irbis_pb_urls": {},
        "_irbis_rd": [],
        "_irbis_remuneration": [],
        "_irbis_balance": [],
        "_irbis_tax_modes": "",
        "_irbis_founded": {},
        "_irbis_graph": {},
        "_irbis_neighbours": {},
        "_irbis_judge_preview": {},
    }

    return agent_data


def _build_connections(graph: dict, company_name: str) -> list:
    connections = []
    if isinstance(graph, dict):
        links = graph.get("links", [])
        nodes = graph.get("nodes", [])
        node_map = {}
        for node in nodes:
            node_id = node.get("id", "")
            node_map[node_id] = node

        for link in links:
            source_id = link.get("source", "")
            target_id = link.get("target", "")
            roles = link.get("roles", [])
            role_names = ", ".join(r.get("name", "") for r in roles)

            source = node_map.get(source_id, {})
            target = node_map.get(target_id, {})

            source_name = source.get("name", "") or source.get("short_name", "")
            target_name = target.get("name", "") or target.get("short_name", "")

            if company_name in source_name or company_name in target_name:
                other = target_name if source_name == company_name else source_name
                connections.append({
                    "type": role_names or "связь",
                    "entity_a": company_name,
                    "entity_b": other,
                    "person_inn": source.get("inn", "") or target.get("inn", ""),
                    "detail": role_names or "участие",
                    "strength": "strong" if "генеральн" in role_names.lower()
                                or "учредител" in role_names.lower() else "medium",
                })
    return connections
