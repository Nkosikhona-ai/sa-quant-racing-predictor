# ComputaForm Data Dictionary Audit Report
## Phase 2 -- Validation and Schema Engineering
Source PDF: debug_uploaded.pdf | Date: 2026-08-11 | Extractor: v6.0

## 1. Extraction Summary
Races: 8 | Horses: 69 | Confidence: 100% | Engine: PyMuPDF

## 2. Race-Level Field Coverage
| Field | Normalized Name | Type | ML | Leakage | Filled | Pct | Status |
|---|---|---|---|---|---|---|---|
| Race number | race_number | integer | Y | PRE_RACE | 8/8 | 100% | EXTRACTED |
| Venue | venue | string | Y | PRE_RACE | 8/8 | 100% | EXTRACTED |
| Surface | surface | string | Y | PRE_RACE | 8/8 | 100% | EXTRACTED |
| Distance | distance_m | integer | Y | PRE_RACE | 8/8 | 100% | EXTRACTED |
| Race time | race_time | string | N | PRE_RACE | 8/8 | 100% | EXTRACTED |
| Stake | stake_zar | integer | Y | PRE_RACE | 8/8 | 100% | EXTRACTED |
| Race ref | race_ref | integer | Y | PRE_RACE | 8/8 | 100% | EXTRACTED |
| Betting leg | betting_leg | string | N | PRE_RACE | 5/8 | 62% | PARTIAL |
| Race class | race_class | string | Y | PRE_RACE | 0/8 | 0% | NOT_EXTRACTED |
| Meeting date | meeting_date | string | N | PRE_RACE | 8/8 | 100% | EXTRACTED |

## 3. Horse-Level Field Coverage
| Field | Normalized Name | Type | ML | Leakage | Filled | Pct | Status |
|---|---|---|---|---|---|---|---|
| Horse name | horse_name | string | N | PRE_RACE | 69/69 | 100% | EXTRACTED |
| Saddle number | saddle_number | integer | N | PRE_RACE | 69/69 | 100% | EXTRACTED |
| Draw | draw | integer | Y | PRE_RACE | 69/69 | 100% | EXTRACTED |
| Weight | weight_kg | float | Y | PRE_RACE | 69/69 | 100% | EXTRACTED |
| Jockey | jockey | string | Y | PRE_RACE | 69/69 | 100% | EXTRACTED |
| Trainer | trainer | string | Y | PRE_RACE | 0/69 | 0% | NOT_EXTRACTED |
| Merit Rating | merit_rating | integer | Y | PRE_RACE | 65/69 | 94% | EXTRACTED |
| Headgear | headgear_code | string | Y | PRE_RACE | 39/69 | 56% | PARTIAL |
| F/B fractional | forecast_odds_fractional | string | Y | MARKET | 69/69 | 100% | EXTRACTED |
| F/B decimal | forecast_odds_decimal | float | Y | MARKET | 69/69 | 100% | EXTRACTED |
| Market odds | market_odds | float | Y | MARKET | 69/69 | 100% | EXTRACTED |
| Is apprentice | is_apprentice | boolean | Y | PRE_RACE | 12/69 | 17% | PARTIAL (correct) |
| Sire | sire | string | Y | PRE_RACE | 0/69 | 0% | NOT_EXTRACTED |
| Dam | dam | string | N | PRE_RACE | 0/69 | 0% | NOT_EXTRACTED |
| Dam sire | dam_sire | string | N | PRE_RACE | 0/69 | 0% | NOT_EXTRACTED |
| Age | age | integer | Y | PRE_RACE | 0/69 | 0% | NOT_EXTRACTED |
| Sex | sex | string | Y | PRE_RACE | 0/69 | 0% | NOT_EXTRACTED |
| Colour | colour | string | N | PRE_RACE | 0/69 | 0% | NOT_EXTRACTED |
| Owner | owner | string | N | PRE_RACE | 0/69 | 0% | NOT_EXTRACTED |
| Breeder | breeder | string | N | PRE_RACE | 0/69 | 0% | NOT_EXTRACTED |
| Career runs | career_runs | integer | Y | HISTORICAL | 68/69 | 98% | EXTRACTED |
| Career wins | career_wins | integer | Y | HISTORICAL | 40/69 | 57% | PARTIAL |
| Career thirds | career_thirds | integer | Y | HISTORICAL | 51/69 | 73% | PARTIAL |
| F3 pct | f3_pct | integer | Y | HISTORICAL | 54/69 | 78% | PARTIAL |
| Days since last race | days_since_last_race | integer | Y | PRE_RACE | 0/69 | 0% | NOT_EXTRACTED |
| Days since last win | days_since_last_win | integer | Y | PRE_RACE | 0/69 | 0% | NOT_EXTRACTED |
| CF Rate | cf_rate | integer | Y | PRE_RACE | 0/69 | 0% | NOT_EXTRACTED |
| Career earnings | career_earnings_zar | integer | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| Season stats | season_stats_current | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| J+H stats | jockey_horse_stats | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| J+T stats | jockey_trainer_stats | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| Surface stats turf | surface_stats_turf | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| Course stats | course_stats | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| Going good | going_stats_good | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| Going wet | going_stats_wet | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| Distance stats | distance_stats | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| C and D stats | course_distance_stats | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| Headgear stats | headgear_stats | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| Dcat stats | distance_category_stats | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| Rest 14 plus | rest_14_plus_stats | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| Class stats | class_stats | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| WPR | wpr | object | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| Best vs Average | best_vs_average | float | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| Speed rating | speed_rating_current | integer | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |
| Recent rating | recent_rating | integer | Y | HISTORICAL | 0/69 | 0% | NOT_EXTRACTED |

## 4. HistoricalRace Coverage
ALL 25 hist_* fields are NOT YET EXTRACTED (parser reads aggregated totals only, not individual rows)
Fields: hist_date, hist_venue_code, hist_going, hist_race_class, hist_stake_zar,
hist_ability_rating, hist_distance_m, hist_merit_rating, hist_jockey, hist_weight_kg,
hist_draw, hist_field_size, hist_opening_odds, hist_starting_price, hist_800m_position,
hist_400m_position, hist_finish_position, hist_defeat_margin_lengths, hist_winner_name,
hist_winning_time_sec, hist_400f_time_sec, hist_rail_position, hist_adjusted_time_per_metre,
hist_speed_rating, hist_comment

## 5. Coverage Summary
| Category | Total | Extracted | Partial | Not Extracted |
|---|---|---|---|---|
| Race-level | 10 | 9 | 1 | 1 |
| Horse-level | 48 | 10 | 5 | 33 |
| HistoricalRace | 25 | 0 | 0 | 25 |
| TOTAL | 83 | 19 | 6 | 59 |

## 6. Leakage Classification
| Class | Count | Allowed |
|---|---|---|
| PRE_RACE | 35 | YES |
| HISTORICAL | 52 | YES |
| MARKET | 3 | Caution |
| TARGET | 1 | NO (output only) |
| POST_RACE_LEAKAGE | 6 | NEVER |
| TOTAL | 97 | -- |

## 7. Confirmed Safe ML Features (Extracted)
draw, weight_kg, jockey (encode), merit_rating, forecast_odds_decimal,
career_runs, venue, surface, distance_m, stake_zar

## 8. High-Value Unextracted Fields (Phase 3 Priority)
HIGH: trainer, sire, age, sex, days_since_last_race, days_since_last_win,
season_stats_current, course_stats, going_stats_good, going_stats_wet,
distance_stats, course_distance_stats, jockey_horse_stats, jockey_trainer_stats,
best_vs_average, wpr, class_stats, all hist_* rows
MEDIUM: cf_rate, headgear_code, rest_14_plus_stats, career_earnings_zar,
surface_stats_turf, headgear_stats, distance_category_stats

## 9. Fields That Must NEVER Be Used as Pre-Race Inputs
today_finish_position    TARGET / POST_RACE_LEAKAGE
today_starting_price     POST_RACE_LEAKAGE
today_winning_time       POST_RACE_LEAKAGE
today_defeat_margin      POST_RACE_LEAKAGE
today_speed_rating       POST_RACE_LEAKAGE
today_ability_rating     POST_RACE_LEAKAGE

## 10. Fields Requiring Verification
headgear_code (code mapping), cf_rate (structure), wpr (formula),
H/Av column (meaning), SH column (meaning), W/R column (meaning),
CMR/HMR (venue archive), hist_field_size_grade, shoes, trainer (line), purchase_price_zar

## 11. Abbreviation Registry Summary
CONFIRMED HIGH: 38 | MEDIUM: 4 | REQUIRES_VERIFICATION: 7 | TOTAL: 49

Generated from debug_uploaded.pdf on 2026-08-11.
No application code was modified.
Next phase: Phase 3 -- Parser Enhancement for HIGH-priority unextracted fields.