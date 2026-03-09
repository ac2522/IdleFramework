# Idle & Incremental Game Mechanics - Comprehensive Research

## Table of Contents
1. [Core Mechanics Taxonomy](#1-core-mechanics-taxonomy)
2. [AdVenture Capitalist Deep Dive](#2-adventure-capitalist-deep-dive)
3. [Mathematical Models](#3-mathematical-models)
4. [Mechanics Examples from Popular Games](#4-mechanics-examples-from-popular-games)

---

## 1. Core Mechanics Taxonomy

### 1.1 Generators (Production Buildings)

Generators are the foundational mechanic of idle games. They produce a primary currency at a defined rate.

**Properties of a Generator:**
- `base_cost` - Initial purchase price
- `cost_growth_rate` - Multiplier applied to cost per unit owned (typically 1.07-1.15)
- `base_production` - Currency produced per cycle
- `cycle_time` - Time to complete one production cycle (some games use per-second, others use variable cycle times)
- `owned_count` - Number of this generator the player owns

**Production formula:**
```
total_production = base_production * owned_count * multipliers
cost_next = base_cost * (cost_growth_rate ^ owned_count)
```

**Nested/Derivative Generators (Generators that produce generators):**
Higher-tier generators produce lower-tier generators instead of currency directly. This creates derivative growth chains:
- Tier 1: Produces currency
- Tier 2: Produces Tier 1 generators
- Tier 3: Produces Tier 2 generators
- ...and so on

Example from Derivative Clicker: Every purchased Tier 1 building boosts production of all Tier 1 buildings by 0.05%, creating compound growth. This is "derivative growth" as opposed to simple exponential growth.

Example from Antimatter Dimensions: Each dimension produces the dimension below it, with the 1st Dimension producing antimatter (the currency). This creates extremely deep exponential chains.

### 1.2 Prestige / Reset Systems

Prestige is the mechanic where a player voluntarily resets most of their progress in exchange for a permanent bonus that accelerates all future runs.

**Core concept:**
- Player accumulates progress (lifetime earnings, total levels, etc.)
- At a threshold, they can "prestige" / "reset" / "ascend"
- Most progress is wiped (generators, currency, upgrades)
- A prestige currency is awarded based on total progress
- The prestige currency provides a permanent multiplier or unlocks permanent upgrades

**Key design properties:**
- `prestige_currency_formula` - How much prestige currency is earned (usually sqrt or log of lifetime earnings)
- `prestige_bonus_per_unit` - Bonus granted per unit of prestige currency (e.g., +2% per Angel in AdCap)
- `prestige_threshold` - Minimum progress required before prestige is available
- `retained_items` - What persists across resets (prestige currency, certain upgrades)
- `reset_items` - What gets wiped (generators, cash, non-permanent upgrades)

**When to prestige (player decision):**
The optimal prestige point is when the prestige bonus gained would make the next run significantly faster than continuing the current run. A common rule of thumb is "prestige when you can at least double your prestige currency."

### 1.3 Ascension Layers (Multiple Prestige Layers)

Some games stack multiple prestige layers, where each higher layer resets the layers below it.

**Example structure (Clicker Heroes):**
```
Layer 0: Base gameplay (kill monsters, earn gold, hire heroes)
Layer 1: Ascension - resets gold/heroes, grants Hero Souls
         Hero Souls -> buy Ancients (permanent bonuses)
Layer 2: Transcendence - resets Hero Souls/Ancients, grants Ancient Souls
         Ancient Souls -> buy Outsiders (meta-permanent bonuses)
```

**Example structure (Antimatter Dimensions):**
```
Layer 0: Produce antimatter via 8 dimensions
Layer 1: Infinity - reset dimensions, earn Infinity Points
Layer 2: Eternity - reset Infinity, earn Eternity Points
Layer 3: Reality - reset Eternity, earn Reality Machines
```

Each layer typically introduces:
- A new currency
- New upgrade trees that affect all layers below
- Longer time horizons between resets
- More strategic depth

### 1.4 Upgrades

Upgrades modify game values and come in several mathematical types:

**Multiplicative Upgrades:**
- Multiply a value by a factor: `production *= 3`
- Most common type, stacks multiplicatively with other multipliers
- Example: "Triple Lemonade Stand profits" (x3 multiplier)

**Additive Upgrades:**
- Add a flat amount: `production += 100`
- Less common for production, more common for base stats
- Example: "+10 base damage per click"

**Percentage-Based Upgrades:**
- Increase by a percentage: `production *= (1 + percentage/100)`
- Example: "All profits +2% per Angel Investor"
- Can be additive with each other but multiplicative with base: `base * (1 + sum_of_percentages)`

**Upgrade Categories by Cost Type:**
- **Cash Upgrades** - Purchased with primary currency
- **Prestige Currency Upgrades** - Purchased by spending prestige currency (opportunity cost: lose the passive bonus)
- **Premium Upgrades** - Purchased with real money or premium currency
- **Achievement Upgrades** - Unlocked automatically by reaching milestones
- **Conditional Upgrades** - Active only when certain conditions are met

**Upgrade Stacking:**
```
final_production = base_production
    * product(multiplicative_upgrades)
    * (1 + sum(percentage_upgrades))
    * (1 + prestige_bonus)
    + sum(additive_upgrades)
```

### 1.5 Unlocks and Achievements

**Unlocks (Milestones):**
Triggered automatically when a condition is met. Provide a permanent bonus.
- Example (AdCap): Own 25 Lemonade Stands -> x2 Lemonade profit
- Example (AdCap): Own 100 of everything -> x3 all profits
- Often tied to generator ownership thresholds (25, 50, 100, 200, 300, 400...)

**Achievements:**
Similar to unlocks but often more varied in their trigger conditions:
- Production milestones ("Produce 1 million cookies")
- Speed milestones ("Reach 1 billion in under 10 minutes")
- Collection milestones ("Own every type of generator")
- Exploration milestones ("Unlock all prestige upgrades")

Some games (Cookie Clicker, Synergism) tie achievement count to gameplay bonuses, making achievements mechanically meaningful rather than purely cosmetic.

### 1.6 Multiple Currencies / Economies

Many idle games feature multiple interacting currencies:

**Currency Hierarchy:**
```
Primary Currency (Gold, Cookies, Cash)
  -> Used to buy generators and basic upgrades
Secondary Currency (Gems, Diamonds, Premium)
  -> Earned slowly or purchased with real money
  -> Used for premium upgrades, time skips, cosmetics
Prestige Currency (Angels, Heavenly Chips, Hero Souls)
  -> Earned through prestige resets
  -> Used for permanent upgrades
Meta-Prestige Currency (Ancient Souls, Eternity Points)
  -> Earned through higher-tier resets
  -> Used for meta-permanent upgrades
```

**Resource Conversion:**
Some games allow or require converting one resource into another:
- Craft basic materials into advanced materials
- Convert primary currency into secondary at a rate
- Sacrifice one resource to boost another

### 1.7 Resource Consumption (Generators that Consume)

Some generators require input resources to produce output resources:

```
Generator: Bakery
  Consumes: 10 Flour per second
  Produces: 5 Bread per second
  Requires: Flour supply >= consumption rate
```

**Design considerations:**
- If input runs out, does production stop or slow?
- Can the player stockpile inputs?
- Are there efficiency upgrades that reduce consumption?
- Do conversion ratios improve with upgrades?

This creates supply-chain management gameplay where the player must balance production across multiple resource types.

### 1.8 Automation (Managers)

Automation removes the need for manual player input:

**Types of automation:**
- **Auto-collect**: Automatically collects produced resources
- **Auto-buy**: Automatically purchases generators or upgrades
- **Auto-prestige**: Automatically triggers prestige at optimal points
- **Auto-start**: Automatically restarts production cycles (AdCap Managers)

**Progression:**
Early game requires active clicking/interaction. Automation is unlocked progressively, shifting gameplay from active to idle. This transition is itself a core satisfaction loop.

### 1.9 Tick-Based vs. Continuous Production

**Tick-Based (Cycle-Based):**
- Production happens in discrete cycles
- Each generator has a cycle time (e.g., Lemonade Stand takes 1 second per cycle)
- Player (or manager) must initiate each cycle
- Used by: AdVenture Capitalist, most mobile idle games

```
profit_per_cycle = base_profit * owned * multipliers
cycles_per_second = 1 / cycle_time
effective_cps = profit_per_cycle * cycles_per_second
```

**Continuous (Per-Second):**
- Production is calculated as a rate (units per second)
- Applied continuously using delta time
- Used by: Cookie Clicker, most browser idle games

```
production_per_second = sum(generator.base_rate * generator.owned * generator.multipliers)
resources += production_per_second * delta_time
```

**Hybrid approaches:**
Some games use per-second display but internally calculate in ticks for performance.

### 1.10 Probability Mechanics

**Critical Hits / Lucky Events:**
- A random chance to produce bonus output
- Example: 5% chance to produce 10x output on any production tick
- Expected value: `base_production * (1 + crit_chance * (crit_multiplier - 1))`

**Random Events (Golden Cookies, etc.):**
- Timed random spawns that reward attentive players
- Cookie Clicker's Golden Cookies: spawn randomly, clicking gives temporary buffs
- Rewards active play within an otherwise idle game

**Probability Upgrades:**
- Increase crit chance, crit damage, or lucky event frequency
- Some games: crit chance can exceed 100%, meaning guaranteed crit with chance for "double crit"

**Expected Value Formula:**
```
EV = sum(outcome_value * probability_of_outcome)
EV_with_crit = base * (1 - crit_chance) + base * crit_multiplier * crit_chance
            = base * (1 + crit_chance * (crit_multiplier - 1))
```

### 1.11 Offline Progression

When the player is not actively playing, the game simulates progress:

**Approaches:**
- **Full simulation**: Calculate exact production for elapsed time (simple for linear production, complex for compound growth)
- **Reduced rate**: Offline production at 50% or some fraction of online rate (incentivizes active play)
- **Capped duration**: Offline accumulation stops after X hours (creates urgency to return)
- **Catch-up mechanic**: On return, player can watch an ad or pay to claim full offline earnings

**Calculation:**
```
offline_earnings = production_rate * elapsed_seconds * offline_multiplier
// Capped version:
offline_earnings = production_rate * min(elapsed_seconds, max_offline_seconds) * offline_multiplier
```

**Complications:**
- If production rate changes during offline time (from auto-purchased upgrades), simple multiplication is inaccurate
- Most games use the rate at the time of disconnection as a constant
- Some games run a simplified simulation tick-by-tick for accuracy

### 1.12 Paid / Premium Mechanics

**Time Skips:**
- Jump forward X hours of production instantly
- Priced in premium currency or via watching ads
- Most effective when aligned with natural progression points

**Permanent Multipliers:**
- x2, x3, x5 permanent production multipliers
- One-time purchase, never resets
- AdCap Gold Multipliers: permanent multipliers per planet

**Premium Currency:**
- Earned slowly through gameplay or purchased with real money
- Used for: time skips, premium upgrades, cosmetics, ad removal
- Often the only currency that persists through ALL reset types

**Ad-Based Boosts:**
- Watch a rewarded ad for temporary x2 production (typically 2-4 hours)
- Watch an ad to claim full offline earnings
- Watch an ad for a free time skip

**Monetization Split:**
- ~62% of revenue from IAP, ~38% from ads (industry average for idle games)
- Paying players have 2.6x higher lifetime value

### 1.13 Synergy Mechanics

Some games create interactions between different systems:

**Cross-Generator Synergies:**
- Owning Generator A boosts Generator B's production
- Example: "Each Bakery increases Farm output by 1%"

**Combo/Buff Stacking:**
- Multiple temporary buffs can stack for massive multipliers
- Cookie Clicker: Frenzy (x7) + Click Frenzy (x777) = x5,439 clicking power

**Conditional Multipliers:**
- Bonuses that only apply under certain conditions
- "Production x10 while you have more than 1000 of Resource X"

---

## 2. AdVenture Capitalist Deep Dive

### 2.1 Game Structure

AdVenture Capitalist is the quintessential idle/incremental game and serves as a reference implementation for many mechanics.

**Planets:** Earth, Moon, Mars (each is an independent economy)

### 2.2 Businesses (Generators)

Earth businesses, in order of unlock:

| # | Business | Base Cost | Cost Multiplier | Base Profit | Base Cycle Time |
|---|----------|-----------|----------------|-------------|-----------------|
| 1 | Lemonade Stand | $4 | 1.07 | $1 | 0.6s |
| 2 | Newspaper Delivery | $60 | 1.15 | $60 | 3s |
| 3 | Car Wash | $720 | 1.14 | $540 | 6s |
| 4 | Pizza Delivery | $8,640 | 1.13 | $4,320 | 12s |
| 5 | Donut Shop | $103,680 | 1.12 | $51,840 | 24s |
| 6 | Shrimp Boat | $1,244,160 | 1.11 | $622,080 | 96s |
| 7 | Hockey Team | $14,929,920 | 1.10 | $7,464,960 | 384s |
| 8 | Movie Studio | $179,159,040 | 1.09 | $89,579,520 | 1536s |
| 9 | Bank | $2,149,908,480 | 1.08 | $1,074,954,240 | 6144s |
| 10 | Oil Company | $25,798,901,760 | 1.07 | $12,899,450,880 | 36864s |

**Key observations:**
- Higher-tier businesses have lower cost multipliers (cheaper to scale)
- Higher-tier businesses have much longer cycle times
- The cost/profit ratio is designed so each business is relevant at different stages
- Profitability leadership rotates as milestone multipliers kick in

### 2.3 Managers (Automation)

Each business has a corresponding manager:
- Purchased with cash (one-time cost, increasing per business tier)
- Once hired, the manager automatically restarts the business cycle when it completes
- This is what makes the game truly "idle" - without managers, you must manually click each business
- **Discount Managers**: Later unlockable managers that reduce business costs by 99.999%

### 2.4 Unlocks (Milestone Multipliers)

Reaching ownership thresholds grants permanent multipliers:
- Typically at 25, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100...
- Multipliers are typically x2, x3, x5, x7, x9, x11 etc.
- Some milestones grant "all profit" multipliers affecting every business
- These create dramatic jumps in profitability and drive purchasing decisions

### 2.5 Angel Investors (Prestige System)

**Earning Angels:**
```
angels = floor(150 * sqrt(lifetime_earnings / 1e15))
```
(For Earth/Moon. Mars uses 1e14 divisor.)

**Angel Bonus:**
- Each Angel Investor provides +2% to ALL profits
- 50 Angels = +100% = x2 multiplier
- Formula: `profit_multiplier = 1 + (angel_count * 0.02)`

**Angel Upgrades:**
- Some upgrades cost Angel Investors (they are spent/consumed)
- Spending Angels reduces your passive bonus
- Strategy: Only spend Angels on upgrades if the upgrade provides more benefit than the lost percentage bonus
- Rule of thumb: Don't spend more than 1% of your Angels on non-"all profit" upgrades

**Reset Decision:**
- Resetting is worthwhile when pending Angels would significantly boost your multiplier
- Common heuristic: Reset when you can gain at least as many Angels as you currently have (doubling)

### 2.6 Cash Upgrades

Purchased with in-game currency:
- Multiply a specific business's profit (x3, x5, x7, x9, etc.)
- Multiply all business profits
- Reduce cycle time for specific businesses
- Costs scale to be relevant at each stage of the game

### 2.7 Gold Upgrades (Premium)

Purchased with Gold (premium currency):
- Permanent profit multipliers per planet
- Persist through Angel resets
- Can be purchased with real money or earned through events
- "Additive stacking" - Gold multipliers add together rather than multiply

### 2.8 Events

Time-limited events with separate economies:
- Unique businesses and upgrade trees
- Event-specific currency
- Rewards (Gold, permanent multipliers) carry back to main game
- Creates recurring engagement and limited-time urgency

---

## 3. Mathematical Models

### 3.1 Cost Functions

**Exponential cost (most common):**
```
cost(n) = base_cost * growth_rate^n
```
Where n = number already owned.

**Total cost to buy k units starting from n owned:**
```
total_cost(n, k) = base_cost * growth_rate^n * (growth_rate^k - 1) / (growth_rate - 1)
```

**Maximum affordable units:**
```
max_buyable = floor(log((currency * (growth_rate - 1)) / (base_cost * growth_rate^n) + 1) / log(growth_rate))
```

**Polynomial cost (less common):**
```
cost(n) = base_cost * n^power
```
- Grows slower than exponential
- Used when gentler scaling is desired

### 3.2 Production Functions

**Linear production (standard):**
```
production = base_production * owned_count
```
Total production grows linearly with number owned.

**Production with multipliers:**
```
effective_production = base_production * owned_count * product(all_multipliers) * (1 + prestige_bonus)
```

**Nested/Derivative production:**
```
// Tier 1 produces currency
tier1_production = tier1_base * tier1_count * tier1_multipliers

// Tier 2 produces Tier 1 generators
tier1_count += tier2_base * tier2_count * tier2_multipliers * delta_time

// This creates polynomial or super-exponential growth depending on depth
```

### 3.3 Growth Rate Analysis

**Why costs must grow faster than production:**
- Production grows linearly (or polynomially with nested generators)
- Costs grow exponentially
- This ensures the player eventually hits a "wall" where buying more becomes slow
- This wall drives prestige decisions and creates the game's pacing

**Growth rate comparison:**
```
Linear:      f(n) = a*n + b           (generators producing currency)
Polynomial:  f(n) = a*n^k             (nested generators)
Exponential: f(n) = a*r^n             (cost scaling)
```
Exponential always eventually overtakes polynomial, which always eventually overtakes linear.

### 3.4 Prestige Bonus Formulas

**AdVenture Capitalist style (linear percentage per unit):**
```
bonus = angel_count * bonus_per_angel
multiplier = 1 + bonus
```

**Cookie Clicker style (prestige level = percentage boost):**
```
prestige_level = floor((lifetime_cookies / 1e12) ^ (1/3))
// Cubic root relationship - each successive level costs more
// Each level = +1% CpS (must be unlocked via Heavenly Upgrade)
multiplier = 1 + prestige_level * 0.01
```

**Square root scaling (common pattern):**
```
prestige_currency = floor(C * sqrt(lifetime_earnings / D))
// C and D are balancing constants
// Square root ensures diminishing returns per unit of earnings
```

### 3.5 Time-to-Next-Milestone

**Simple case (constant production):**
```
time_to_target = (target_cost - current_currency) / production_rate
```

**With production increasing (buying generators along the way):**
This becomes an optimization problem. The player must decide:
- Buy a new generator now (increases rate, costs currency)?
- Save for an expensive upgrade (delays but bigger boost)?

**Optimal purchase decision:**
```
// Time to earn enough to buy upgrade, then earn target after:
time_with_upgrade = time_to_afford_upgrade + (target - remaining) / new_production_rate

// Time to earn target without buying upgrade:
time_without = (target - current) / current_production_rate

// Buy if time_with_upgrade < time_without
```

### 3.6 Offline Earnings Calculation

**Simple (constant rate):**
```
earnings = rate_at_disconnect * seconds_elapsed * offline_modifier
```

**With cap:**
```
earnings = rate_at_disconnect * min(seconds_elapsed, max_seconds) * offline_modifier
```

**Accurate (simulated ticks):**
```
for each tick in elapsed_time:
    apply_auto_purchases()
    accumulate_production()
// Expensive but accurate; usually simplified
```

### 3.7 Big Number Representation

Idle games frequently exceed standard floating-point limits. Common approaches:
- Scientific notation display: 1.23e45
- Named tiers: Million, Billion, Trillion, Quadrillion, Quintillion...
- Letter notation: 1.23aa, 1.23ab, etc.
- Logarithmic storage: Store log10 of the value internally

---

## 4. Mechanics Examples from Popular Games

### 4.1 Cookie Clicker

| Mechanic | Implementation |
|----------|---------------|
| Primary Currency | Cookies |
| Generators | Cursor, Grandma, Farm, Mine, Factory, Bank, Temple, Wizard Tower, Shipment, Alchemy Lab, Portal, Time Machine, Antimatter Condenser, Prism, Chancemaker, Fractal Engine, Javascript Console, Idleverse, Cortex Baker, You |
| Prestige | Ascension -> Heavenly Chips + Prestige Levels |
| Prestige Formula | `level = floor((lifetime_cookies / 1e12)^(1/3))` |
| Prestige Bonus | +1% CpS per Prestige Level (requires unlock) |
| Random Events | Golden Cookies (temporary buffs: Lucky, Frenzy, Click Frenzy, etc.) |
| Synergies | Grandma synergies with other buildings, Kitten upgrades scale with milk (achievement %) |
| Special Mechanic | Wrinklers (consume cookies but return 1.1x when popped) |
| Special Mechanic | Sugar Lumps (grow in real-time, used to level up buildings) |
| Automation | No built-in auto-clicker; upgrades increase passive CpS |

### 4.2 Clicker Heroes

| Mechanic | Implementation |
|----------|---------------|
| Primary Currency | Gold (from killing monsters) |
| Generators | Heroes (deal DPS automatically) |
| Active Mechanic | Clicking deals damage based on click damage stat |
| Prestige Layer 1 | Ascension -> Hero Souls (each gives +10% DPS) |
| Prestige Layer 1 Spending | Ancients (permanent upgrades bought with Hero Souls) |
| Prestige Layer 2 | Transcendence -> Ancient Souls |
| Prestige Layer 2 Spending | Outsiders (meta-upgrades bought with Ancient Souls) |
| Special Mechanic | Transcendent Power (increases Hero Souls from primal bosses) |
| Zone System | Progress through zones, boss every 5 zones |
| Gilding | Heroes can be "gilded" for bonus damage, gilds transfer on ascension |

### 4.3 Antimatter Dimensions

| Mechanic | Implementation |
|----------|---------------|
| Primary Currency | Antimatter |
| Generators | 8 Dimensions (each produces the one below it) |
| Nested Generators | Dimension 8 -> Dim 7 -> ... -> Dim 1 -> Antimatter |
| Prestige Layer 1 | Infinity (reset for Infinity Points) |
| Prestige Layer 2 | Eternity (reset Infinity progress for Eternity Points) |
| Prestige Layer 3 | Reality (reset Eternity progress for Reality Machines) |
| Special Mechanic | Dimension Boosts and Galaxies (multiplier resets within a run) |
| Challenges | Special runs with restrictions for unique rewards |
| Automation | Autobuyers for each dimension, purchasable and upgradeable |

### 4.4 Idle Heroes (Mobile RPG Hybrid)

| Mechanic | Implementation |
|----------|---------------|
| Primary Currencies | Gold, Spirit, Promotion Stones, Hero Promotion Stones |
| Premium Currency | Gems |
| Generators | Idle Campaign (produces gold/XP/loot over time) |
| Prestige | Hero regression/foddering (sacrifice heroes to upgrade others) |
| Gacha Mechanic | Random hero summons with rarity tiers |
| Team Building | 6-hero teams with faction synergies |
| Multiple Game Modes | Campaign, Tower, Arena, Guild Wars |
| Time-Gated Content | Daily/weekly events, limited attempts |

### 4.5 NGU Idle

| Mechanic | Implementation |
|----------|---------------|
| Core Loop | Train stats, fight bosses, earn EXP |
| Automation | Time Machine (idle gold), Blood Magic (idle resources) |
| Prestige | Rebirth (reset for permanent bonuses) |
| Multiple Systems | Adventure, Augments, Time Machine, Blood Magic, Wandoos, NGU, Yggdrasil, Questing, Hacks, Wishes |
| Resource Management | Energy, Magic, Resource 3 (allocated across systems) |
| Depth | Hundreds of hours of content across multiple rebirth tiers |

---

## Summary of All Mechanic Types

1. **Generators** - Produce currency at a rate; cost scales exponentially
2. **Nested Generators** - Generators that produce other generators (derivative growth)
3. **Upgrades (Multiplicative)** - Multiply production by a factor
4. **Upgrades (Additive)** - Add flat amounts to production
5. **Upgrades (Percentage)** - Increase production by a percentage
6. **Prestige/Reset** - Voluntary reset for permanent bonuses
7. **Multi-Layer Prestige** - Multiple prestige tiers (Ascension -> Transcendence -> Reality)
8. **Unlocks/Milestones** - Automatic bonuses at ownership/progress thresholds
9. **Achievements** - Goal-based rewards, sometimes mechanically meaningful
10. **Multiple Currencies** - Separate economies with different earning/spending rules
11. **Resource Consumption** - Generators that require input resources
12. **Resource Conversion** - Transform one resource into another
13. **Automation/Managers** - Remove manual interaction requirements
14. **Tick/Cycle-Based Production** - Discrete production cycles with start/complete
15. **Continuous Production** - Per-second rate applied via delta time
16. **Probability/Critical Hits** - Random bonus production events
17. **Random Events** - Time-based spawns rewarding active players (Golden Cookies)
18. **Offline Progression** - Accumulate resources while not playing
19. **Time Skips** - Jump forward in production time (premium or ad-rewarded)
20. **Premium Multipliers** - Permanent or temporary boosts from IAP
21. **Premium Currency** - Secondary currency earned slowly or bought with real money
22. **Ad-Rewarded Boosts** - Temporary multipliers from watching ads
23. **Synergies** - Cross-system interactions that reward diverse investment
24. **Challenges/Restrictions** - Special runs with limitations for unique rewards
25. **Events** - Time-limited content with separate economies
26. **Big Number Systems** - Handling numbers beyond standard numeric limits
27. **Gacha/Random Rewards** - Randomized reward systems (hero summons, loot boxes)
28. **Prestige Currency Spending** - Opportunity cost: spend prestige currency on upgrades vs keep passive bonus
29. **Cost Reduction** - Upgrades that reduce generator costs (Discount Managers in AdCap)
30. **Cycle Time Reduction** - Upgrades that speed up production cycles
31. **Conditional/Situational Bonuses** - Multipliers active only under certain conditions
32. **Buff Stacking/Combos** - Multiple temporary effects combining multiplicatively

---

## Sources

- [The Math of Idle Games, Part I - Kongregate](https://blog.kongregate.com/the-math-of-idle-games-part-i/)
- [The Math of Idle Games, Part II - Kongregate](https://blog.kongregate.com/the-math-of-idle-games-part-ii/)
- [The Math of Idle Games, Part III - Kongregate](https://blog.kongregate.com/the-math-of-idle-games-part-iii/)
- [The Math Behind Idle Games - GameAnalytics](https://gameanalytics.com/blog/idle-game-mathematics/)
- [Math - the backbone of Idle Games - Medium](https://medvescekmurovec.medium.com/math-the-backbone-of-idle-games-part-1-f46b54706cf1)
- [Idle vs Incremental vs Tycoon - Medium](https://medium.com/tindalos-games/idle-vs-incremental-vs-tycoon-understanding-the-core-mechanics-f12d62f4b9f7)
- [Top 7 Idle Game Mechanics - Mobile Free To Play](https://mobilefreetoplay.com/top-7-idle-game-mechanics/)
- [Idle Game Design Principles - Eric Guan](https://ericguan.substack.com/p/idle-game-design-principles)
- [How to Design Idle Games - Machinations.io](https://machinations.io/articles/idle-games-and-how-to-design-them)
- [Passive Resource Systems in Idle Games - Adrian Crook](https://adriancrook.com/passive-resource-systems-in-idle-games/)
- [Idle Games: Mechanics and Monetization - Computools](https://computools.com/idle-games-the-mechanics-and-monetization-of-self-playing-games/)
- [Idle Games: Mechanics and Monetization - GDC Vault](https://www.gdcvault.com/play/1022065/Idle-Games-The-Mechanics-and)
- [AdVenture Capitalist Wiki - Angel Investors](https://adventure-capitalist.fandom.com/wiki/Angel_Investors)
- [AdVenture Capitalist Wiki - Managers](https://adventure-capitalist.fandom.com/wiki/Managers)
- [AdVenture Capitalist Wiki - Businesses](https://adventure-capitalist.fandom.com/wiki/Businesses)
- [AdVenture Capitalist Wiki - Upgrades](https://adventure-capitalist.fandom.com/wiki/Upgrades)
- [AdVenture Capitalist Wiki - Cash Upgrades](https://adventure-capitalist.fandom.com/wiki/Cash_Upgrades)
- [AdVenture Capitalist Wiki - Angel Upgrades](https://adventure-capitalist.fandom.com/wiki/Angel_Upgrades)
- [AdVenture Capitalist Wiki - Gold Multipliers](https://adventure-capitalist.fandom.com/wiki/Gold_Multipliers)
- [Cookie Clicker Wiki - Ascension](https://cookieclicker.fandom.com/wiki/Ascension)
- [Cookie Clicker Wiki - Heavenly Chips](https://cookieclicker.fandom.com/wiki/Heavenly_Chips)
- [Clicker Heroes - Transcendence](https://clickerheroes.fandom.com/wiki/Transcendence)
- [Clicker Heroes - Hero Souls Guide](https://blog.clickerheroes.com/clicker-heroes-hero-souls-complete-guide-to-power-up/)
- [Clicker Heroes - Transcendence Guide](https://blog.clickerheroes.com/clicker-heroes-transcendence-guide-outsiders-souls-explained/)
- [Incremental Game - Wikipedia](https://en.wikipedia.org/wiki/Incremental_game)
- [Guide to Incrementals - The Paper Pilot](https://paperpilot.dev/garden/guide-to-incrementals/defining-the-genre)
- [Idle Game - TV Tropes](https://tvtropes.org/pmwiki/pmwiki.php/Main/IdleGame)
- [Idle Game Worksheets - Internet Archive](https://archive.org/details/idlegameworksheets)
