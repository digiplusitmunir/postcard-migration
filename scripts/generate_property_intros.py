"""Generate AI titles + intros for Postcard StarPartner Stays properties.

Fetches all albums belonging to the "Postcard StarPartner Stays" directory
(slug: mindful-luxury-hotels) from the legacy Strapi CMS, then generates a
property title (60-65 chars) and intro (70-80 words, British English) for
each via the Anthropic Message Batches API, and writes everything to a CSV:

    id, property_name, country, property_title, property_intro

Why the Batches API instead of 5-10 albums per live call:
  - 50% cheaper than standard API calls
  - one album per request = best per-property quality, and one bad result
    never spoils the other 9 in the same prompt
  - a ~2k-request batch is submitted in one shot and usually completes
    within the hour; no rate-limit juggling

Idempotent / resumable: results are keyed by album id. If the output CSV
already exists, albums already present in it are skipped, so a partial or
failed run can simply be re-run to fill in the gaps.

Usage:
    python scripts/generate_property_intros.py            # full run
    python scripts/generate_property_intros.py --dry-run  # fetch + count only
"""

import argparse
import csv
import json
import time
from pathlib import Path
import os

import requests
import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

CMS_BASE_URL = os.environ["CMS_BASE_URL"].rstrip("/")
HEADERS = {"Authorization": f"Bearer {os.environ['CMS_API_TOKEN']}"}

DIRECTORY_SLUG = "mindful-luxury-hotels"  # Postcard StarPartner Stays
MODEL = "claude-opus-5"
OUT_CSV = ROOT / "property_intros.csv"
POLL_SECONDS = 30

FIELDNAMES = ["id", "property_name", "country", "property_title", "property_intro"]

INSTRUCTIONS = """\
Write an engaging introduction for this property in 70-80 words using British \
English. The tone should feel warm, invitational and refined, appealing to \
conscious luxury travellers. Introduce the property's location, surrounding \
and what makes it distinctive, while briefly highlighting its experiences, \
design and conservation or community impact where relevant. Avoid generic \
travel cliches and overused AI phrases. The introduction should spark \
curiosity and inspire readers to imagine themselves staying there.

Also, write a title of 60-65 characters that includes the property's name and \
feels inspiring, while reflecting the essence of the stay."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {
            "type": "string",
            "description": "Inspiring title, 60-65 characters, includes the property's name",
        },
        "intro": {
            "type": "string",
            "description": "70-80 word introduction in British English",
        },
    },
    "required": ["title", "intro"],
    "additionalProperties": False,
}


def attrs(item):
    """Entry fields — Strapi v4 nests them under 'attributes', v5 is flat."""
    return item.get("attributes", item)


def rel(obj):
    """Unwrap a populated relation — v4: {'data': {'attributes': {...}}}, v5: flat dict."""
    if isinstance(obj, dict) and "data" in obj:
        obj = obj["data"]
    if not obj:
        return None
    return obj.get("attributes", obj)


def fetch_all(path, params=None):
    """Fetch every page of a Strapi collection endpoint (data/meta envelope)."""
    items, page = [], 1
    while True:
        p = {"pagination[page]": page, "pagination[pageSize]": 100, "sort": "id", **(params or {})}
        r = requests.get(f"{CMS_BASE_URL}{path}", headers=HEADERS, params=p, timeout=120)
        r.raise_for_status()
        body = r.json()
        items.extend(body["data"])
        pg = body.get("meta", {}).get("pagination", {})
        if page >= pg.get("pageCount", 1):
            return items
        page += 1


def fetch_properties():
    albums = fetch_all(
        "/api/albums",
        {
            "filters[directories][slug][$eq]": DIRECTORY_SLUG,
            "populate": "country",
        },
    )
    props, skipped_no_name = [], []
    for al in sorted(albums, key=lambda x: x["id"]):
        a = attrs(al)
        name = (a.get("name") or "").strip()
        if not name:
            skipped_no_name.append(al["id"])
            continue
        country = rel(a.get("country"))
        props.append(
            {
                "id": al["id"],
                "name": name,
                "country": ((country or {}).get("name") or "").strip(),
                "description": (a.get("description") or "").strip(),
            }
        )
    if skipped_no_name:
        print(f"WARNING: skipped {len(skipped_no_name)} albums with no name: {skipped_no_name}")
    missing_country = [p["id"] for p in props if not p["country"]]
    if missing_country:
        print(f"WARNING: {len(missing_country)} properties have no country: {missing_country}")
    return props


def build_prompt(prop):
    lines = [f"Property name: {prop['name']}"]
    if prop["country"]:
        lines.append(f"Country: {prop['country']}")
    if prop["description"]:
        lines.append(f"Existing description (use for factual grounding):\n{prop['description']}")
    return "\n".join(lines) + "\n\n" + INSTRUCTIONS


def load_done_ids():
    """Album ids already present in the output CSV (for resume)."""
    if not OUT_CSV.exists():
        return {}
    with OUT_CSV.open(newline="", encoding="utf-8") as f:
        return {int(row["id"]): row for row in csv.DictReader(f)}


def run_batch(client, props):
    requests_ = [
        Request(
            custom_id=f"album-{p['id']}",
            params=MessageCreateParamsNonStreaming(
                model=MODEL,
                max_tokens=2048,
                output_config={
                    "effort": "medium",
                    "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
                },
                messages=[{"role": "user", "content": build_prompt(p)}],
            ),
        )
        for p in props
    ]
    batch = client.messages.batches.create(requests=requests_)
    print(f"submitted batch {batch.id} with {len(requests_)} requests")

    while True:
        batch = client.messages.batches.retrieve(batch.id)
        c = batch.request_counts
        print(
            f"  status={batch.processing_status} "
            f"processing={c.processing} succeeded={c.succeeded} errored={c.errored}"
        )
        if batch.processing_status == "ended":
            break
        time.sleep(POLL_SECONDS)

    results, failed = {}, []
    for result in client.messages.batches.results(batch.id):
        album_id = int(result.custom_id.removeprefix("album-"))
        if result.result.type != "succeeded":
            failed.append((album_id, result.result.type))
            continue
        msg = result.result.message
        if msg.stop_reason == "refusal":
            failed.append((album_id, "refusal"))
            continue
        text = next((b.text for b in msg.content if b.type == "text"), "")
        try:
            data = json.loads(text)
            results[album_id] = {"title": data["title"], "intro": data["intro"]}
        except (json.JSONDecodeError, KeyError) as e:
            failed.append((album_id, f"parse: {e}"))
    return results, failed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="fetch + count only, no Anthropic calls")
    parser.add_argument("--limit", type=int, help="generate for at most N properties (e.g. --limit 10 to test)")
    args = parser.parse_args()

    props = fetch_properties()
    print(f"fetched {len(props)} StarPartner Stays properties from Strapi")

    done = load_done_ids()
    todo = [p for p in props if p["id"] not in done]
    if done:
        print(f"resume: {len(done)} already in {OUT_CSV.name}, {len(todo)} remaining")
    if args.limit:
        todo = todo[: args.limit]
        print(f"--limit {args.limit}: generating for {len(todo)} properties this run")
    if args.dry_run:
        for p in props[:5]:
            print(" ", p["id"], p["name"], "-", p["country"] or "(no country)")
        print("dry run - stopping before Anthropic batch")
        return
    if not todo:
        print("nothing to do - all properties already generated")
        return

    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY from .env
    generated, failed = run_batch(client, todo)

    rows = list(done.values())
    for p in todo:
        g = generated.get(p["id"])
        if not g:
            continue
        rows.append(
            {
                "id": p["id"],
                "property_name": p["name"],
                "country": p["country"],
                "property_title": g["title"],
                "property_intro": g["intro"],
            }
        )
    rows.sort(key=lambda r: int(r["id"]))

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT_CSV}")

    if failed:
        print(f"FAILED ({len(failed)}) - re-run the script to retry just these:")
        for album_id, reason in failed:
            print(f"  album {album_id}: {reason}")


if __name__ == "__main__":
    main()
