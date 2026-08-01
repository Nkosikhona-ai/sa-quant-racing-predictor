/**
 * SA Quant Racing — Race Data (v3.9)
 * South African tracks, race cards, horses, and betting history
 */

// ─── SOUTH AFRICAN TRACKS ─────────────────────────────────────────────────────
const SA_TRACKS = [
  { id: 'turffontein', name: 'Turffontein', city: 'Johannesburg', province: 'Gauteng', surface: 'Turf', distances: [1000, 1200, 1400, 1600, 1800, 2000, 2400, 3200] },
  { id: 'kenilworth',  name: 'Kenilworth',  city: 'Cape Town',    province: 'Western Cape', surface: 'Turf', distances: [1000, 1200, 1400, 1600, 1800, 2000, 2400] },
  { id: 'greyville',   name: 'Greyville',   city: 'Durban',       province: 'KwaZulu-Natal', surface: 'Polytrack', distances: [1000, 1200, 1400, 1600, 1800, 2000] },
  { id: 'scottsville', name: 'Scottsville', city: 'Pietermaritzburg', province: 'KwaZulu-Natal', surface: 'Turf', distances: [1000, 1200, 1400, 1600] },
  { id: 'vaal',        name: 'Vaal',        city: 'Vereeniging',  province: 'Gauteng', surface: 'Turf', distances: [1000, 1200, 1400, 1600, 1800, 2000] },
  { id: 'durbanville', name: 'Durbanville', city: 'Cape Town',    province: 'Western Cape', surface: 'Turf', distances: [1000, 1250, 1400, 1600, 1800, 2000] },
  { id: 'fairview',    name: 'Fairview',    city: 'Gqeberha',     province: 'Eastern Cape', surface: 'Turf', distances: [1000, 1200, 1400, 1600, 1800, 2000, 2400] }
];

// ─── TODAY'S RACES ─────────────────────────────────────────────────────────────
const TODAY_RACES = [
  {
    id: 'r1', raceNum: 1, track: 'Turffontein', grade: 'Maiden Plate', distance: 1000, surface: 'Turf',
    going: 'Good', time: '11:30', prize: 'R 75,000', status: 'completed',
    runners: [
      { no: 1,  name: 'Fast Flyer',     jockey: 'W. Marwing',    trainer: 'S. Tarry',     weight: 60.0, barrier: 3, form: '2-1-3-1-2', runs: 18, speedRating: 88, classRating: 82, goingPref: 92, distPref: 78, jockeyRating: 91, odds: 2.80, modelScore: 0, finish: 1 },
      { no: 2,  name: 'Cape Glory',     jockey: 'R. Fourie',     trainer: 'M. de Kock',   weight: 58.5, barrier: 7, form: '1-2-1-3-1', runs: 22, speedRating: 92, classRating: 88, goingPref: 85, distPref: 90, jockeyRating: 88, odds: 3.20, modelScore: 0, finish: 2 },
      { no: 3,  name: 'Silver Storm',   jockey: 'K. de Melo',    trainer: 'J. Snaith',    weight: 57.0, barrier: 1, form: '3-4-2-1-1', runs: 15, speedRating: 85, classRating: 79, goingPref: 88, distPref: 82, jockeyRating: 85, odds: 4.50, modelScore: 0, finish: 3 },
      { no: 4,  name: 'Durban Queen',   jockey: 'A. Fortune',    trainer: 'D. Kannemeyer',weight: 56.5, barrier: 4, form: '5-3-4-2-5', runs: 20, speedRating: 78, classRating: 75, goingPref: 72, distPref: 70, jockeyRating: 78, odds: 8.00, modelScore: 0, finish: 4 },
      { no: 5,  name: 'Vaal Rocket',    jockey: 'C. Murray',     trainer: 'J. van Zyl',   weight: 59.0, barrier: 6, form: '1-1-3-5-3', runs: 12, speedRating: 83, classRating: 80, goingPref: 78, distPref: 85, jockeyRating: 82, odds: 6.00, modelScore: 0, finish: 5 }
    ]
  },
  {
    id: 'r2', raceNum: 2, track: 'Turffontein', grade: 'Stakes', distance: 1200, surface: 'Turf',
    going: 'Good to Firm', time: '12:05', prize: 'R 150,000', status: 'completed',
    runners: [
      { no: 1,  name: 'Gold Digger',    jockey: 'W. Marwing',    trainer: 'S. Tarry',     weight: 60.0, barrier: 5, form: '1-1-2-1-1', runs: 14, speedRating: 96, classRating: 94, goingPref: 95, distPref: 94, jockeyRating: 91, odds: 1.80, modelScore: 0, finish: 1 },
      { no: 2,  name: 'Highveld Hero',  jockey: 'R. Fourie',     trainer: 'M. de Kock',   weight: 59.0, barrier: 2, form: '2-3-1-2-2', runs: 10, speedRating: 90, classRating: 88, goingPref: 88, distPref: 90, jockeyRating: 88, odds: 3.50, modelScore: 0, finish: 2 },
      { no: 3,  name: 'Karoo Wind',     jockey: 'K. de Melo',    trainer: 'C. Laird',     weight: 57.5, barrier: 8, form: '4-2-3-3-4', runs: 16, speedRating: 84, classRating: 82, goingPref: 80, distPref: 85, jockeyRating: 85, odds: 5.50, modelScore: 0, finish: 3 },
      { no: 4,  name: 'Joburg Jet',     jockey: 'A. Fortune',    trainer: 'J. Snaith',    weight: 58.0, barrier: 3, form: '3-1-4-1-3', runs: 11, speedRating: 88, classRating: 86, goingPref: 86, distPref: 88, jockeyRating: 78, odds: 4.20, modelScore: 0, finish: 4 },
      { no: 5,  name: 'Ubuntu Star',    jockey: 'C. Murray',     trainer: 'J. van Zyl',   weight: 56.0, barrier: 1, form: '5-4-5-4-5', runs: 8,  speedRating: 72, classRating: 68, goingPref: 70, distPref: 72, jockeyRating: 82, odds: 18.0, modelScore: 0, finish: 5 }
    ]
  },
  {
    id: 'r3', raceNum: 3, track: 'Turffontein', grade: 'Listed', distance: 1400, surface: 'Turf',
    going: 'Good', time: '12:40', prize: 'R 250,000', status: 'completed',
    runners: [
      { no: 1,  name: 'Mandela Spirit', jockey: 'W. Marwing',    trainer: 'S. Tarry',     weight: 60.0, barrier: 2, form: '1-2-1-1-2', runs: 19, speedRating: 94, classRating: 92, goingPref: 90, distPref: 96, jockeyRating: 91, odds: 2.20, modelScore: 0, finish: 2 },
      { no: 2,  name: 'Thunder Reef',   jockey: 'R. Fourie',     trainer: 'M. de Kock',   weight: 59.5, barrier: 4, form: '2-1-2-3-1', runs: 15, speedRating: 93, classRating: 91, goingPref: 89, distPref: 92, jockeyRating: 88, odds: 2.60, modelScore: 0, finish: 1 },
      { no: 3,  name: 'Cape Crusader',  jockey: 'K. de Melo',    trainer: 'C. Laird',     weight: 58.0, barrier: 6, form: '3-3-4-2-3', runs: 25, speedRating: 86, classRating: 83, goingPref: 84, distPref: 88, jockeyRating: 85, odds: 6.00, modelScore: 0, finish: 3 },
      { no: 4,  name: 'Reef Diamond',   jockey: 'A. Fortune',    trainer: 'J. Snaith',    weight: 57.0, barrier: 1, form: '4-4-3-4-4', runs: 14, speedRating: 79, classRating: 76, goingPref: 76, distPref: 80, jockeyRating: 78, odds: 11.0, modelScore: 0, finish: 4 },
      { no: 5,  name: 'Soweto Sunrise', jockey: 'C. Murray',     trainer: 'J. van Zyl',   weight: 58.5, barrier: 7, form: '2-2-3-1-4', runs: 13, speedRating: 89, classRating: 85, goingPref: 88, distPref: 84, jockeyRating: 82, odds: 3.80, modelScore: 0, finish: 5 }
    ]
  },
  {
    id: 'r4', raceNum: 4, track: 'Turffontein', grade: 'Grade 1', distance: 1400, surface: 'Turf',
    going: 'Good', time: '13:20', prize: 'R 500,000', status: 'live',
    runners: [
      { no: 1,  name: 'African Gold',   jockey: 'W. Marwing',    trainer: 'S. Tarry',     weight: 60.0, barrier: 5, form: '1-1-1-2-1', runs: 18, speedRating: 98, classRating: 96, goingPref: 94, distPref: 97, jockeyRating: 91, odds: 1.90, modelScore: 0, finish: null },
      { no: 2,  name: 'Protea Pride',   jockey: 'R. Fourie',     trainer: 'M. de Kock',   weight: 59.5, barrier: 3, form: '2-1-2-1-2', runs: 22, speedRating: 95, classRating: 93, goingPref: 92, distPref: 95, jockeyRating: 88, odds: 2.80, modelScore: 0, finish: null },
      { no: 3,  name: 'Silver Storm',   jockey: 'K. de Melo',    trainer: 'J. Snaith',    weight: 58.5, barrier: 1, form: '3-2-3-2-1', runs: 15, speedRating: 92, classRating: 90, goingPref: 91, distPref: 93, jockeyRating: 85, odds: 4.50, modelScore: 0, finish: null },
      { no: 4,  name: 'Highveld King',  jockey: 'A. Fortune',    trainer: 'D. Kannemeyer',weight: 60.0, barrier: 8, form: '1-3-1-3-3', runs: 20, speedRating: 90, classRating: 91, goingPref: 88, distPref: 90, jockeyRating: 78, odds: 5.00, modelScore: 0, finish: null },
      { no: 5,  name: 'Vaal Champion',  jockey: 'C. Murray',     trainer: 'J. van Zyl',   weight: 57.5, barrier: 2, form: '4-4-2-4-2', runs: 12, speedRating: 88, classRating: 87, goingPref: 86, distPref: 88, jockeyRating: 82, odds: 6.00, modelScore: 0, finish: null },
      { no: 6,  name: 'Dragon Heart',   jockey: 'L. Hewitson',   trainer: 'G. Azzie',     weight: 58.0, barrier: 6, form: '5-2-4-5-4', runs: 16, speedRating: 84, classRating: 83, goingPref: 82, distPref: 84, jockeyRating: 86, odds: 8.50, modelScore: 0, finish: null },
      { no: 7,  name: 'Cape Legend',    jockey: 'F. Schoeman',   trainer: 'J. de Beer',   weight: 56.5, barrier: 4, form: '3-5-5-3-5', runs: 10, speedRating: 80, classRating: 78, goingPref: 79, distPref: 80, jockeyRating: 80, odds: 14.0, modelScore: 0, finish: null },
      { no: 8,  name: 'Ubuntu Prince',  jockey: 'B. Fayd\'herbe',trainer: 'P. Matchett',  weight: 59.0, barrier: 7, form: '2-3-3-4-3', runs: 19, speedRating: 87, classRating: 85, goingPref: 87, distPref: 86, jockeyRating: 84, odds: 7.50, modelScore: 0, finish: null }
    ]
  },
  {
    id: 'r5', raceNum: 5, track: 'Turffontein', grade: 'Grade 3', distance: 1600, surface: 'Turf',
    going: 'Good', time: '14:00', prize: 'R 300,000', status: 'upcoming',
    runners: [
      { no: 1,  name: 'Gauteng Gold',   jockey: 'W. Marwing',    trainer: 'S. Tarry',     weight: 59.5, barrier: 3, form: '2-1-1-1-2', runs: 17, speedRating: 93, classRating: 91, goingPref: 90, distPref: 95, jockeyRating: 91, odds: 2.30, modelScore: 0, finish: null },
      { no: 2,  name: 'River Rush',     jockey: 'R. Fourie',     trainer: 'M. de Kock',   weight: 60.0, barrier: 1, form: '1-2-3-2-1', runs: 20, speedRating: 91, classRating: 89, goingPref: 89, distPref: 93, jockeyRating: 88, odds: 3.00, modelScore: 0, finish: null },
      { no: 3,  name: 'Zebra Stripes',  jockey: 'K. de Melo',    trainer: 'J. Snaith',    weight: 57.0, barrier: 5, form: '3-3-2-3-3', runs: 14, speedRating: 85, classRating: 83, goingPref: 83, distPref: 87, jockeyRating: 85, odds: 5.50, modelScore: 0, finish: null },
      { no: 4,  name: 'Savanna Wind',   jockey: 'A. Fortune',    trainer: 'D. Kannemeyer',weight: 58.0, barrier: 2, form: '4-4-4-4-4', runs: 28, speedRating: 78, classRating: 76, goingPref: 76, distPref: 78, jockeyRating: 78, odds: 12.0, modelScore: 0, finish: null },
      { no: 5,  name: 'Rand Racer',     jockey: 'C. Murray',     trainer: 'J. van Zyl',   weight: 58.5, barrier: 6, form: '1-1-4-1-3', runs: 11, speedRating: 88, classRating: 86, goingPref: 85, distPref: 89, jockeyRating: 82, odds: 4.50, modelScore: 0, finish: null }
    ]
  },
  {
    id: 'r6', raceNum: 1, track: 'Kenilworth', grade: 'Maiden Plate', distance: 1000, surface: 'Turf',
    going: 'Firm', time: '14:30', prize: 'R 80,000', status: 'upcoming',
    runners: [
      { no: 1,  name: 'Table Mountain', jockey: 'A. Marcus',     trainer: 'J. Ramsden',   weight: 58.0, barrier: 2, form: '0-0-2-1-2', runs: 5,  speedRating: 82, classRating: 78, goingPref: 90, distPref: 85, jockeyRating: 80, odds: 3.80, modelScore: 0, finish: null },
      { no: 2,  name: 'Winelands Way',  jockey: 'M. Yeni',       trainer: 'A. Laird',     weight: 57.0, barrier: 4, form: '1-1-1-3-2', runs: 12, speedRating: 88, classRating: 84, goingPref: 88, distPref: 88, jockeyRating: 76, odds: 2.60, modelScore: 0, finish: null },
      { no: 3,  name: 'Simonsberg',     jockey: 'G. Lerena',     trainer: 'M. Roberts',   weight: 59.0, barrier: 1, form: '2-3-3-2-1', runs: 9,  speedRating: 84, classRating: 80, goingPref: 85, distPref: 82, jockeyRating: 85, odds: 4.20, modelScore: 0, finish: null },
      { no: 4,  name: 'Ocean Breeze',   jockey: 'C. Maujean',    trainer: 'P. Strydom',   weight: 56.5, barrier: 3, form: '3-2-4-4-3', runs: 10, speedRating: 79, classRating: 76, goingPref: 86, distPref: 80, jockeyRating: 78, odds: 6.50, modelScore: 0, finish: null },
      { no: 5,  name: 'Stellenbosch',   jockey: 'B. Fayd\'herbe',trainer: 'J. de Beer',   weight: 58.5, barrier: 5, form: '4-4-2-1-4', runs: 15, speedRating: 80, classRating: 77, goingPref: 83, distPref: 84, jockeyRating: 84, odds: 7.00, modelScore: 0, finish: null }
    ]
  },
  {
    id: 'r7', raceNum: 1, track: 'Greyville', grade: 'Stakes', distance: 1200, surface: 'Polytrack',
    going: 'Standard', time: '10:00', prize: 'R 100,000', status: 'completed',
    runners: [
      { no: 1,  name: 'Zulu Warrior',   jockey: 'K. Nkosi',      trainer: 'A. Drier',     weight: 59.0, barrier: 3, form: '1-2-1-1-2', runs: 14, speedRating: 87, classRating: 84, goingPref: 88, distPref: 86, jockeyRating: 80, odds: 2.90, modelScore: 0, finish: 1 },
      { no: 2,  name: 'Durban Dancer',  jockey: 'P. Strydom',    trainer: 'G. Kotzen',    weight: 58.0, barrier: 1, form: '2-1-3-2-1', runs: 11, speedRating: 85, classRating: 82, goingPref: 85, distPref: 84, jockeyRating: 78, odds: 3.50, modelScore: 0, finish: 2 },
      { no: 3,  name: 'Indian Ocean',   jockey: 'W. Mapelo*',    trainer: 'S. Tarry',     weight: 57.5, barrier: 5, form: '3-3-2-3-3', runs: 8,  speedRating: 80, classRating: 78, goingPref: 82, distPref: 80, jockeyRating: 76, odds: 5.80, modelScore: 0, finish: 3 },
      { no: 4,  name: 'Poly Princess',  jockey: 'T. Drier',      trainer: 'J. Ramsden',   weight: 56.0, barrier: 2, form: '4-4-4-4-4', runs: 21, speedRating: 74, classRating: 72, goingPref: 78, distPref: 76, jockeyRating: 74, odds: 9.00, modelScore: 0, finish: 4 }
    ]
  },
  {
    id: 'r8', raceNum: 8, track: 'Greyville', grade: 'MR 80 Handicap', distance: 1800, surface: 'Polytrack',
    going: 'Standard', time: '15:10', prize: 'R 85,000', status: 'upcoming',
    runners: [
      { no: 1,  name: 'Poly Power',     jockey: 'K. Nkosi',      trainer: 'A. Wright',    weight: 60.0, barrier: 2, form: '2-1-3-4-2', runs: 13, speedRating: 84, classRating: 81, goingPref: 86, distPref: 88, jockeyRating: 80, odds: 3.50, modelScore: 0, finish: null },
      { no: 2,  name: 'Zulu Wizard',    jockey: 'R. Fourie',     trainer: 'G. Kotzen',    weight: 58.5, barrier: 5, form: '1-2-1-5-3', runs: 16, speedRating: 89, classRating: 85, goingPref: 88, distPref: 90, jockeyRating: 88, odds: 2.80, modelScore: 0, finish: null },
      { no: 3,  name: 'Greyville Boy',  jockey: 'W. Mapelo*',    trainer: 'S. Tarry',     weight: 57.0, barrier: 1, form: '4-3-2-2-4', runs: 9,  speedRating: 81, classRating: 78, goingPref: 82, distPref: 84, jockeyRating: 76, odds: 5.50, modelScore: 0, finish: null },
      { no: 4,  name: 'Poly Princess',  jockey: 'T. Drier',      trainer: 'J. Ramsden',   weight: 55.0, barrier: 4, form: '4-4-4-4-4', runs: 21, speedRating: 74, classRating: 72, goingPref: 78, distPref: 76, jockeyRating: 74, odds: 12.0, modelScore: 0, finish: null }
    ]
  }
];

// ─── BET HISTORY ───────────────────────────────────────────────────────────────
const BET_HISTORY_DATA = [
  { date: '2026-06-07', track: 'Turffontein', race: 3, horse: 'Mandela Spirit', type: 'Win', stake: 200, odds: 2.20, result: 'lost',    return: 0 },
  { date: '2026-06-07', track: 'Greyville',   race: 1, horse: 'Zulu Warrior',   type: 'Win', stake: 150, odds: 2.90, result: 'won',     return: 435 },
  { date: '2026-06-07', track: 'Kenilworth',  race: 2, horse: 'Winelands Way',  type: 'Win', stake: 100, odds: 2.60, result: 'won',     return: 260 },
  { date: '2026-06-06', track: 'Turffontein', race: 4, horse: 'African Gold',   type: 'Each Way', stake: 200, odds: 2.10, result: 'won', return: 420 },
  { date: '2026-06-06', track: 'Turffontein', race: 2, horse: 'Gold Digger',    type: 'Win', stake: 300, odds: 1.80, result: 'won',     return: 540 },
  { date: '2026-06-05', track: 'Vaal',        race: 5, horse: 'Rand Flyer',     type: 'Win', stake: 100, odds: 5.50, result: 'lost',    return: 0 },
  { date: '2026-06-05', track: 'Turffontein', race: 1, horse: 'Fast Flyer',     type: 'Win', stake: 150, odds: 2.80, result: 'won',     return: 420 },
  { date: '2026-06-04', track: 'Kenilworth',  race: 3, horse: 'Table Mountain', type: 'Place', stake: 100, odds: 1.60, result: 'won',  return: 160 },
  { date: '2026-06-04', track: 'Greyville',   race: 2, horse: 'Poly Princess',  type: 'Win', stake: 100, odds: 9.00, result: 'lost',    return: 0 },
  { date: '2026-06-03', track: 'Turffontein', race: 3, horse: 'Thunder Reef',   type: 'Win', stake: 250, odds: 2.60, result: 'won',     return: 650 }
];

// ─── ANALYTICS DATA ────────────────────────────────────────────────────────────
const ANALYTICS_DATA = {
  bankrollHistory: [
    { date: '2026-05-09', value: 13500 },
    { date: '2026-05-16', value: 13200 },
    { date: '2026-05-23', value: 14100 },
    { date: '2026-05-30', value: 13860 },
    { date: '2026-06-06', value: 14500 },
    { date: '2026-06-08', value: 14820 }
  ],
  trackROI: {
    labels: ['Turffontein', 'Kenilworth', 'Greyville', 'Scottsville', 'Vaal', 'Durbanville', 'Fairview'],
    data: [22.4, 15.8, 8.1, -4.2, 11.5, 14.2, 9.6]
  },
  edgeDistribution: {
    labels: ['<0%','0-5%','5-10%','10-15%','15-20%','>20%'],
    data: [18, 22, 28, 16, 10, 6]
  },
  distanceStrikeRate: {
    labels: ['1000m','1200m','1400m','1600m','1800m','2000m+'],
    data: [61, 68, 74, 72, 65, 58]
  },
  trackPerformance: [
    { track:'Turffontein', bets:38, wins:26, strikeRate:'68.4%', pnl:'+R 3,520', roi:'+22.4%', bestDist:'1400m', goingPref:'Good' },
    { track:'Kenilworth',  bets:18, wins:12, strikeRate:'66.7%', pnl:'+R 1,140', roi:'+15.8%', bestDist:'1200m', goingPref:'Firm' },
    { track:'Greyville',   bets:12, wins: 8, strikeRate:'66.7%', pnl:'+R 390',   roi:'+8.1%',  bestDist:'1200m', goingPref:'Standard' },
    { track:'Scottsville', bets: 6, wins: 2, strikeRate:'33.3%', pnl:'-R 100',   roi:'-4.2%',  bestDist:'1000m', goingPref:'Good' },
    { track:'Vaal',        bets:14, wins: 9, strikeRate:'64.3%', pnl:'+R 610',   roi:'+11.5%', bestDist:'1400m', goingPref:'Good to Firm' },
    { track:'Durbanville', bets: 8,  wins: 5, strikeRate:'62.5%', pnl:'+R 450',   roi:'+14.2%', bestDist:'1400m', goingPref:'Good' },
    { track:'Fairview',    bets: 10, wins: 6, strikeRate:'60.0%', pnl:'+R 310',   roi:'+9.6%',  bestDist:'1600m', goingPref:'Good' }
  ]
};

// ─── JOCKEY STATS ──────────────────────────────────────────────────────────────
const JOCKEY_RATINGS = {
  'W. Marwing':    91,
  'R. Fourie':     88,
  'K. de Melo':    85,
  'A. Fortune':    78,
  'C. Murray':     82,
  'L. Hewitson':   86,
  'F. Schoeman':   80,
  "B. Fayd'herbe": 84,
  'G. Lerena':     85,
  'A. Marcus':     80,
  'M. Yeni':       76,
  'C. Maujean':    78,
  'K. Nkosi':      80,
  'P. Strydom':    78,
  'W. Mapelo':     76,
  'T. Drier':      74
};
