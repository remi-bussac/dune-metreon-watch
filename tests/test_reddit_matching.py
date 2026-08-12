"""Reddit matching, pinned against real observed posts.

The two announcements below are the actual posts that told us about the
Aug 18 on-sale, captured from state.json. They are the reason this source
exists, and they arrived ~a day before the news reached the user by other
means -- into an inbox channel that was switched off at the time.

The noise post is also real: it matched only because the old rule searched
the post BODY for the film name, so an Odyssey write-up that happened to
mention Dune 3 somewhere in its text was filed under Dune.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "scripts" / "sources"))

import pytest  # noqa: E402

from sources.reddit_rss import _matches  # noqa: E402

TARGETS = {t["id"]: t for t in json.loads((REPO / "config" / "targets.json").read_text())}
DUNE = TARGETS["dune-part-three"]
ODYSSEY = TARGETS["the-odyssey"]

# (title, body, target, should_fire)  -- all REAL, from state.json
REAL_POSTS = [
    (
        "The next opportunity to get DUNE: PART THREE tickets will arrive in one week on Tuesday",
        "Tickets go on sale Tuesday at 9am PT for the IMAX 70mm screenings.",
        DUNE, True,
    ),
    (
        "The next opportunity to get DUNE: PART THREE tickets happens next week on Tuesday",
        "They go on sale next Tuesday morning.",
        DUNE, True,
    ),
    (
        "Finally saw Odyssey in 70MM, just no credits.",
        "Great print. Also cannot wait for dune 3 tickets to go on sale.",
        DUNE, False,          # film name only in the body -> not about Dune
    ),
]


@pytest.mark.parametrize("title,body,target,want", REAL_POSTS)
def test_real_observed_posts(title, body, target, want):
    assert _matches(title, body, target) is want, title


def test_regression_announcement_matched_via_body_still_fires():
    """Both real announcements name the film in the TITLE but put the
    on-sale wording in the BODY. Requiring both in the title would have
    silenced the single most valuable signal this project has produced."""
    assert _matches(
        "The next opportunity to get DUNE: PART THREE tickets will arrive in one week on Tuesday",
        "Tickets go on sale Tuesday at 9am PT.",
        DUNE,
    )


def test_regression_film_named_only_in_body_is_ignored():
    """A post about something else that mentions the film in passing is not
    news about the film."""
    assert not _matches(
        "Random cinema chat thread",
        "by the way dune 3 tickets go on sale soon",
        DUNE,
    )


def test_film_in_title_but_no_availability_wording_is_ignored():
    assert not _matches(
        "DUNE: PART THREE trailer breakdown",
        "Some thoughts on the cinematography.",
        DUNE,
    )


def test_odyssey_run_extension_still_fires():
    assert _matches(
        "IMAX 70mm showings for THE ODYSSEY are being extended through September 16",
        "",
        ODYSSEY,
    )
