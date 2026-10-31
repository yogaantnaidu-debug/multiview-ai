// Pure helpers for channel names and URL state. No React here, so the rules
// are easy to read on their own (and the backend re-checks them in Phase 2).

export const MAX_STREAMS = 6

// Twitch logins: 4–25 chars, letters/digits/underscore. Lowercase because
// Twitch treats names case-insensitively, so "XQC" and "xqc" are one stream.
const NAME_RE = /^[a-z0-9_]{4,25}$/

// Accepts "name", "twitch.tv/name" or "https://www.twitch.tv/name/videos".
// Returns the clean channel name, or null if it isn't valid.
export function parseChannel(input) {
  let text = String(input).trim().toLowerCase()
  const match = text.match(/twitch\.tv\/([^/?#]+)/)
  if (match) text = match[1]
  return NAME_RE.test(text) ? text : null
}

// The URL is the only "storage" in Phase 1: ?c=chan1,chan2 rebuilds the grid,
// so a link can be shared and a refresh doesn't lose anything.
// Anything in the URL is user-editable, so it goes through the same validation.
export function readChannelsFromUrl() {
  const raw = new URLSearchParams(window.location.search).get('c') || ''
  const channels = []
  for (const part of raw.split(',')) {
    const name = parseChannel(part)
    if (name && !channels.includes(name) && channels.length < MAX_STREAMS) {
      channels.push(name)
    }
  }
  return channels
}

export function writeChannelsToUrl(channels) {
  const url = new URL(window.location.href)
  // Built by hand so commas stay readable (URLSearchParams would write %2C).
  // Safe because every name already passed NAME_RE.
  url.search = channels.length ? `?c=${channels.join(',')}` : ''
  // replaceState, not pushState: editing the grid shouldn't fill the Back button.
  window.history.replaceState(null, '', url)
}
