# Low-level materials to stockpile in WoW Forever — Researcher report (2026-11-15)

**Brief (owner):** which low-level crafting materials (skill 1–225, character level 1–40) will be worth much more once the
player base levels up: rare, made by a profession seldom paired with the one that consumes it, and needed in volume or as
a bottleneck. Include Malachite, Tigerseye, Lesser Moonstone. Saved by the main session from the Researcher agent's report
(ADR 0010); the live-price columns are one hour of our data.

## Part 1: for the owner

### Answer
- **Malachite, Tigerseye and Lesser Moonstone cost almost nothing to hold.** They sell on the AH at their vendor price
  (or within ~10%), and a vendor always buys them back at that price. The only cost is idle gold and bag space.
- **But their demand grows only modestly.** In Forever they mostly feed one-time Blacksmithing/Engineering crafts, and
  Forever's new "variant family" recipes let crafters swap in other gems. Tigerseye medium; Lesser Moonstone and Malachite weak.
- **The materials most likely to outrun supply are Forever's new "scarce" materials.** Tier 1 (low level): **Pyrite**
  (mining), **Pristine Leather** (skinning), **Frilled Lichen** (herbs → Cerulean Dye). Several beta testers and one live
  player (2026-11-08) report **only characters level ≤25 can gather them** (untested for Pyrite). Forever's new high-level
  recipes need them (Blacksmithing/Leatherworking sets at skill 200–290, Runecloth Bag, new necklace enchants). Supply
  shrinks as players level past 25 while demand grows: the owner's thesis in a Forever-specific form.
- **Pyrite stands out:** still at vendor price (1s), and it is the base of Sulfuric Acid (2 Pyrite each), which every version
  of the new high-level Blacksmithing sets needs, with no substitute.
- **Ceiling:** a fixed-price "Black Market" vendor sold scarce materials in beta (5g for tier 1, 20g tier 2, 50g tier 3).
  Live prices unverified. 5g is still ~50× Pyrite's current price.

### Confidence
| Claim | Confidence | What would settle it |
|---|---|---|
| Recipes, counts, skill ranges, vendor prices | **Firm** (Forever game files, build 1.60.1.70938, 2026-11-13) | — (how recipe scrolls are obtained is not in the files) |
| Gems at vendor price now | **Firm for today** (our snapshot, both regions) | 2–3 weeks of data (H-L1) |
| Tier-1 scarce gatherable only at level ≤25 | **Likely** for Pristine Leather / Frilled Lichen; **unknown** for Pyrite | Owner check B, or H-L2 |
| Black Market ceiling 5g / 20g | **Unknown on live** (one beta list, 2026-09-19) | Owner check A |
| Gem drop rates in Forever | **Unknown** (~1% per node in TBC databases, snippet only) | — |
| Speed of launch-economy recovery | **Unknown** (one 2019 forum prediction) | Our data over months |

### What changes for DayTrader
- New PLANNING facts (§3, "Leveling-material speculation").
- **#70 (vendor prices) matters more:** "trading at or below vendor price" is the clearest buy signal for this strategy.
- Strategist: consider a **floor watch** (items listed within ~10% of vendor) and a **scarce tier** tag; fits catalog #32
  (leveling-demand index).
- **Possible ADR 0003 impact:** wowauctionhouse.com labels houses by ruleset: 110/113/116 PvP, 111/114/117 Normal,
  119/120/121 RP, 123/124/125 RP-PvP, 112/115/118 unlisted (Hardcore, not launched?). If true, Normal Horde = **114**, not 113,
  and "five houses per faction" = five rulesets. One site's labels; #13's in-game check can confirm.

### Checks for the owner
- **A. Black Market prices (2 min):** Mister Graphed, Powderfuse Port, Riverglades (~78, 52, from a guide snippet). Note prices
  of Pyrite, Frilled Lichen, Pristine Leather, Rosecap, Pristine Hide, Bauxite; any gems; any purchase limit.
- **B. Pyrite level limit** (needs a miner level ≥26): mine 100 Copper/Tin veins, count Pyrite; compare with a ≤25 miner.
- **C. Recipe scroll sources:** at the faction's Waylaid Supply depot recipe vendor, check for Plans: Protector's / Guard's
  Chain Shirt, Plans: Officer's Gauntlet, Formula: Enchant Necklace (any), Pattern: Runecloth Bag, and their cost.
- **D. Bank space:** all of these stack 20 per slot in Forever; free slots cap the stockpile.
- **Decide: stockpile now or wait?** (a) small test stockpile now, only items within ~10% of vendor, Pyrite first, capped by
  bank space; (b) wait 2–3 weeks for H-L1–H-L3; (c) skip. Suggested default **(a)**.

## Part 2: detail

### Candidate table
AH lowest price: our snapshot 2026-11-15 17:17 UTC (US) / 18:19 UTC (EU), lowest unit price on US Horde 113 / US Horde 114 / EU Horde 113.

| Item | ID | Source / rarity | Main consumers in Forever | Vendor sell | AH lowest now | Substitutes | Demand | Thesis |
|---|---|---|---|---|---|---|---|---|
| **Pyrite** | 249391 | Scarce tier 1 (ilvl 25); Copper/Tin/Silver/Iron veins; level limit unproven for mining | Alchemy: Sulfuric Acid (2 each) → BS sets skill 200–290 (every version), LW Totemic set, Eng EZ-Thro Wrap, Str/Agi necklace enchants. Tailoring Shining set (36 total). Healing Power necklace enchant (4) | 1s (BM 5g, beta) | 2.4s / 1.4s / 7.0s | None in high-level BS sets | Recurring + one-time | **Strong** |
| **Pristine Leather** | 249427 | Scarce tier 1, skinning, level ≤25 only (beta + one live report) | 126 recipes in LW/BS/Tailoring incl. skill 255–290 and end-game bags | 1.25s (BM 5g) | 4.0s / 2.8s / 5.0s | Mostly none | Recurring + one-time | **Strong** (already 2–7× vendor) |
| **Frilled Lichen** → Cerulean Dye | 249399 → 249409 | Scarce tier 1, herbs, level ≤25 (beta) | Dye in 131 recipes, mostly Tailoring; Runecloth Bag 2, Mooncloth Bag 4, SP/Deflection necklace enchants 4 | 30c, dye 75c (BM 5g) | Lichen 30s/20s/24s; dye 62s/43s/55s | Variant families only | Recurring | **Strong**, already priced |
| Shadowgem | 1210 | Copper/Tin veins, rare; mob drops | Ench Runed Silver Rod (1 per enchanter); BS "Guard's" (46), LW "Brawler's" (34), Tail "Shadow" (37); Shadow Goggles | 2.5s | 2.67s / 2.70s / 2.50s | Yes in families; none for rod | Mostly one-time | Medium |
| **Tigerseye** | 818 | Copper veins, rare | BS "Protector's" family (10 recipes, 45 total), Heavy Copper Broadsword, Big Bronze Knife, Ironforge Breastplate, Barbaric Iron Boots; Eng Flying Tiger Goggles (2), Universal Remote | 1s | 1.19s / 1.00s / 1.05s | Yes (Guard's/Veteran's/Acolyte's/Crusader's) | One-time | Medium |
| Small Lustrous Pearl | 5498 | Small Barnacled Clams | BS "Veteran's" (38), LW "Wisdom's" (24), Moonglow Boots/Vest, Tail "Pearly" (39), Pearl-clasped Cloak | 2s | 2.15s / 2.66s / 2.21s | Yes in families | One-time | Medium |
| Iridescent Pearl | 5500 | Clams, mid-level (from memory) | Ench Runed Golden Rod (1 per enchanter); Spidersilk Boots, Phoenix pieces; LW "Mender's" (59, skill 155–290) | 7.5s | 8.5s / 9.3s / 7.8s | Families; none for rod | One-time | Medium |
| Jade | 1529 | Tin (very rare) and higher veins | BS "Officer's" (39 at 225+, 19 at 150–225), LW "Prowler's" (39), Eng scopes | 7s | 7.35s / 7.19s / 7.00s | Purple Lotus, Black Pearl, Golden Pearl, Globe of Water | One-time | Medium |
| **Lesser Moonstone** | 1705 | Tin/Silver/Iron/Gold veins, rare | BS skill 135–265 (12 recipes, mostly plans); Eng Moonsight Rifle, Cloaking Device | 6s | 6.00s / 6.20s / 6.00s | Few | One-time | **Weak**, free to hold |
| **Malachite** | 774 | Copper veins, rare; mob drops | BS skill 70–120 (4) + Gemmed Copper Boots; Eng Crude Scope, Mechanical Squirrel | 15c | 15c / 64c / 15c | Gemmed/Strange/Glowing Copper Boots | One-time | **Weak** |
| Strange Dust | 10940 | Disenchanting | Enchanting (≈halved), Dust→Motes (1→3), BS "Acolyte's" | 1c (**no floor**) | 1.20s / 1.40s / 1.15s | Lesser Magic Essence | Mixed | Weak |
| Pristine Hide | 249428 | Scarce tier 2 (ilvl 45) | LW skill 255–290 (8–10 each), Eng EZ-Thro Fireproof Fuse | 2.5s (BM 20g) | 2.60s / 2.45s / 2.90s | — | Mixed | Watch (supply grows as players reach its band) |

**Typical use per leveler (estimates):** Malachite 0–10; Tigerseye 10–20 (engineer) up to ~45 (full Protector's set);
Shadowgem 1 per enchanter (hard); a full new-family set 20–46 of its flavour reagent; Pyrite ~40 per Officer's-type set
(20 Sulfuric Acid) + 8 per necklace enchant.

### Findings
- **F1 [official]** Forever launched 2026-11-04, level 60 from day one (no level-capped phases); three raids open
  2026-12-09; Hardcore "sometime after launch", enclosed (transfers out only); 600+ new recipes; Legacy system rewards
  leveling alts; "Bountiful Harvest" talent.
- **F2 [datamined]** (Forever 1.60.1.70938 vs Era 1.15.9.70576) **Variant families:** same item in 5–6 versions, each with
  a different flavour reagent (e.g. BS chain at skill 85: Small Lustrous Pearl / Shadowgem / Tigerseye / Strange Dust /
  Lesser Magic Essence). New BS plans are blue and BoP; some Tailoring/LW patterns tradeable; acquisition not in files.
  Sulfuric Acid and Pristine Leather are **common to every version** of the high-level families (e.g. Officer's /
  Sentinel's / Warder's / Prefect's / Justicar's Sabatons each 4 Sulfuric Acid + 4 Pristine Leather). **No Jewelcrafting**,
  so no prospecting (which flooded low-level gems in TBC Classic).
- **F3 [datamined]** Most BS/LW/Tailoring recipes stop giving skill ~25 points earlier than Era. Enchanting needs ~half the
  dust/essence. Mote of Magic (1 Strange Dust → 3) replaces dust in Runed Copper Rod. Runed Silver Rod still uses a
  Shadowgem; Runed Golden Rod an Iridescent Pearl. Runecloth Bag adds 4 Magenta + 2 Cerulean Dye. New necklace enchants
  (skill 225–265) use 4 Sulfuric Acid, Pyrite or Cerulean Dye. EZ-Thro Dynamite needs an EZ-Thro Wrap (Wool + Sulfuric Acid).
- **F4 [datamined]** Vendor prices of every item checked equal Classic Era's (except Strange Dust / Lesser Magic Essence
  0 → 1c). All stack 20.
- **F5** Scarce tiers [datamined]: ilvl 25 Pyrite / Frilled Lichen / Pristine Leather; 45 Rosecap / Pristine Hide; 60
  Stranglevine / Pristine Scale. Level limit [guide / forum]: beta testers (2026-10-11 to 10-16; ~150 herb nodes at level 26
  gave no Lichen, ~300 skins at level 30 gave no Pristine Leather) and one live player (11-08, level 26 couldn't skin it).
  Pyrite untested (one beta miner had 17 at skill 75–100; another said it "dropped off" after ~75). Bountiful Harvest =
  "100% more likely to discover scarce materials" (one live player, 11-11); not for normal gems. No live hotfix 11-06 to
  11-14 touched any of this [official].
- **F6 [guide / forum, beta 2026-09-19]** Black Market vendor, fixed prices, no limit: 5g Pristine Leather / Frilled Lichen /
  Pyrite; 20g Rosecap / Pristine Hide / Bauxite; 50g Pristine Scale / Stranglevine and others. No classic gems.
- **F7 [community-tested, Classic/TBC]** Copper Vein: Malachite, Shadowgem, Tigerseye (rare). Tin Vein: Lesser Moonstone,
  Moss Agate, Shadowgem (rare), Jade (very rare). Lesser Moonstone also Silver/Iron/Gold. ~1% per gem (TBC, snippet only).
  Forever's loot tables are server-side.
- **F8 [our data, one hour]** Classic gems within ~0–20% of vendor on big houses, both regions, hundreds to thousands
  listed. Ores at 4–40× vendor (Copper Ore 0.9–2.0s vs 5c). Pyrite and Pristine Hide at floor. Lichen and dyes many× vendor.
  Reading: gems are by-products of heavy ore demand; Waylaid Crates (Copper/Tin Ore, Linen, Light Leather, bars) keep copper
  mining busy, keeping gem supply up.
- **F9 [guide / forum]** Classic 2019 EU forum (2019-09-24): linen/silk "little over vendor price"; players *predicted*
  normal prices "around Christmas" or "in 6 months" (a prediction, not a measurement). No measured gem history found.
  Forever beta prices were inflated (beta capped at level 30).

### Sources
| Link | Label | Version | Date | What it says |
|---|---|---|---|---|
| wago.tools `/db2/{ItemSparse, SkillLineAbility, SpellReagents, SpellEffect, ItemEffect, ItemXItemEffect, SkillLine, SpellName}/csv?branch=wowf` | [datamined] | Forever 1.60.1.70938 | 2026-11-13 | Recipes, reagents, skill ranges, vendor prices |
| same, `branch=wow_classic_era` | [datamined] | Era 1.15.9.70576 | 2026-10-26 | Baseline |
| [Forever Deep Dive recap](https://news.blizzard.com/en-us/article/24303313/world-of-warcraft-forever-deep-dive-panel-recap) | [official] | Forever | pre-launch | 600+ recipes; Bountiful Harvest |
| [Forever Now Live](https://news.blizzard.com/en-us/article/24315820/world-of-warcraft-forever-goes-live-globally-november-4), [What's Next](https://news.blizzard.com/en-us/article/24303862/world-of-warcraft-forever-whats-next-panel-recap) | [official] | Forever | 2026-11-04 / pre-launch | Raids 12-09; Hardcore later |
| [Forever hotfixes](https://us.forums.blizzard.com/en/wow/t/wow-forever-hotfixes-november-13-2026/2403040) | [official] | live | 11-06–11-14 | Nothing on scarce materials or gathering |
| [Mechanics of "Scarce" Resources Tested](https://us.forums.blizzard.com/en/wow/t/mechanics-of-scarce-resources-tested-or-why-the-beta-economy-is-a-mess/2379537) | [guide / forum] | beta | 2026-10-11–16 | "Only by a level 1 to 25 character" |
| [Scarce Material](https://us.forums.blizzard.com/en/wow/t/scarce-material/2406534) | [guide / forum] | live | 2026-11-08 | Level 26 couldn't skin Pristine Leather |
| [EU: Pristine Leather drop rates](https://eu.forums.blizzard.com/en/wow/t/pristine-leather-drop-rates/634869), [EU: Bountiful Harvest](https://eu.forums.blizzard.com/en/wow/t/bountiful-harvest/641910) | [guide / forum] | beta / live | 10-11 / 11-11 | Low rates; "16 Pyrite but only 1 Frilled Lichen" |
| [Arcane Crystals & BMAH](https://us.forums.blizzard.com/en/wow/t/arcane-crystals-black-market-auction-house/2355417) | [guide / forum] | beta | 2026-09-19 | Black Market price list |
| warcraft.wiki.gg: [Copper Vein](https://warcraft.wiki.gg/wiki/Copper_Vein), [Tin Vein](https://warcraft.wiki.gg/wiki/Tin_Vein), [Malachite](https://warcraft.wiki.gg/wiki/Malachite), [Lesser Moonstone](https://warcraft.wiki.gg/wiki/Lesser_Moonstone), [Shadowgem](https://warcraft.wiki.gg/wiki/Shadowgem), [Small Lustrous Pearl](https://warcraft.wiki.gg/wiki/Small_Lustrous_Pearl) | [community-tested] | Classic / retail | undated | Gem sources; Malachite ~1% |
| [Moonwell object 103713](https://moonwell.su/en/db/object/103713) | [community-tested], snippet | TBC 2.4.3 | — | 1% per gem |
| [wowauctionhouse.com Tigerseye](https://wowauctionhouse.com/forever/item/818-tigerseye/) | [community-tested] | Forever | 2026-11-15 | House → ruleset labels |
| [EU: Realm Economy ruined yet?](https://eu.forums.blizzard.com/en/wow/t/realm-economy-ruined-yet/89370) | [guide / forum] | Classic 2019 | 2019-09-24 | Linen/silk near vendor |
| Waylaid Crate guides (gitm.gg, wow-professions.com) | [guide], snippet | Forever | 2026 | Crate turn-ins |

### Conflicts
- PLANNING §1 / ADR 0003: Normal Horde may be house **114**, not 113 (unconfirmed; #13).
- PLANNING "vendor prices were cut on some items": true, but not for any material here.
- No conflict with ADR 0008: flows' "posted"/"vanished early" are what H-L2 and H-L6 need.

### Hypotheses for the Analyst (stated before looking at any trend)
- **H-L1 floor pinning:** 11-16 → 12-09, daily median of hourly min price ≤1.15× vendor on houses 110/111/113/114 for
  Malachite, Tigerseye, Lesser Moonstone, Shadowgem, Jade, both pearls. Refuted per item if ≥1.5× for 3 days running.
- **H-L2 level-gated supply:** units posted/day of Pristine Leather, Frilled Lichen, Pyrite fall ≥25% from week of 11-16 to
  week of 12-07, and ≥2× as fast (%) as Copper Ore. Refuted if no faster than Copper Ore.
- **H-L3 rising scarce prices:** p10 of Pristine Leather, Frilled Lichen, Cerulean Dye up ≥50% (week of 11-16 → 12-14);
  Pyrite p10 > 1.5s by 12-31. Refuted if flat or falling.
- **H-L4 Black Market cap:** p10 of tier 1 never >5g for >24 h; Rosecap / Pristine Hide never >20g.
- **H-L5 substitution:** weekly price/vendor ratios of Shadowgem, Tigerseye, Small Lustrous Pearl stay within 2× of each other.
- **H-L6 raid opening:** after 12-09, est. sales of Sulfuric Acid and Cerulean Dye rise ≥30% week over week; classic gems ≤10%.
- **H-L7 gems are ore by-products:** daily posted gems correlate >0.6 with Copper/Tin Ore posted.
- **H-L8 EU vs US:** same direction on H-L2 and H-L3.

### Blocked sites
wowhead.com (CloudFront 403; most valuable: Forever drop rates and recipe sources), icy-veins.com (Cloudflare), ahledger.com
(429; has Forever sold-per-day), reddit.com; refused by network policy: foreverwisp.com, allthings.how, chaosboost.com,
masterofwarcraft.net, wowforever.be, warcraftforever.games, warcraftmaps.com, gamemargins.com, metaforge.app,
bootybaybroker.com, vaultalts.com, loreforeverwow.com, wowhandbook.com. Allowing wowhead.com and ahledger.com would help most.
