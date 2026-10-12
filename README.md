# VOOL reports

This is where bug reports and wrong-answer reports from the VOOL app land. Everything here is public.

## How to send a report

You don't need to write anything by hand. In VOOL:

- **Wrong answer:** press **Report** (or 👎) under the answer, or highlight the wrong part and press **Report**.
- **Something broke:** open the menu and choose **Report a problem**.

VOOL builds the report on your computer, shows you the exact text, and waits for you to approve it.
Then **Open on GitHub** brings you to a filled-in page here. Read it once more and press **Submit**.
VOOL itself sends nothing over the network.

No GitHub account? Use **Copy report** or **Save a local copy** in VOOL instead.

## What a report contains

- What went wrong, in your words.
- For a wrong answer: the part you highlighted (or the whole answer). Your question is left out unless you tick the box.
- Your computer's shape: OS version, chip, memory, GPU, local model server version.
- A short health check: is the local model server answering, free disk space (as a range).
- The answer's receipt: model, provider, tokens, time, which steps ran, error codes. Never the content of those steps.

## What is removed before you even see it

Keys, passwords, tokens, PINs and one-time codes, card numbers, bank numbers (IBAN), phone numbers,
email addresses, wallet addresses, your user name, your computer name, folder paths with your name in
them, and the personal details you saved in VOOL's profile.

VOOL can't recognise every name or private detail you typed yourself, so please read the preview
before you approve it.

## If something private got through

Every new or edited report is checked again here. If the check finds a key, password, card number or
similar, it masks it and marks the report `needs-scrub` so a maintainer clears it from the edit
history. You can also edit or close your own report at any time.

Security problems: please **don't** post them here. Use
[private vulnerability reporting](https://github.com/Parad0x-Labs/vool/security/advisories/new).

## Labels

| Label | Meaning |
| --- | --- |
| `wrong-answer` | VOOL answered something wrong, outdated, unsafe, or not what was asked |
| `bug` | Something in the app broke |
| `from-app` | Sent through VOOL's report button (it carries a report fingerprint) |
| `needs-scrub` | The automatic check masked something private; a maintainer clears the history |
| `needs-info` | We need more from the reporter; closes after 21 quiet days |
| `duplicate` | Same fingerprint as an earlier report |
| `confirmed` | Reproduced by a maintainer |
| `fixed` | Fixed in a release |

## For maintainers

- `bug-report-fingerprint:` at the end of each report groups the same problem. Search for it to find repeats.
- `.github/workflows/scrub.yml` re-checks every opened or edited report, masks what it finds, labels it,
  and flags repeats.
- `.github/workflows/labels.yml` creates the labels above (run it once from the Actions tab).
- After a `needs-scrub` report, delete the old revision from the issue's edit history (the "edited" menu).
