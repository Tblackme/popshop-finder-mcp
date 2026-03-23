"""
seed_dev.py — Populate Vendor Atlas with 100 fake users and 80+ real-looking events.
Run from the project root: python scripts/seed_dev.py
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage_users import create_user, init_users_db
from storage_events import Event, upsert_event, init_events_db

# ── EVENTS ────────────────────────────────────────────────────────────────────
# 80 real-style US craft market / popup / artisan fair events
EVENTS = [
    # ── Austin, TX ────────────────────────────────────────────
    ("atx-001", "Austin Night Market – Spring Edition",    "Austin",       "TX", "2026-04-11", 180, 4200,  75,  "handmade,food,art",           "large"),
    ("atx-002", "Barton Creek Farmers & Artisan Market",   "Austin",       "TX", "2026-04-18", 90,  2800,  45,  "handmade,farmers,food",        "medium"),
    ("atx-003", "East Austin Makers Fair",                 "Austin",       "TX", "2026-05-03", 65,  1800,  60,  "handmade,art,craft",           "medium"),
    ("atx-004", "South Congress Vintage Flea",             "Austin",       "TX", "2026-05-17", 55,  2200,  50,  "vintage,antiques,clothing",    "medium"),
    ("atx-005", "Mueller Farmers Market",                  "Austin",       "TX", "2026-04-05", 40,  1400,  25,  "farmers,food,handmade",        "small"),
    ("atx-006", "Cherrywood Art Fair",                     "Austin",       "TX", "2026-05-09", 110, 3100,  65,  "art,handmade,jewelry",         "large"),
    # ── Dallas / Fort Worth, TX ───────────────────────────────
    ("dfw-001", "Dallas Renegade Craft Fair",              "Dallas",       "TX", "2026-04-25", 200, 5500,  95,  "handmade,craft,art",           "large"),
    ("dfw-002", "Deep Ellum Arts Festival",                "Dallas",       "TX", "2026-04-17", 300, 8000,  0,   "art,music,food",               "large"),
    ("dfw-003", "Cottonwood Art Festival",                 "Richardson",   "TX", "2026-05-02", 250, 6500,  0,   "art,jewelry,ceramics",         "large"),
    ("dfw-004", "Fort Worth Main Street Arts Festival",    "Fort Worth",   "TX", "2026-04-10", 220, 5800,  0,   "art,handmade,food",            "large"),
    ("dfw-005", "Bishop Arts Market",                      "Dallas",       "TX", "2026-05-23", 60,  1600,  55,  "handmade,vintage,art",         "medium"),
    # ── Houston, TX ───────────────────────────────────────────
    ("hou-001", "Houston Urban Market – Spring",           "Houston",      "TX", "2026-04-19", 75,  2400,  65,  "handmade,food,art",            "medium"),
    ("hou-002", "Heights Mercantile Pop-Up",               "Houston",      "TX", "2026-05-10", 50,  1500,  45,  "vintage,handmade,clothing",    "medium"),
    ("hou-003", "Midtown Farmers Market",                  "Houston",      "TX", "2026-04-12", 45,  1800,  30,  "farmers,food,handmade",        "small"),
    ("hou-004", "Montrose Flea",                           "Houston",      "TX", "2026-05-16", 80,  2000,  40,  "vintage,antiques,art",         "medium"),
    # ── Nashville, TN ────────────────────────────────────────
    ("nas-001", "Nashville Flea Market – April",           "Nashville",    "TN", "2026-04-26", 350, 9000,  20,  "vintage,antiques,handmade",    "large"),
    ("nas-002", "Cheekwood Artisan Market",                "Nashville",    "TN", "2026-05-02", 80,  2200,  55,  "handmade,art,jewelry",         "medium"),
    ("nas-003", "Germantown Night Market",                 "Nashville",    "TN", "2026-04-17", 60,  1700,  60,  "handmade,food,vintage",        "medium"),
    ("nas-004", "East Nashville Makers Market",            "Nashville",    "TN", "2026-05-23", 70,  2000,  65,  "craft,handmade,art",           "medium"),
    # ── Denver, CO ───────────────────────────────────────────
    ("den-001", "Denver Flea – May",                       "Denver",       "CO", "2026-05-16", 150, 4500,  85,  "vintage,handmade,art",         "large"),
    ("den-002", "RiNo Art District Market",                "Denver",       "CO", "2026-04-19", 90,  2500,  70,  "art,handmade,ceramics",        "medium"),
    ("den-003", "Wash Park Farmers & Artisan Market",      "Denver",       "CO", "2026-04-26", 55,  1800,  35,  "farmers,food,handmade",        "medium"),
    ("den-004", "Highlands Square Night Market",           "Denver",       "CO", "2026-05-09", 65,  2000,  75,  "handmade,food,jewelry",        "medium"),
    ("den-005", "Cherry Creek Fresh Market",               "Denver",       "CO", "2026-04-05", 45,  3200,  40,  "farmers,food,handmade",        "small"),
    # ── Portland, OR ─────────────────────────────────────────
    ("pdx-001", "Portland Saturday Market – Spring",       "Portland",     "OR", "2026-04-04", 250, 6000,  35,  "handmade,art,food",            "large"),
    ("pdx-002", "Hawthorne Night Market",                  "Portland",     "OR", "2026-04-18", 80,  2400,  60,  "vintage,handmade,food",        "medium"),
    ("pdx-003", "Alberta Arts District Fair",              "Portland",     "OR", "2026-05-30", 120, 3500,  0,   "art,handmade,music",           "large"),
    ("pdx-004", "Mississippi Avenue Makers Fair",          "Portland",     "OR", "2026-05-10", 70,  1900,  55,  "handmade,craft,ceramics",      "medium"),
    # ── Seattle, WA ──────────────────────────────────────────
    ("sea-001", "Capitol Hill Block Party Artisan Market", "Seattle",      "WA", "2026-04-25", 90,  3000,  70,  "handmade,art,vintage",         "medium"),
    ("sea-002", "Ballard Farmers Market",                  "Seattle",      "WA", "2026-04-12", 60,  4000,  0,   "farmers,food,handmade",        "medium"),
    ("sea-003", "Georgetown Flea",                         "Seattle",      "WA", "2026-05-03", 110, 2800,  25,  "vintage,antiques,clothing",    "large"),
    ("sea-004", "Fremont Sunday Market",                   "Seattle",      "WA", "2026-04-19", 75,  2200,  0,   "vintage,handmade,art",         "medium"),
    # ── Chicago, IL ──────────────────────────────────────────
    ("chi-001", "Renegade Craft Fair Chicago",             "Chicago",      "IL", "2026-06-06", 250, 7000,  100, "handmade,craft,art",           "large"),
    ("chi-002", "Andersonville Midsommarfest Art Fair",    "Chicago",      "IL", "2026-06-12", 80,  5000,  0,   "art,handmade,food",            "medium"),
    ("chi-003", "Logan Square Farmers Market",             "Chicago",      "IL", "2026-05-10", 50,  2500,  0,   "farmers,food,handmade",        "medium"),
    ("chi-004", "Wicker Park Fest Artisan Village",        "Chicago",      "IL", "2026-07-25", 100, 4500,  0,   "handmade,art,jewelry",         "large"),
    ("chi-005", "Chicago Vintage Garage Sale",             "Chicago",      "IL", "2026-04-18", 90,  2000,  15,  "vintage,antiques,clothing",    "medium"),
    # ── Brooklyn / NYC, NY ───────────────────────────────────
    ("nyc-001", "Brooklyn Flea – Williamsburg Spring",     "Brooklyn",     "NY", "2026-04-05", 150, 5500,  0,   "vintage,handmade,food",        "large"),
    ("nyc-002", "Smorgasburg Williamsburg",                "Brooklyn",     "NY", "2026-04-12", 100, 8000,  0,   "food,handmade,art",            "large"),
    ("nyc-003", "Artists & Fleas Chelsea",                 "New York",     "NY", "2026-04-19", 80,  3000,  50,  "handmade,vintage,art",         "medium"),
    ("nyc-004", "Hell's Kitchen Flea Market",              "New York",     "NY", "2026-04-26", 130, 4000,  0,   "vintage,antiques,clothing",    "large"),
    ("nyc-005", "Queens Night Market",                     "Flushing",     "NY", "2026-05-02", 90,  6000,  0,   "food,handmade,art",            "medium"),
    # ── Los Angeles, CA ──────────────────────────────────────
    ("la-001",  "Melrose Trading Post",                    "Los Angeles",  "CA", "2026-04-05", 200, 3500,  3,   "vintage,handmade,clothing",    "large"),
    ("la-002",  "Echo Park Craft Fair",                    "Los Angeles",  "CA", "2026-04-18", 90,  2800,  75,  "handmade,craft,art",           "medium"),
    ("la-003",  "Silver Lake Flea",                        "Los Angeles",  "CA", "2026-05-03", 100, 2500,  25,  "vintage,antiques,handmade",    "large"),
    ("la-004",  "Unique LA Spring Market",                 "Los Angeles",  "CA", "2026-05-17", 250, 6000,  95,  "handmade,craft,jewelry",       "large"),
    ("la-005",  "Highland Park Art Walk Market",           "Los Angeles",  "CA", "2026-04-25", 55,  1600,  0,   "art,handmade,ceramics",        "medium"),
    ("la-006",  "Smorgasburg LA",                          "Los Angeles",  "CA", "2026-04-12", 80,  5000,  0,   "food,handmade,art",            "medium"),
    # ── San Francisco / Bay Area, CA ─────────────────────────
    ("sf-001",  "Mission District Artisan Market",         "San Francisco","CA", "2026-04-19", 80,  3000,  65,  "handmade,art,food",            "medium"),
    ("sf-002",  "Oakland Art Murmur Night Market",         "Oakland",      "CA", "2026-05-01", 70,  2200,  0,   "art,handmade,vintage",         "medium"),
    ("sf-003",  "Renegade Craft Fair SF",                  "San Francisco","CA", "2026-05-30", 200, 5500,  90,  "handmade,craft,art",           "large"),
    ("sf-004",  "Ferry Building Farmers Market",           "San Francisco","CA", "2026-04-05", 50,  6000,  0,   "farmers,food,handmade",        "medium"),
    # ── Phoenix / Scottsdale, AZ ─────────────────────────────
    ("phx-001", "Old Town Scottsdale Art Walk",            "Scottsdale",   "AZ", "2026-04-09", 60,  2000,  0,   "art,jewelry,ceramics",         "medium"),
    ("phx-002", "Phoenix Flea Spring Market",              "Phoenix",      "AZ", "2026-04-26", 100, 2800,  55,  "vintage,handmade,art",         "large"),
    ("phx-003", "Gilbert Farmers Market",                  "Gilbert",      "AZ", "2026-04-11", 40,  1500,  0,   "farmers,food,handmade",        "small"),
    ("phx-004", "Tempe Festival of the Arts",              "Tempe",        "AZ", "2026-04-03", 350, 7000,  0,   "art,jewelry,ceramics",         "large"),
    # ── Miami / South Florida ────────────────────────────────
    ("mia-001", "Wynwood Flea",                            "Miami",        "FL", "2026-04-12", 80,  2500,  60,  "vintage,handmade,art",         "medium"),
    ("mia-002", "South Beach Artisan Market",              "Miami Beach",  "FL", "2026-04-19", 60,  2000,  70,  "handmade,jewelry,art",         "medium"),
    ("mia-003", "Coral Gables Art Cinema Night Market",    "Coral Gables", "FL", "2026-05-02", 55,  1600,  65,  "handmade,food,vintage",        "medium"),
    ("mia-004", "Las Olas Art Fair",                       "Fort Lauderdale","FL","2026-04-10",200, 5000,  0,   "art,jewelry,ceramics",         "large"),
    # ── Atlanta, GA ──────────────────────────────────────────
    ("atl-001", "Ponce City Market Rooftop Pop-Up",        "Atlanta",      "GA", "2026-04-18", 55,  1800,  60,  "handmade,vintage,food",        "medium"),
    ("atl-002", "Little 5 Points Arts & Craft Fair",       "Atlanta",      "GA", "2026-05-09", 90,  2500,  50,  "art,handmade,craft",           "medium"),
    ("atl-003", "Inman Park Spring Festival",              "Atlanta",      "GA", "2026-04-25", 200, 6000,  0,   "art,handmade,food",            "large"),
    ("atl-004", "Grant Park Farmers Market",               "Atlanta",      "GA", "2026-04-12", 45,  2000,  0,   "farmers,food,handmade",        "small"),
    # ── Minneapolis, MN ──────────────────────────────────────
    ("msp-001", "Mill City Farmers Market",                "Minneapolis",  "MN", "2026-05-09", 60,  3500,  0,   "farmers,food,handmade",        "medium"),
    ("msp-002", "Northeast Minneapolis Art Crawl Market",  "Minneapolis",  "MN", "2026-05-01", 120, 3200,  55,  "art,handmade,ceramics",        "large"),
    ("msp-003", "Midtown Global Market Pop-Up",            "Minneapolis",  "MN", "2026-04-18", 50,  1800,  45,  "food,handmade,art",            "medium"),
    # ── Kansas City, MO ──────────────────────────────────────
    ("kc-001",  "First Fridays Crossroads Arts",           "Kansas City",  "MO", "2026-04-03", 80,  2500,  0,   "art,handmade,food",            "medium"),
    ("kc-002",  "KC Night Market – Midtown",               "Kansas City",  "MO", "2026-04-25", 70,  2200,  65,  "handmade,food,vintage",        "medium"),
    ("kc-003",  "Brookside Farmers Market",                "Kansas City",  "MO", "2026-04-12", 40,  1500,  0,   "farmers,food,handmade",        "small"),
    ("kc-004",  "Westport Flea Market Spring Sale",        "Kansas City",  "MO", "2026-05-17", 90,  2000,  25,  "vintage,antiques,clothing",    "medium"),
    # ── New Orleans, LA ──────────────────────────────────────
    ("nol-001", "Frenchmen Art Market",                    "New Orleans",  "LA", "2026-04-11", 60,  2200,  0,   "art,handmade,jewelry",         "medium"),
    ("nol-002", "Crescent City Farmers Market",            "New Orleans",  "LA", "2026-04-19", 50,  3000,  0,   "farmers,food,handmade",        "medium"),
    ("nol-003", "Magazine Street Artisan Fair",            "New Orleans",  "LA", "2026-05-09", 80,  2500,  55,  "handmade,art,vintage",         "medium"),
    # ── Misc national ────────────────────────────────────────
    ("rdu-001", "Durham Craft Market",                     "Durham",       "NC", "2026-04-18", 70,  2000,  60,  "handmade,craft,art",           "medium"),
    ("bos-001", "SoWa Open Market Opening Day",            "Boston",       "MA", "2026-05-03", 100, 3500,  0,   "handmade,vintage,food",        "large"),
    ("pit-001", "Pittsburgh Handmade Market",              "Pittsburgh",   "PA", "2026-04-25", 65,  1800,  55,  "handmade,art,craft",           "medium"),
    ("col-001", "Short North Arts Festival",               "Columbus",     "OH", "2026-06-06", 200, 5500,  0,   "art,handmade,food",            "large"),
    ("stl-001", "Cherokee Street Art Market",              "St. Louis",    "MO", "2026-04-19", 55,  1800,  45,  "art,handmade,vintage",         "medium"),
    ("slc-001", "Salt Lake Farmers Market",                "Salt Lake City","UT", "2026-05-23", 75,  4000,  0,   "farmers,food,handmade",        "medium"),
    ("ral-001", "Moore Square Artists' Market",            "Raleigh",      "NC", "2026-04-25", 45,  1600,  35,  "handmade,art,craft",           "small"),
    ("clt-001", "Charlotte Makers Market",                 "Charlotte",    "NC", "2026-05-09", 70,  2200,  65,  "handmade,craft,jewelry",       "medium"),
    ("ind-001", "Broad Ripple Art Fair",                   "Indianapolis", "IN", "2026-05-16", 180, 4000,  0,   "art,handmade,ceramics",        "large"),
    ("mem-001", "Memphis Made Craft Market",               "Memphis",      "TN", "2026-04-18", 60,  1800,  55,  "handmade,craft,art",           "medium"),
]


# ── USERS ─────────────────────────────────────────────────────────────────────
FIRST_NAMES = [
    "Maya", "Jordan", "Priya", "Sofia", "Marcus", "Aaliyah", "Chloe", "Devon",
    "Elena", "Finn", "Grace", "Hana", "Ivan", "Jade", "Kenji", "Luna",
    "Miles", "Nadia", "Oscar", "Paige", "Quinn", "Rosa", "Sam", "Tara",
    "Uma", "Victor", "Willow", "Xander", "Yasmin", "Zoe", "Ava", "Ben",
    "Carmen", "Diego", "Ellie", "Fiona", "George", "Harper", "Iris", "Jake",
    "Kira", "Leo", "Mia", "Noah", "Olivia", "Parker", "Remi", "Sage",
    "Theo", "Una", "Violet", "Wren", "Xena", "Yuki", "Zara", "Aiden",
    "Blake", "Casey", "Dana", "Evan", "Frankie", "Gabi", "Hunter", "Ingrid",
    "Jules", "Kai", "Lena", "Marco", "Nia", "Owen", "Penelope", "Rio",
    "Sierra", "Tyler", "Ursula", "Vale", "West", "Xio", "Yara", "Zion",
    "Ariel", "Bryce", "Celeste", "Dani", "Emilio", "Faye", "Glen", "Holly",
    "Imani", "Jesse", "Kobe", "Luz", "Maren", "Nico", "Odessa", "Paz",
    "Rafaela", "Sterling", "Tariq", "Ulla",
]

LAST_NAMES = [
    "Chen", "Reyes", "Kim", "Patel", "Johnson", "Williams", "Brown", "Davis",
    "Martinez", "Garcia", "Wilson", "Anderson", "Taylor", "Thomas", "Moore",
    "Jackson", "White", "Harris", "Martin", "Thompson", "Young", "Walker",
    "Hall", "Allen", "Wright", "Scott", "Green", "Baker", "Adams", "Nelson",
    "Hill", "Ramirez", "Campbell", "Mitchell", "Roberts", "Carter", "Phillips",
    "Evans", "Turner", "Torres", "Parker", "Collins", "Edwards", "Stewart",
    "Flores", "Morris", "Nguyen", "Murphy", "Rivera", "Cook", "Rogers",
    "Morgan", "Peterson", "Cooper", "Reed", "Bailey", "Bell", "Gomez",
    "Kelly", "Howard", "Ward", "Cox", "Diaz", "Richardson", "Wood", "Watson",
    "Brooks", "Bennett", "Gray", "James", "Reyes", "Cruz", "Hughes", "Price",
    "Myers", "Long", "Foster", "Sanders", "Ross", "Morales", "Powell", "Sullivan",
    "Russell", "Ortiz", "Jenkins", "Gutierrez", "Perry", "Butler", "Barnes", "Fisher",
    "Henderson", "Coleman", "Simmons", "Patterson", "Jordan", "Reynolds", "Hamilton",
    "Graham", "Kim", "Gonzalez", "Alexander", "Ramos", "Lewis",
]

BIOS_VENDOR = [
    "Handmade jewelry inspired by the Pacific Northwest.",
    "Ceramics and pottery made in my backyard studio.",
    "Vintage clothing curator with an eye for the 70s and 80s.",
    "Small-batch hot sauces and spice blends — all local ingredients.",
    "Watercolor prints and original art for walls that deserve more.",
    "Upcycled leather goods — wallets, bags, and belts.",
    "Natural soy candles with botanicals from my garden.",
    "Beeswax wraps and zero-waste kitchen goods.",
    "Custom screen-printed tees and totes.",
    "Macramé wall hangings and plant hangers.",
    "Handwoven baskets and textile art.",
    "Sourdough breads and pastries baked fresh every week.",
    "Pressed flower art and botanical prints.",
    "Felted wool accessories — hats, scarves, and ornaments.",
    "Woodworking — cutting boards, spoons, and small furniture.",
    "Knitted goods: socks, sweaters, and baby items.",
    "Photography prints from trails across the US.",
    "Herbal teas and tinctures from my certified garden.",
    "Stained glass suncatchers and panels.",
    "Handmade soap and body care with zero synthetics.",
]

BIOS_SHOPPER = [
    "Here for the handmade finds and great food.",
    "Love supporting local artists and small vendors.",
    "Weekend market explorer. Coffee in hand, always.",
    "Searching for the perfect ceramics for my kitchen.",
    "Vintage collector. Anything pre-1990 has my attention.",
    "Farmers market regular. Seasonal produce and local honey only.",
    "Gift hunter — always shopping for someone else.",
    "Pop-up market enthusiast in the DFW area.",
    "Following my favorite vendors wherever they go.",
    "In it for the discovery. Every market is different.",
]

BIOS_MARKET = [
    "Organizer of the downtown night market series.",
    "Running seasonal artisan fairs since 2018.",
    "Community event planner focused on local makers.",
    "Juried craft fair organizer. Quality over quantity.",
    "Pop-up market coordinator and venue scout.",
]

CATEGORIES = ["handmade", "vintage", "food", "art", "craft", "jewelry", "ceramics", "clothing", "farmers"]

ROLES = (
    ["vendor"] * 55 +
    ["shopper"] * 30 +
    ["market"] * 15
)


def seed_events() -> int:
    init_events_db()
    inserted = 0
    skipped = 0
    for row in EVENTS:
        eid, name, city, state, date, vendor_count, traffic, booth_price, category, size = row
        e = Event(
            id=eid,
            name=name,
            city=city,
            state=state,
            date=date,
            vendor_count=vendor_count,
            estimated_traffic=traffic,
            booth_price=booth_price,
            vendor_category=category,
            event_size=size,
            popularity_score=min(100, int(traffic / 80)),
        )
        try:
            upsert_event(e)
            inserted += 1
        except Exception as ex:
            print(f"  skip event {eid}: {ex}")
            skipped += 1
    return inserted


def seed_users() -> int:
    init_users_db()
    inserted = 0
    skipped = 0
    for i in range(100):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last  = LAST_NAMES[i % len(LAST_NAMES)]
        role  = ROLES[i]
        name  = f"{first} {last}"
        username = f"{first.lower()}{last.lower()}{i}"
        email    = f"{username}@vendoratlas.dev"

        if role == "vendor":
            bio = BIOS_VENDOR[i % len(BIOS_VENDOR)]
            interests = CATEGORIES[i % len(CATEGORIES)]
        elif role == "shopper":
            bio = BIOS_SHOPPER[i % len(BIOS_SHOPPER)]
            interests = CATEGORIES[(i + 3) % len(CATEGORIES)]
        else:
            bio = BIOS_MARKET[i % len(BIOS_MARKET)]
            interests = "event management"

        try:
            create_user(
                name=name,
                email=email,
                username=username,
                password="DevPass123!",
                role=role,
                interests=interests,
                bio=bio,
            )
            inserted += 1
        except ValueError:
            skipped += 1  # already exists — idempotent
        except Exception as ex:
            print(f"  skip user {username}: {ex}")
            skipped += 1

    return inserted


if __name__ == "__main__":
    print("Seeding events…")
    n_events = seed_events()
    print(f"  {n_events} events upserted ({len(EVENTS)} total rows)")

    print("Seeding users…")
    n_users = seed_users()
    print(f"  {n_users} users created (100 attempted, duplicates skipped)")

    print("\nDone. Test login: any seed user, password = DevPass123!")
    print("Example: username=mayachen0  email=mayachen0@vendoratlas.dev")
