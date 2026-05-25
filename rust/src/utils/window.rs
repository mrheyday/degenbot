//! Time-bounded sliding window of recent elements.
//!
//! Ported from `ava-labs/avalanchego` `utils/window/window.go`
//! (BSD-licensed). Elements expire once they have been in the window
//! longer than `ttl`; the window also caps at `max_size`, and never
//! shrinks below `min_size` on time-expiry alone.
//!
//! Time is supplied explicitly as a monotonic [`Instant`] so the window is
//! deterministic under test. Used by the monitor for stale-feed detection.

use std::collections::VecDeque;
use std::time::{Duration, Instant};

struct Node<T> {
    value: T,
    entry_time: Instant,
}

/// A sliding window of recent `T` values.
pub struct Window<T> {
    ttl: Duration,
    max_size: usize,
    min_size: usize,
    elements: VecDeque<Node<T>>,
}

impl<T> Window<T> {
    /// Create a window holding at most `max_size` elements, expiring those
    /// older than `ttl` — but never expiring below `min_size` elements.
    pub fn new(ttl: Duration, max_size: usize, min_size: usize) -> Self {
        Self {
            ttl,
            max_size,
            min_size,
            elements: VecDeque::new(),
        }
    }

    /// Append `value`, evict expired elements, and enforce `max_size`.
    pub fn add(&mut self, value: T, now: Instant) {
        self.elements.push_back(Node {
            value,
            entry_time: now,
        });
        self.remove_stale(now);
        if self.elements.len() > self.max_size {
            self.elements.pop_front();
        }
    }

    /// The oldest live element, or `None` if the window is empty.
    pub fn oldest(&mut self, now: Instant) -> Option<&T> {
        self.remove_stale(now);
        self.elements.front().map(|node| &node.value)
    }

    /// The number of live elements.
    pub fn len(&mut self, now: Instant) -> usize {
        self.remove_stale(now);
        self.elements.len()
    }

    /// Whether the window holds no live elements.
    pub fn is_empty(&mut self, now: Instant) -> bool {
        self.len(now) == 0
    }

    /// Drop elements older than `ttl` from the front. Entry times are
    /// strictly increasing, so the first live element ends the scan.
    fn remove_stale(&mut self, now: Instant) {
        while self.elements.len() > self.min_size {
            match self.elements.front() {
                Some(node) if now.duration_since(node.entry_time) > self.ttl => {
                    self.elements.pop_front();
                }
                _ => return,
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn evicts_elements_past_the_ttl() {
        let start = Instant::now();
        let mut window: Window<u64> = Window::new(Duration::from_secs(10), 100, 0);
        window.add(1, start);
        window.add(2, start + Duration::from_secs(1));
        assert_eq!(window.len(start + Duration::from_secs(2)), 2);
        // 11s after the first element — it has expired, the second has not.
        assert_eq!(window.len(start + Duration::from_secs(11)), 1);
        assert_eq!(window.oldest(start + Duration::from_secs(11)), Some(&2));
        // Past both TTLs — the window drains.
        assert!(window.is_empty(start + Duration::from_secs(30)));
    }

    #[test]
    fn caps_at_max_size() {
        let now = Instant::now();
        let mut window: Window<u64> = Window::new(Duration::from_secs(3600), 3, 0);
        for value in 0..10 {
            window.add(value, now);
        }
        assert_eq!(window.len(now), 3);
        // The three most-recent values survive; the oldest is value 7.
        assert_eq!(window.oldest(now), Some(&7));
    }

    #[test]
    fn min_size_holds_elements_against_ttl_expiry() {
        let start = Instant::now();
        let mut window: Window<u64> = Window::new(Duration::from_secs(1), 100, 2);
        window.add(1, start);
        window.add(2, start + Duration::from_secs(1));
        window.add(3, start + Duration::from_secs(2));
        // Long past every TTL, but min_size = 2 keeps the two newest.
        assert_eq!(window.len(start + Duration::from_secs(1000)), 2);
    }

    #[test]
    fn empty_window_has_no_oldest() {
        let now = Instant::now();
        let mut window: Window<u64> = Window::new(Duration::from_secs(10), 10, 0);
        assert!(window.oldest(now).is_none());
        assert!(window.is_empty(now));
    }
}
