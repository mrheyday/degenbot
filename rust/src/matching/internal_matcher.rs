use crate::matching::price_compat::{clearing_price, fill_amount, is_price_compatible};
use crate::monitor::{MatchCandidate, MatchPair};

pub fn find_matches(outbound: &[MatchCandidate], counters: &[MatchCandidate]) -> Vec<MatchPair> {
    let mut matches = Vec::new();
    for o in outbound {
        for c in counters {
            if !is_price_compatible(o, c) {
                continue;
            }

            let fill = fill_amount(o, c);
            if fill.is_zero() {
                continue;
            }

            matches.push(MatchPair {
                o: o.clone(),
                c: c.clone(),
                fill_amount: fill,
                clearing_price: clearing_price(o, c),
            });
        }
    }
    matches
}

pub fn find_best_match(
    outbound: &[MatchCandidate],
    counters: &[MatchCandidate],
) -> Option<MatchPair> {
    let mut best: Option<MatchPair> = None;
    for m in find_matches(outbound, counters) {
        if let Some(ref b) = best {
            if m.fill_amount > b.fill_amount {
                best = Some(m);
            }
        } else {
            best = Some(m);
        }
    }
    best
}
